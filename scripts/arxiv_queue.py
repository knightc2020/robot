#!/usr/bin/env python3
"""Maintain a durable per-paper queue for the arXiv publishing workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_STATE = Path.home() / ".hermes/state/arxiv-robotics-ledger.json"
DEFAULT_REMOTE_RAW_BASE = "https://raw.githubusercontent.com/knightc2020/robot/master"
DEFAULT_REMOTE_VERIFY_ATTEMPTS = 4
DEFAULT_REMOTE_VERIFY_RETRY_SECONDS = 2.0
VALID_STATUSES = {"unseen", "selected", "published", "skipped", "failed"}
ARXIV_ID_PATTERN = re.compile(r"^(?P<id>\d{4}\.\d{4,5})(?:v(?P<version>\d+))?$")
SLUG_PATTERN = re.compile(r"^arxiv-\d{4}-\d{4,5}$")
ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_arxiv_id(value: str) -> str:
    candidate = value.strip().rstrip("/").split("/")[-1]
    match = ARXIV_ID_PATTERN.fullmatch(candidate)
    if not match:
        raise ValueError(f"Invalid arXiv ID or URL: {value}")
    return match.group("id")


def normalized_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{canonical_arxiv_id(arxiv_id)}"


def element_text(entry: ET.Element, path: str) -> str:
    element = entry.find(path, ATOM_NS)
    if element is None or element.text is None:
        return ""
    return " ".join(element.text.split())


def parse_feed(path: Path) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot()
    papers: list[dict[str, Any]] = []

    for entry in root.findall("atom:entry", ATOM_NS):
        raw_id = element_text(entry, "atom:id")
        arxiv_id = canonical_arxiv_id(raw_id)
        authors = [
            " ".join(name.text.split())
            for author in entry.findall("atom:author", ATOM_NS)
            if (name := author.find("atom:name", ATOM_NS)) is not None and name.text
        ]
        categories = [
            term
            for category in entry.findall("atom:category", ATOM_NS)
            if (term := category.get("term"))
        ]
        primary = entry.find("arxiv:primary_category", ATOM_NS)

        papers.append(
            {
                "arxiv_id": arxiv_id,
                "url": normalized_url(arxiv_id),
                "title": element_text(entry, "atom:title"),
                "abstract": element_text(entry, "atom:summary"),
                "published_at": element_text(entry, "atom:published"),
                "updated_at": element_text(entry, "atom:updated"),
                "authors": authors,
                "categories": categories,
                "primary_category": primary.get("term", "") if primary is not None else "",
            }
        )

    return papers


def empty_ledger() -> dict[str, Any]:
    return {"version": 1, "updated_at": None, "papers": {}}


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_ledger()
    with path.open(encoding="utf-8") as handle:
        ledger = json.load(handle)
    if ledger.get("version") != 1 or not isinstance(ledger.get("papers"), dict):
        raise ValueError(f"Unsupported or invalid ledger: {path}")
    return ledger


def save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = utc_now()
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(ledger, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def ingest(feed: Path, state: Path) -> dict[str, Any]:
    ledger = load_ledger(state)
    now = utc_now()
    added: list[str] = []
    papers = parse_feed(feed)

    for paper in papers:
        arxiv_id = paper["arxiv_id"]
        existing = ledger["papers"].get(arxiv_id)
        if existing is None:
            existing = {
                "status": "unseen",
                "first_seen_at": now,
                "attempts": 0,
            }
            ledger["papers"][arxiv_id] = existing
            added.append(arxiv_id)
        existing.update(paper)
        existing["last_seen_at"] = now

    save_ledger(state, ledger)
    return {
        "feed_count": len(papers),
        "added_count": len(added),
        "added_ids": added,
        "status_counts": dict(Counter(p["status"] for p in ledger["papers"].values())),
    }


def list_candidates(state: Path, statuses: set[str], limit: int) -> list[dict[str, Any]]:
    ledger = load_ledger(state)
    candidates = [
        paper for paper in ledger["papers"].values() if paper.get("status") in statuses
    ]
    candidates.sort(key=lambda paper: paper.get("published_at", ""), reverse=True)
    return candidates[:limit]


def canonical_slug(value: str) -> str:
    """Validate and normalize a canonical research-post slug."""
    slug = value.strip()
    if slug.endswith(".md"):
        slug = slug[:-3]
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(f"Invalid canonical research slug: {value}")
    return slug


def _validate_published_content(content: str, arxiv_id: str, location: str) -> None:
    """Ensure a research brief has the identity fields required for publication."""
    frontmatter = re.match(r"\A---\s*\n(?P<frontmatter>.*?)\n---\s*\n", content, re.DOTALL)
    if frontmatter is None:
        raise ValueError(f"{location} has no valid YAML frontmatter")

    fields = frontmatter.group("frontmatter")
    required = {
        "arxiv_id": arxiv_id,
        "status": "published",
    }
    for field, expected in required.items():
        pattern = rf"^{re.escape(field)}:\s*[\"']?{re.escape(expected)}[\"']?\s*$"
        if re.search(pattern, fields, re.MULTILINE) is None:
            raise ValueError(f"{location} is missing {field}: {expected}")


def verify_published_pair(
    repo_root: Path,
    raw_id: str,
    slug: str,
    remote_base_url: str = DEFAULT_REMOTE_RAW_BASE,
    remote_attempts: int = DEFAULT_REMOTE_VERIFY_ATTEMPTS,
    retry_delay_seconds: float = DEFAULT_REMOTE_VERIFY_RETRY_SECONDS,
) -> dict[str, Any]:
    """Verify the exact bilingual content pair exists locally and on GitHub.

    A ledger entry becomes ``published`` only after the same two files are
    present on the remote master branch. Comparing full contents catches
    partial writes and stale or incorrectly named remote files. The remote is
    retried briefly because GitHub Raw can lag immediately after a push.
    """
    arxiv_id = canonical_arxiv_id(raw_id)
    canonical = canonical_slug(slug)
    root = repo_root.resolve()
    base_url = remote_base_url.rstrip("/")
    if remote_attempts < 1:
        raise ValueError("Remote verification attempts must be at least one")
    if retry_delay_seconds < 0:
        raise ValueError("Remote verification retry delay cannot be negative")

    local_files: list[tuple[Path, str]] = []
    for language in ("cn", "en"):
        relative_path = Path("src") / "content" / language / "research" / f"{canonical}.md"
        local_path = root / relative_path
        if not local_path.is_file():
            raise ValueError(f"Missing local publication file: {local_path}")

        local_content = local_path.read_text(encoding="utf-8")
        _validate_published_content(local_content, arxiv_id, str(local_path))
        local_files.append((relative_path, local_content))

    last_errors: list[str] = []
    for attempt in range(1, remote_attempts + 1):
        errors: list[str] = []
        for relative_path, local_content in local_files:
            remote_url = f"{base_url}/{relative_path.as_posix()}"
            request = Request(remote_url, headers={"User-Agent": "arxiv-robotics-publisher"})
            try:
                with urlopen(request, timeout=20) as response:
                    remote_content = response.read().decode("utf-8")
                _validate_published_content(remote_content, arxiv_id, remote_url)
                if remote_content != local_content:
                    raise ValueError(
                        f"Remote publication content differs from local file: {relative_path}"
                    )
            except HTTPError as error:
                errors.append(f"Remote publication file is unavailable ({error.code}): {remote_url}")
            except URLError as error:
                errors.append(f"Could not verify remote publication file: {remote_url}: {error.reason}")
            except (UnicodeDecodeError, ValueError) as error:
                errors.append(str(error))

        if not errors:
            return {
                "arxiv_id": arxiv_id,
                "slug": canonical,
                "verified_paths": [path.as_posix() for path, _content in local_files],
                "remote_base_url": base_url,
                "remote_attempts": attempt,
            }

        last_errors = errors
        if attempt < remote_attempts:
            time.sleep(retry_delay_seconds)

    raise ValueError(
        f"Remote publication verification failed after {remote_attempts} attempt(s): "
        + "; ".join(last_errors)
    )


def mark_paper(
    state: Path,
    raw_id: str,
    status: str,
    score: int | None,
    reason: str | None,
    slug: str | None,
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    if score is not None and not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100")
    canonical_published_slug = None
    if status == "published":
        if not slug:
            raise ValueError("Published papers require --slug")
        canonical_published_slug = canonical_slug(slug)

    arxiv_id = canonical_arxiv_id(raw_id)
    ledger = load_ledger(state)
    paper = ledger["papers"].get(arxiv_id)
    if paper is None:
        raise KeyError(f"Paper {arxiv_id} is not in the ledger; ingest a feed first")

    paper["status"] = status
    paper["reviewed_at"] = utc_now()
    if score is not None:
        paper["importance_score"] = score
    if reason:
        paper["selection_reason"] = reason
    if slug:
        paper["slug"] = canonical_published_slug or slug
    if status in {"selected", "failed"}:
        paper["attempts"] = int(paper.get("attempts", 0)) + 1
    if status == "published":
        paper["published_to_site_at"] = utc_now()

    save_ledger(state, ledger)
    return {
        "arxiv_id": arxiv_id,
        "status": status,
        "importance_score": paper.get("importance_score"),
        "slug": paper.get("slug"),
    }


def parse_statuses(value: str) -> set[str]:
    statuses = {item.strip() for item in value.split(",") if item.strip()}
    invalid = statuses - VALID_STATUSES
    if invalid:
        raise argparse.ArgumentTypeError(f"Invalid statuses: {', '.join(sorted(invalid))}")
    return statuses


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Add/update papers from an Atom feed")
    ingest_parser.add_argument("--feed", type=Path, required=True)

    list_parser = subparsers.add_parser("list", help="List queued candidates as JSON")
    list_parser.add_argument("--statuses", type=parse_statuses, default={"unseen", "failed"})
    list_parser.add_argument("--limit", type=int, default=30)

    mark_parser = subparsers.add_parser("mark", help="Update editorial/publication state")
    mark_parser.add_argument("--id", required=True)
    mark_parser.add_argument("--status", choices=sorted(VALID_STATUSES), required=True)
    mark_parser.add_argument("--score", type=int)
    mark_parser.add_argument("--reason")
    mark_parser.add_argument("--slug")
    mark_parser.add_argument(
        "--verify-repo-root",
        type=Path,
        help="Required when marking a paper published; verifies both remote Markdown files.",
    )
    mark_parser.add_argument("--remote-base-url", default=DEFAULT_REMOTE_RAW_BASE)
    mark_parser.add_argument("--verify-attempts", type=int, default=DEFAULT_REMOTE_VERIFY_ATTEMPTS)
    mark_parser.add_argument(
        "--verify-retry-delay-seconds",
        type=float,
        default=DEFAULT_REMOTE_VERIFY_RETRY_SECONDS,
    )

    verify_parser = subparsers.add_parser(
        "verify-published", help="Verify a bilingual research brief on the remote master branch"
    )
    verify_parser.add_argument("--id", required=True)
    verify_parser.add_argument("--slug", required=True)
    verify_parser.add_argument("--repo-root", type=Path, required=True)
    verify_parser.add_argument("--remote-base-url", default=DEFAULT_REMOTE_RAW_BASE)
    verify_parser.add_argument("--verify-attempts", type=int, default=DEFAULT_REMOTE_VERIFY_ATTEMPTS)
    verify_parser.add_argument(
        "--verify-retry-delay-seconds",
        type=float,
        default=DEFAULT_REMOTE_VERIFY_RETRY_SECONDS,
    )

    subparsers.add_parser("summary", help="Show queue counts")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "ingest":
        result: Any = ingest(args.feed, args.state)
    elif args.command == "list":
        result = list_candidates(args.state, args.statuses, args.limit)
    elif args.command == "mark":
        verification = None
        if args.status == "published":
            if args.verify_repo_root is None:
                parser.error("mark --status published requires --verify-repo-root")
            verification = verify_published_pair(
                args.verify_repo_root,
                args.id,
                args.slug or "",
                args.remote_base_url,
                args.verify_attempts,
                args.verify_retry_delay_seconds,
            )
        result = mark_paper(
            args.state,
            args.id,
            args.status,
            args.score,
            args.reason,
            args.slug,
        )
        if verification is not None:
            result["verification"] = verification
    elif args.command == "verify-published":
        result = verify_published_pair(
            args.repo_root,
            args.id,
            args.slug,
            args.remote_base_url,
            args.verify_attempts,
            args.verify_retry_delay_seconds,
        )
    else:
        ledger = load_ledger(args.state)
        result = {
            "paper_count": len(ledger["papers"]),
            "status_counts": dict(Counter(p["status"] for p in ledger["papers"].values())),
            "updated_at": ledger["updated_at"],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Maintain a durable per-paper queue for the arXiv publishing workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STATE = Path.home() / ".hermes/state/arxiv-robotics-ledger.json"
VALID_STATUSES = {"unseen", "selected", "published", "skipped", "failed"}
ARXIV_ID_PATTERN = re.compile(r"^(?P<id>\d{4}\.\d{4,5})(?:v(?P<version>\d+))?$")
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
    if status == "published" and not slug:
        raise ValueError("Published papers require --slug")

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
        paper["slug"] = slug
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

    subparsers.add_parser("summary", help="Show queue counts")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "ingest":
        result: Any = ingest(args.feed, args.state)
    elif args.command == "list":
        result = list_candidates(args.state, args.statuses, args.limit)
    elif args.command == "mark":
        result = mark_paper(
            args.state,
            args.id,
            args.status,
            args.score,
            args.reason,
            args.slug,
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

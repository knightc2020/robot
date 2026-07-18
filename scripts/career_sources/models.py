"""Identity and normalized staging models for recruitment-source dry-runs."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from dataclasses import asdict, dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "source",
}
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d().\s-]{7,}\d)(?!\w)")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalize_detail_url(url: str) -> str:
    """Normalize identity URLs while retaining non-tracking query parameters."""

    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Job URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials are not allowed in job URLs")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    if parsed.port and not (
        (scheme == "https" and parsed.port == 443)
        or (scheme == "http" and parsed.port == 80)
    ):
        host = f"{host}:{parsed.port}"
    path = posixpath.normpath(parsed.path or "/")
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/":
        path = path.rstrip("/")
    retained_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_QUERY_KEYS:
            continue
        retained_query.append((key, value))
    query = urlencode(sorted(retained_query), doseq=True)
    return urlunsplit((scheme, host, path, query, ""))


def build_job_key(source_id: str, external_job_id: str | None, detail_url: str) -> str:
    """Use source-native identity first and normalized detail URL as fallback."""

    source = source_id.strip()
    if not source:
        raise ValueError("source_id is required")
    if external_job_id and external_job_id.strip():
        identity = f"external:{external_job_id.strip()}"
    else:
        identity = f"url:{normalize_detail_url(detail_url)}"
    return f"{source}:{identity}"


def content_sha256(value: bytes | str | dict[str, Any] | list[Any]) -> str:
    if isinstance(value, bytes):
        content = value
    elif isinstance(value, str):
        content = value.encode("utf-8")
    else:
        content = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def normalized_strings(values: Iterable[str] | None) -> list[str]:
    return sorted({value.strip() for value in values or [] if value and value.strip()})


def plain_text(value: str | None) -> str | None:
    """Convert source HTML to text and redact contact details not needed for analysis."""

    if value is None:
        return None
    parser = _TextExtractor()
    # Greenhouse returns its description markup HTML-entity encoded. Decode
    # before parsing so tags do not survive as literal ``<p>`` text.
    parser.feed(unescape(value))
    text = " ".join(unescape(" ".join(parser.parts)).split())
    text = EMAIL_PATTERN.sub("[email redacted]", text)
    text = PHONE_PATTERN.sub("[phone redacted]", text)
    return text or None


def job_content_hash(fields: dict[str, Any]) -> str:
    """Hash normalized job content; identity and fetch metadata are deliberately excluded."""

    content_fields = {
        "title": fields.get("title"),
        "location": fields.get("location"),
        "department": fields.get("department"),
        "employment_type": fields.get("employment_type"),
        "description": fields.get("description"),
        "published_at": fields.get("published_at"),
    }
    return content_sha256(content_fields)


@dataclass(frozen=True)
class StagingJob:
    """Unified non-business DTO emitted by fixture and live-smoke dry-runs."""

    source_id: str
    company_id: str
    external_job_id: str | None
    job_key: str
    title: str
    location: str | None
    department: str | None
    employment_type: str | None
    description: str | None
    detail_url: str
    canonical_url: str
    published_at: str | None
    content_hash: str
    fetched_at: str
    requested_url: str
    final_url: str
    identity_strategy: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

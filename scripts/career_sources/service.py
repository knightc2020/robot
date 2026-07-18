"""Source registration, bounded dry-runs, and manual verification."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import career_db

from .adapters import ADAPTERS, BaseSourceAdapter, SchemaDriftError, adapter_for_source
from .http_client import (
    AccessBarrierError,
    AccessBlockedError,
    HttpPage,
    RateLimitedError,
    SafeHttpClient,
    SsrfProtectionError,
)
from .models import StagingJob, normalize_detail_url
from .staging import StagingRunWriter


FIXTURE_ROOT = career_db.REPOSITORY_ROOT / "tests" / "fixtures" / "career_sources"
SOURCE_TYPE_MAPPING = {
    "official_html": "official_career_page",
    "standard_ats": "official_ats_api",
    "official_json": "official_ats_api",
}


class SourceServiceError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{uuid.uuid4().hex[:10]}"


def _validate_https_url(value: str, label: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise SourceServiceError(f"{label} must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise SourceServiceError(f"{label} must not contain credentials")
    return value


def _normalize_domains(values: list[str]) -> list[str]:
    domains: set[str] = set()
    for value in values:
        candidate = value.strip().rstrip(".")
        if not candidate or "://" in candidate or "/" in candidate or ":" in candidate:
            raise SourceServiceError("Allowed domains must be hostnames without scheme, port, or path")
        domains.add(candidate.encode("idna").decode("ascii").lower())
    if not domains:
        raise SourceServiceError("At least one allowed domain is required")
    return sorted(domains)


def _host_is_allowed(hostname: str, allowed_domains: list[str]) -> bool:
    normalized = hostname.rstrip(".").encode("idna").decode("ascii").lower()
    return any(normalized == domain or normalized.endswith(f".{domain}") for domain in allowed_domains)


def register_company(
    database: str | Path,
    *,
    company_id: str,
    display_name: str,
    official_website_url: str,
    official_career_url: str,
) -> dict[str, Any]:
    path = career_db.assert_external_path(database, "Database path")
    career_db.validate_database(path)
    website = _validate_https_url(official_website_url, "Official website URL")
    careers = _validate_https_url(official_career_url, "Official career URL")
    if not company_id.strip() or not display_name.strip():
        raise SourceServiceError("company_id and display_name are required")
    now = _utc_now()
    connection = career_db.connect_database(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO companies(
              company_id, legal_name, display_name, official_website_url,
              official_career_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id.strip(),
                display_name.strip(),
                display_name.strip(),
                website,
                careers,
                now,
                now,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise SourceServiceError(f"Company registration failed without overwriting data: {error}") from error
    finally:
        connection.close()
    return {"company_id": company_id.strip(), "status": "candidate"}


def register_source(
    database: str | Path,
    *,
    source_id: str,
    company_id: str,
    source_name: str,
    official_careers_url: str,
    listing_url: str,
    source_type: str,
    allowed_domains: list[str],
    adapter_name: str,
    external_id_strategy: str,
    owner: str,
    ats_vendor: str | None = None,
    official_evidence_url: str | None = None,
    evidence_checked: bool = False,
    robots_status: str = "not_checked",
    terms_status: str = "not_checked",
    login_required: bool = False,
    captcha_detected: bool = False,
    notes: str | None = None,
) -> dict[str, Any]:
    path = career_db.assert_external_path(database, "Database path")
    career_db.validate_database(path)
    careers_url = _validate_https_url(official_careers_url, "Official careers URL")
    list_url = _validate_https_url(listing_url, "Listing URL")
    domains = _normalize_domains(allowed_domains)
    listing_host = urlsplit(list_url).hostname
    assert listing_host is not None
    if not _host_is_allowed(listing_host, domains):
        raise SourceServiceError("Listing URL hostname must be covered by allowed_domains")
    adapter_type = ADAPTERS.get(adapter_name)
    if adapter_type is None:
        raise SourceServiceError(f"Unsupported adapter: {adapter_name}")
    adapter = adapter_type()
    if source_type != adapter.source_type:
        raise SourceServiceError(
            f"Adapter {adapter_name} requires source_type={adapter.source_type}"
        )
    if source_type == "standard_ats" and not ats_vendor:
        raise SourceServiceError("standard_ats requires --ats-vendor")
    if source_type != "standard_ats" and ats_vendor:
        raise SourceServiceError("ats_vendor is only valid for standard_ats")
    evidence_url = (
        _validate_https_url(official_evidence_url, "Official evidence URL")
        if official_evidence_url
        else None
    )
    if evidence_checked and not evidence_url:
        raise SourceServiceError("evidence_checked requires official_evidence_url")
    if not all(value.strip() for value in (source_id, company_id, source_name, owner)):
        raise SourceServiceError("Source identifiers, name, and owner are required")
    mock_source = {
        "source_type": source_type,
        "adapter_name": adapter_name,
        "adapter_version": adapter.adapter_version,
        "parser_version": adapter.parser_version,
        "ats_vendor": ats_vendor,
    }
    adapter.validate_source_config(mock_source)
    now = _utc_now()
    base_terms = {
        "reviewed_no_obvious_restriction": "approved",
        "restricted": "restricted",
    }.get(terms_status, "not_reviewed")
    base_robots = {
        "allowed": "allowed",
        "not_found": "not_applicable",
        "disallowed": "blocked",
    }.get(robots_status, "not_reviewed")
    connection = career_db.connect_database(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM companies WHERE company_id = ?", (company_id.strip(),)
        ).fetchone() is None:
            raise SourceServiceError("company_id is not registered")
        connection.execute(
            """
            INSERT INTO career_sources(
              source_id, company_id, source_url, source_type, collection_method,
              scope_json, terms_review_status, terms_reviewed_at,
              robots_review_status, owner, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id.strip(),
                company_id.strip(),
                list_url,
                SOURCE_TYPE_MAPPING[source_type],
                adapter_name,
                json.dumps({"allowed_domains": domains}, separators=(",", ":")),
                base_terms,
                now if terms_status != "not_checked" else None,
                base_robots,
                owner.strip(),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO career_source_profiles(
              source_id, company_id, source_name, official_careers_url,
              listing_url, source_type, ats_vendor, allowed_domains_json,
              adapter_name, adapter_version, parser_version,
              external_id_strategy, official_evidence_url,
              official_evidence_checked_at, robots_status, terms_status,
              login_required, captcha_detected, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id.strip(),
                company_id.strip(),
                source_name.strip(),
                careers_url,
                list_url,
                source_type,
                ats_vendor.strip() if ats_vendor else None,
                json.dumps(domains, separators=(",", ":")),
                adapter_name,
                adapter.adapter_version,
                adapter.parser_version,
                external_id_strategy,
                evidence_url,
                now if evidence_checked else None,
                robots_status,
                terms_status,
                int(login_required),
                int(captcha_detected),
                notes.strip() if notes else None,
                now,
                now,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise SourceServiceError(f"Source registration failed without overwriting data: {error}") from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return load_source(path, source_id)


def load_source(database: str | Path, source_id: str) -> dict[str, Any]:
    path = career_db.assert_external_path(database, "Database path")
    connection = career_db.connect_database(path)
    try:
        row = connection.execute(
            """
            SELECT p.*, s.enabled AS base_enabled, s.lifecycle_status AS base_status,
                   s.owner
            FROM career_source_profiles p
            JOIN career_sources s
              ON s.source_id = p.source_id AND s.company_id = p.company_id
            WHERE p.source_id = ?
            """,
            (source_id,),
        ).fetchone()
        if row is None:
            raise SourceServiceError(f"Unknown source_id: {source_id}")
        source = dict(row)
        source["allowed_domains"] = json.loads(source.pop("allowed_domains_json"))
        return source
    finally:
        connection.close()


def list_sources(database: str | Path) -> list[dict[str, Any]]:
    path = career_db.assert_external_path(database, "Database path")
    career_db.validate_database(path)
    connection = career_db.connect_database(path)
    try:
        rows = connection.execute(
            """
            SELECT p.source_id, p.company_id, p.source_name, p.source_type,
                   p.ats_vendor, p.adapter_name, p.external_id_strategy,
                   p.status, p.collection_enabled, p.publication_enabled,
                   p.last_checked_at, p.last_success_at, p.failure_reason
            FROM career_source_profiles p
            ORDER BY p.source_id
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _business_counts(connection: sqlite3.Connection) -> tuple[int, int]:
    return (
        connection.execute("SELECT count(*) FROM job_postings").fetchone()[0],
        connection.execute("SELECT count(*) FROM job_changes").fetchone()[0],
    )


def _preflight(database: Path, source: dict[str, Any], mode: str, confirm_live: bool) -> tuple[int, int]:
    if mode == "live-smoke" and not confirm_live:
        raise SourceServiceError("live-smoke requires explicit --confirm-live")
    if mode not in {"fixture", "live-smoke"}:
        raise SourceServiceError(f"Unsupported dry-run mode: {mode}")
    if source["status"] in {"paused", "blocked"}:
        raise SourceServiceError(f"Source status {source['status']} forbids dry-run")
    if source["collection_enabled"] or source["publication_enabled"] or source["base_enabled"]:
        raise SourceServiceError("Source collection/publication controls must remain disabled")
    connection = career_db.connect_database(database)
    try:
        controls = connection.execute(
            "SELECT collection_enabled, publication_enabled FROM system_controls WHERE singleton = 1"
        ).fetchone()
        if controls["collection_enabled"] or controls["publication_enabled"]:
            raise SourceServiceError("Global collection/publication controls must remain disabled")
        return _business_counts(connection)
    finally:
        connection.close()


def _fixture_page(fixture_directory: Path, entry: dict[str, Any]) -> HttpPage:
    filename = entry.get("file")
    if not isinstance(filename, str):
        raise SourceServiceError("Fixture manifest page is missing file")
    path = (fixture_directory / filename).resolve()
    try:
        path.relative_to(fixture_directory.resolve())
    except ValueError as error:
        raise SourceServiceError("Fixture manifest path escapes fixture directory") from error
    if not path.is_file():
        raise SourceServiceError(f"Fixture page is missing: {filename}")
    return HttpPage(
        requested_url=str(entry["requested_url"]),
        final_url=str(entry.get("final_url") or entry["requested_url"]),
        redirect_chain=[],
        fetched_at=_utc_now(),
        http_status=int(entry.get("http_status", 200)),
        content_type=str(entry["content_type"]),
        body=path.read_bytes(),
    )


def _fixture_pages(adapter: BaseSourceAdapter) -> tuple[HttpPage, dict[str, HttpPage]]:
    fixture_directory = FIXTURE_ROOT / adapter.adapter_name
    manifest_path = fixture_directory / "manifest.json"
    if not manifest_path.is_file():
        raise SourceServiceError(f"No fixture set exists for adapter {adapter.adapter_name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("adapter_name") != adapter.adapter_name:
        raise SourceServiceError("Fixture manifest adapter_name does not match")
    listing = _fixture_page(fixture_directory, manifest["listing"])
    details: dict[str, HttpPage] = {}
    for entry in manifest.get("details", []):
        page = _fixture_page(fixture_directory, entry)
        key = normalize_detail_url(str(entry.get("match_url") or page.requested_url))
        if key in details:
            raise SourceServiceError("Fixture manifest contains duplicate detail match URLs")
        details[key] = page
    return listing, details


def _record_run(
    database: Path,
    source: dict[str, Any],
    summary: dict[str, Any],
    summary_path: Path,
) -> None:
    now = _utc_now()
    connection = career_db.connect_database(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO source_verification_runs(
              verification_run_id, source_id, mode, started_at, finished_at,
              result, adapter_version, parser_version, run_summary_path,
              failure_reason, listing_requests, detail_requests, parsed_jobs,
              job_postings_before, job_postings_after, job_changes_before,
              job_changes_after, collection_enabled, publication_enabled, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
            """,
            (
                summary["run_id"],
                source["source_id"],
                "live_smoke" if summary["mode"] == "live-smoke" else "fixture",
                summary["started_at"],
                summary["finished_at"],
                summary["result"],
                source["adapter_version"],
                source["parser_version"],
                str(summary_path),
                summary.get("failure_reason"),
                summary["network_requests"]["listing"],
                summary["network_requests"]["detail"],
                summary["parsed_job_count"],
                summary["business_table_counts"]["job_postings_before"],
                summary["business_table_counts"]["job_postings_after"],
                summary["business_table_counts"]["job_changes_before"],
                summary["business_table_counts"]["job_changes_after"],
                now,
            ),
        )
        connection.execute(
            """
            UPDATE career_source_profiles
            SET adapter_test_status = CASE
                  WHEN ? = 'fixture' AND ? = 'succeeded' THEN 'passed'
                  WHEN ? = 'fixture' THEN 'failed'
                  ELSE adapter_test_status
                END,
                last_checked_at = ?,
                last_success_at = CASE WHEN ? = 'succeeded' THEN ? ELSE last_success_at END,
                failure_reason = CASE WHEN ? = 'succeeded' THEN NULL ELSE ? END,
                updated_at = ?
            WHERE source_id = ?
            """,
            (
                summary["mode"], summary["result"], summary["mode"],
                summary["finished_at"], summary["result"], summary["finished_at"],
                summary["result"], summary.get("failure_reason"), now,
                source["source_id"],
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def dry_run(
    database: str | Path,
    staging_dir: str | Path,
    *,
    source_id: str,
    mode: str,
    confirm_live: bool = False,
    client: SafeHttpClient | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    database_path = career_db.assert_external_path(database, "Database path")
    career_db.validate_database(database_path)
    source = load_source(database_path, source_id)
    adapter = adapter_for_source(source)
    before_jobs, before_changes = _preflight(database_path, source, mode, confirm_live)
    verification_run_id = run_id or _run_id()
    writer = StagingRunWriter(staging_dir, source_id, verification_run_id)
    started_at = _utc_now()
    network_listing_requests = 0
    network_detail_requests = 0
    parsed_jobs: list[StagingJob] = []
    caught: Exception | None = None
    result = "succeeded"

    try:
        if mode == "fixture":
            listing_page, fixture_details = _fixture_pages(adapter)
        else:
            http_client = client or SafeHttpClient()
            network_listing_requests = 1
            listing_page = adapter.fetch_listing(http_client, source)
            fixture_details = {}
        writer.write_page("listing", listing_page)
        listing_items = adapter.parse_listing(listing_page, source)
        links = adapter.extract_detail_links(listing_items)
        if not links:
            raise SchemaDriftError("Listing did not produce detail links")
        selected: list[tuple[dict[str, Any], str]] = []
        seen_links: set[str] = set()
        for item, link in zip(listing_items, links, strict=True):
            normalized_link = normalize_detail_url(link)
            if normalized_link in seen_links:
                raise SchemaDriftError("Listing contains duplicate detail links")
            seen_links.add(normalized_link)
            selected.append((item, link))
            if len(selected) == 2:
                break
        for number, (listing_item, detail_link) in enumerate(selected, start=1):
            if mode == "fixture":
                detail_page = fixture_details.get(normalize_detail_url(detail_link))
                if detail_page is None:
                    raise SourceServiceError(f"Fixture detail is missing for {detail_link}")
            else:
                network_detail_requests += 1
                detail_page = adapter.fetch_detail(http_client, source, detail_link)
            writer.write_page("detail", detail_page, number)
            parsed_detail = adapter.parse_detail(detail_page, listing_item, source)
            job = adapter.build_staging_record(source, listing_item, parsed_detail, detail_page)
            if any(existing.job_key == job.job_key for existing in parsed_jobs):
                raise SchemaDriftError(f"Duplicate job_key in dry-run: {job.job_key}")
            parsed_jobs.append(job)
    except Exception as error:  # The summary and zero-write proof are still preserved.
        caught = error
        result = "blocked" if isinstance(
            error,
            (AccessBarrierError, AccessBlockedError, RateLimitedError, SsrfProtectionError),
        ) else "failed"

    writer.write_parsed_jobs(parsed_jobs)
    connection = career_db.connect_database(database_path)
    try:
        after_jobs, after_changes = _business_counts(connection)
    finally:
        connection.close()
    if (after_jobs, after_changes) != (before_jobs, before_changes):
        caught = SourceServiceError("Dry-run business-table counts changed")
        result = "failed"
    finished_at = _utc_now()
    summary = {
        "schema_version": 1,
        "source_id": source_id,
        "company_id": source["company_id"],
        "run_id": verification_run_id,
        "mode": mode,
        "result": result,
        "started_at": started_at,
        "finished_at": finished_at,
        "adapter_name": source["adapter_name"],
        "adapter_version": source["adapter_version"],
        "parser_version": source["parser_version"],
        "network_requests": {
            "listing": network_listing_requests,
            "detail": network_detail_requests,
            "total": network_listing_requests + network_detail_requests,
        },
        "limits": {"listing_pages": 1, "detail_pages": 2, "automatic_pagination": False},
        "parsed_job_count": len(parsed_jobs),
        "business_table_counts": {
            "job_postings_before": before_jobs,
            "job_postings_after": after_jobs,
            "job_changes_before": before_changes,
            "job_changes_after": after_changes,
        },
        "source_controls": {"collection_enabled": False, "publication_enabled": False},
        "failure_reason": str(caught) if caught else None,
    }
    summary_path = writer.write_summary(summary)
    _record_run(database_path, source, summary, summary_path)
    summary["run_summary_path"] = str(summary_path)
    if caught:
        raise SourceServiceError(
            f"Dry-run {result}; summary preserved at {summary_path}: {caught}"
        ) from caught
    return summary


def verify_source(
    database: str | Path,
    *,
    source_id: str,
    actor: str,
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        raise SourceServiceError("Source verification requires explicit --confirm")
    if not actor.strip():
        raise SourceServiceError("Verification requires an attributable actor")
    path = career_db.assert_external_path(database, "Database path")
    career_db.validate_database(path)
    source = load_source(path, source_id)
    _preflight(path, source, "fixture", False)
    if source["status"] == "verified":
        return source
    missing: list[str] = []
    requirements = {
        "official_evidence_url": source.get("official_evidence_url"),
        "official_evidence_checked_at": source.get("official_evidence_checked_at"),
        "fixture adapter test": source.get("adapter_test_status") == "passed",
        "stable identity strategy": source.get("external_id_strategy") != "review_required",
        "robots review": source.get("robots_status") in {"allowed", "not_found"},
        "terms review": source.get("terms_status") == "reviewed_no_obvious_restriction",
        "no login": not source.get("login_required"),
        "no captcha": not source.get("captcha_detected"),
    }
    missing.extend(label for label, value in requirements.items() if not value)
    connection = career_db.connect_database(path)
    try:
        successful_modes = {
            row["mode"] for row in connection.execute(
                "SELECT DISTINCT mode FROM source_verification_runs WHERE source_id = ? AND result = 'succeeded'",
                (source_id,),
            )
        }
        if "fixture" not in successful_modes:
            missing.append("successful fixture dry-run")
        if "live_smoke" not in successful_modes:
            missing.append("successful live smoke dry-run")
        if missing:
            raise SourceServiceError("Source cannot be verified; missing: " + ", ".join(missing))
        now = _utc_now()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            UPDATE career_source_profiles
            SET status = 'verified', reviewed_by = ?, reviewed_at = ?, updated_at = ?
            WHERE source_id = ?
            """,
            (actor.strip(), now, now, source_id),
        )
        connection.execute(
            """
            UPDATE career_sources
            SET lifecycle_status = 'verified', verified_at = ?, updated_at = ?
            WHERE source_id = ? AND enabled = 0
            """,
            (now, now, source_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    verified = load_source(path, source_id)
    if verified["collection_enabled"] or verified["publication_enabled"] or verified["base_enabled"]:
        raise SourceServiceError("Verification unexpectedly enabled collection or publication")
    return verified

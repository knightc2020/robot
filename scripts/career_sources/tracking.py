"""Phase 3B one-shot Greenhouse collection and deterministic change tracking."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import career_db

from .adapters import SchemaDriftError, StandardAtsAdapter, adapter_for_source
from .http_client import (
    AccessBarrierError,
    AccessBlockedError,
    HttpPage,
    RateLimitedError,
    SafeHttpClient,
)
from .models import StagingJob, content_sha256
from .service import load_source
from .staging import StagingError, StagingRunWriter


PHASE3B_SOURCE_IDS = (
    "nuro-greenhouse",
    "zipline-greenhouse",
    "agility-robotics-greenhouse",
)
OPEN_LIFECYCLE_STATUSES = {"observed", "active", "changed"}
TRACKED_FIELDS = (
    "title",
    "location",
    "department",
    "employment_type",
    "description",
    "detail_url",
    "canonical_url",
    "published_at",
)


class TrackingError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"phase3b-{timestamp}-{uuid.uuid4().hex[:10]}"


def _selected_source_ids(source_ids: list[str] | tuple[str, ...]) -> list[str]:
    selected: list[str] = []
    for source_id in source_ids:
        if source_id not in PHASE3B_SOURCE_IDS:
            raise TrackingError(f"Phase 3B source is not allowlisted: {source_id}")
        if source_id not in selected:
            selected.append(source_id)
    if not selected:
        raise TrackingError("At least one Phase 3B source_id is required")
    return selected


def set_collection_enabled(
    database: str | Path,
    *,
    source_ids: list[str] | tuple[str, ...],
    enabled: bool,
    actor: str,
    confirm: bool,
) -> dict[str, Any]:
    """Change only the source collection switches used by the Phase 3B collector."""

    if not confirm:
        raise TrackingError("Source collection control requires explicit --confirm")
    if not actor.strip():
        raise TrackingError("Source collection control requires an attributable actor")
    selected = _selected_source_ids(source_ids)
    path = career_db.assert_external_path(database, "Database path")
    career_db.validate_database(path)
    sources = [load_source(path, source_id) for source_id in selected]
    for source in sources:
        if source["status"] != "verified":
            raise TrackingError(f"Source must be verified before collection: {source['source_id']}")
        if source["publication_enabled"]:
            raise TrackingError(f"Source publication must remain disabled: {source['source_id']}")

    now = _utc_now()
    connection = career_db.connect_database(path)
    try:
        controls = connection.execute(
            "SELECT publication_enabled FROM system_controls WHERE singleton = 1"
        ).fetchone()
        if controls["publication_enabled"]:
            raise TrackingError("Global publication must be disabled")
        connection.execute("BEGIN IMMEDIATE")
        for source_id in selected:
            connection.execute(
                """
                UPDATE career_source_profiles
                SET collection_enabled = ?, updated_at = ?
                WHERE source_id = ? AND status = 'verified' AND publication_enabled = 0
                """,
                (int(enabled), now, source_id),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise TrackingError(f"Source collection profile was not updated: {source_id}")
            connection.execute(
                """
                UPDATE career_sources
                SET enabled = ?, lifecycle_status = ?, updated_at = ?
                WHERE source_id = ?
                """,
                (int(enabled), "enabled" if enabled else "verified", now, source_id),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {
        "collection_enabled": enabled,
        "publication_enabled": False,
        "sources": [load_source(path, source_id) for source_id in selected],
    }


class DailySummaryWriter:
    def __init__(self, staging_dir: str | Path, summary_date: str) -> None:
        root = career_db.assert_external_path(staging_dir, "Staging directory")
        if Path(staging_dir).is_symlink():
            raise StagingError("Staging directory must not be a symlink")
        if len(summary_date) != 10 or summary_date[4] != "-" or summary_date[7] != "-":
            raise StagingError("Summary date must use YYYY-MM-DD")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        daily_root = root / "daily-summaries"
        if daily_root.is_symlink():
            raise StagingError("Daily summary directory must not be a symlink")
        daily_root.mkdir(exist_ok=True, mode=0o700)
        self.directory = daily_root / summary_date
        try:
            self.directory.mkdir(mode=0o700)
        except FileExistsError as error:
            raise StagingError(f"Daily summary already exists: {self.directory}") from error

    def _write(self, filename: str, content: str) -> Path:
        path = self.directory / filename
        try:
            with path.open("x", encoding="utf-8") as output:
                output.write(content)
        except FileExistsError as error:
            raise StagingError(f"Daily summary file already exists: {path}") from error
        os.chmod(path, 0o600)
        return path

    def write(self, summary: dict[str, Any]) -> dict[str, str]:
        json_path = self._write(
            "summary.json",
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        markdown_path = self._write("summary.md", render_markdown_summary(summary))
        return {"json": str(json_path), "markdown": str(markdown_path)}


def _markdown_cell(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown_summary(summary: dict[str, Any]) -> str:
    totals = summary["totals"]
    lines = [
        "# 机器人岗位每日变化",
        "",
        "## 运行概况",
        "",
        f"- 成功来源数：{totals['successful_sources']}",
        f"- 失败来源数：{totals['failed_sources']}",
        f"- 当前开放岗位数：{totals['open_jobs']}",
        f"- 基线导入数量：{totals['baseline_import_count']}",
        f"- 新增数量：{totals['added']}",
        f"- 更新数量：{totals['updated']}",
        f"- 首次缺失数量：{totals['missing']}",
        f"- 关闭数量：{totals['closed']}",
        f"- 重新开放数量：{totals['reopened']}",
        "",
        "## 分公司情况",
        "",
    ]
    for source in summary["sources"]:
        lines.extend(
            [
                f"### {source['company_name']}",
                "",
                f"- 当前开放岗位数：{source['open_jobs']}",
                f"- 基线导入：{source['baseline_import_count']}",
                f"- 本次新增：{source['added']}",
                f"- 本次更新：{source['updated']}",
                f"- 本次缺失：{source['missing']}",
                f"- 本次关闭：{source['closed']}",
                f"- 本次重新开放：{source['reopened']}",
                f"- 运行结果：{'成功' if source['success'] else '失败'}",
                f"- 失败原因：{source.get('failure_reason') or '无'}",
                "",
            ]
        )
    lines.extend(["## 变化岗位明细", ""])
    if not summary["changes"]:
        lines.extend(["本次未发现岗位变化。", ""])
    else:
        lines.extend(
            [
                "| 公司 | title | location | department | change_type | detail_url | changed_fields |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for change in summary["changes"]:
            link = change.get("detail_url")
            rendered_link = f"[职位链接]({link})" if link else "—"
            lines.append(
                "| "
                + " | ".join(
                    (
                        _markdown_cell(change.get("company")),
                        _markdown_cell(change.get("title")),
                        _markdown_cell(change.get("location")),
                        _markdown_cell(change.get("department")),
                        _markdown_cell(change.get("change_type")),
                        rendered_link,
                        _markdown_cell(", ".join(change.get("changed_fields", []))),
                    )
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def _normalized_employment_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.lower().replace("_", " ").replace("-", " ").split())
    if "intern" in normalized:
        return "internship"
    if normalized in {"full time", "fulltime", "regular"}:
        return "full_time"
    if normalized in {"part time", "parttime"}:
        return "part_time"
    if "contract" in normalized:
        return "contract"
    if "temporary" in normalized or normalized == "temp":
        return "temporary"
    if "apprentice" in normalized:
        return "apprenticeship"
    return "other"


def _job_fields(job: StagingJob) -> dict[str, Any]:
    return {
        "title": job.title,
        "location": job.location,
        "department": job.department,
        "employment_type": job.employment_type,
        "description": job.description,
        "detail_url": job.detail_url,
        "canonical_url": job.canonical_url,
        "published_at": job.published_at,
    }


def _row_fields(row: sqlite3.Row) -> dict[str, Any]:
    metadata = json.loads(row["extraction_metadata_json"])
    return {
        "title": row["source_title"],
        "location": row["location_text"],
        "department": row["department_text"],
        "employment_type": metadata.get("employment_type_raw"),
        "description": row["description_text"],
        "detail_url": row["source_url"],
        "canonical_url": row["canonical_url"],
        "published_at": row["source_posted_at"],
    }


def _changed_fields(row: sqlite3.Row, job: StagingJob) -> list[str]:
    previous = _row_fields(row)
    current = _job_fields(job)
    return [field for field in TRACKED_FIELDS if previous[field] != current[field]]


def _job_metadata(job: StagingJob) -> str:
    return json.dumps(
        {
            "canonical_url": job.canonical_url,
            "detail_url": job.detail_url,
            "employment_type_raw": job.employment_type,
            "fetched_at": job.fetched_at,
            "identity_strategy": job.identity_strategy,
            "listing_requested_url": job.requested_url,
            "listing_final_url": job.final_url,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _insert_job(
    connection: sqlite3.Connection,
    job: StagingJob,
    *,
    now: str,
    raw_snapshot_ref: str,
    parser_version: str,
) -> None:
    connection.execute(
        """
        INSERT INTO job_postings(
          job_id, company_id, source_id, source_native_id, source_url,
          source_title, description_text, location_text, employment_type,
          source_posted_at, first_collected_at, last_collected_at,
          lifecycle_status, content_hash, raw_snapshot_ref, parser_version,
          extraction_metadata_json, quality_status, review_status,
          publication_status, created_at, updated_at, department_text,
          canonical_url, consecutive_missing_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?,
                  'parsed', 'pending', 'blocked', ?, ?, ?, ?, 0)
        """,
        (
            job.job_key,
            job.company_id,
            job.source_id,
            job.external_job_id,
            job.detail_url,
            job.title,
            job.description,
            job.location,
            _normalized_employment_type(job.employment_type),
            job.published_at,
            now,
            now,
            job.content_hash,
            raw_snapshot_ref,
            parser_version,
            _job_metadata(job),
            now,
            now,
            job.department,
            job.canonical_url,
        ),
    )


def _update_seen_job(
    connection: sqlite3.Connection,
    job: StagingJob,
    *,
    now: str,
    raw_snapshot_ref: str,
    parser_version: str,
) -> None:
    connection.execute(
        """
        UPDATE job_postings
        SET source_url = ?, source_title = ?, description_text = ?,
            location_text = ?, employment_type = ?, source_posted_at = ?,
            last_collected_at = ?, lifecycle_status = 'active', content_hash = ?,
            raw_snapshot_ref = ?, parser_version = ?, extraction_metadata_json = ?,
            updated_at = ?, department_text = ?, canonical_url = ?,
            consecutive_missing_count = 0
        WHERE job_id = ?
        """,
        (
            job.detail_url,
            job.title,
            job.description,
            job.location,
            _normalized_employment_type(job.employment_type),
            job.published_at,
            now,
            job.content_hash,
            raw_snapshot_ref,
            parser_version,
            _job_metadata(job),
            now,
            job.department,
            job.canonical_url,
            job.job_key,
        ),
    )


def _insert_change(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    source_id: str,
    job_id: str,
    change_type: str,
    previous_hash: str | None,
    current_hash: str | None,
    changed_fields: list[str],
    now: str,
    source_url: str,
    raw_snapshot_ref: str,
) -> None:
    connection.execute(
        """
        INSERT INTO job_changes(
          change_id, job_id, source_id, run_id, change_type,
          previous_content_hash, new_content_hash, changed_fields_json,
          observed_at, source_url, collected_at, raw_snapshot_ref,
          retrieval_result, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'success', ?)
        """,
        (
            f"change-{uuid.uuid4().hex}",
            job_id,
            source_id,
            run_id,
            change_type,
            previous_hash,
            current_hash,
            json.dumps({field: True for field in changed_fields}, separators=(",", ":")),
            now,
            source_url,
            now,
            raw_snapshot_ref,
            now,
        ),
    )


def _change_summary(
    *,
    company_name: str,
    change_type: str,
    changed_fields: list[str],
    job: StagingJob | None = None,
    row: sqlite3.Row | None = None,
) -> dict[str, Any]:
    return {
        "company": company_name,
        "title": job.title if job else row["source_title"],
        "location": job.location if job else row["location_text"],
        "department": job.department if job else row["department_text"],
        "change_type": change_type,
        "detail_url": job.detail_url if job else row["source_url"],
        "changed_fields": changed_fields,
        "job_key": job.job_key if job else row["job_id"],
    }


def _apply_source_snapshot(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    source: dict[str, Any],
    jobs: list[StagingJob],
    raw_snapshot_ref: str,
    now: str,
    company_name: str,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    existing_rows = connection.execute(
        "SELECT * FROM job_postings WHERE source_id = ?",
        (source["source_id"],),
    ).fetchall()
    existing = {row["job_id"]: row for row in existing_rows}
    baseline = not existing
    counts = {
        "baseline_import_count": 0,
        "added": 0,
        "updated": 0,
        "missing": 0,
        "closed": 0,
        "reopened": 0,
    }
    changes: list[dict[str, Any]] = []
    current_keys = {job.job_key for job in jobs}

    for job in jobs:
        row = existing.get(job.job_key)
        if row is None:
            _insert_job(
                connection,
                job,
                now=now,
                raw_snapshot_ref=raw_snapshot_ref,
                parser_version=source["parser_version"],
            )
            if baseline:
                counts["baseline_import_count"] += 1
            else:
                counts["added"] += 1
                _insert_change(
                    connection,
                    run_id=run_id,
                    source_id=source["source_id"],
                    job_id=job.job_key,
                    change_type="added",
                    previous_hash=None,
                    current_hash=job.content_hash,
                    changed_fields=list(TRACKED_FIELDS),
                    now=now,
                    source_url=job.detail_url,
                    raw_snapshot_ref=raw_snapshot_ref,
                )
                changes.append(
                    _change_summary(
                        company_name=company_name,
                        change_type="added",
                        changed_fields=list(TRACKED_FIELDS),
                        job=job,
                    )
                )
            continue

        fields = _changed_fields(row, job)
        was_absent = row["lifecycle_status"] in {"missing", "closed"}
        if was_absent:
            event = "reopened"
            event_fields = ["status", *fields]
            counts[event] += 1
            _insert_change(
                connection,
                run_id=run_id,
                source_id=source["source_id"],
                job_id=job.job_key,
                change_type=event,
                previous_hash=row["content_hash"],
                current_hash=job.content_hash,
                changed_fields=event_fields,
                now=now,
                source_url=job.detail_url,
                raw_snapshot_ref=raw_snapshot_ref,
            )
            changes.append(
                _change_summary(
                    company_name=company_name,
                    change_type=event,
                    changed_fields=event_fields,
                    job=job,
                )
            )
        elif fields or row["content_hash"] != job.content_hash:
            event_fields = fields or ["content_hash"]
            counts["updated"] += 1
            _insert_change(
                connection,
                run_id=run_id,
                source_id=source["source_id"],
                job_id=job.job_key,
                change_type="updated",
                previous_hash=row["content_hash"],
                current_hash=job.content_hash,
                changed_fields=event_fields,
                now=now,
                source_url=job.detail_url,
                raw_snapshot_ref=raw_snapshot_ref,
            )
            changes.append(
                _change_summary(
                    company_name=company_name,
                    change_type="updated",
                    changed_fields=event_fields,
                    job=job,
                )
            )
        _update_seen_job(
            connection,
            job,
            now=now,
            raw_snapshot_ref=raw_snapshot_ref,
            parser_version=source["parser_version"],
        )

    for row in existing_rows:
        if row["job_id"] in current_keys or row["lifecycle_status"] == "closed":
            continue
        missing_count = row["consecutive_missing_count"] + 1
        if row["lifecycle_status"] in OPEN_LIFECYCLE_STATUSES:
            event = "missing"
            status = "missing"
        else:
            event = "closed"
            status = "closed"
        connection.execute(
            """
            UPDATE job_postings
            SET lifecycle_status = ?, consecutive_missing_count = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (status, missing_count, now, row["job_id"]),
        )
        counts[event] += 1
        _insert_change(
            connection,
            run_id=run_id,
            source_id=source["source_id"],
            job_id=row["job_id"],
            change_type=event,
            previous_hash=row["content_hash"],
            current_hash=None,
            changed_fields=["status", "consecutive_missing_count"],
            now=now,
            source_url=row["source_url"],
            raw_snapshot_ref=raw_snapshot_ref,
        )
        changes.append(
            _change_summary(
                company_name=company_name,
                change_type=event,
                changed_fields=["status", "consecutive_missing_count"],
                row=row,
            )
        )
    return counts, changes


def _failure_retrieval_result(error: Exception) -> str:
    if isinstance(error, RateLimitedError):
        return "rate_limited"
    if isinstance(error, (AccessBarrierError, AccessBlockedError)):
        return "access_denied"
    if isinstance(error, (SchemaDriftError, ValueError, json.JSONDecodeError)):
        return "invalid_response"
    return "network_error"


def _preflight_sources(database: Path, source_ids: list[str]) -> list[dict[str, Any]]:
    connection = career_db.connect_database(database)
    try:
        controls = connection.execute(
            "SELECT collection_enabled, publication_enabled FROM system_controls WHERE singleton = 1"
        ).fetchone()
        if not controls["collection_enabled"]:
            raise TrackingError("Global collection is disabled")
        if controls["publication_enabled"]:
            raise TrackingError("Global publication must remain disabled")
    finally:
        connection.close()
    sources = [load_source(database, source_id) for source_id in source_ids]
    for source in sources:
        if source["status"] != "verified":
            raise TrackingError(f"Source is not verified: {source['source_id']}")
        if not source["collection_enabled"] or not source["base_enabled"]:
            raise TrackingError(f"Source collection is disabled: {source['source_id']}")
        if source["publication_enabled"]:
            raise TrackingError(f"Source publication must remain disabled: {source['source_id']}")
        if source["adapter_name"] != StandardAtsAdapter.adapter_name:
            raise TrackingError(f"Phase 3B supports the existing Greenhouse adapter only: {source['source_id']}")
    return sources


def collect(
    database: str | Path,
    staging_dir: str | Path,
    *,
    source_ids: list[str] | tuple[str, ...],
    confirm_write: bool,
    client: SafeHttpClient | None = None,
    now: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Fetch one complete list per source and apply changes in one DB transaction."""

    if not confirm_write:
        raise TrackingError("Collection writes require explicit --confirm-write")
    selected = _selected_source_ids(source_ids)
    database_path = career_db.assert_external_path(database, "Database path")
    career_db.validate_database(database_path)
    sources = _preflight_sources(database_path, selected)
    observed_at = now or _utc_now()
    if len(observed_at) < 10:
        raise TrackingError("now must be an ISO-8601 timestamp")
    collection_run_id = run_id or _run_id()
    summary_writer = DailySummaryWriter(staging_dir, observed_at[:10])
    writers = {
        source["source_id"]: StagingRunWriter(staging_dir, source["source_id"], collection_run_id)
        for source in sources
    }
    http_client = client or SafeHttpClient()
    results: list[dict[str, Any]] = []

    for source in sources:
        source_id = source["source_id"]
        writer = writers[source_id]
        result: dict[str, Any] = {
            "source": source,
            "success": False,
            "jobs": [],
            "raw_snapshot_ref": None,
            "failure_reason": None,
            "retrieval_result": None,
            "http_status": None,
        }
        try:
            adapter = adapter_for_source(source)
            if not isinstance(adapter, StandardAtsAdapter):
                raise TrackingError("Phase 3B received a non-Greenhouse adapter")
            page: HttpPage = adapter.fetch_listing(http_client, source)
            raw_path = writer.write_page("listing", page)
            jobs = adapter.parse_complete_listing(page, source)
            if len({job.job_key for job in jobs}) != len(jobs):
                raise TrackingError(f"Duplicate job_key in source snapshot: {source_id}")
            writer.write_parsed_jobs(jobs)
            result.update(
                {
                    "success": True,
                    "jobs": jobs,
                    "raw_snapshot_ref": str(raw_path),
                    "retrieval_result": "success",
                    "http_status": page.http_status,
                }
            )
        except Exception as error:
            result["failure_reason"] = str(error)
            result["retrieval_result"] = _failure_retrieval_result(error)
            writer.write_parsed_jobs([])
        results.append(result)

    connection = career_db.connect_database(database_path)
    changes: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    try:
        company_names = {
            row["company_id"]: row["display_name"]
            for row in connection.execute(
                "SELECT company_id, display_name FROM companies"
            )
        }
        connection.execute("BEGIN IMMEDIATE")
        failed = [result for result in results if not result["success"]]
        connection.execute(
            """
            INSERT INTO pipeline_runs(
              run_id, pipeline_name, pipeline_stage, environment, status,
              code_version, config_hash, input_refs_json, output_refs_json,
              metrics_json, started_at, finished_at, error_summary, created_at
            ) VALUES (?, 'phase3b_greenhouse_tracking', 'collection', 'staging', ?,
                      'phase3b-mvp-v1', ?, ?, ?, '{}', ?, ?, ?, ?)
            """,
            (
                collection_run_id,
                "failed" if failed else "succeeded",
                content_sha256(selected),
                json.dumps([source["listing_url"] for source in sources], separators=(",", ":")),
                json.dumps(
                    [
                        str(writers[source["source_id"]].run_directory)
                        for source in sources
                    ],
                    separators=(",", ":"),
                ),
                observed_at,
                observed_at,
                "; ".join(
                    f"{result['source']['source_id']}: {result['failure_reason']}"
                    for result in failed
                )
                or None,
                observed_at,
            ),
        )
        for result in results:
            source = result["source"]
            source_id = source["source_id"]
            company_name = company_names[source["company_id"]]
            counts = {
                "baseline_import_count": 0,
                "added": 0,
                "updated": 0,
                "missing": 0,
                "closed": 0,
                "reopened": 0,
            }
            if result["success"]:
                counts, source_changes = _apply_source_snapshot(
                    connection,
                    run_id=collection_run_id,
                    source=source,
                    jobs=result["jobs"],
                    raw_snapshot_ref=result["raw_snapshot_ref"],
                    now=observed_at,
                    company_name=company_name,
                )
                changes.extend(source_changes)
                connection.execute(
                    """
                    UPDATE career_sources
                    SET health_status = 'healthy', last_collected_at = ?,
                        last_http_status = ?, last_retrieval_result = 'success',
                        updated_at = ?
                    WHERE source_id = ?
                    """,
                    (observed_at, result["http_status"], observed_at, source_id),
                )
                connection.execute(
                    """
                    UPDATE career_source_profiles
                    SET last_checked_at = ?, last_success_at = ?, failure_reason = NULL,
                        updated_at = ?
                    WHERE source_id = ?
                    """,
                    (observed_at, observed_at, observed_at, source_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE career_sources
                    SET health_status = 'degraded', last_http_status = ?,
                        last_retrieval_result = ?, updated_at = ?
                    WHERE source_id = ?
                    """,
                    (
                        result["http_status"],
                        result["retrieval_result"],
                        observed_at,
                        source_id,
                    ),
                )
                connection.execute(
                    """
                    UPDATE career_source_profiles
                    SET last_checked_at = ?, failure_reason = ?, updated_at = ?
                    WHERE source_id = ?
                    """,
                    (observed_at, result["failure_reason"], observed_at, source_id),
                )
            source_summaries.append(
                {
                    "source_id": source_id,
                    "company_id": source["company_id"],
                    "company_name": company_name,
                    "success": result["success"],
                    "fetched_jobs": len(result["jobs"]),
                    "failure_reason": result["failure_reason"],
                    **counts,
                }
            )

        open_counts = {
            row["source_id"]: row["count"]
            for row in connection.execute(
                """
                SELECT source_id, count(*) AS count
                FROM job_postings
                WHERE lifecycle_status IN ('observed', 'active', 'changed')
                GROUP BY source_id
                """
            )
        }
        for source_summary in source_summaries:
            source_summary["open_jobs"] = open_counts.get(source_summary["source_id"], 0)
        totals = {
            "successful_sources": sum(item["success"] for item in source_summaries),
            "failed_sources": sum(not item["success"] for item in source_summaries),
            "open_jobs": sum(open_counts.values()),
            **{
                field: sum(item[field] for item in source_summaries)
                for field in (
                    "baseline_import_count",
                    "added",
                    "updated",
                    "missing",
                    "closed",
                    "reopened",
                )
            },
        }
        metrics = {
            "sources": source_summaries,
            "totals": totals,
            "change_count": len(changes),
        }
        connection.execute(
            "UPDATE pipeline_runs SET metrics_json = ? WHERE run_id = ?",
            (json.dumps(metrics, ensure_ascii=False, separators=(",", ":")), collection_run_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    summary = {
        "schema_version": 1,
        "run_id": collection_run_id,
        "run_type": "baseline" if totals["baseline_import_count"] else "incremental",
        "observed_at": observed_at,
        "summary_date": observed_at[:10],
        "limits": {
            "listing_requests_per_source": 1,
            "detail_requests": 0,
            "automatic_pagination": False,
        },
        "totals": totals,
        "sources": source_summaries,
        "changes": changes,
        "publication_enabled": False,
        "result": "succeeded" if totals["failed_sources"] == 0 else "partial_failure",
    }
    summary_paths = summary_writer.write(summary)
    for result, source_summary in zip(results, source_summaries, strict=True):
        writer = writers[result["source"]["source_id"]]
        writer.write_summary(
            {
                "schema_version": 1,
                "run_id": collection_run_id,
                "source_id": result["source"]["source_id"],
                "mode": "phase3b-collection",
                "result": "succeeded" if result["success"] else "failed",
                "listing_requests": 1,
                "detail_requests": 0,
                "parsed_job_count": len(result["jobs"]),
                "failure_reason": result["failure_reason"],
                "changes": source_summary,
            }
        )
    summary["summary_paths"] = summary_paths
    return summary

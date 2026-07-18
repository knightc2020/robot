#!/usr/bin/env python3
"""Career-intelligence SQLite adapter and safe public-snapshot publisher."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIRECTORY = REPOSITORY_ROOT / "career-intelligence" / "migrations"
PUBLIC_SNAPSHOT_ROOT = REPOSITORY_ROOT / "src" / "data" / "career-public"
RUNTIME_DIRECTORY_NAMES = ("raw", "staging", "exports", "logs", "backups")

DOMAIN_TABLES = (
    "companies",
    "career_sources",
    "job_postings",
    "skills",
    "skill_aliases",
    "job_skill_relations",
    "job_changes",
    "project_templates",
    "project_template_job_families",
    "project_template_skills",
    "pipeline_runs",
    "review_queue",
)

REQUIRED_TABLES = {
    "schema_migrations",
    "system_controls",
    "system_control_events",
    "career_source_profiles",
    "source_verification_runs",
    *DOMAIN_TABLES,
}

REQUIRED_INDEXES = {
    "companies_display_name_unique",
    "companies_lifecycle_index",
    "career_sources_company_index",
    "career_sources_health_index",
    "career_source_profiles_status_index",
    "career_source_profiles_controls_index",
    "source_verification_runs_source_mode_index",
    "job_postings_company_status_index",
    "job_postings_source_status_index",
    "job_postings_hash_index",
    "job_postings_family_index",
    "skills_category_status_index",
    "skill_aliases_normalized_unique",
    "skill_aliases_skill_status_index",
    "job_skill_relations_skill_index",
    "job_changes_job_time_index",
    "job_changes_source_time_index",
    "pipeline_runs_stage_time_index",
    "pipeline_runs_status_index",
    "review_queue_status_priority_index",
    "review_queue_entity_index",
}

REQUIRED_TRIGGERS = {
    "job_changes_no_update",
    "job_changes_no_delete",
    "system_controls_require_audit_metadata",
    "system_controls_record_event",
    "system_controls_no_delete",
    "career_source_profiles_verified_guard",
    "source_verification_runs_no_update",
    "source_verification_runs_no_delete",
}

PUBLIC_FILES = (
    "companies.json",
    "jobs.json",
    "skills.json",
    "role-summary.json",
    "project-templates.json",
)

PUBLIC_FIELD_WHITELISTS = {
    "companies.json": {
        "id", "name", "countryCode", "regions", "websiteUrl", "careerUrl"
    },
    "jobs.json": {
        "id", "companyId", "title", "location", "countryCode", "region",
        "employmentType", "jobFamily", "sourceUrl", "postedAt", "updatedAt", "status"
    },
    "skills.json": {
        "id", "name", "aliases", "category", "definition", "evidenceExpectations"
    },
    "role-summary.json": {
        "role", "jobCount", "companyCount", "skillIds"
    },
    "project-templates.json": {
        "id", "slug", "title", "summary", "difficulty", "estimatedEffortHours",
        "prerequisites", "deliverables", "acceptanceEvidence", "safetyNotes",
        "licenseNotes", "targetJobFamilies", "skillIds"
    },
}

FORBIDDEN_PUBLIC_KEYS = {
    "raw_snapshot_path",
    "raw_snapshot_ref",
    "content_hash",
    "parser_confidence",
    "extraction_metadata",
    "extraction_version",
    "review_status",
    "reviewed_by",
    "reviewed_at",
    "error",
    "error_log",
    "error_summary",
    "confidence",
    "confidence_level",
    "local_path",
}

PROTECTED_PATH_ROOTS = (
    Path("/root/robot"),
    Path("/root/.hermes"),
    Path("/root/hermes-workspace"),
)


class CareerDataError(RuntimeError):
    """Raised when a career-data safety or validation rule fails."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _is_within(parent: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False


def assert_external_path(candidate: str | Path, label: str) -> Path:
    path = Path(candidate)
    if not path.is_absolute():
        raise CareerDataError(f"{label} must be an explicit absolute path")
    resolved = path.resolve(strict=False)
    if resolved in {Path("/"), Path("/root"), Path("/tmp")}:
        raise CareerDataError(f"{label} must not target a broad system/workspace directory")
    if _is_within(REPOSITORY_ROOT, resolved):
        raise CareerDataError(f"{label} must be outside the Git worktree")
    for protected_root in PROTECTED_PATH_ROOTS:
        if _is_within(protected_root, resolved):
            raise CareerDataError(f"{label} must not target a protected production or Hermes path")
    return resolved


def assert_public_snapshot_path(candidate: str | Path) -> Path:
    path = Path(candidate)
    if not path.is_absolute():
        raise CareerDataError("Public snapshot path must be absolute")
    resolved = path.resolve(strict=False)
    if resolved != PUBLIC_SNAPSHOT_ROOT:
        raise CareerDataError(
            f"Public snapshots must use the repository-owned path {PUBLIC_SNAPSHOT_ROOT}"
        )
    return resolved


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def initialize_runtime(runtime_root: str | Path) -> dict[str, Any]:
    root = assert_external_path(runtime_root, "Runtime root")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    paths: dict[str, str] = {}
    for name in RUNTIME_DIRECTORY_NAMES:
        directory = root / name
        if directory.is_symlink():
            raise CareerDataError(f"Runtime directory must not be a symlink: {directory}")
        directory.mkdir(exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        paths[name] = str(directory)
    return {"root": str(root), "mode": "0700", "paths": paths}


def validate_runtime(runtime_root: str | Path) -> dict[str, Any]:
    root = assert_external_path(runtime_root, "Runtime root")
    checked: dict[str, str] = {}
    for path in (root, *(root / name for name in RUNTIME_DIRECTORY_NAMES)):
        if not path.is_dir() or path.is_symlink():
            raise CareerDataError(f"Runtime directory is missing, not a directory, or a symlink: {path}")
        if _mode(path) != 0o700:
            raise CareerDataError(f"Runtime directory must have mode 0700: {path}")
        checked[str(path)] = "0700"
    staging_database = root / "staging" / "career.sqlite3"
    if staging_database.exists():
        if not staging_database.is_file() or staging_database.is_symlink():
            raise CareerDataError("Staging database must be a regular file")
        if _mode(staging_database) != 0o600:
            raise CareerDataError("Staging database must have mode 0600")
        checked[str(staging_database)] = "0600"
    return {"runtime": str(root), "checked": checked}


def _migration_files(directory: Path = MIGRATIONS_DIRECTORY) -> list[dict[str, Any]]:
    migrations: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.sql")):
        parts = path.name.split("_", 1)
        if len(parts) != 2 or len(parts[0]) != 4 or not parts[0].isdigit():
            raise CareerDataError(f"Invalid migration filename: {path.name}")
        suffix = parts[1].removesuffix(".sql")
        if not suffix or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_" for character in suffix):
            raise CareerDataError(f"Invalid migration filename: {path.name}")
        sql = path.read_text(encoding="utf-8")
        migrations.append({
            "version": int(parts[0]),
            "name": path.name,
            "sql": sql,
            "checksum": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        })
    if not migrations:
        raise CareerDataError("No career database migrations found")
    versions = [migration["version"] for migration in migrations]
    if versions != sorted(set(versions)):
        raise CareerDataError("Migration versions must be unique and strictly increasing")
    return migrations


def _sql_statements(sql: str) -> Iterable[str]:
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                yield statement
            buffer = ""
    if buffer.strip():
        raise CareerDataError("Migration contains an incomplete SQL statement")


def connect_database(database_path: str | Path, *, must_exist: bool = True) -> sqlite3.Connection:
    path = Path(database_path)
    if must_exist and not path.is_file():
        raise CareerDataError(f"Database does not exist: {path}")
    connection = sqlite3.connect(path, timeout=5.0, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA synchronous = FULL")
    return connection


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          checksum TEXT NOT NULL CHECK(length(checksum) = 64),
          applied_at TEXT NOT NULL
        ) STRICT
    """)


def migrate_database(database_path: str | Path) -> dict[str, Any]:
    path = assert_external_path(database_path, "Database path")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    migrations = _migration_files()
    connection = connect_database(path, must_exist=False)
    applied_now: list[int] = []
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        _ensure_migration_table(connection)
        for migration in migrations:
            connection.execute("BEGIN IMMEDIATE")
            try:
                applied = connection.execute(
                    "SELECT name, checksum FROM schema_migrations WHERE version = ?",
                    (migration["version"],),
                ).fetchone()
                if applied:
                    if applied["name"] != migration["name"] or applied["checksum"] != migration["checksum"]:
                        raise CareerDataError(
                            f"Applied migration {migration['version']} does not match repository checksum"
                        )
                    connection.commit()
                    continue
                for statement in _sql_statements(migration["sql"]):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, checksum, applied_at) VALUES (?, ?, ?, ?)",
                    (migration["version"], migration["name"], migration["checksum"], utc_now()),
                )
                connection.commit()
                applied_now.append(migration["version"])
            except Exception:
                connection.rollback()
                raise
    finally:
        connection.close()
    os.chmod(path, 0o600)
    return {"applied": applied_now, "currentVersion": migrations[-1]["version"]}


def validate_database(database_path: str | Path) -> dict[str, Any]:
    path = assert_external_path(database_path, "Database path")
    if not path.is_file() or path.is_symlink():
        raise CareerDataError("Database must be a regular non-symlink file")
    if _mode(path) != 0o600:
        raise CareerDataError("Database must have mode 0600")
    migrations = _migration_files()
    connection = connect_database(path)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise CareerDataError(f"SQLite integrity check failed: {integrity}")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise CareerDataError("SQLite foreign key check failed")
        schema_rows = connection.execute(
            "SELECT type, name FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        schema_by_type: dict[str, set[str]] = {}
        for row in schema_rows:
            schema_by_type.setdefault(row["type"], set()).add(row["name"])
        for object_type, required in (
            ("table", REQUIRED_TABLES),
            ("index", REQUIRED_INDEXES),
            ("trigger", REQUIRED_TRIGGERS),
        ):
            missing = sorted(required - schema_by_type.get(object_type, set()))
            if missing:
                raise CareerDataError(f"Missing required {object_type} objects: {', '.join(missing)}")
        controls = connection.execute(
            "SELECT collection_enabled, publication_enabled FROM system_controls WHERE singleton = 1"
        ).fetchone()
        if controls is None or controls["collection_enabled"] not in (0, 1) or controls["publication_enabled"] not in (0, 1):
            raise CareerDataError("Collection/publication controls are invalid")
        applied = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
        if len(applied) != len(migrations):
            raise CareerDataError("Not all repository migrations are applied")
        for migration, row in zip(migrations, applied, strict=True):
            if (
                row["version"] != migration["version"]
                or row["name"] != migration["name"]
                or row["checksum"] != migration["checksum"]
            ):
                raise CareerDataError(f"Migration verification failed for version {migration['version']}")
        domain_counts = {
            table: connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            for table in DOMAIN_TABLES
        }
        return {
            "integrity": "ok",
            "currentVersion": migrations[-1]["version"],
            "collectionEnabled": bool(controls["collection_enabled"]),
            "publicationEnabled": bool(controls["publication_enabled"]),
            "domainCounts": domain_counts,
            "mode": "0600",
        }
    finally:
        connection.close()


def set_safety_controls(
    database_path: str | Path,
    *,
    collection_enabled: bool | None,
    publication_enabled: bool | None,
    reason: str,
    actor: str,
) -> dict[str, Any]:
    if collection_enabled is None and publication_enabled is None:
        raise CareerDataError("At least one safety control must be explicitly specified")
    if not reason.strip() or not actor.strip():
        raise CareerDataError("Safety-control changes require a reason and actor")
    path = assert_external_path(database_path, "Database path")
    validate_database(path)
    connection = connect_database(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT collection_enabled, publication_enabled FROM system_controls WHERE singleton = 1"
        ).fetchone()
        connection.execute("""
            UPDATE system_controls
            SET collection_enabled = ?, publication_enabled = ?, change_reason = ?,
                updated_by = ?, updated_at = ?
            WHERE singleton = 1
        """, (
            int(collection_enabled) if collection_enabled is not None else current["collection_enabled"],
            int(publication_enabled) if publication_enabled is not None else current["publication_enabled"],
            reason.strip(),
            actor.strip(),
            utc_now(),
        ))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return validate_database(path)


def _atomic_non_overwriting_install(temporary_file: Path, destination: Path) -> None:
    try:
        os.link(temporary_file, destination)
    except FileExistsError as error:
        raise CareerDataError(f"Destination already exists: {destination}") from error


def backup_database(database_path: str | Path, destination_path: str | Path) -> dict[str, Any]:
    source_path = assert_external_path(database_path, "Database path")
    destination = assert_external_path(destination_path, "Backup destination")
    if destination.exists():
        raise CareerDataError(f"Backup destination already exists: {destination}")
    validate_database(source_path)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary_directory = Path(tempfile.mkdtemp(prefix=".backup-tmp-", dir=destination.parent))
    temporary_file = temporary_directory / "backup.sqlite3"
    try:
        source = connect_database(source_path)
        target = sqlite3.connect(temporary_file)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        os.chmod(temporary_file, 0o600)
        validation = validate_database(temporary_file)
        _atomic_non_overwriting_install(temporary_file, destination)
        return {"backup": str(destination), "validation": validation}
    finally:
        shutil.rmtree(temporary_directory, ignore_errors=True)


def restore_database(backup_path: str | Path, destination_path: str | Path) -> dict[str, Any]:
    backup = assert_external_path(backup_path, "Backup path")
    destination = assert_external_path(destination_path, "Restore destination")
    if destination.exists():
        raise CareerDataError(f"Restore destination already exists: {destination}")
    validate_database(backup)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary_directory = Path(tempfile.mkdtemp(prefix=".restore-tmp-", dir=destination.parent))
    temporary_file = temporary_directory / "restored.sqlite3"
    try:
        shutil.copyfile(backup, temporary_file)
        os.chmod(temporary_file, 0o600)
        validation = validate_database(temporary_file)
        _atomic_non_overwriting_install(temporary_file, destination)
        return {"restored": str(destination), "validation": validation}
    finally:
        shutil.rmtree(temporary_directory, ignore_errors=True)


def _decode_json(value: str | None, fallback: Any) -> Any:
    return json.loads(value) if value is not None else fallback


def _public_snapshot_rows(connection: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    companies = [
        {
            "id": row["company_id"],
            "name": row["display_name"],
            "countryCode": row["country_code"],
            "regions": _decode_json(row["regions_json"], []),
            "websiteUrl": row["official_website_url"],
            "careerUrl": row["official_career_url"],
        }
        for row in connection.execute("""
            SELECT DISTINCT c.company_id, c.display_name, c.country_code, c.regions_json,
                   c.official_website_url, c.official_career_url
            FROM companies c
            JOIN job_postings j ON j.company_id = c.company_id
            WHERE c.verification_status = 'verified'
              AND j.publication_status = 'published'
              AND j.quality_status = 'published'
              AND j.review_status = 'approved'
            ORDER BY c.company_id
        """)
    ]
    jobs = [
        {
            "id": row["job_id"],
            "companyId": row["company_id"],
            "title": row["normalized_title"] or row["source_title"],
            "location": row["location_text"],
            "countryCode": row["country_code"],
            "region": row["region"],
            "employmentType": row["employment_type"],
            "jobFamily": row["job_family_key"],
            "sourceUrl": row["source_url"],
            "postedAt": row["source_posted_at"],
            "updatedAt": row["source_updated_at"],
            "status": row["lifecycle_status"],
        }
        for row in connection.execute("""
            SELECT job_id, company_id, source_title, normalized_title, location_text,
                   country_code, region, employment_type, job_family_key, source_url,
                   source_posted_at, source_updated_at, lifecycle_status
            FROM job_postings
            WHERE publication_status = 'published'
              AND quality_status = 'published'
              AND review_status = 'approved'
            ORDER BY job_id
        """)
    ]
    skills: list[dict[str, Any]] = []
    for row in connection.execute("""
        SELECT DISTINCT s.skill_id, s.canonical_name, s.category, s.definition,
               s.evidence_expectations
        FROM skills s
        JOIN job_skill_relations r ON r.skill_id = s.skill_id
        JOIN job_postings j ON j.job_id = r.job_id
        WHERE s.lifecycle_status = 'active' AND s.review_status = 'approved'
          AND r.review_status = 'approved'
          AND j.publication_status = 'published'
          AND j.quality_status = 'published'
          AND j.review_status = 'approved'
        ORDER BY s.skill_id
    """):
        aliases = [
            alias["alias"]
            for alias in connection.execute("""
                SELECT alias FROM skill_aliases
                WHERE skill_id = ? AND lifecycle_status = 'active' AND review_status = 'approved'
                ORDER BY language_code, alias
            """, (row["skill_id"],))
        ]
        skills.append({
            "id": row["skill_id"],
            "name": row["canonical_name"],
            "aliases": aliases,
            "category": row["category"],
            "definition": row["definition"],
            "evidenceExpectations": row["evidence_expectations"],
        })
    role_summary: list[dict[str, Any]] = []
    for row in connection.execute("""
        SELECT job_family_key, count(*) AS job_count, count(DISTINCT company_id) AS company_count
        FROM job_postings
        WHERE publication_status = 'published'
          AND quality_status = 'published'
          AND review_status = 'approved'
          AND job_family_key IS NOT NULL
        GROUP BY job_family_key
        ORDER BY job_family_key
    """):
        skill_ids = [
            skill["skill_id"]
            for skill in connection.execute("""
                SELECT DISTINCT r.skill_id
                FROM job_skill_relations r
                JOIN job_postings j ON j.job_id = r.job_id
                WHERE j.job_family_key = ?
                  AND j.publication_status = 'published'
                  AND j.quality_status = 'published'
                  AND j.review_status = 'approved'
                  AND r.review_status = 'approved'
                ORDER BY r.skill_id
            """, (row["job_family_key"],))
        ]
        role_summary.append({
            "role": row["job_family_key"],
            "jobCount": row["job_count"],
            "companyCount": row["company_count"],
            "skillIds": skill_ids,
        })
    project_templates: list[dict[str, Any]] = []
    for row in connection.execute("""
        SELECT project_template_id, slug, title, summary, difficulty,
               estimated_effort_hours, prerequisites_text, deliverables_json,
               acceptance_evidence_json, safety_notes, license_notes
        FROM project_templates
        WHERE lifecycle_status = 'approved' AND review_status = 'approved'
        ORDER BY project_template_id
    """):
        job_families = [
            target["job_family_key"]
            for target in connection.execute("""
                SELECT job_family_key FROM project_template_job_families
                WHERE project_template_id = ? ORDER BY job_family_key
            """, (row["project_template_id"],))
        ]
        skill_ids = [
            target["skill_id"]
            for target in connection.execute("""
                SELECT skill_id FROM project_template_skills
                WHERE project_template_id = ? ORDER BY skill_id
            """, (row["project_template_id"],))
        ]
        project_templates.append({
            "id": row["project_template_id"],
            "slug": row["slug"],
            "title": row["title"],
            "summary": row["summary"],
            "difficulty": row["difficulty"],
            "estimatedEffortHours": row["estimated_effort_hours"],
            "prerequisites": row["prerequisites_text"],
            "deliverables": _decode_json(row["deliverables_json"], []),
            "acceptanceEvidence": _decode_json(row["acceptance_evidence_json"], []),
            "safetyNotes": row["safety_notes"],
            "licenseNotes": row["license_notes"],
            "targetJobFamilies": job_families,
            "skillIds": skill_ids,
        })
    return {
        "companies.json": companies,
        "jobs.json": jobs,
        "skills.json": skills,
        "role-summary.json": role_summary,
        "project-templates.json": project_templates,
    }


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, 0o600)


def _walk_public_value(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_PUBLIC_KEYS.intersection(value)
        if forbidden:
            raise CareerDataError(f"Forbidden public fields: {', '.join(sorted(forbidden))}")
        for key, nested in value.items():
            lowered = key.lower()
            if "error" in lowered or "confidence" in lowered or "raw_snapshot" in lowered or "local_path" in lowered:
                raise CareerDataError(f"Forbidden public field: {key}")
            _walk_public_value(nested)
    elif isinstance(value, list):
        for nested in value:
            _walk_public_value(nested)
    elif isinstance(value, str) and (value.startswith("/") or value.startswith("file://")):
        raise CareerDataError("Local filesystem paths are forbidden in public snapshots")


def validate_snapshot_directory(snapshot_directory: Path) -> dict[str, Any]:
    if snapshot_directory.is_symlink() or not snapshot_directory.is_dir():
        raise CareerDataError("Snapshot version must be an ordinary directory")
    expected = {"manifest.json", *PUBLIC_FILES}
    actual = {path.name for path in snapshot_directory.iterdir()}
    if actual != expected:
        raise CareerDataError("Snapshot file inventory is incomplete or contains unexpected files")
    if any(path.is_symlink() or not path.is_file() for path in snapshot_directory.iterdir()):
        raise CareerDataError("Snapshot files must be ordinary files")
    manifest = json.loads((snapshot_directory / "manifest.json").read_text(encoding="utf-8"))
    if set(manifest) != {"format", "schemaVersion", "generatedAt", "files"}:
        raise CareerDataError("Snapshot manifest fields are invalid")
    if manifest["format"] != "robotcareer-career-public-snapshot" or manifest["schemaVersion"] != 1:
        raise CareerDataError("Snapshot manifest version is invalid")
    if set(manifest["files"]) != set(PUBLIC_FILES):
        raise CareerDataError("Snapshot manifest file inventory is invalid")
    for filename in PUBLIC_FILES:
        content = (snapshot_directory / filename).read_bytes()
        metadata = manifest["files"][filename]
        if set(metadata) != {"sha256", "records"}:
            raise CareerDataError(f"Snapshot metadata fields are invalid for {filename}")
        if hashlib.sha256(content).hexdigest() != metadata["sha256"]:
            raise CareerDataError(f"Snapshot checksum failed for {filename}")
        rows = json.loads(content)
        if not isinstance(rows, list) or len(rows) != metadata["records"]:
            raise CareerDataError(f"Snapshot record count failed for {filename}")
        whitelist = PUBLIC_FIELD_WHITELISTS[filename]
        for row in rows:
            if not isinstance(row, dict) or set(row) != whitelist:
                raise CareerDataError(f"Public field whitelist failed for {filename}")
            _walk_public_value(row)
    return manifest


def _validate_current_pointer(snapshot_root: Path, pointer_path: Path) -> dict[str, Any]:
    if pointer_path.is_symlink() or not pointer_path.is_file():
        raise CareerDataError("current.json must be an ordinary file")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if set(pointer) != {"version", "manifest"}:
        raise CareerDataError("current.json fields are invalid")
    version_relative = Path(pointer["version"])
    manifest_relative = Path(pointer["manifest"])
    if version_relative.is_absolute() or manifest_relative.is_absolute() or ".." in version_relative.parts or ".." in manifest_relative.parts:
        raise CareerDataError("current.json must use repository-relative paths")
    version_directory = (snapshot_root / version_relative).resolve(strict=True)
    manifest_path = (snapshot_root / manifest_relative).resolve(strict=True)
    if not _is_within(snapshot_root, version_directory) or not _is_within(version_directory, manifest_path):
        raise CareerDataError("current.json points outside the repository snapshot root")
    if any(path.is_symlink() for path in (snapshot_root, snapshot_root / "versions", version_directory, manifest_path)):
        raise CareerDataError("Public snapshot pointers and targets must not use symlinks")
    manifest = validate_snapshot_directory(version_directory)
    if manifest_path != version_directory / "manifest.json":
        raise CareerDataError("current.json manifest path is invalid")
    return {"pointer": pointer, "manifest": manifest}


def validate_public_snapshot(snapshot_root: str | Path) -> dict[str, Any]:
    root = assert_public_snapshot_path(snapshot_root)
    if not root.is_dir() or root.is_symlink():
        raise CareerDataError("Public snapshot root must be an ordinary repository directory")
    return _validate_current_pointer(root, root / "current.json")


def publish_public_snapshot(
    database_path: str | Path,
    snapshot_root: str | Path,
    *,
    replace: bool = False,
    snapshot_established_hook: Callable[[], None] | None = None,
) -> dict[str, Any]:
    database = assert_external_path(database_path, "Database path")
    root = assert_public_snapshot_path(snapshot_root)
    validation = validate_database(database)
    current_path = root / "current.json"
    if current_path.exists() and not replace:
        raise CareerDataError("Public snapshot already exists; pass --replace explicitly")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    versions = root / "versions"
    versions.mkdir(exist_ok=True, mode=0o700)
    temporary_directory = Path(tempfile.mkdtemp(prefix=".snapshot-tmp-", dir=versions))
    temporary_pointer: Path | None = None
    final_directory: Path | None = None
    pointer_switched = False
    try:
        connection = connect_database(database)
        try:
            connection.execute("BEGIN")
            controls = connection.execute(
                "SELECT publication_enabled FROM system_controls WHERE singleton = 1"
            ).fetchone()
            if controls["publication_enabled"] != 1:
                raise CareerDataError("Public snapshot publication is disabled")
            connection.execute("SELECT max(version) FROM schema_migrations").fetchone()
            if snapshot_established_hook:
                snapshot_established_hook()
            rows_by_file = _public_snapshot_rows(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        file_metadata: dict[str, dict[str, Any]] = {}
        digest_source = hashlib.sha256()
        for filename in PUBLIC_FILES:
            content = _json_bytes(rows_by_file[filename])
            _write_bytes(temporary_directory / filename, content)
            checksum = hashlib.sha256(content).hexdigest()
            file_metadata[filename] = {"sha256": checksum, "records": len(rows_by_file[filename])}
            digest_source.update(filename.encode("utf-8"))
            digest_source.update(content)
        generated_at = utc_now()
        manifest = {
            "format": "robotcareer-career-public-snapshot",
            "schemaVersion": 1,
            "generatedAt": generated_at,
            "files": file_metadata,
        }
        _write_bytes(temporary_directory / "manifest.json", _json_bytes(manifest))
        validate_snapshot_directory(temporary_directory)
        version_name = (
            f"snapshot-{generated_at.replace(':', '').replace('-', '').replace('.', '')}-"
            f"{digest_source.hexdigest()[:12]}"
        )
        final_directory = versions / version_name
        if final_directory.exists():
            raise CareerDataError(f"Snapshot version already exists: {version_name}")
        os.replace(temporary_directory, final_directory)
        pointer = {
            "version": f"versions/{version_name}",
            "manifest": f"versions/{version_name}/manifest.json",
        }
        pointer_fd, pointer_name = tempfile.mkstemp(prefix=".current-", suffix=".tmp", dir=root)
        temporary_pointer = Path(pointer_name)
        try:
            with os.fdopen(pointer_fd, "wb") as handle:
                handle.write(_json_bytes(pointer))
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_pointer, 0o600)
            _validate_current_pointer(root, temporary_pointer)
            os.replace(temporary_pointer, current_path)
            pointer_switched = True
        finally:
            if temporary_pointer.exists():
                temporary_pointer.unlink()
        published = validate_public_snapshot(root)
        return {
            "snapshot": version_name,
            "current": str(current_path),
            "databaseValidation": validation,
            "snapshotValidation": published,
        }
    finally:
        if temporary_directory.exists():
            shutil.rmtree(temporary_directory, ignore_errors=True)
        if final_directory and final_directory.exists() and not pointer_switched:
            shutil.rmtree(final_directory, ignore_errors=True)


def _parse_switch(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "enabled"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    runtime_init = subparsers.add_parser("runtime-init")
    runtime_init.add_argument("--root", required=True)
    runtime_validate = subparsers.add_parser("runtime-validate")
    runtime_validate.add_argument("--root", required=True)
    for command in ("migrate", "validate"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--database", required=True)
    controls = subparsers.add_parser("controls")
    controls.add_argument("--database", required=True)
    controls.add_argument("--collection", choices=("enabled", "disabled"))
    controls.add_argument("--publication", choices=("enabled", "disabled"))
    controls.add_argument("--reason", required=True)
    controls.add_argument("--actor", default="career-db-cli")
    backup = subparsers.add_parser("backup")
    backup.add_argument("--database", required=True)
    backup.add_argument("--output", required=True)
    restore = subparsers.add_parser("restore")
    restore.add_argument("--backup", required=True)
    restore.add_argument("--database", required=True)
    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--database", required=True)
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--replace", action="store_true")
    snapshot_validate = subparsers.add_parser("snapshot-validate")
    snapshot_validate.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "runtime-init":
        result = initialize_runtime(args.root)
    elif args.command == "runtime-validate":
        result = validate_runtime(args.root)
    elif args.command == "migrate":
        result = migrate_database(args.database)
    elif args.command == "validate":
        result = validate_database(args.database)
    elif args.command == "controls":
        result = set_safety_controls(
            args.database,
            collection_enabled=_parse_switch(args.collection),
            publication_enabled=_parse_switch(args.publication),
            reason=args.reason,
            actor=args.actor,
        )
    elif args.command == "backup":
        result = backup_database(args.database, args.output)
    elif args.command == "restore":
        result = restore_database(args.backup, args.database)
    elif args.command == "snapshot":
        result = publish_public_snapshot(args.database, args.output, replace=args.replace)
    elif args.command == "snapshot-validate":
        result = validate_public_snapshot(args.output)
    else:
        raise CareerDataError(f"Unsupported command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CareerDataError, sqlite3.Error) as error:
        print(f"career-db: {error}", file=sys.stderr)
        raise SystemExit(1) from error

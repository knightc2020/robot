from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import career_db


FIXED_TIME = "2026-07-18T06:30:00.000Z"


class CareerDatabaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="career-db-phase21-")
        self.root = Path(self.temporary.name) / "runtime"
        career_db.initialize_runtime(self.root)
        self.database = self.root / "staging" / "career.sqlite3"
        career_db.migrate_database(self.database)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def enable_publication(self) -> None:
        career_db.set_safety_controls(
            self.database,
            collection_enabled=None,
            publication_enabled=True,
            reason="Enable disposable public-snapshot test",
            actor="career_db_test",
        )

    def insert_public_fixture(self) -> None:
        connection = career_db.connect_database(self.database)
        try:
            connection.execute("""
                INSERT INTO companies(
                  company_id, legal_name, display_name, country_code, regions_json,
                  official_website_url, official_career_url, lifecycle_status,
                  verification_status, verified_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 'verified', ?, ?, ?)
            """, (
                "fixture-company", "Fixture Company", "Fixture Company", "SG", '["Singapore"]',
                "https://company.example.invalid", "https://company.example.invalid/careers",
                FIXED_TIME, FIXED_TIME, FIXED_TIME,
            ))
            connection.execute("""
                INSERT INTO career_sources(
                  source_id, company_id, source_url, source_type, collection_method,
                  owner, verified_at, created_at, updated_at
                ) VALUES (?, ?, ?, 'official_career_page', ?, ?, ?, ?, ?)
            """, (
                "fixture-source", "fixture-company", "https://company.example.invalid/careers",
                "fixture-adapter", "internal-owner", FIXED_TIME, FIXED_TIME, FIXED_TIME,
            ))
            connection.execute("""
                INSERT INTO job_postings(
                  job_id, company_id, source_id, source_native_id, source_url,
                  source_title, normalized_title, description_text, location_text,
                  country_code, region, employment_type, job_family_key,
                  source_posted_at, source_updated_at, first_collected_at,
                  last_collected_at, lifecycle_status, content_hash, raw_snapshot_ref,
                  parser_version, extraction_metadata_json, quality_status,
                  review_status, reviewed_by, reviewed_at, publication_status,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          'active', ?, ?, ?, ?, 'published', 'approved', ?, ?,
                          'published', ?, ?)
            """, (
                "fixture-job", "fixture-company", "fixture-source", "native-fixture-job",
                "https://company.example.invalid/jobs/fixture", "Internal source title",
                "Robotics Test Engineer", "Internal description must not be exported",
                "Singapore", "SG", "Singapore", "full_time", "robotics-test",
                FIXED_TIME, FIXED_TIME, FIXED_TIME, FIXED_TIME, "a" * 64,
                "/root/robot-data/raw/fixture-job.html", "fixture-parser-v1",
                '{"internal": true}', "internal-reviewer", FIXED_TIME, FIXED_TIME, FIXED_TIME,
            ))
            connection.execute("""
                INSERT INTO skills(
                  skill_id, canonical_name, category, definition, evidence_expectations,
                  lifecycle_status, review_status, reviewed_by, reviewed_at,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'active', 'approved', ?, ?, ?, ?)
            """, (
                "fixture-skill", "Fixture Skill", "testing", "Public definition",
                "Public evidence expectations", "internal-reviewer", FIXED_TIME,
                FIXED_TIME, FIXED_TIME,
            ))
            connection.execute("""
                INSERT INTO skill_aliases(
                  skill_id, alias, language_code, lifecycle_status, review_status,
                  reviewed_by, reviewed_at, created_at, updated_at
                ) VALUES (?, ?, 'en', 'active', 'approved', ?, ?, ?, ?)
            """, (
                "fixture-skill", "Fixture Alias", "internal-reviewer", FIXED_TIME,
                FIXED_TIME, FIXED_TIME,
            ))
            connection.execute("""
                INSERT INTO job_skill_relations(
                  job_id, skill_id, requirement_strength, evidence_excerpt,
                  parser_confidence, extraction_method, extraction_version,
                  review_status, reviewed_by, reviewed_at, first_observed_at,
                  last_observed_at
                ) VALUES (?, ?, 'required', ?, 0.99, 'model_assisted', ?,
                          'approved', ?, ?, ?, ?)
            """, (
                "fixture-job", "fixture-skill", "Internal evidence excerpt",
                "internal-extractor-v1", "internal-reviewer", FIXED_TIME,
                FIXED_TIME, FIXED_TIME,
            ))
            connection.execute("""
                INSERT INTO project_templates(
                  project_template_id, slug, title, summary, difficulty,
                  estimated_effort_hours, prerequisites_text, deliverables_json,
                  acceptance_evidence_json, safety_notes, license_notes,
                  lifecycle_status, review_status, reviewed_by, reviewed_at,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'introductory', 8, ?, ?, ?, ?, ?,
                          'approved', 'approved', ?, ?, ?, ?)
            """, (
                "fixture-project", "fixture-project", "Fixture Project",
                "Public project summary", "Public prerequisites", '["Deliverable"]',
                '["Evidence"]', "Safety note", "License note", "internal-reviewer",
                FIXED_TIME, FIXED_TIME, FIXED_TIME,
            ))
            connection.execute("""
                INSERT INTO project_template_job_families(project_template_id, job_family_key)
                VALUES ('fixture-project', 'robotics-test')
            """)
            connection.execute("""
                INSERT INTO project_template_skills(
                  project_template_id, skill_id, evidence_expectation
                ) VALUES ('fixture-project', 'fixture-skill', 'Internal relation evidence')
            """)
        finally:
            connection.close()

    def test_runtime_paths_permissions_and_empty_database(self) -> None:
        runtime = career_db.validate_runtime(self.root)
        self.assertEqual(runtime["checked"][str(self.database)], "0600")
        validation = career_db.validate_database(self.database)
        self.assertEqual(validation["currentVersion"], 3)
        self.assertFalse(validation["collectionEnabled"])
        self.assertFalse(validation["publicationEnabled"])
        self.assertTrue(all(count == 0 for count in validation["domainCounts"].values()))
        for name in career_db.RUNTIME_DIRECTORY_NAMES:
            self.assertEqual(career_db._mode(self.root / name), 0o700)

    def test_database_paths_are_external_and_protected(self) -> None:
        with self.assertRaises(career_db.CareerDataError):
            career_db.assert_external_path("relative.sqlite3", "Database")
        with self.assertRaises(career_db.CareerDataError):
            career_db.assert_external_path(career_db.REPOSITORY_ROOT / "local.sqlite3", "Database")
        with self.assertRaises(career_db.CareerDataError):
            career_db.assert_external_path("/root/robot/career.sqlite3", "Database")
        self.assertEqual(
            career_db.assert_external_path(self.database, "Database"), self.database.resolve()
        )

    def test_migration_is_idempotent_and_checksum_is_enforced(self) -> None:
        self.assertEqual(career_db.migrate_database(self.database)["applied"], [])
        connection = career_db.connect_database(self.database)
        try:
            connection.execute("UPDATE schema_migrations SET checksum = ? WHERE version = 2", ("0" * 64,))
        finally:
            connection.close()
        with self.assertRaisesRegex(career_db.CareerDataError, "Migration verification failed"):
            career_db.validate_database(self.database)

    def test_versioned_contracts_physical_schema_and_integrity_constraints(self) -> None:
        schema_path = career_db.REPOSITORY_ROOT / "career-intelligence/schema/v1/entities.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        entity_definitions = (
            "company", "career_source", "job_posting", "skill",
            "job_skill_relation", "job_change", "project_template",
        )
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(len(schema["oneOf"]), len(entity_definitions))
        for entity in entity_definitions:
            self.assertFalse(schema["$defs"][entity]["additionalProperties"])
            self.assertTrue(schema["$defs"][entity]["required"])

        connection = career_db.connect_database(self.database)
        try:
            tables = {
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            self.assertTrue(career_db.REQUIRED_TABLES.issubset(tables))
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("""
                    INSERT INTO job_postings(
                      job_id, company_id, source_id, source_native_id, source_url,
                      source_title, first_collected_at, last_collected_at,
                      content_hash, raw_snapshot_ref, parser_version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "invalid-job", "unknown-company", "unknown-source", "invalid-native-id",
                    "https://example.invalid/jobs/invalid", "Invalid fixture", FIXED_TIME,
                    FIXED_TIME, "b" * 64, "/tmp/invalid-fixture", "fixture-parser-v1",
                    FIXED_TIME, FIXED_TIME,
                ))
        finally:
            connection.close()

        with self.assertRaisesRegex(career_db.CareerDataError, "publication is disabled"):
            snapshot_root = Path(self.temporary.name) / "repo" / "src" / "data" / "career-public"
            with patch.object(career_db, "PUBLIC_SNAPSHOT_ROOT", snapshot_root):
                career_db.publish_public_snapshot(self.database, snapshot_root)

    def test_controls_are_independent_audited_and_job_history_is_append_only(self) -> None:
        career_db.set_safety_controls(
            self.database,
            collection_enabled=True,
            publication_enabled=None,
            reason="Test collection independently",
            actor="career_db_test",
        )
        validation = career_db.validate_database(self.database)
        self.assertTrue(validation["collectionEnabled"])
        self.assertFalse(validation["publicationEnabled"])
        career_db.set_safety_controls(
            self.database,
            collection_enabled=False,
            publication_enabled=True,
            reason="Test publication independently",
            actor="career_db_test",
        )
        connection = career_db.connect_database(self.database)
        try:
            events = connection.execute(
                "SELECT collection_enabled, publication_enabled, change_reason, changed_by "
                "FROM system_control_events ORDER BY event_id"
            ).fetchall()
            self.assertEqual(len(events), 2)
            self.assertEqual(tuple(events[0]), (1, 0, "Test collection independently", "career_db_test"))
            self.assertEqual(tuple(events[1]), (0, 1, "Test publication independently", "career_db_test"))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "audit metadata"):
                connection.execute(
                    "UPDATE system_controls SET collection_enabled = 1 WHERE singleton = 1"
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "cannot be deleted"):
                connection.execute("DELETE FROM system_controls WHERE singleton = 1")
        finally:
            connection.close()

        self.insert_public_fixture()
        connection = career_db.connect_database(self.database)
        try:
            connection.execute("""
                INSERT INTO job_changes(
                  change_id, job_id, source_id, change_type, new_content_hash,
                  observed_at, source_url, collected_at, raw_snapshot_ref,
                  retrieval_result, created_at
                ) VALUES (?, ?, ?, 'first_observed', ?, ?, ?, ?, ?, 'success', ?)
            """, (
                "fixture-change", "fixture-job", "fixture-source", "a" * 64,
                FIXED_TIME, "https://company.example.invalid/jobs/fixture", FIXED_TIME,
                "/root/robot-data/raw/fixture-job.html", FIXED_TIME,
            ))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute(
                    "UPDATE job_changes SET change_type = 'closed' WHERE change_id = 'fixture-change'"
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute("DELETE FROM job_changes WHERE change_id = 'fixture-change'")
        finally:
            connection.close()

    def test_empty_public_snapshot_has_explicit_files_and_no_symlinks(self) -> None:
        self.enable_publication()
        snapshot_root = Path(self.temporary.name) / "repo" / "src" / "data" / "career-public"
        with patch.object(career_db, "PUBLIC_SNAPSHOT_ROOT", snapshot_root):
            result = career_db.publish_public_snapshot(self.database, snapshot_root)
            self.assertTrue((snapshot_root / "current.json").is_file())
            self.assertFalse((snapshot_root / "current.json").is_symlink())
            validation = career_db.validate_public_snapshot(snapshot_root)
            self.assertEqual(validation["manifest"]["schemaVersion"], 1)
            version = snapshot_root / validation["pointer"]["version"]
            self.assertEqual(
                {path.name for path in version.iterdir()}, {"manifest.json", *career_db.PUBLIC_FILES}
            )
            for filename in career_db.PUBLIC_FILES:
                self.assertEqual(json.loads((version / filename).read_text()), [])
            self.assertEqual(result["snapshotValidation"]["manifest"]["format"], "robotcareer-career-public-snapshot")

    def test_public_whitelists_exclude_internal_fields_and_paths(self) -> None:
        self.insert_public_fixture()
        self.enable_publication()
        snapshot_root = Path(self.temporary.name) / "repo" / "src" / "data" / "career-public"
        with patch.object(career_db, "PUBLIC_SNAPSHOT_ROOT", snapshot_root):
            career_db.publish_public_snapshot(self.database, snapshot_root)
            validation = career_db.validate_public_snapshot(snapshot_root)
            version = snapshot_root / validation["pointer"]["version"]
            combined = ""
            for filename in career_db.PUBLIC_FILES:
                rows = json.loads((version / filename).read_text())
                for row in rows:
                    self.assertEqual(set(row), career_db.PUBLIC_FIELD_WHITELISTS[filename])
                combined += json.dumps(rows)
            for forbidden in (
                "raw_snapshot", "content_hash", "internal-reviewer", "parser_confidence",
                "extraction_metadata", "/root/", "Internal description", "Internal evidence"
            ):
                self.assertNotIn(forbidden, combined)
            skills = json.loads((version / "skills.json").read_text())
            projects = json.loads((version / "project-templates.json").read_text())
            self.assertEqual(skills[0]["aliases"], ["Fixture Alias"])
            self.assertEqual(projects[0]["targetJobFamilies"], ["robotics-test"])
            self.assertEqual(projects[0]["skillIds"], ["fixture-skill"])

    def test_snapshot_uses_consistent_view_and_atomic_current_file(self) -> None:
        self.insert_public_fixture()
        self.enable_publication()
        snapshot_root = Path(self.temporary.name) / "repo" / "src" / "data" / "career-public"

        def concurrent_update() -> None:
            connection = career_db.connect_database(self.database)
            try:
                connection.execute(
                    "UPDATE project_templates SET title = ?, updated_at = ? WHERE project_template_id = ?",
                    ("Updated Fixture Project", "2026-07-18T06:31:00.000Z", "fixture-project"),
                )
            finally:
                connection.close()

        with patch.object(career_db, "PUBLIC_SNAPSHOT_ROOT", snapshot_root):
            first = career_db.publish_public_snapshot(
                self.database, snapshot_root, snapshot_established_hook=concurrent_update
            )
            first_pointer = json.loads((snapshot_root / "current.json").read_text())
            first_projects = json.loads(
                (snapshot_root / first_pointer["version"] / "project-templates.json").read_text()
            )
            self.assertEqual(first_projects[0]["title"], "Fixture Project")
            with self.assertRaisesRegex(career_db.CareerDataError, "--replace"):
                career_db.publish_public_snapshot(self.database, snapshot_root)
            second = career_db.publish_public_snapshot(self.database, snapshot_root, replace=True)
            second_pointer = json.loads((snapshot_root / "current.json").read_text())
            self.assertNotEqual(first["snapshot"], second["snapshot"])
            self.assertNotEqual(first_pointer, second_pointer)
            second_projects = json.loads(
                (snapshot_root / second_pointer["version"] / "project-templates.json").read_text()
            )
            self.assertEqual(second_projects[0]["title"], "Updated Fixture Project")
            self.assertFalse(any(path.name.startswith(".snapshot-tmp-") for path in (snapshot_root / "versions").iterdir()))
            self.assertFalse(any(path.name.startswith(".current-") for path in snapshot_root.iterdir()))

    def test_wal_busy_timeout_concurrent_readers_and_migration_lock(self) -> None:
        reader_one = career_db.connect_database(self.database)
        reader_two = career_db.connect_database(self.database)
        writer = career_db.connect_database(self.database)
        try:
            self.assertEqual(reader_one.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(reader_one.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
            writer.execute("BEGIN IMMEDIATE")
            writer.execute(
                "INSERT INTO companies(company_id, legal_name, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                ("uncommitted", "Uncommitted", "Uncommitted", FIXED_TIME, FIXED_TIME),
            )
            self.assertEqual(reader_one.execute("SELECT count(*) FROM companies").fetchone()[0], 0)
            self.assertEqual(reader_two.execute("SELECT count(*) FROM companies").fetchone()[0], 0)
            writer.commit()
            self.assertEqual(reader_one.execute("SELECT count(*) FROM companies").fetchone()[0], 1)
            self.assertEqual(reader_two.execute("SELECT count(*) FROM companies").fetchone()[0], 1)
        finally:
            writer.close()
            reader_two.close()
            reader_one.close()

        ready = threading.Event()

        def lock_holder() -> None:
            connection = career_db.connect_database(self.database)
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO companies(company_id, legal_name, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    ("writer-one", "Writer One", "Writer One", FIXED_TIME, FIXED_TIME),
                )
                ready.set()
                time.sleep(0.3)
                connection.commit()
            finally:
                connection.close()

        thread = threading.Thread(target=lock_holder)
        thread.start()
        self.assertTrue(ready.wait(timeout=2))
        waiting_writer = career_db.connect_database(self.database)
        started = time.monotonic()
        try:
            waiting_writer.execute(
                "INSERT INTO companies(company_id, legal_name, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                ("writer-two", "Writer Two", "Writer Two", FIXED_TIME, FIXED_TIME),
            )
        finally:
            waiting_writer.close()
        self.assertGreaterEqual(time.monotonic() - started, 0.15)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

        migration_connection = career_db.connect_database(self.database)
        competitor = career_db.connect_database(self.database)
        try:
            migration_connection.execute("BEGIN IMMEDIATE")
            competitor.execute("PRAGMA busy_timeout = 50")
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                competitor.execute(
                    "INSERT INTO companies(company_id, legal_name, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    ("blocked", "Blocked", "Blocked", FIXED_TIME, FIXED_TIME),
                )
            migration_connection.rollback()
        finally:
            competitor.close()
            migration_connection.close()

    def test_backup_restore_permissions_and_non_overwrite(self) -> None:
        backup = self.root / "backups" / "career.sqlite3"
        restored = self.root / "staging" / "restored.sqlite3"
        backup_result = career_db.backup_database(self.database, backup)
        self.assertEqual(backup_result["validation"]["integrity"], "ok")
        self.assertEqual(career_db._mode(backup), 0o600)
        restore_result = career_db.restore_database(backup, restored)
        self.assertEqual(restore_result["validation"]["integrity"], "ok")
        self.assertEqual(career_db._mode(restored), 0o600)
        self.assertEqual(career_db.validate_database(restored), restore_result["validation"])
        with self.assertRaisesRegex(career_db.CareerDataError, "already exists"):
            career_db.backup_database(self.database, backup)
        with self.assertRaisesRegex(career_db.CareerDataError, "already exists"):
            career_db.restore_database(backup, restored)

    def test_public_output_is_repository_owned(self) -> None:
        outside = Path(self.temporary.name) / "outside"
        with self.assertRaisesRegex(career_db.CareerDataError, "repository-owned"):
            career_db.assert_public_snapshot_path(outside)


class RepositorySnapshotIntegrationTest(unittest.TestCase):
    def test_astro_uses_only_repository_snapshot_files(self) -> None:
        loader = (career_db.REPOSITORY_ROOT / "src/lib/career-public-snapshot.ts").read_text()
        self.assertIn("import.meta.glob", loader)
        self.assertNotIn("node:fs", loader)
        self.assertNotIn("/root/robot-data", loader)
        for page in (
            "src/pages/cn/career/index.astro",
            "src/pages/en/career/index.astro",
        ):
            source = (career_db.REPOSITORY_ROOT / page).read_text()
            self.assertIn("careerPublicSnapshot", source)
            self.assertNotIn("/root/robot-data", source)
        validation = career_db.validate_public_snapshot(career_db.PUBLIC_SNAPSHOT_ROOT)
        self.assertEqual(validation["manifest"]["format"], "robotcareer-career-public-snapshot")
        for path in career_db.PUBLIC_SNAPSHOT_ROOT.rglob("*"):
            self.assertFalse(path.is_symlink(), str(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)

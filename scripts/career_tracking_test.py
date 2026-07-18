"""Offline Phase 3B baseline and change-tracking regression tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import career_db  # noqa: E402
from career_sources.http_client import AccessBlockedError, HttpPage  # noqa: E402
from career_sources.service import register_company, register_source, verify_source  # noqa: E402
from career_sources.staging import StagingError  # noqa: E402
from career_sources.tracking import (  # noqa: E402
    PHASE3B_SOURCE_IDS,
    TrackingError,
    collect,
    set_collection_enabled,
)


FIXED_TIME = "2026-07-01T00:00:00.000Z"
COMPANIES = {
    "nuro-greenhouse": ("nuro-fixture", "Nuro"),
    "zipline-greenhouse": ("zipline-fixture", "Zipline"),
    "agility-robotics-greenhouse": ("agility-fixture", "Agility Robotics"),
}


class SnapshotClient:
    def __init__(self, payloads):  # type: ignore[no-untyped-def]
        self.payloads = payloads
        self.calls: list[str] = []

    def fetch(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(url)
        payload = self.payloads[url]
        if isinstance(payload, Exception):
            raise payload
        return HttpPage(
            requested_url=url,
            final_url=url,
            redirect_chain=[],
            fetched_at=FIXED_TIME,
            http_status=200,
            content_type="application/json",
            body=json.dumps({"jobs": payload}).encode("utf-8"),
        )


def fixture_job(source_id: str, job_id: str, **overrides):  # type: ignore[no-untyped-def]
    value = {
        "id": int(job_id),
        "title": f"Robotics Software Engineer {job_id}",
        "absolute_url": f"https://jobs.example.invalid/{source_id}/jobs/{job_id}?gh_jid={job_id}",
        "location": {"name": "Mountain View, CA"},
        "departments": [{"name": "Autonomy Engineering"}],
        "metadata": [{"name": "Employment Type", "value": "Full-time"}],
        "content": f"<p>Build and validate robot software for fixture job {job_id}.</p>",
        "first_published": "2026-06-01T00:00:00-07:00",
    }
    value.update(overrides)
    return value


class CareerTrackingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="career-tracking-test-")
        self.addCleanup(self.temporary.cleanup)
        self.runtime = Path(self.temporary.name) / "runtime"
        career_db.initialize_runtime(self.runtime)
        self.database = self.runtime / "staging" / "career.sqlite3"
        career_db.migrate_database(self.database)
        self.staging = self.runtime / "raw" / "career-sources"
        self.urls: dict[str, str] = {}
        for source_id in PHASE3B_SOURCE_IDS:
            company_id, company_name = COMPANIES[source_id]
            token = source_id.removesuffix("-greenhouse")
            listing_url = (
                f"https://boards-api.example.invalid/v1/boards/{token}/jobs?content=true"
            )
            self.urls[source_id] = listing_url
            register_company(
                self.database,
                company_id=company_id,
                display_name=company_name,
                official_website_url=f"https://{company_id}.example.invalid",
                official_career_url=f"https://{company_id}.example.invalid/careers",
            )
            register_source(
                self.database,
                source_id=source_id,
                company_id=company_id,
                source_name=f"{company_name} Greenhouse Fixture",
                official_careers_url=f"https://{company_id}.example.invalid/careers",
                listing_url=listing_url,
                source_type="standard_ats",
                ats_vendor="greenhouse",
                allowed_domains=["boards-api.example.invalid"],
                adapter_name="standard_ats_greenhouse_v1",
                external_id_strategy="native_job_id",
                owner="offline-test",
                official_evidence_url=f"https://{company_id}.example.invalid/careers",
                evidence_checked=True,
                robots_status="allowed",
                terms_status="reviewed_no_obvious_restriction",
                notes="Synthetic Phase 3B fixture; not a factual source.",
            )
            self._make_verified(source_id)
        career_db.set_safety_controls(
            self.database,
            collection_enabled=True,
            publication_enabled=None,
            reason="Enable isolated Phase 3B offline tests",
            actor="career_tracking_test",
        )
        set_collection_enabled(
            self.database,
            source_ids=list(PHASE3B_SOURCE_IDS),
            enabled=True,
            actor="career_tracking_test",
            confirm=True,
        )

    def _make_verified(self, source_id: str) -> None:
        connection = career_db.connect_database(self.database)
        try:
            connection.execute(
                "UPDATE career_source_profiles SET adapter_test_status = 'passed' WHERE source_id = ?",
                (source_id,),
            )
            for mode in ("fixture", "live_smoke"):
                connection.execute(
                    """
                    INSERT INTO source_verification_runs(
                      verification_run_id, source_id, mode, started_at, finished_at,
                      result, adapter_version, parser_version, run_summary_path,
                      listing_requests, detail_requests, parsed_jobs,
                      job_postings_before, job_postings_after, job_changes_before,
                      job_changes_after, collection_enabled, publication_enabled,
                      created_at
                    ) VALUES (?, ?, ?, ?, ?, 'succeeded', '1.0.0', '1.0.0', ?,
                              0, 0, 2, 0, 0, 0, 0, 0, 0, ?)
                    """,
                    (
                        f"{source_id}-{mode}",
                        source_id,
                        mode,
                        FIXED_TIME,
                        FIXED_TIME,
                        f"/tmp/{source_id}-{mode}.json",
                        FIXED_TIME,
                    ),
                )
        finally:
            connection.close()
        verify_source(
            self.database,
            source_id=source_id,
            actor="offline-reviewer",
            confirm=True,
        )

    def snapshots(self):  # type: ignore[no-untyped-def]
        return {
            source_id: [fixture_job(source_id, "100"), fixture_job(source_id, "101")]
            for source_id in PHASE3B_SOURCE_IDS
        }

    def run_snapshot(self, snapshots, day: int, *, failures=None):  # type: ignore[no-untyped-def]
        failures = failures or {}
        payloads = {
            self.urls[source_id]: failures.get(source_id, jobs)
            for source_id, jobs in snapshots.items()
        }
        client = SnapshotClient(payloads)
        summary = collect(
            self.database,
            self.staging,
            source_ids=list(PHASE3B_SOURCE_IDS),
            confirm_write=True,
            client=client,
            now=f"2026-07-{day:02d}T00:00:00.000Z",
            run_id=f"phase3b-offline-run-{day:02d}",
        )
        return summary, client

    def query_one(self, sql: str, parameters=()):  # type: ignore[no-untyped-def]
        connection = career_db.connect_database(self.database)
        try:
            return connection.execute(sql, parameters).fetchone()
        finally:
            connection.close()

    def test_first_run_is_baseline_without_added_events(self) -> None:
        summary, client = self.run_snapshot(self.snapshots(), 1)
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(summary["run_type"], "baseline")
        self.assertEqual(summary["totals"]["baseline_import_count"], 6)
        self.assertEqual(summary["totals"]["added"], 0)
        self.assertEqual(summary["totals"]["open_jobs"], 6)
        self.assertEqual(self.query_one("SELECT count(*) FROM job_postings")[0], 6)
        self.assertEqual(self.query_one("SELECT count(*) FROM job_changes")[0], 0)
        self.assertEqual(
            self.query_one("SELECT count(DISTINCT job_id) FROM job_postings")[0], 6
        )
        self.assertEqual(
            self.query_one(
                "SELECT count(*) FROM job_postings WHERE source_native_id = '100'"
            )[0],
            3,
        )

    def test_new_job_added_and_identical_repeats_are_idempotent(self) -> None:
        snapshots = self.snapshots()
        self.run_snapshot(snapshots, 1)
        changed = deepcopy(snapshots)
        changed["nuro-greenhouse"].append(fixture_job("nuro-greenhouse", "102"))
        second, _ = self.run_snapshot(changed, 2)
        third, _ = self.run_snapshot(changed, 3)
        self.assertEqual(second["totals"]["added"], 1)
        self.assertEqual(third["totals"]["added"], 0)
        self.assertEqual(third["totals"]["updated"], 0)
        self.assertEqual(self.query_one("SELECT count(*) FROM job_postings")[0], 7)
        self.assertEqual(
            self.query_one("SELECT count(*) FROM job_changes WHERE change_type = 'added'")[0],
            1,
        )

    def test_content_title_and_location_changes_list_changed_fields(self) -> None:
        snapshots = self.snapshots()
        self.run_snapshot(snapshots, 1)
        changed = deepcopy(snapshots)
        changed["nuro-greenhouse"][0].update(
            {
                "title": "Senior Robotics Software Engineer",
                "location": {"name": "Fremont, CA"},
                "content": "<p>Build robot software and own production validation.</p>",
            }
        )
        summary, _ = self.run_snapshot(changed, 2)
        event = next(item for item in summary["changes"] if item["change_type"] == "updated")
        self.assertEqual(summary["totals"]["updated"], 1)
        self.assertTrue({"title", "location", "description"}.issubset(event["changed_fields"]))
        row = self.query_one(
            "SELECT previous_content_hash, new_content_hash, changed_fields_json "
            "FROM job_changes WHERE change_type = 'updated'"
        )
        self.assertNotEqual(row["previous_content_hash"], row["new_content_hash"])
        self.assertTrue(
            {"title", "location", "description"}.issubset(
                json.loads(row["changed_fields_json"])
            )
        )

    def test_first_and_second_consecutive_absence_become_missing_then_closed(self) -> None:
        snapshots = self.snapshots()
        self.run_snapshot(snapshots, 1)
        missing = deepcopy(snapshots)
        missing["nuro-greenhouse"] = missing["nuro-greenhouse"][1:]
        first, _ = self.run_snapshot(missing, 2)
        first_row = self.query_one(
            "SELECT lifecycle_status, consecutive_missing_count FROM job_postings "
            "WHERE job_id = 'nuro-greenhouse:external:100'"
        )
        second, _ = self.run_snapshot(missing, 3)
        second_row = self.query_one(
            "SELECT lifecycle_status, consecutive_missing_count FROM job_postings "
            "WHERE job_id = 'nuro-greenhouse:external:100'"
        )
        self.assertEqual(first["totals"]["missing"], 1)
        self.assertEqual(tuple(first_row), ("missing", 1))
        self.assertEqual(second["totals"]["closed"], 1)
        self.assertEqual(tuple(second_row), ("closed", 2))

    def test_failed_source_does_not_increment_missing_or_close_jobs(self) -> None:
        snapshots = self.snapshots()
        self.run_snapshot(snapshots, 1)
        summary, client = self.run_snapshot(
            snapshots,
            2,
            failures={"nuro-greenhouse": AccessBlockedError("HTTP 403 is forbidden")},
        )
        row = self.query_one(
            "SELECT lifecycle_status, consecutive_missing_count FROM job_postings "
            "WHERE job_id = 'nuro-greenhouse:external:100'"
        )
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(summary["result"], "partial_failure")
        self.assertEqual(summary["totals"]["failed_sources"], 1)
        self.assertEqual(summary["totals"]["missing"], 0)
        self.assertEqual(tuple(row), ("active", 0))
        self.assertEqual(
            self.query_one(
                "SELECT status FROM pipeline_runs WHERE run_id = 'phase3b-offline-run-02'"
            )[0],
            "failed",
        )

    def test_closed_job_reappearance_is_reopened(self) -> None:
        snapshots = self.snapshots()
        self.run_snapshot(snapshots, 1)
        missing = deepcopy(snapshots)
        missing["nuro-greenhouse"] = missing["nuro-greenhouse"][1:]
        self.run_snapshot(missing, 2)
        self.run_snapshot(missing, 3)
        summary, _ = self.run_snapshot(snapshots, 4)
        row = self.query_one(
            "SELECT lifecycle_status, consecutive_missing_count FROM job_postings "
            "WHERE job_id = 'nuro-greenhouse:external:100'"
        )
        self.assertEqual(summary["totals"]["reopened"], 1)
        self.assertEqual(tuple(row), ("active", 0))
        self.assertEqual(
            self.query_one("SELECT count(*) FROM job_changes WHERE change_type = 'reopened'")[0],
            1,
        )

    def test_confirm_write_is_required_and_publication_stays_disabled(self) -> None:
        client = SnapshotClient(
            {self.urls[source_id]: jobs for source_id, jobs in self.snapshots().items()}
        )
        with self.assertRaisesRegex(TrackingError, "--confirm-write"):
            collect(
                self.database,
                self.staging,
                source_ids=list(PHASE3B_SOURCE_IDS),
                confirm_write=False,
                client=client,
            )
        self.assertEqual(client.calls, [])
        self.assertEqual(self.query_one("SELECT count(*) FROM job_postings")[0], 0)
        controls = self.query_one(
            "SELECT collection_enabled, publication_enabled FROM system_controls WHERE singleton = 1"
        )
        self.assertEqual(tuple(controls), (1, 0))
        self.assertEqual(
            self.query_one(
                "SELECT sum(publication_enabled) FROM career_source_profiles"
            )[0],
            0,
        )

    def test_summary_json_and_markdown_are_generated_without_changes(self) -> None:
        summary, _ = self.run_snapshot(self.snapshots(), 1)
        json_path = Path(summary["summary_paths"]["json"])
        markdown_path = Path(summary["summary_paths"]["markdown"])
        self.assertTrue(json_path.is_file())
        self.assertTrue(markdown_path.is_file())
        self.assertEqual(json.loads(json_path.read_text())["totals"]["open_jobs"], 6)
        markdown = markdown_path.read_text()
        self.assertIn("# 机器人岗位每日变化", markdown)
        self.assertIn("本次未发现岗位变化。", markdown)
        self.assertIn("Nuro", markdown)
        with self.assertRaisesRegex(StagingError, "already exists"):
            self.run_snapshot(self.snapshots(), 1)

    def test_database_and_staging_must_remain_outside_repository(self) -> None:
        with self.assertRaisesRegex(career_db.CareerDataError, "outside the Git worktree"):
            collect(
                self.database,
                career_db.REPOSITORY_ROOT / "phase3b-staging",
                source_ids=list(PHASE3B_SOURCE_IDS),
                confirm_write=True,
                client=SnapshotClient({}),
            )
        with self.assertRaisesRegex(career_db.CareerDataError, "outside the Git worktree"):
            collect(
                career_db.REPOSITORY_ROOT / "career.sqlite3",
                self.staging,
                source_ids=list(PHASE3B_SOURCE_IDS),
                confirm_write=True,
                client=SnapshotClient({}),
            )

    def test_source_collection_control_is_explicit_and_does_not_enable_publication(self) -> None:
        with self.assertRaisesRegex(TrackingError, "--confirm"):
            set_collection_enabled(
                self.database,
                source_ids=["nuro-greenhouse"],
                enabled=False,
                actor="offline-test",
                confirm=False,
            )
        result = set_collection_enabled(
            self.database,
            source_ids=["nuro-greenhouse"],
            enabled=False,
            actor="offline-test",
            confirm=True,
        )
        source = result["sources"][0]
        self.assertEqual(source["collection_enabled"], 0)
        self.assertEqual(source["base_enabled"], 0)
        self.assertEqual(source["publication_enabled"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

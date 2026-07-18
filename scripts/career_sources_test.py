"""Offline regression tests for Phase 3A source registration and dry-runs."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import career_db  # noqa: E402
from career_sources.adapters import adapter_for_source  # noqa: E402
from career_sources.http_client import (  # noqa: E402
    AccessBlockedError,
    RateLimitedError,
    RawHttpResponse,
    SafeHttpClient,
    SsrfProtectionError,
    detect_access_barrier,
)
from career_sources.models import (  # noqa: E402
    build_job_key,
    job_content_hash,
    normalize_detail_url,
    plain_text,
)
from career_sources import service  # noqa: E402
from career_sources.service import (  # noqa: E402
    SourceServiceError,
    dry_run,
    load_source,
    register_company,
    register_source,
    verify_source,
)
from career_sources.staging import StagingError, StagingRunWriter  # noqa: E402


class FakeFixtureClient:
    def __init__(self, listing, details):  # type: ignore[no-untyped-def]
        self.listing = listing
        self.details = details
        self.calls: list[str] = []

    def fetch(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(url)
        if len(self.calls) == 1:
            return self.listing
        return self.details[normalize_detail_url(url)]


class CareerSourcesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="career-sources-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "runtime"
        career_db.initialize_runtime(self.root)
        self.database = self.root / "staging" / "career.sqlite3"
        career_db.migrate_database(self.database)
        self.staging = self.root / "raw" / "source-staging"
        register_company(
            self.database,
            company_id="fixture-company",
            display_name="Synthetic Fixture Company",
            official_website_url="https://company.example.invalid",
            official_career_url="https://company.example.invalid/careers",
        )
        register_source(
            self.database,
            source_id="fixture-greenhouse",
            company_id="fixture-company",
            source_name="Synthetic Greenhouse Fixture",
            official_careers_url="https://company.example.invalid/careers",
            listing_url="https://boards-api.example.invalid/v1/boards/fixture/jobs?content=true",
            source_type="standard_ats",
            ats_vendor="greenhouse",
            allowed_domains=["boards-api.example.invalid", "job-boards.example.invalid"],
            adapter_name="standard_ats_greenhouse_v1",
            external_id_strategy="native_job_id",
            owner="offline-test",
            official_evidence_url="https://company.example.invalid/careers",
            evidence_checked=True,
            robots_status="allowed",
            terms_status="reviewed_no_obvious_restriction",
            notes="Synthetic test record; never a factual source.",
        )

    def fixture_run(self):  # type: ignore[no-untyped-def]
        return dry_run(
            self.database,
            self.staging,
            source_id="fixture-greenhouse",
            mode="fixture",
        )

    def live_client(self) -> FakeFixtureClient:
        source = load_source(self.database, "fixture-greenhouse")
        adapter = adapter_for_source(source)
        listing, details = service._fixture_pages(adapter)
        return FakeFixtureClient(listing, details)

    def test_migration_and_source_defaults_are_fail_closed(self) -> None:
        validation = career_db.validate_database(self.database)
        self.assertEqual(validation["currentVersion"], 3)
        source = load_source(self.database, "fixture-greenhouse")
        self.assertEqual(source["status"], "candidate")
        self.assertEqual(source["adapter_test_status"], "pending")
        self.assertEqual(source["collection_enabled"], 0)
        self.assertEqual(source["publication_enabled"], 0)
        self.assertEqual(source["base_enabled"], 0)

    def test_fixture_parses_listing_details_and_unified_jobs(self) -> None:
        summary = self.fixture_run()
        self.assertEqual(summary["result"], "succeeded")
        self.assertEqual(summary["network_requests"]["total"], 0)
        self.assertEqual(summary["parsed_job_count"], 2)
        run_directory = Path(summary["run_summary_path"]).parent
        self.assertEqual(
            {path.name for path in run_directory.iterdir()},
            {
                "listing.json",
                "detail_001.json",
                "detail_002.json",
                "parsed_jobs.jsonl",
                "run_summary.json",
            },
        )
        jobs = [json.loads(line) for line in (run_directory / "parsed_jobs.jsonl").read_text().splitlines()]
        self.assertEqual([job["external_job_id"] for job in jobs], ["900001", "900002"])
        self.assertEqual(jobs[0]["department"], "Autonomy")
        self.assertEqual(jobs[0]["employment_type"], "Full-time")
        self.assertEqual(jobs[0]["location"], "Singapore")
        self.assertEqual(jobs[0]["company_id"], "fixture-company")
        self.assertEqual(len(jobs[0]["content_hash"]), 64)
        page = json.loads((run_directory / "run_summary.json").read_text())["pages"][0]
        self.assertEqual(page["http_status"], 200)
        self.assertEqual(len(page["raw_sha256"]), 64)
        self.assertIn("requested_url", page)
        self.assertIn("final_url", page)
        self.assertIn("fetched_at", page)

    def test_external_job_id_and_url_identity_are_stable(self) -> None:
        summary = self.fixture_run()
        run_directory = Path(summary["run_summary_path"]).parent
        jobs = [json.loads(line) for line in (run_directory / "parsed_jobs.jsonl").read_text().splitlines()]
        self.assertEqual(jobs[0]["job_key"], "fixture-greenhouse:external:900001")
        self.assertEqual(
            jobs[0]["canonical_url"],
            "https://job-boards.example.invalid/fixture/jobs/900001?gh_jid=900001",
        )
        self.assertEqual(jobs[0]["identity_strategy"], "native_job_id")

    def test_normalized_detail_url_is_the_identity_fallback(self) -> None:
        first = build_job_key(
            "source-a",
            None,
            "https://jobs.example.com/roles/42/?utm_source=feed&region=apac#apply",
        )
        second = build_job_key(
            "source-a",
            None,
            "https://JOBS.example.com:443/roles/42?region=apac&utm_campaign=other",
        )
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            "source-a:url:https://jobs.example.com/roles/42?region=apac",
        )

    def test_url_normalization_removes_only_tracking_and_fragment(self) -> None:
        value = normalize_detail_url(
            "HTTPS://Jobs.Example.COM:443/roles/42/?utm_source=x&gh_jid=42&ref=feed#apply"
        )
        self.assertEqual(value, "https://jobs.example.com/roles/42?gh_jid=42")

    def test_content_hash_changes_with_normalized_job_content(self) -> None:
        original = {
            "title": "Robotics Engineer",
            "location": "Singapore",
            "department": "Autonomy",
            "employment_type": "Full-time",
            "description": "Build planners",
            "published_at": None,
        }
        changed = {**original, "description": "Build planners and controllers"}
        self.assertEqual(job_content_hash(original), job_content_hash(dict(original)))
        self.assertNotEqual(job_content_hash(original), job_content_hash(changed))

    def test_description_redacts_unneeded_contact_details(self) -> None:
        text = plain_text("<p>Contact person@example.org or +1 (415) 555-0100.</p>")
        self.assertNotIn("person@example.org", text or "")
        self.assertNotIn("555-0100", text or "")
        self.assertIn("[email redacted]", text or "")

    def test_description_decodes_greenhouse_html_entities_before_parsing(self) -> None:
        text = plain_text("&lt;p&gt;&lt;strong&gt;Build robots&lt;/strong&gt; safely.&lt;/p&gt;")
        self.assertEqual(text, "Build robots safely.")
        self.assertNotIn("<p>", text or "")

    def test_json_job_content_does_not_trigger_a_false_login_barrier(self) -> None:
        body = json.dumps({"jobs": [{"content": "Sign in to the weekly team meeting."}]}).encode()
        self.assertIsNone(
            detect_access_barrier("application/json", body, "https://jobs.example.com/jobs")
        )

    def test_json_error_still_triggers_a_login_barrier(self) -> None:
        body = json.dumps({"error": "Login required"}).encode()
        self.assertEqual(
            detect_access_barrier("application/json", body, "https://jobs.example.com/jobs"),
            "login",
        )

    def test_repository_internal_staging_is_rejected(self) -> None:
        with self.assertRaisesRegex(career_db.CareerDataError, "outside the Git worktree"):
            dry_run(
                self.database,
                career_db.REPOSITORY_ROOT / "source-staging",
                source_id="fixture-greenhouse",
                mode="fixture",
            )

    def test_repository_internal_database_is_rejected(self) -> None:
        with self.assertRaisesRegex(career_db.CareerDataError, "outside the Git worktree"):
            service.list_sources(career_db.REPOSITORY_ROOT / "career.sqlite3")

    def test_live_smoke_requires_explicit_confirmation(self) -> None:
        with self.assertRaisesRegex(SourceServiceError, "--confirm-live"):
            dry_run(
                self.database,
                self.staging,
                source_id="fixture-greenhouse",
                mode="live-smoke",
                client=self.live_client(),
            )

    def test_live_smoke_is_bounded_to_one_listing_and_two_details(self) -> None:
        client = self.live_client()
        summary = dry_run(
            self.database,
            self.staging,
            source_id="fixture-greenhouse",
            mode="live-smoke",
            confirm_live=True,
            client=client,
        )
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(summary["network_requests"], {"listing": 1, "detail": 2, "total": 3})
        self.assertFalse(summary["limits"]["automatic_pagination"])

    def test_401_403_and_429_stop_without_retry(self) -> None:
        cases = (
            (401, AccessBlockedError),
            (403, AccessBlockedError),
            (429, RateLimitedError),
        )
        for status, exception_type in cases:
            with self.subTest(status=status):
                calls: list[str] = []

                def request_once(url, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
                    calls.append(url)
                    return RawHttpResponse(
                        status=status,
                        headers={"Content-Type": "text/html", "Retry-After": "60"},
                        body=b"blocked",
                    )

                client = SafeHttpClient(
                    resolver=lambda hostname: ["8.8.8.8"],
                    request_once=request_once,
                )
                with self.assertRaises(exception_type):
                    client.fetch("https://jobs.example.com/openings", allowed_domains=["example.com"])
                self.assertEqual(len(calls), 1)

    def test_redirect_to_unknown_domain_stops_before_following(self) -> None:
        calls: list[str] = []

        def request_once(url, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
            calls.append(url)
            return RawHttpResponse(
                status=302,
                headers={"location": "https://unknown.example.net/login"},
                body=b"",
            )

        client = SafeHttpClient(
            resolver=lambda hostname: ["8.8.8.8"],
            request_once=request_once,
        )
        with self.assertRaisesRegex(SsrfProtectionError, "outside the configured allowlist"):
            client.fetch("https://jobs.example.com/openings", allowed_domains=["example.com"])
        self.assertEqual(calls, ["https://jobs.example.com/openings"])

    def test_staging_source_directory_symlink_is_rejected(self) -> None:
        self.staging.mkdir(parents=True)
        outside = self.root / "raw" / "unexpected-target"
        outside.mkdir()
        (self.staging / "fixture-greenhouse").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(StagingError, "must not be a symlink"):
            StagingRunWriter(self.staging, "fixture-greenhouse", "symlink-run")

    def test_dry_run_does_not_write_job_or_change_tables(self) -> None:
        connection = career_db.connect_database(self.database)
        try:
            before = (
                connection.execute("SELECT count(*) FROM job_postings").fetchone()[0],
                connection.execute("SELECT count(*) FROM job_changes").fetchone()[0],
            )
        finally:
            connection.close()
        summary = self.fixture_run()
        connection = career_db.connect_database(self.database)
        try:
            after = (
                connection.execute("SELECT count(*) FROM job_postings").fetchone()[0],
                connection.execute("SELECT count(*) FROM job_changes").fetchone()[0],
            )
        finally:
            connection.close()
        self.assertEqual(before, (0, 0))
        self.assertEqual(after, before)
        self.assertEqual(summary["business_table_counts"]["job_postings_after"], 0)
        self.assertEqual(summary["business_table_counts"]["job_changes_after"], 0)

    def test_existing_staging_run_is_never_overwritten(self) -> None:
        StagingRunWriter(self.staging, "fixture-greenhouse", "fixed-run")
        with self.assertRaisesRegex(StagingError, "already exists"):
            StagingRunWriter(self.staging, "fixture-greenhouse", "fixed-run")

    def test_verify_is_manual_and_never_enables_collection_or_publication(self) -> None:
        self.fixture_run()
        client = self.live_client()
        dry_run(
            self.database,
            self.staging,
            source_id="fixture-greenhouse",
            mode="live-smoke",
            confirm_live=True,
            client=client,
        )
        self.assertEqual(load_source(self.database, "fixture-greenhouse")["status"], "candidate")
        with self.assertRaisesRegex(SourceServiceError, "--confirm"):
            verify_source(
                self.database,
                source_id="fixture-greenhouse",
                actor="offline-reviewer",
                confirm=False,
            )
        verified = verify_source(
            self.database,
            source_id="fixture-greenhouse",
            actor="offline-reviewer",
            confirm=True,
        )
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(verified["collection_enabled"], 0)
        self.assertEqual(verified["publication_enabled"], 0)
        self.assertEqual(verified["base_enabled"], 0)

    def test_verification_runs_are_append_only(self) -> None:
        self.fixture_run()
        connection = career_db.connect_database(self.database)
        try:
            run_id = connection.execute(
                "SELECT verification_run_id FROM source_verification_runs"
            ).fetchone()[0]
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute(
                    "UPDATE source_verification_runs SET parsed_jobs = 0 WHERE verification_run_id = ?",
                    (run_id,),
                )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute(
                    "DELETE FROM source_verification_runs WHERE verification_run_id = ?",
                    (run_id,),
                )
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)

-- Phase 3B: minimal persistence needed for three-source job change tracking.
-- This migration seeds no factual records and keeps publication fail-closed.

ALTER TABLE job_postings ADD COLUMN department_text TEXT;
ALTER TABLE job_postings ADD COLUMN canonical_url TEXT
  CHECK(canonical_url IS NULL OR canonical_url LIKE 'https://%');
ALTER TABLE job_postings ADD COLUMN consecutive_missing_count INTEGER NOT NULL DEFAULT 0
  CHECK(consecutive_missing_count >= 0);

CREATE INDEX job_postings_source_missing_index
  ON job_postings(source_id, lifecycle_status, consecutive_missing_count);

-- Widen the append-only event vocabulary and associate Phase 3B events with the
-- existing pipeline run ledger. Legacy event names remain valid for old rows.
DROP TRIGGER job_changes_no_update;
DROP TRIGGER job_changes_no_delete;

ALTER TABLE job_changes RENAME TO job_changes_before_phase3b;

CREATE TABLE job_changes (
  change_id TEXT PRIMARY KEY CHECK(length(change_id) BETWEEN 1 AND 160),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  job_id TEXT NOT NULL REFERENCES job_postings(job_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  source_id TEXT NOT NULL REFERENCES career_sources(source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  run_id TEXT REFERENCES pipeline_runs(run_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  change_type TEXT NOT NULL CHECK(change_type IN (
    'added', 'updated', 'missing', 'closed', 'reopened',
    'first_observed', 'content_changed', 'status_changed', 'source_updated',
    'location_changed', 'quarantined'
  )),
  previous_content_hash TEXT CHECK(previous_content_hash IS NULL OR (
    length(previous_content_hash) = 64 AND previous_content_hash NOT GLOB '*[^0-9a-f]*'
  )),
  new_content_hash TEXT CHECK(new_content_hash IS NULL OR (
    length(new_content_hash) = 64 AND new_content_hash NOT GLOB '*[^0-9a-f]*'
  )),
  changed_fields_json TEXT NOT NULL DEFAULT '{}'
    CHECK(json_valid(changed_fields_json) AND json_type(changed_fields_json) = 'object'),
  observed_at TEXT NOT NULL,
  source_url TEXT NOT NULL CHECK(source_url LIKE 'https://%'),
  collected_at TEXT NOT NULL,
  raw_snapshot_ref TEXT NOT NULL CHECK(length(trim(raw_snapshot_ref)) > 0),
  retrieval_result TEXT NOT NULL CHECK(retrieval_result IN (
    'success', 'not_modified', 'empty', 'rate_limited', 'access_denied', 'network_error', 'invalid_response'
  )),
  created_at TEXT NOT NULL
) STRICT;

INSERT INTO job_changes(
  change_id, schema_version, job_id, source_id, run_id, change_type,
  previous_content_hash, new_content_hash, changed_fields_json, observed_at,
  source_url, collected_at, raw_snapshot_ref, retrieval_result, created_at
)
SELECT
  change_id, schema_version, job_id, source_id, NULL, change_type,
  previous_content_hash, new_content_hash, changed_fields_json, observed_at,
  source_url, collected_at, raw_snapshot_ref, retrieval_result, created_at
FROM job_changes_before_phase3b;

DROP TABLE job_changes_before_phase3b;

CREATE INDEX job_changes_job_time_index ON job_changes(job_id, observed_at);
CREATE INDEX job_changes_source_time_index ON job_changes(source_id, collected_at);
CREATE INDEX job_changes_run_index ON job_changes(run_id, change_type);

CREATE TRIGGER job_changes_no_update
BEFORE UPDATE ON job_changes
BEGIN
  SELECT RAISE(ABORT, 'job_changes is append-only');
END;

CREATE TRIGGER job_changes_no_delete
BEFORE DELETE ON job_changes
BEGIN
  SELECT RAISE(ABORT, 'job_changes is append-only');
END;

-- Phase 3A intentionally constrained collection_enabled to literal zero. Phase
-- 3B permits it only for a fully verified source; publication remains fixed off.
CREATE TABLE career_source_profiles_phase3b (
  source_id TEXT PRIMARY KEY,
  company_id TEXT NOT NULL,
  source_name TEXT NOT NULL CHECK(length(trim(source_name)) > 0),
  official_careers_url TEXT NOT NULL CHECK(official_careers_url LIKE 'https://%'),
  listing_url TEXT NOT NULL CHECK(listing_url LIKE 'https://%'),
  source_type TEXT NOT NULL
    CHECK(source_type IN ('official_html', 'standard_ats', 'official_json')),
  ats_vendor TEXT,
  allowed_domains_json TEXT NOT NULL
    CHECK(json_valid(allowed_domains_json)
      AND json_type(allowed_domains_json) = 'array'
      AND json_array_length(allowed_domains_json) > 0),
  adapter_name TEXT NOT NULL CHECK(length(trim(adapter_name)) > 0),
  adapter_version TEXT NOT NULL CHECK(length(trim(adapter_version)) > 0),
  parser_version TEXT NOT NULL CHECK(length(trim(parser_version)) > 0),
  adapter_test_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(adapter_test_status IN ('pending', 'passed', 'failed')),
  external_id_strategy TEXT NOT NULL
    CHECK(external_id_strategy IN ('native_job_id', 'normalized_detail_url', 'review_required')),
  official_evidence_url TEXT CHECK(official_evidence_url IS NULL OR official_evidence_url LIKE 'https://%'),
  official_evidence_checked_at TEXT,
  robots_status TEXT NOT NULL DEFAULT 'not_checked'
    CHECK(robots_status IN ('not_checked', 'allowed', 'disallowed', 'not_found', 'unclear')),
  terms_status TEXT NOT NULL DEFAULT 'not_checked'
    CHECK(terms_status IN ('not_checked', 'reviewed_no_obvious_restriction', 'restricted', 'unclear')),
  login_required INTEGER NOT NULL DEFAULT 0 CHECK(login_required IN (0, 1)),
  captcha_detected INTEGER NOT NULL DEFAULT 0 CHECK(captcha_detected IN (0, 1)),
  request_interval_seconds REAL NOT NULL DEFAULT 3.0 CHECK(request_interval_seconds >= 3.0),
  timeout_seconds REAL NOT NULL DEFAULT 15.0 CHECK(timeout_seconds > 0 AND timeout_seconds <= 60),
  status TEXT NOT NULL DEFAULT 'candidate'
    CHECK(status IN ('candidate', 'verified', 'paused', 'blocked')),
  collection_enabled INTEGER NOT NULL DEFAULT 0 CHECK(collection_enabled IN (0, 1)),
  publication_enabled INTEGER NOT NULL DEFAULT 0 CHECK(publication_enabled = 0),
  last_checked_at TEXT,
  last_success_at TEXT,
  failure_reason TEXT,
  reviewed_by TEXT,
  reviewed_at TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(source_id, company_id) REFERENCES career_sources(source_id, company_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CHECK(source_type = 'standard_ats' OR ats_vendor IS NULL),
  CHECK(status <> 'verified' OR (
    official_evidence_url IS NOT NULL
    AND official_evidence_checked_at IS NOT NULL
    AND reviewed_by IS NOT NULL
    AND reviewed_at IS NOT NULL
    AND adapter_test_status = 'passed'
    AND external_id_strategy <> 'review_required'
    AND robots_status IN ('allowed', 'not_found')
    AND terms_status = 'reviewed_no_obvious_restriction'
    AND login_required = 0
    AND captcha_detected = 0
  )),
  CHECK(collection_enabled = 0 OR status = 'verified')
) STRICT;

INSERT INTO career_source_profiles_phase3b
SELECT * FROM career_source_profiles;

-- source_verification_runs references the profile table. Preserve and rebuild
-- the existing append-only rows inside this migration transaction so foreign
-- keys remain enabled throughout the parent-table replacement.
CREATE TEMP TABLE source_verification_runs_phase3b_backup AS
SELECT * FROM source_verification_runs;

DROP TRIGGER source_verification_runs_no_update;
DROP TRIGGER source_verification_runs_no_delete;
DROP TABLE source_verification_runs;
DROP TABLE career_source_profiles;
ALTER TABLE career_source_profiles_phase3b RENAME TO career_source_profiles;

CREATE INDEX career_source_profiles_status_index
  ON career_source_profiles(status, source_type, adapter_test_status);
CREATE INDEX career_source_profiles_controls_index
  ON career_source_profiles(collection_enabled, publication_enabled, status);

CREATE TABLE source_verification_runs (
  verification_run_id TEXT PRIMARY KEY CHECK(length(verification_run_id) BETWEEN 1 AND 160),
  source_id TEXT NOT NULL
    REFERENCES career_source_profiles(source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  mode TEXT NOT NULL CHECK(mode IN ('fixture', 'live_smoke')),
  started_at TEXT NOT NULL,
  finished_at TEXT NOT NULL,
  result TEXT NOT NULL CHECK(result IN ('succeeded', 'failed', 'blocked')),
  adapter_version TEXT NOT NULL CHECK(length(trim(adapter_version)) > 0),
  parser_version TEXT NOT NULL CHECK(length(trim(parser_version)) > 0),
  run_summary_path TEXT NOT NULL CHECK(length(trim(run_summary_path)) > 0),
  failure_reason TEXT,
  listing_requests INTEGER NOT NULL DEFAULT 0 CHECK(listing_requests BETWEEN 0 AND 1),
  detail_requests INTEGER NOT NULL DEFAULT 0 CHECK(detail_requests BETWEEN 0 AND 2),
  parsed_jobs INTEGER NOT NULL DEFAULT 0 CHECK(parsed_jobs >= 0),
  job_postings_before INTEGER NOT NULL CHECK(job_postings_before >= 0),
  job_postings_after INTEGER NOT NULL CHECK(job_postings_after = job_postings_before),
  job_changes_before INTEGER NOT NULL CHECK(job_changes_before >= 0),
  job_changes_after INTEGER NOT NULL CHECK(job_changes_after = job_changes_before),
  collection_enabled INTEGER NOT NULL CHECK(collection_enabled = 0),
  publication_enabled INTEGER NOT NULL CHECK(publication_enabled = 0),
  created_at TEXT NOT NULL,
  CHECK(finished_at >= started_at),
  CHECK(result = 'succeeded' OR failure_reason IS NOT NULL)
) STRICT;

INSERT INTO source_verification_runs
SELECT * FROM source_verification_runs_phase3b_backup;

DROP TABLE source_verification_runs_phase3b_backup;

CREATE INDEX source_verification_runs_source_mode_index
  ON source_verification_runs(source_id, mode, result, finished_at);

CREATE TRIGGER career_source_profiles_verified_guard
BEFORE UPDATE OF status ON career_source_profiles
WHEN NEW.status = 'verified' AND OLD.status <> 'verified'
BEGIN
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM source_verification_runs
    WHERE source_id = NEW.source_id AND mode = 'fixture' AND result = 'succeeded'
  ) THEN RAISE(ABORT, 'Verified source requires a successful fixture dry-run') END;
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM source_verification_runs
    WHERE source_id = NEW.source_id AND mode = 'live_smoke' AND result = 'succeeded'
  ) THEN RAISE(ABORT, 'Verified source requires a successful live smoke dry-run') END;
END;

CREATE TRIGGER source_verification_runs_no_update
BEFORE UPDATE ON source_verification_runs
BEGIN
  SELECT RAISE(ABORT, 'source_verification_runs is append-only');
END;

CREATE TRIGGER source_verification_runs_no_delete
BEFORE DELETE ON source_verification_runs
BEGIN
  SELECT RAISE(ABORT, 'source_verification_runs is append-only');
END;

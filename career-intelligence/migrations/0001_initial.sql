-- Career intelligence schema version 1.
-- This migration intentionally seeds no factual domain records.

CREATE TABLE system_controls (
  singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
  schema_contract_version INTEGER NOT NULL CHECK(schema_contract_version = 1),
  collection_enabled INTEGER NOT NULL DEFAULT 0 CHECK(collection_enabled IN (0, 1)),
  publication_enabled INTEGER NOT NULL DEFAULT 0 CHECK(publication_enabled IN (0, 1)),
  change_reason TEXT NOT NULL DEFAULT 'Phase 2 safe default',
  updated_by TEXT NOT NULL DEFAULT '0001_initial',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  CHECK(length(trim(change_reason)) > 0),
  CHECK(length(trim(updated_by)) > 0)
) STRICT;

INSERT INTO system_controls(singleton, schema_contract_version) VALUES (1, 1);

CREATE TABLE companies (
  company_id TEXT PRIMARY KEY CHECK(length(company_id) BETWEEN 1 AND 128),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  legal_name TEXT NOT NULL CHECK(length(trim(legal_name)) > 0),
  display_name TEXT NOT NULL CHECK(length(trim(display_name)) > 0),
  aliases_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(aliases_json) AND json_type(aliases_json) = 'array'),
  country_code TEXT CHECK(country_code IS NULL OR (length(country_code) = 2 AND country_code = upper(country_code))),
  regions_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(regions_json) AND json_type(regions_json) = 'array'),
  official_website_url TEXT CHECK(official_website_url IS NULL OR official_website_url LIKE 'https://%'),
  official_career_url TEXT CHECK(official_career_url IS NULL OR official_career_url LIKE 'https://%'),
  ats_type TEXT,
  lifecycle_status TEXT NOT NULL DEFAULT 'candidate'
    CHECK(lifecycle_status IN ('candidate', 'verified', 'active', 'paused', 'retired')),
  verification_status TEXT NOT NULL DEFAULT 'unverified'
    CHECK(verification_status IN ('unverified', 'pending', 'verified', 'rejected')),
  verified_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK(verification_status <> 'verified' OR verified_at IS NOT NULL)
) STRICT;

CREATE UNIQUE INDEX companies_display_name_unique
  ON companies(display_name COLLATE NOCASE);
CREATE INDEX companies_lifecycle_index ON companies(lifecycle_status, verification_status);

CREATE TABLE career_sources (
  source_id TEXT PRIMARY KEY CHECK(length(source_id) BETWEEN 1 AND 128),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  company_id TEXT NOT NULL REFERENCES companies(company_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  source_url TEXT NOT NULL CHECK(source_url LIKE 'https://%'),
  source_type TEXT NOT NULL CHECK(source_type IN (
    'official_career_page', 'official_ats_api', 'official_ats_feed', 'approved_official_export'
  )),
  collection_method TEXT NOT NULL CHECK(length(trim(collection_method)) > 0),
  scope_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(scope_json) AND json_type(scope_json) = 'object'),
  schedule_hint TEXT,
  terms_review_status TEXT NOT NULL DEFAULT 'not_reviewed'
    CHECK(terms_review_status IN ('not_reviewed', 'approved', 'restricted', 'blocked')),
  terms_reviewed_at TEXT,
  robots_review_status TEXT NOT NULL DEFAULT 'not_reviewed'
    CHECK(robots_review_status IN ('not_reviewed', 'allowed', 'restricted', 'blocked', 'not_applicable')),
  enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0, 1)),
  lifecycle_status TEXT NOT NULL DEFAULT 'candidate'
    CHECK(lifecycle_status IN ('candidate', 'verified', 'enabled', 'degraded', 'paused', 'retired')),
  health_status TEXT NOT NULL DEFAULT 'never_run'
    CHECK(health_status IN ('never_run', 'healthy', 'degraded', 'blocked', 'paused', 'retired')),
  last_collected_at TEXT,
  last_source_updated_at TEXT,
  last_http_status INTEGER CHECK(last_http_status IS NULL OR last_http_status BETWEEN 100 AND 599),
  last_retrieval_result TEXT CHECK(last_retrieval_result IS NULL OR last_retrieval_result IN (
    'success', 'not_modified', 'empty', 'rate_limited', 'access_denied', 'network_error', 'invalid_response'
  )),
  owner TEXT NOT NULL CHECK(length(trim(owner)) > 0),
  verified_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(company_id, source_url, collection_method),
  UNIQUE(source_id, company_id),
  CHECK(enabled = 0 OR (
    lifecycle_status = 'enabled'
    AND terms_review_status = 'approved'
    AND robots_review_status IN ('allowed', 'not_applicable')
    AND verified_at IS NOT NULL
  ))
) STRICT;

CREATE INDEX career_sources_company_index ON career_sources(company_id, lifecycle_status);
CREATE INDEX career_sources_health_index ON career_sources(enabled, health_status);

CREATE TABLE job_postings (
  job_id TEXT PRIMARY KEY CHECK(length(job_id) BETWEEN 1 AND 160),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  company_id TEXT NOT NULL REFERENCES companies(company_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  source_id TEXT NOT NULL,
  source_native_id TEXT NOT NULL CHECK(length(trim(source_native_id)) > 0),
  source_url TEXT NOT NULL CHECK(source_url LIKE 'https://%'),
  source_title TEXT NOT NULL CHECK(length(trim(source_title)) > 0),
  normalized_title TEXT,
  description_text TEXT,
  location_text TEXT,
  country_code TEXT CHECK(country_code IS NULL OR (length(country_code) = 2 AND country_code = upper(country_code))),
  region TEXT,
  employment_type TEXT CHECK(employment_type IS NULL OR employment_type IN (
    'full_time', 'part_time', 'contract', 'temporary', 'internship', 'apprenticeship', 'other', 'unknown'
  )),
  job_family_key TEXT,
  source_posted_at TEXT,
  source_updated_at TEXT,
  first_collected_at TEXT NOT NULL,
  last_collected_at TEXT NOT NULL,
  lifecycle_status TEXT NOT NULL DEFAULT 'observed'
    CHECK(lifecycle_status IN ('observed', 'active', 'changed', 'missing', 'closed', 'quarantined')),
  content_hash TEXT NOT NULL CHECK(length(content_hash) = 64 AND content_hash NOT GLOB '*[^0-9a-f]*'),
  raw_snapshot_ref TEXT NOT NULL CHECK(length(trim(raw_snapshot_ref)) > 0),
  parser_version TEXT NOT NULL CHECK(length(trim(parser_version)) > 0),
  extraction_metadata_json TEXT NOT NULL DEFAULT '{}'
    CHECK(json_valid(extraction_metadata_json) AND json_type(extraction_metadata_json) = 'object'),
  quality_status TEXT NOT NULL DEFAULT 'raw'
    CHECK(quality_status IN ('raw', 'parsed', 'validation_failed', 'review_pending', 'approved', 'publishable', 'published')),
  review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(review_status IN ('pending', 'approved', 'rejected')),
  reviewed_by TEXT,
  reviewed_at TEXT,
  publication_status TEXT NOT NULL DEFAULT 'blocked'
    CHECK(publication_status IN ('blocked', 'review_pending', 'eligible', 'published')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(source_id, company_id) REFERENCES career_sources(source_id, company_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  UNIQUE(source_id, source_native_id),
  CHECK(last_collected_at >= first_collected_at),
  CHECK(review_status <> 'approved' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)),
  CHECK(publication_status <> 'published' OR (quality_status = 'published' AND review_status = 'approved'))
) STRICT;

CREATE INDEX job_postings_company_status_index
  ON job_postings(company_id, lifecycle_status, last_collected_at);
CREATE INDEX job_postings_source_status_index
  ON job_postings(source_id, lifecycle_status, source_updated_at);
CREATE INDEX job_postings_hash_index ON job_postings(content_hash);
CREATE INDEX job_postings_family_index ON job_postings(job_family_key, lifecycle_status);

CREATE TABLE skills (
  skill_id TEXT PRIMARY KEY CHECK(length(skill_id) BETWEEN 1 AND 128),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  canonical_name TEXT NOT NULL CHECK(length(trim(canonical_name)) > 0),
  aliases_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(aliases_json) AND json_type(aliases_json) = 'array'),
  category TEXT NOT NULL CHECK(length(trim(category)) > 0),
  definition TEXT NOT NULL CHECK(length(trim(definition)) > 0),
  evidence_expectations TEXT NOT NULL CHECK(length(trim(evidence_expectations)) > 0),
  lifecycle_status TEXT NOT NULL DEFAULT 'draft'
    CHECK(lifecycle_status IN ('draft', 'review', 'active', 'deprecated')),
  taxonomy_version INTEGER NOT NULL DEFAULT 1 CHECK(taxonomy_version >= 1),
  review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(review_status IN ('pending', 'approved', 'rejected')),
  reviewed_by TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(canonical_name COLLATE NOCASE),
  CHECK(review_status <> 'approved' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
) STRICT;

CREATE INDEX skills_category_status_index ON skills(category, lifecycle_status);

CREATE TABLE skill_aliases (
  skill_id TEXT NOT NULL REFERENCES skills(skill_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  alias TEXT NOT NULL CHECK(length(trim(alias)) > 0),
  language_code TEXT NOT NULL DEFAULT 'und' CHECK(length(language_code) BETWEEN 2 AND 16),
  alias_type TEXT NOT NULL DEFAULT 'synonym'
    CHECK(alias_type IN ('synonym', 'abbreviation', 'translation', 'legacy')),
  lifecycle_status TEXT NOT NULL DEFAULT 'draft'
    CHECK(lifecycle_status IN ('draft', 'review', 'active', 'deprecated')),
  review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(review_status IN ('pending', 'approved', 'rejected')),
  reviewed_by TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(skill_id, alias, language_code),
  CHECK(review_status <> 'approved' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
) STRICT;

CREATE UNIQUE INDEX skill_aliases_normalized_unique
  ON skill_aliases(lower(trim(alias)), language_code);
CREATE INDEX skill_aliases_skill_status_index
  ON skill_aliases(skill_id, lifecycle_status, review_status);

CREATE TABLE job_skill_relations (
  job_id TEXT NOT NULL REFERENCES job_postings(job_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  skill_id TEXT NOT NULL REFERENCES skills(skill_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  requirement_strength TEXT NOT NULL
    CHECK(requirement_strength IN ('mentioned', 'preferred', 'required', 'core')),
  evidence_excerpt TEXT NOT NULL CHECK(length(trim(evidence_excerpt)) > 0),
  parser_confidence REAL CHECK(parser_confidence IS NULL OR parser_confidence BETWEEN 0.0 AND 1.0),
  extraction_method TEXT NOT NULL CHECK(extraction_method IN ('deterministic', 'model_assisted', 'manual')),
  extraction_version TEXT NOT NULL CHECK(length(trim(extraction_version)) > 0),
  review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(review_status IN ('pending', 'approved', 'rejected')),
  reviewed_by TEXT,
  reviewed_at TEXT,
  first_observed_at TEXT NOT NULL,
  last_observed_at TEXT NOT NULL,
  PRIMARY KEY(job_id, skill_id),
  CHECK(last_observed_at >= first_observed_at),
  CHECK(review_status <> 'approved' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
) STRICT;

CREATE INDEX job_skill_relations_skill_index
  ON job_skill_relations(skill_id, requirement_strength, review_status);

CREATE TABLE job_changes (
  change_id TEXT PRIMARY KEY CHECK(length(change_id) BETWEEN 1 AND 160),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  job_id TEXT NOT NULL REFERENCES job_postings(job_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  source_id TEXT NOT NULL REFERENCES career_sources(source_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  change_type TEXT NOT NULL CHECK(change_type IN (
    'first_observed', 'content_changed', 'status_changed', 'source_updated', 'location_changed',
    'missing', 'closed', 'reopened', 'quarantined'
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

CREATE INDEX job_changes_job_time_index ON job_changes(job_id, observed_at);
CREATE INDEX job_changes_source_time_index ON job_changes(source_id, collected_at);

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

CREATE TABLE project_templates (
  project_template_id TEXT PRIMARY KEY CHECK(length(project_template_id) BETWEEN 1 AND 128),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  slug TEXT NOT NULL UNIQUE CHECK(length(trim(slug)) > 0),
  title TEXT NOT NULL CHECK(length(trim(title)) > 0),
  summary TEXT NOT NULL CHECK(length(trim(summary)) > 0),
  difficulty TEXT NOT NULL CHECK(difficulty IN ('introductory', 'intermediate', 'advanced')),
  estimated_effort_hours INTEGER CHECK(estimated_effort_hours IS NULL OR estimated_effort_hours > 0),
  prerequisites_text TEXT,
  deliverables_json TEXT NOT NULL CHECK(json_valid(deliverables_json) AND json_type(deliverables_json) = 'array'),
  acceptance_evidence_json TEXT NOT NULL
    CHECK(json_valid(acceptance_evidence_json) AND json_type(acceptance_evidence_json) = 'array'),
  safety_notes TEXT,
  license_notes TEXT,
  lifecycle_status TEXT NOT NULL DEFAULT 'draft'
    CHECK(lifecycle_status IN ('draft', 'review', 'approved', 'archived')),
  review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(review_status IN ('pending', 'approved', 'rejected')),
  reviewed_by TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK(review_status <> 'approved' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
) STRICT;

CREATE TABLE project_template_job_families (
  project_template_id TEXT NOT NULL REFERENCES project_templates(project_template_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  job_family_key TEXT NOT NULL CHECK(length(trim(job_family_key)) > 0),
  PRIMARY KEY(project_template_id, job_family_key)
) STRICT;

CREATE TABLE project_template_skills (
  project_template_id TEXT NOT NULL REFERENCES project_templates(project_template_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  skill_id TEXT NOT NULL REFERENCES skills(skill_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
  evidence_expectation TEXT NOT NULL CHECK(length(trim(evidence_expectation)) > 0),
  PRIMARY KEY(project_template_id, skill_id)
) STRICT;

CREATE TABLE pipeline_runs (
  run_id TEXT PRIMARY KEY CHECK(length(run_id) BETWEEN 1 AND 160),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  pipeline_name TEXT NOT NULL CHECK(length(trim(pipeline_name)) > 0),
  pipeline_stage TEXT NOT NULL CHECK(pipeline_stage IN (
    'collection', 'parsing', 'validation', 'review', 'internal_export', 'public_snapshot', 'migration'
  )),
  environment TEXT NOT NULL CHECK(environment IN ('test', 'staging', 'production')),
  status TEXT NOT NULL CHECK(status IN ('started', 'succeeded', 'failed', 'cancelled')),
  code_version TEXT NOT NULL CHECK(length(trim(code_version)) > 0),
  config_hash TEXT CHECK(config_hash IS NULL OR (
    length(config_hash) = 64 AND config_hash NOT GLOB '*[^0-9a-f]*'
  )),
  input_refs_json TEXT NOT NULL DEFAULT '[]'
    CHECK(json_valid(input_refs_json) AND json_type(input_refs_json) = 'array'),
  output_refs_json TEXT NOT NULL DEFAULT '[]'
    CHECK(json_valid(output_refs_json) AND json_type(output_refs_json) = 'array'),
  metrics_json TEXT NOT NULL DEFAULT '{}'
    CHECK(json_valid(metrics_json) AND json_type(metrics_json) = 'object'),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  error_summary TEXT,
  created_at TEXT NOT NULL,
  CHECK((status = 'started' AND finished_at IS NULL) OR (status <> 'started' AND finished_at IS NOT NULL)),
  CHECK(status <> 'failed' OR error_summary IS NOT NULL)
) STRICT;

CREATE INDEX pipeline_runs_stage_time_index
  ON pipeline_runs(pipeline_stage, environment, started_at);
CREATE INDEX pipeline_runs_status_index ON pipeline_runs(status, started_at);

CREATE TABLE review_queue (
  review_id TEXT PRIMARY KEY CHECK(length(review_id) BETWEEN 1 AND 160),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version = 1),
  entity_type TEXT NOT NULL CHECK(entity_type IN (
    'company', 'career_source', 'job_posting', 'skill', 'job_skill_relation',
    'job_change', 'project_template'
  )),
  entity_id TEXT NOT NULL CHECK(length(trim(entity_id)) > 0),
  reason_code TEXT NOT NULL CHECK(length(trim(reason_code)) > 0),
  evidence_json TEXT NOT NULL DEFAULT '{}'
    CHECK(json_valid(evidence_json) AND json_type(evidence_json) = 'object'),
  priority INTEGER NOT NULL DEFAULT 50 CHECK(priority BETWEEN 0 AND 100),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending', 'in_review', 'approved', 'rejected', 'cancelled')),
  assigned_to TEXT,
  reviewed_by TEXT,
  reviewed_at TEXT,
  resolution_notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK(status NOT IN ('approved', 'rejected') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
) STRICT;

CREATE INDEX review_queue_status_priority_index
  ON review_queue(status, priority DESC, created_at);
CREATE INDEX review_queue_entity_index ON review_queue(entity_type, entity_id, status);

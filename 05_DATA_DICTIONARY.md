# Data Dictionary

Status: Phase 3A source-verification extension implemented; the formal external
database is at migration 3 with one verified company/source and no job/change rows.

## Current content frontmatter

| Field | Current type | Meaning/risk |
|---|---|---|
| `title` | string, required | Public article title |
| `date` | date, required (legacy) | Existing publication date; retained for compatibility |
| `publishedAt` | optional date | Explicit publication time; public display falls back to legacy `date` |
| `updatedAt` | optional date | Content/governance update time from frontmatter; never derived from build time |
| `updated` | optional date (legacy) | Older compatibility field; not used as the Phase 1 governance field |
| `author` | string | Defaults to `Editorial Team` |
| `tags` | string array | Free-form labels |
| `industry_sector` | enum | Robot-sector classification |
| `data_source` | optional string | Free text; not a source registry relation |
| `confidence_level` | optional legacy enum | Deprecated for public display; no default and not accepted as evidence/review state |
| `status` | required enum | `draft`, `review`, `published`, `archived`; only exact `published` is public |
| `sourceType` | optional enum | `academic_paper`, `official_source`, `first_party`, or `other` |
| `sourceUrls` | optional URL array in schema | Required by the deterministic gate for every published entry |
| `reviewStatus` | optional enum in schema | `ai_generated`, `ai_assisted`, `pending_review`, `human_reviewed`, `source_verified`; required for publication by the gate |
| `summary` | optional string | Public excerpt |
| `cover_image` | optional string | Public asset reference |
| `career_level` | optional enum | Career article audience level |
| `skill_domain` | string array | Free-form skills; not normalized |
| `salary_range` | optional string | Unstructured salary claim |
| `region` | optional string | Unstructured geography |

## Phase 1 public content minimum

A public entry must declare:

- `title`;
- `status: published`;
- valid `publishedAt` or legacy `date`;
- a valid governance `updatedAt`;
- `sourceType`;
- a non-empty structured `sourceUrls` array containing at least one external, non-placeholder URL;
- `reviewStatus` describing the actual review state.

Missing fields do not receive invented defaults in the quality gate. The site itself cannot be the only factual source. `example.com`, local hosts, and fixture/demo/test payloads are rejected.

Current retained public research uses `academic_paper`, normalized arXiv URLs, and `pending_review`. This establishes paper identity only; it does not certify every interpretation in the article body.

## Required provenance envelope for future external records

Every collected record must carry:

- `source_id`: registry foreign key.
- `source_url`: exact official page/API URL.
- `collected_at`: UTC retrieval timestamp.
- `source_updated_at`: source-reported update time when available.
- `content_hash`: deterministic hash of normalized source content.
- `raw_snapshot_ref`: immutable raw snapshot location.
- `parser_version`: version/commit of deterministic parser.
- `quality_status`: validation result.
- `review_status`: pending/approved/rejected and reviewer metadata.

## Version 1 career-intelligence entities

The logical contracts are versioned in
`career-intelligence/schema/v1/entities.schema.json`; the physical mapping is in
`docs/PHASE_2_DATA_MODEL.md` and migration `0001_initial.sql`.

### `companies`

Canonical employer identity: legal/display names, aliases, country/region, official website, career URL, ATS type, active state, and verification timestamps.

### `career_sources`

One registered source endpoint per collection method: company, source URL, source type, collection method, allowed scope, frequency, terms/robots review, enabled state, timestamps, and last health result.

### `job_postings`

Source-native job identity plus normalized title, description, company, location, employment type, job family, source dates, status, content hash, provenance envelope, and review state.

### `skills`

Canonical skill ID/name, category, definition, evidence expectations, lifecycle status, review state, and taxonomy version. Aliases are normalized in `skill_aliases` and decoded into the logical `aliases` field.

### `job_skill_relations`

Job-to-skill relation with requirement strength, evidence excerpt, parser confidence, extraction method/version, and review state.

### `job_changes`

Append-only status/content change history: job, change type, old/new hash or fields, observation timestamp, and source observation.

### `project_templates`

Portfolio project template: target job families, skills demonstrated, deliverables, acceptance evidence, estimated effort, prerequisites, and safety/licensing notes.

## Phase 2 operational tables

- `schema_migrations`: ordered filename/checksum/application ledger.
- `system_controls`: independently configurable collection and public-snapshot switches; both default disabled.
- `system_control_events`: trigger-created audit rows for every explicit control update.
- `pipeline_runs`: immutable-at-source execution metadata for later collection, parsing, validation, review, export, and migration commands.
- `review_queue`: cross-entity manual-review items with priority, evidence, assignment, and resolution.
- `project_template_job_families` and `project_template_skills`: normalized project target links.

## Phase 3A source-verification tables

- `career_source_profiles`: one-to-one extension of the existing `career_sources`
  row with official/listing URLs, MVP source type, ATS vendor, allowed domains,
  adapter/parser versions, identity strategy, verification evidence/status, fail-closed
  source controls, health timestamps, failure reason, review fields, and notes.
- `source_verification_runs`: append-only fixture/live-smoke result ledger with
  external summary path, bounded request counts, parsed count, and before/after
  `job_postings`/`job_changes` counts. Equal-count constraints prevent a successful
  dry-run record from asserting business-table writes.

The source-profile vocabulary is `candidate`, `verified`, `paused`, or `blocked`.
The MVP source structures are `official_html`, `standard_ats`, and `official_json`.
`collection_enabled` and `publication_enabled` default to and remain 0 in Phase 3A.

The non-database staging DTO contains `source_id`, `company_id`,
`external_job_id`, `job_key`, `title`, `location`, `department`,
`employment_type`, `description`, `detail_url`, `canonical_url`, `published_at`,
`content_hash`, and `fetched_at`, plus requested/final URL and identity strategy.
It is serialized only beneath the explicitly supplied external staging directory.

Phase 2.1 creates only the `system_controls` singleton, its control-event audit rows,
and the migration ledger. All domain,
pipeline-run, and review-queue tables remain empty.

## Phase 2.1 public DTO boundary

- `companies.json`: `id`, `name`, `countryCode`, `regions`, `websiteUrl`, `careerUrl`.
- `jobs.json`: `id`, `companyId`, `title`, `location`, `countryCode`, `region`, `employmentType`, `jobFamily`, `sourceUrl`, `postedAt`, `updatedAt`, `status`.
- `skills.json`: `id`, `name`, `aliases`, `category`, `definition`, `evidenceExpectations`.
- `role-summary.json`: `role`, `jobCount`, `companyCount`, `skillIds`.
- `project-templates.json`: `id`, `slug`, `title`, `summary`, `difficulty`, `estimatedEffortHours`, `prerequisites`, `deliverables`, `acceptanceEvidence`, `safetyNotes`, `licenseNotes`, `targetJobFamilies`, `skillIds`.

The exporter rejects every field outside these allowlists. In particular,
`raw_snapshot_path`, `raw_snapshot_ref`, `content_hash`, internal review fields,
errors/logs, confidence values, parser/extraction metadata, and local paths are never
public DTO fields. `manifest.json` contains only snapshot schema/version metadata,
relative entity filenames, counts, and SHA-256 checksums.

## Controlled vocabularies to define later

- Eight robot job families.
- 50–100 normalized skills and aliases.
- Job lifecycle: observed, active, changed, missing, closed, quarantined.
- Source lifecycle: candidate, verified, enabled, degraded, paused, retired.
- Quality lifecycle: raw, parsed, validation_failed, review_pending, approved, publishable, published.

No AI-generated classification may silently become canonical. Model-assisted outputs require stored evidence and review state.

# Data Dictionary

Status: logical baseline only. No career-intelligence database exists yet.

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

## Future logical entities (Phase 2 draft)

These names are required by the project plan but are not implemented in Phase 0.

### `companies`

Canonical employer identity: legal/display names, aliases, country/region, official website, career URL, ATS type, active state, and verification timestamps.

### `career_sources`

One registered source endpoint per collection method: company, source URL, source type, collection method, allowed scope, frequency, terms/robots review, enabled state, timestamps, and last health result.

### `job_postings`

Source-native job identity plus normalized title, description, company, location, employment type, job family, source dates, status, content hash, provenance envelope, and review state.

### `skills`

Canonical skill ID/name, aliases, category, definition, evidence expectations, lifecycle status, and version.

### `job_skill_relations`

Job-to-skill relation with requirement strength, evidence excerpt, parser confidence, extraction method/version, and review state.

### `job_changes`

Append-only status/content change history: job, change type, old/new hash or fields, observation timestamp, and source observation.

### `project_templates`

Portfolio project template: target job families, skills demonstrated, deliverables, acceptance evidence, estimated effort, prerequisites, and safety/licensing notes.

## Controlled vocabularies to define later

- Eight robot job families.
- 50–100 normalized skills and aliases.
- Job lifecycle: observed, active, changed, missing, closed, quarantined.
- Source lifecycle: candidate, verified, enabled, degraded, paused, retired.
- Quality lifecycle: raw, parsed, validation_failed, review_pending, approved, publishable, published.

No AI-generated classification may silently become canonical. Model-assisted outputs require stored evidence and review state.

# Phase 2 Data Model and Physical Mapping

Date: 2026-07-18 UTC

The version 1 JSON Schema bundle defines the seven logical exchange contracts at
`career-intelligence/schema/v1/entities.schema.json`. The SQLite migration at
`career-intelligence/migrations/0001_initial.sql` implements those entities plus
normalized relations and operational control tables. A logical contract does not
replace a physical table.

## Logical contract to physical storage

| Version 1 entity contract | Primary physical table | Supporting physical tables / mapping |
|---|---|---|
| `company` | `companies` | Referenced by `career_sources` and `job_postings` foreign keys |
| `career_source` | `career_sources` | Collection attempts are attributable through `pipeline_runs`; uncertain records can enter `review_queue` |
| `job_posting` | `job_postings` | Source/company composite foreign key; observations append to `job_changes` |
| `skill` | `skills` | Logical `aliases` array is normalized into `skill_aliases` |
| `job_skill_relation` | `job_skill_relations` | Composite primary key links `job_postings` and `skills`; evidence/review fields are stored on the relation |
| `job_change` | `job_changes` | Append-only triggers prohibit update and delete |
| `project_template` | `project_templates` | Many-to-many links use `project_template_skills`; job-family keys use `project_template_job_families` until the reviewed Phase 5 taxonomy exists |

SQLite JSON text columns such as `aliases_json`, `scope_json`, and
`deliverables_json` are decoded to arrays/objects at the logical contract and
snapshot boundary.

## Complete application-table inventory

| Physical table | Contract/role | Phase 2 state |
|---|---|---|
| `schema_migrations` | Checksummed ordered migration ledger created by the migrator | One row for migration 1 after initialization |
| `system_controls` | Independent collection/publication safety switches with reason and actor | Singleton row; both switches default off |
| `companies` | `company` entity | Empty |
| `career_sources` | `career_source` entity | Empty; sources default disabled |
| `job_postings` | `job_posting` entity and full provenance envelope | Empty |
| `skills` | `skill` canonical record | Empty |
| `skill_aliases` | Normalized aliases belonging to `skill` | Empty |
| `job_skill_relations` | `job_skill_relation` entity | Empty |
| `job_changes` | `job_change` entity; append-only | Empty |
| `project_templates` | `project_template` entity | Empty |
| `project_template_job_families` | Normalized project-to-future-job-family link | Empty |
| `project_template_skills` | Normalized project-to-skill/evidence link | Empty |
| `pipeline_runs` | Collection/parsing/validation/review/export/migration run audit | Empty; no collector or schedule exists |
| `review_queue` | Cross-entity manual review work queue | Empty |

SQLite internal tables are excluded from this application mapping. No seed
migration inserts a company, source, job, skill, alias, relation, change, project,
pipeline run, or review item.

## Integrity and state rules

- Foreign keys are enabled on every repository-managed connection.
- WAL and a 5-second busy timeout support concurrent readers and bounded serialized
  writers. Each migration uses `BEGIN IMMEDIATE`, so another writer cannot mutate
  the database during a schema transition.
- `job_changes` cannot be updated or deleted.
- Source enablement requires verified ownership and approved access reviews.
- Published jobs require approved review and published quality status.
- Model-assisted relations retain extraction evidence/version and cannot silently
  become canonical skill records.
- Public snapshots read one SQLite transaction, contain approved rows only, validate
  all checksums/counts before exposure, and update `current` atomically.

# Acceptance Criteria

## Phase 0 acceptance

- [x] Environment, disk, runtimes, repository, branch, remote, and starting changes inventoried.
- [x] Production role and current Vercel delivery identified.
- [x] Pre-refactor tag and refactor branch created from a clean baseline.
- [x] Frontend/backend, commands, runtime managers, proxy, domain, HTTPS, database, migrations, logs, schedules, and Hermes inventoried.
- [x] Career/research/source/demo-data files and current data flow documented.
- [x] Demonstration/unverified-data candidate list created without deletion.
- [x] Minimal production/development isolation recommendations documented.
- [x] Required project-control files created without secrets.
- [x] Build passed; absent test script and existing Astro warnings are recorded.
- [x] Final diff contains only Phase 0 documentation.
- [x] Scoped commit exists.
- [x] Branch and backup tag are pushed or the precise push blocker is recorded.
- [x] No Phase 1 content change or production deployment occurred.

## Phase 1 acceptance

- [x] Claim/evidence ledger covers homepage samples, career surveys, BOM interviews/costs, feedback/database wording, legacy confidence labels, test payload, and duplicate arXiv content.
- [x] Unsupported statements are absent from public source files and generated output.
- [x] Two career articles, two BOM articles, and one generated test article no longer produce public details.
- [x] The unused root test payload is deleted and no production/Hermes reference remains.
- [x] Seven duplicate-source groups were reviewed by normalized arXiv ID; ten files were removed and seven canonical pages retained.
- [x] All 28 withdrawn detail URLs have permanent redirect definitions.
- [x] Missing or non-published status cannot appear in lists or static detail routes.
- [x] Source/date/review fields exist in schema and a shared bilingual component renders only present, truthful metadata.
- [x] Published content has at least one valid external structured source URL and no placeholder/self-only source.
- [x] `npm run content:check` and the deliberate failure/recovery fixture test pass.
- [x] `npm run build` invokes the quality gate and post-build verifier; Chinese and English pages build successfully.
- [x] Build output contains no withdrawn article body or user-visible legacy estimate label.
- [x] No dependency upgrade, audit fix, Hermes change, production merge, or deployment occurred.
- [x] One scoped Phase 1 commit is pushed to `origin/refactor/career-intelligence`.

## Phase 2 acceptance

- [x] Storage selection follows documented staging, backup/restore, concurrency, query, and snapshot evaluation.
- [x] SQLite WAL is limited to the current single-host serialized-writer workload, with explicit PostgreSQL re-evaluation gates.
- [x] Seven version 1 JSON entity contracts exist and are mapped to physical tables rather than replacing them.
- [x] Physical tables include `schema_migrations`, `companies`, `career_sources`, `job_postings`, `skills`, `skill_aliases`, `job_skill_relations`, `job_changes`, `project_templates`, `pipeline_runs`, and `review_queue`, plus documented controls/relations.
- [x] Migration filenames/order/checksums are verified and migration transactions exclude concurrent writers.
- [x] Collection and public snapshot controls default off and can be enabled independently only through an explicit reasoned command.
- [x] Backup refuses existing destinations, validates a temporary copy, and installs without overwrite.
- [x] Public snapshot generation requires publication enablement, reads a consistent transaction, includes approved rows only, validates complete output, and atomically switches `current`; replacement is explicit.
- [x] Tests cover two readers, read-during-write behavior, WAL, busy timeout, waiting writers, migration write exclusion, snapshot consistency, backup restore/validate, foreign keys, and append-only job changes.
- [x] No factual company, source, job, skill, relation, change, project, pipeline-run, or review-queue seed record exists.
- [x] Content tests and the production build pass with only documented baseline warnings.
- [x] No collector, Hermes change, operational database, public-content change, `master` change, or production deployment is included.
- [x] One scoped Phase 2 commit is pushed to `origin/refactor/career-intelligence`.

## Phase 2.1 acceptance

- [x] The five `/root/robot-data` runtime subdirectories exist outside Git with mode `0700`.
- [x] The empty staging database is migrated through version 2, validates, uses mode `0600`, and leaves all factual tables empty.
- [x] A non-overwriting mode-`0600` backup is validated, restored to an independent database, revalidated, and retained without the disposable restore target.
- [x] Python 3.12 standard-library `sqlite3` replaces Node's experimental SQLite API for every data operation.
- [x] The public snapshot contains exactly the manifest and five required entity files under a repository-owned ordinary-file tree.
- [x] Strict DTO allowlists reject unknown/internal fields, local paths, confidence, audit, error, raw-snapshot, and content-hash data.
- [x] Snapshot publication uses a temporary directory, full validation, immutable version rename, and atomic ordinary `current.json` replacement; no symlink or external target is accepted.
- [x] Collection and publication remain independently default-off; explicit changes require actor/reason and are appended to `system_control_events`.
- [x] Tests cover external paths/modes, migrations/checksums, two readers, read during write, WAL, busy timeout, migration write exclusion, consistent snapshots, backup/restore, no-overwrite, Astro static imports, and Vercel path independence.
- [x] Content checks, negative tests, Astro production build, generated-output verification, and `git diff --check` pass.
- [x] Only identified Phase 2 temporary test directories were removed; the formal database and backup remain.
- [x] One scoped Phase 2.1 commit is pushed to `origin/refactor/career-intelligence`.
- [x] No real data, Phase 3 work, `master` change, `/root/robot` change, Hermes change, or deployment occurred.

## Initial product targets

- 20 verified companies in the source registry.
- 10 stable official-source collectors.
- 200–300 valid, source-backed job postings.
- 8 reviewed robotics job families.
- 50–100 normalized skills.
- At least 12 evidence-oriented portfolio project templates.
- Daily recruitment change monitoring.
- Weekly career-intelligence report.
- Rebuilt career-navigation pages.
- Controlled Hermes scheduling with quality gates and exception handling.

## Per-record quality gate

A job posting is valid only when:

1. It comes from an enabled official source.
2. Company and source-native job identity are present.
3. Source URL, collection time, source update time when available, and raw snapshot reference are retained.
4. Required fields pass schema validation.
5. Duplicate matching and content hash checks pass.
6. Parser version and extraction evidence are recorded.
7. Job status is supported by observations, not guessed.
8. Model-assisted fields remain reviewable and are never represented as source facts.
9. The record passes manual review or an explicitly approved deterministic rule.

## Publication acceptance

- Collection, parsing, analysis, and publishing run as separate commands/artifacts.
- Failed or quarantined records cannot enter generated site content.
- A preview build succeeds and representative records are manually checked.
- Production data and logs are isolated from staging.
- Backup and rollback are tested.
- Production merge/deployment is explicitly approved.

## Current gap summary

| Target | Baseline |
|---|---|
| Registered career companies | 0 |
| Stable career collectors | 0 |
| Structured job postings | 0 |
| Job families | 0 normalized |
| Standard skills | 0 normalized |
| Project templates | 0 |
| Career database | empty external staging SQLite; no factual rows |
| Career Hermes schedules | none |
| Automated quality tests | content, database, snapshot, negative-fixture, and build gates |

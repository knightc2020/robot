# Current State

Baseline date: 2026-07-18 UTC

Production worktree: `/root/robot`

Refactor development worktree: `/root/robot-career-refactor`

Phase 0 assessment scope was inventory only. Phase 1 changes described at the end of this document exist only on `refactor/career-intelligence`; production remains unchanged.

## 1. Environment

| Item | Observed state |
|---|---|
| Operating system | Ubuntu 24.04.4 LTS, Linux 6.8, x86_64 |
| Disk | 96 GB filesystem, approximately 56 GB free (42% used at baseline) |
| Node.js | v24.12.0 |
| npm | 11.6.2 |
| Python | 3.12.3 system Python; Hermes uses its own Python 3.11.15 environment |
| Git | 2.43.0 |
| Hermes | Hermes Agent v0.18.2 at `/usr/local/bin/hermes` |

## 2. Git and backup state

- Starting state was clean: `master` matched `origin/master` at `7a9a746` with no uncommitted changes.
- Remote: `https://github.com/knightc2020/robot.git`.
- Refactor branch created: `refactor/career-intelligence`.
- Pre-refactor annotated tag created on the untouched baseline: `pre-career-intelligence-refactor-2026-07-18`.
- No checkpoint commit was needed because the starting worktree was clean.
- Phase 0 is limited to the project-control documentation listed in `04_PROJECT_INDEX.md`.
- Phase 0 commit `71255d4`, the refactor branch, and the pre-refactor tag were pushed and verified.

## 3. Current architecture

- Static bilingual site built with Astro 5, MDX, Tailwind CSS 4, and TypeScript configuration.
- npm with `package-lock.json` is the package manager.
- Source content is file-based Markdown/MDX under `src/content/{cn,en}/{research,career}`.
- Page generation uses Astro content collections and static routes.
- There is no current backend API, application server, database, ORM, migration directory, or database schema.
- Historical Git commits show an Astro write API/webhook existed briefly and was removed in commit `82b95a9`; it is not part of the current runtime.
- Build command: `npm run build`.
- Development command: `npm run dev`.
- Local preview command: `npm run preview`.
- No automated test script, lint script, or type-check script is defined in `package.json` at baseline.

## 4. Production and deployment

- `https://robotcareer.cloud` redirects to `https://www.robotcareer.cloud/`.
- The public endpoint and career pages return Vercel response headers; HTTPS and edge delivery are managed by Vercel, not by an Nginx/Caddy service in this repository.
- No running Docker container, PM2 installation, local Astro/Node process, project-specific systemd unit, or project-specific Nginx/Apache/Caddy configuration was found on the VPS.
- The VPS checkout still participates in production workflows because Hermes can push repository changes. It is therefore operationally production-adjacent even though it does not serve web traffic.
- No dedicated staging branch, staging worktree, staging database, staging port, project log directory, or project backup directory was found.
- No repository-local Vercel project metadata was found. Vercel preview behavior and dashboard-side environment separation remain unverified.

## 5. Content inventory and current data flow

- 27 content files exist under `src/content`.
- Career content consists of two published static files: one Chinese salary article and one English career-map article.
- There are no company records, career-source records, job postings, normalized skills, job changes, or project templates.
- Current article flow is:

  1. A person or automation creates/updates Markdown or MDX.
  2. The file is committed to GitHub `master`.
  3. Vercel builds Astro.
  4. Astro validates frontmatter, reads content collections, and emits static HTML.
  5. Vercel publishes the build to the public domain.

- Because publication is Git-driven, a direct push to `master` can change production without a separate data-quality gate.
- `status: published` is the only content-level publication filter on career/research index pages. Detail static paths are generated from all collection entries, so a non-published detail may still be built if its URL is known.
- No article contains an `updated` frontmatter field at baseline.

## 6. Hermes current role

- The system Hermes gateway service is enabled and reported active by systemd.
- `hermes cron status` simultaneously reports that the gateway is not running. This health-check disagreement must be resolved before relying on new schedules.
- Active jobs at baseline:

  - `Fetch arXiv Papers` every 720 minutes. It reads arXiv `cs.RO`, generates Chinese research content, and uses the GitHub API to write directly to repository `master`.
  - `Weekly Robotics Research Review` at `00:30 UTC` every Monday. Its work directory is `/root/robot` and its prompt can build, commit, and push to `master`.

- Hermes is not currently generating career content or collecting job postings.
- The weekly job sharing `/root/robot` with the refactor worktree is a branch-collision risk.
- Hermes logs are under `/root/.hermes/logs`, cron definitions under `/root/.hermes/cron`, and system-service logs are available through the system journal. Credentials/configuration remain outside Git.

## 7. Demonstration or unverified data candidates

This is a candidate list only. Nothing was removed in Phase 0.

| Data/content | Public location | Code/data file | Provenance status | Recommended Phase 1 treatment | Removal risk |
|---|---|---|---|---|---|
| `340+` frontline engineer samples | Chinese and English homepages | `src/pages/cn/index.astro`, `src/pages/en/index.astro` | No source artifact found | Remove or replace with sourced, dated metric | Homepage layout/copy change; low code risk |
| `50+` supplier interviews | Chinese and English homepages | same homepage files | No interview register or evidence found | Remove claim pending proof | Homepage credibility change; low code risk |
| `340` anonymous Chinese survey responses and salary table | Chinese career article | `src/content/cn/career/robotics-salary-2025.mdx` | No raw survey, methodology package, offer URLs, or consent record found | Unpublish/quarantine; retain in Git history | Existing career section may become empty |
| `210` anonymous global survey responses and salary table | English career article | `src/content/en/career/robotics-career-map-2025.mdx` | No raw survey or source URLs found | Unpublish/quarantine; retain in Git history | English career section may become empty |
| 12 supplier interviews and actuator BOM numbers | Chinese/English research articles | both `humanoid-actuator-bom-2025.mdx` files | Generic source label only; no evidence links or interview register | Quarantine or downgrade until evidence is registered | Affects flagship research copy and homepage cards |
| “all feedback is cross-verified and entered into database” | Article footers | `src/components/FeedbackFlywheel.astro` | No database or review workflow exists | Correct copy to match actual process | Changes trust/feedback messaging |
| Raw `estimated` badge on Chinese pages | Published article detail/news UI | `src/layouts/ArticleLayout.astro`, `src/pages/research-news/index.astro`, content frontmatter | Enum is rendered without localization or definition | Localize and define semantics; reassess defaults | Broad visual/content-label change |
| Test article payload marked `published` | Repository root, not directly rendered | `test-payload.json` | Clearly a legacy test fixture; no source URL | Move to explicit test fixtures or remove after dependency check | Historical tooling may reference filename |
| Duplicate arXiv articles | Chinese research/news routes | multiple `src/content/cn/research/arxiv-*.md` files | Source URLs prove duplicate source identity | Select canonical record and redirect/unpublish duplicates | Existing public URLs and search indexing |

Confirmed same-source duplicate groups in Chinese research content:

- arXiv `2602.23287`: 5 files.
- arXiv `2602.22243`: 2 files.
- arXiv `2602.23832`: 2 files.
- arXiv `2603.02291`: 2 files.
- arXiv `2605.04649`: 2 files.
- arXiv `2605.05241`: 2 files.
- arXiv `2605.06662`: 2 files.

## 8. Security and operational risks

1. Direct automation writes to `master`, which bypasses a preview and quality-review branch.
2. The weekly Hermes job uses the same checkout as active development.
3. Hermes service status is inconsistent between systemd and the Hermes CLI.
4. The repository has no automated tests, lint, source-provenance validator, duplicate detector, or publication gate.
5. Public claims imply a database and validation process that do not exist in the current codebase.
6. Career and BOM claims lack auditable source material.
7. All detail pages are included in static paths regardless of publication status.
8. No project-specific staging, backups, logs, or rollback rehearsal is documented.
9. The current arXiv automation records only the last URL, which is insufficient for robust duplicate prevention.
10. `node_modules`, build output, and the production-adjacent checkout coexist in one VPS path, increasing accidental-operations risk.

## 9. Minimal development/production isolation recommendation

Do not migrate production in Phase 0. Before collection work begins:

1. Keep `/root/robot` as the clean production/automation worktree on `master`; never use it for Codex refactor development.
2. Use `/root/robot-career-refactor` for Codex development on `refactor/career-intelligence`.
3. Give each future Hermes publisher its own clean worktree or GitHub-API-only flow pinned to an explicit branch.
4. Use a separate preview branch/project environment; keep `master` production-only.
5. Store career collection raw data and normalized data outside `src/content`; publish only reviewed exports.
6. Use separate staging and production database files/services, credentials, logs, and backup paths when a database is introduced.
7. Add a pre-publication command that validates schema, provenance, duplicates, and status transitions before any commit targeting `master`.

## 10. Recommended Phase 1 plan

1. Freeze direct edits to the identified candidate files while creating an evidence ledger.
2. Define a reversible status for unsupported public claims (`draft`/`quarantined`) before removing visible copy.
3. Remove or neutralize unsupported homepage metrics and methodology assertions.
4. Quarantine the two career articles and two BOM articles unless evidence is supplied.
5. Localize and document confidence labels; stop defaulting missing evidence to a publishable-looking estimate.
6. Canonicalize same-source articles with a URL-preservation/redirect decision.
7. Add required `source_url`, `collected_at`, and `updated`/`observed_at` governance fields before republishing.
8. Add build plus deterministic content-quality checks and review the preview output.

Expected Phase 1 file range:

- `src/pages/cn/index.astro`
- `src/pages/en/index.astro`
- `src/content/cn/career/robotics-salary-2025.mdx`
- `src/content/en/career/robotics-career-map-2025.mdx`
- `src/content/cn/research/humanoid-actuator-bom-2025.mdx`
- `src/content/en/research/humanoid-actuator-bom-2025.mdx`
- `src/layouts/ArticleLayout.astro`
- `src/pages/research-news/index.astro`
- `src/components/FeedbackFlywheel.astro`
- `src/content.config.ts`
- duplicate `src/content/cn/research/arxiv-*.md` groups listed above
- `test-payload.json` after reference verification
- new deterministic governance tests/fixtures and documentation

## 11. Phase 0 validation result

- `npm test --if-present`: exited successfully, but no test script exists and no tests ran.
- `npm run build`: passed and generated 59 static pages.
- Existing build warnings were retained as baseline findings:

  - Astro could not create four collection JSON schema files under `.astro/collections/...` and proceeded without them.
  - the `_stub.md` glob loaders for `src/content/en` and `src/content/cn` found no matching files.

- These warnings were not fixed in Phase 0 because that would change application configuration outside the documentation-only scope.

## 12. Phase 0.5 isolation and runtime baseline

Recorded on 2026-07-18 UTC without changing public content, production business files, or Hermes configuration.

### Final worktree layout

| Path | Branch/purpose | Baseline state |
|---|---|---|
| `/root/robot` | `master`; production/legacy Hermes worktree | Clean and synchronized with `origin/master` at isolation time |
| `/root/robot-career-refactor` | `refactor/career-intelligence`; Codex development | Clean before Phase 0.5 documentation changes |
| `/root/hermes-workspace` | Hermes arXiv task workspace | Preserved; not a Git worktree and not migrated |
| `/root/robot-backups` | Local restricted backups | Created empty with root ownership and mode `0700` |

No Hermes path references `/root/robot-career-refactor`.

### Hermes write paths

- `Fetch arXiv Papers` runs with workdir `/root/hermes-workspace`. It generates matching Chinese and English Markdown and writes them directly to GitHub repository `master` through the GitHub REST API. It does not use the local `/root/robot` Git checkout.
- `Weekly Robotics Research Review` runs in `/root/robot`. It reads committed research Markdown/MDX, generates/overwrites dated HTML under `public/ppt/`, updates `src/pages/cn/index.astro`, runs `npm run build`, commits, and pushes `master`.
- The weekly task is the only current task found that operates directly in `/root/robot`. It may run concurrently with Codex, but the separate development worktree prevents working-tree collisions.
- Direct remote writes to `master` remain a production and branch-divergence risk; worktree isolation does not create a publication quality gate.

### Hermes health conclusion

- The system service runs PID `2161712` with `HERMES_HOME=/root/.hermes`.
- The built-in cron scheduler is a 60-second ticker thread inside the gateway process; it is not a separate daemon.
- Host-level `hermes cron status` reports the gateway and ticker healthy, and the heartbeat/last-success files update every minute.
- The earlier false “gateway is not running” result occurred only inside the Codex PID-isolated sandbox, which cannot see the host gateway PID. It was not caused by a different configuration path, a separate cron component, or a broken production process.
- No restart or repair was performed.

### Time baseline

- VPS timezone: `Etc/UTC`.
- System clock synchronized: yes; NTP service active; RTC stored in UTC.
- Example observation: `2026-07-18T03:49:38+00:00` equals `2026-07-18T11:49:38+08:00` in `Asia/Singapore` (also UTC+8 for `Asia/Shanghai`).
- UTC on the server is normal and should remain the storage/logging baseline. Reports should render explicit `Asia/Singapore` or `Asia/Shanghai` times.
- The tag `pre-career-intelligence-refactor-2026-07-18` used the UTC baseline date. Singapore was also already on 2026-07-18, so the date is unambiguous.

### Backup baseline

- `/root/robot-backups/config`, `/root/robot-backups/data`, and `/root/robot-backups/logs` exist.
- Parent and child directories are `root:root` with mode `0700`.
- They were intentionally left empty in Phase 0.5. No environment file, token, key, or secret-bearing Hermes configuration was copied.

### Phase 0.5 dependency/build baseline

- A clean `npm ci` in `/root/robot-career-refactor` installed 347 packages successfully.
- npm reported 13 dependency vulnerabilities: 2 low, 4 moderate, and 7 high. No automated audit fix was run because dependency upgrades are outside Phase 0.5 and may introduce breaking changes.
- `npm run build` passed and generated 59 static pages.
- The same pre-existing collection schema and missing `_stub.md` warnings recorded in Phase 0 remained. They were not changed in this safety-only phase.

## 13. Phase 1 credibility governance baseline

Implemented on 2026-07-18 UTC only in `/root/robot-career-refactor` on `refactor/career-intelligence`.

### Public claims and withdrawn content

- Removed unsupported homepage metrics and process claims: `340+`, `50+`, `12+` segment coverage, three-layer validation, supplier interviews, anonymous engineer surveys, and production-line research.
- Replaced the claims with non-quantified statements about continuous tracking, public source links, review status, and explicit update dates.
- Replaced the feedback/database assertion with an accurate statement that submissions are review leads and are not automatically verified or published.
- Removed two career survey/salary articles and two actuator BOM/interview articles because repository files, Git history, relevant Hermes definitions, and likely local evidence paths contained no auditable source package.
- Removed the public Chinese article generated from the legacy test payload and deleted the unused root `test-payload.json`.
- Career collections are intentionally empty after the cleanup; both language career index pages remain and state that the system is under development.

### Duplicate and route result

- Reviewed 17 Chinese files in seven same-arXiv-source groups.
- Retained seven canonical Chinese pages and removed ten duplicate files.
- Added 28 source-controlled permanent Vercel redirects: eight withdrawn demo/test detail routes and twenty duplicate routes.
- Duplicate identity is enforced per language, allowing a deliberate Chinese/English translation pair to share a paper source while blocking multiple pages in the same language.
- Removed content no longer generates Astro details. Redirects will become active only after a separately authorized production merge/deployment.

### Publication and provenance rules

- `status` is required and supports `draft`, `review`, `published`, and `archived`; missing status is not public.
- `isPublishableContent()` is reused by every homepage, list, and detail static-path entry point. Only exact `published` entries can appear or generate routes.
- The project has no sitemap integration or sitemap source file, so there was no separate sitemap list to filter; generated route inventory is the authoritative public set in this phase.
- Schema now supports `sourceType`, structured `sourceUrls`, `publishedAt`, `updatedAt`, and `reviewStatus`.
- All 12 retained published research entries have a structured arXiv source, publication date, Phase 1 governance update date, and `pending_review` status.
- Legacy `confidence_level` remains schema-compatible only for non-public history. It has no default and is not rendered. No retained published entry uses it.
- A unified metadata component renders real source links, dates, and review labels. Missing metadata is not replaced by invented labels or build timestamps.

### Deterministic publication gate

- `npm run content:check` validates prohibited claims, explicit status, minimum published metadata, source URL format/placeholders/self-sourcing, test-content isolation, language-scoped arXiv/DOI/canonical-source duplicates, route filter reuse, and redirect coverage.
- `npm run content:test` proves that an intentionally invalid temporary fixture fails and that deleting it restores a clean result.
- `npm run build` now runs the content check, Astro build, and post-build route/content leakage verification. All checks are local, deterministic, read-only with respect to project content, network-free, and AI-free.
- Baseline Astro build: 59 generated pages. Phase 1 Astro build: 31 generated pages. The 28-page reduction matches the eight demo/test detail routes and twenty duplicate detail routes removed from generation.
- Existing collection-schema and missing `_stub.md` warnings remain. Empty career collections add non-fatal warnings, but the build passes and both career indexes generate.

### Residual operational risk

- Existing Hermes jobs still write directly to remote `master` and do not use the Phase 1 metadata contract.
- The quality gate protects production only after this branch is reviewed and explicitly merged into `master`; no such merge or deployment occurred in Phase 1.
- A future legacy Hermes article that lacks structured sources/review metadata will make the Vercel build fail. The Hermes workflow was deliberately not changed in this phase.
- Retained arXiv summaries have source identity but have not been manually fact-checked; `pending_review` is intentionally visible.
- npm still reports the Phase 0.5 dependency vulnerabilities; no dependency fix or upgrade was attempted.

## 14. Phase 2 career-intelligence data baseline

At the Phase 2 closeout, the branch added a non-production SQLite data layer only on
`refactor/career-intelligence`. No operational database had yet been provisioned,
no factual company/job/skill/project data was added, no collector or schedule was
enabled, and the Astro site has no database runtime dependency.

### Storage and isolation

- SQLite was selected after explicit staging, backup, concurrency, query, snapshot,
  and restore evaluation in `docs/PHASE_2_STORAGE_EVALUATION.md`.
- Every CLI database/output path must be absolute and outside the Git worktree;
  there is no default database path.
- Managed connections enable foreign keys, WAL, full synchronous writes, and a
  5-second busy timeout. PostgreSQL is deferred behind documented multi-host/HA
  re-evaluation conditions.

### Schema and controls

- Migration 1 creates all seven required physical entity tables plus normalized
  aliases/project links, `pipeline_runs`, `review_queue`, and `system_controls`.
  The migrator separately maintains checksummed `schema_migrations`.
- The complete logical-contract/physical-table mapping is documented in
  `docs/PHASE_2_DATA_MODEL.md`.
- Collection and public snapshot publication are independent, reasoned controls;
  both default off. Tests exercise explicit changes only in disposable databases.
- At Phase 2 closeout, no real environment was enabled and no operational database
  file existed in the repository or recommended data paths. Phase 2.1 later created
  only the formal empty external staging database described below.

### Backup, snapshot, and concurrency behavior

- Backup writes to a temporary file, validates the restored schema/integrity and
  migration checksums, then uses an atomic non-overwriting link. Existing backup
  destinations are rejected.
- A public snapshot requires the publication switch, uses one consistent read
  transaction, includes only approved/public rows, and validates per-file checksums
  and record counts. The original Phase 2 `current` symlink design is superseded in
  Phase 2.1 by repository-owned ordinary `current.json` replacement.
- Tests cover two simultaneous readers, reads during a write transaction, WAL,
  busy timeout and a waiting second writer, migration write exclusion, snapshot
  consistency across a concurrent update, append-only change history, backup
  restore/validation, and removal of temporary artifacts.

### Constraints recorded at Phase 2 closeout

- Node 24 labelled the original dependency-free `node:sqlite` API experimental.
  Phase 2.1 resolves this risk by replacing that adapter with Python `sqlite3` while
  retaining and extending the regression coverage.
- No source registry entry is enabled, no real raw snapshot exists, and no data may
  be published until a later phase separately authorizes collection and publication.
- Backup retention, pruning, encryption, off-host copying, and production restore
  rehearsal remain later operational work.

## 15. Phase 2.1 career-data runtime hardening

Phase 2.1 resolves the experimental database API and snapshot-delivery risks without
starting collection. The formal staging database exists, but every factual domain,
pipeline, and review table is empty. Collection and publication are disabled.

### Runtime and database

- `/root/robot-data/{raw,staging,exports,logs,backups}` now exist outside Git as
  `root:root` directories with mode `0700`.
- `/root/robot-data/staging/career.sqlite3` is a regular file with mode `0600`.
  It has migrations 1 and 2, passes integrity/foreign-key/schema/checksum validation,
  and contains no company, source, job, skill, project, run, or review data.
- The formal non-overwriting backup is
  `/root/robot-data/backups/career-phase-2.1-initial.sqlite3`; an independent restore
  passed `validate`, and the disposable restore target was removed afterward.
- Database migration, validation, controls, backup, restore, and snapshot export now
  use Python 3.12 standard-library `sqlite3`. The Node `node:sqlite` adapter and tests
  were removed, so the experimental Node API is no longer a runtime dependency.

### Public snapshot boundary

- The only accepted public snapshot root is the repository-owned ordinary directory
  `src/data/career-public`; neither Astro nor Vercel reads the VPS database or an
  external path.
- A complete immutable version contains `manifest.json`, `companies.json`,
  `jobs.json`, `skills.json`, `role-summary.json`, and `project-templates.json`.
- Export writes a same-parent temporary directory, validates inventory, checksums,
  counts, path safety, and strict per-file field allowlists, renames the complete
  version atomically, then atomically replaces ordinary `current.json`. No symlink
  or half-written version is a valid input.
- Raw snapshot paths, content hashes, review/audit details, errors, confidence values,
  and local paths are forbidden from public DTOs. The checked-in snapshot is empty.

### Phase 2.1 verification and remaining constraints

- Tests cover external path enforcement, modes, migrations/checksums, fail-closed
  controls, strict DTO allowlists, internal-field exclusion, entity inventory,
  WAL/read/write behavior, busy timeout, migration write exclusion, consistent
  snapshots, backup/restore/non-overwrite, Astro imports, and absence of VPS paths in
  Vercel output.
- No source is enabled, no collector or schedule exists, no real record was collected,
  and Phase 3 had not started at the Phase 2.1 closeout.
- Retention, encryption, off-host backup, production restore rehearsal, taxonomy,
  collector governance, and human-reviewed source registration remain future gates.

## 16. Phase 3A official recruitment source verification MVP

Phase 3A was authorized on 2026-07-18 as a bounded verification MVP, not as continuous
collection. The starting branch was `refactor/career-intelligence`, matching
`origin/refactor/career-intelligence` at `70156a6`. The worktree already contained
uncommitted Phase 3A code, migration, fixtures, and a reconnaissance plan; those
changes were preserved and reviewed instead of reset or replaced.

### Starting checks

- `git status` showed modified `package.json`, `scripts/career_db.py`, and
  `scripts/career_db_test.py`, plus untracked Phase 3A migration/source/fixture files.
- The starting database suite passed 12/12 tests.
- The starting source suite passed 15/15 tests.
- The deterministic content negative test passed.
- `/root/robot-data/staging/career.sqlite3` is a mode-`0600` external database. A
  read-only migration-ledger check showed migrations 1 and 2 only; migration 3 has
  intentionally not been applied to that formal database during development.

### Implemented boundary

- Migration 3 adds `career_source_profiles` and append-only
  `source_verification_runs` while reusing the existing `companies` and
  `career_sources` tables. It seeds no company, source, job, or change record.
- Source status defaults to `candidate`; source collection/publication controls and
  the base source `enabled` flag remain false. Manual `verified` status cannot enable
  any of them.
- The shared adapter contract and staging DTO cover list/detail parsing, detail-link
  extraction, native-ID extraction, URL normalization, stable job keys, canonical
  URLs, normalized fields, and content hashes.
- A synthetic, credential-free Greenhouse-compatible fixture fully exercises the
  `standard_ats_greenhouse_v1` adapter offline. `official_html_v1` and
  `official_json_v1` provide only the common interface/defensive parser skeletons;
  no source-specific success is claimed for them.
- Live smoke requires `--confirm-live`, makes at most one listing and two detail
  requests, never paginates, and stops on access barriers, 401/403/429, unknown-domain
  redirects, or schema drift.
- Raw responses, parsed JSONL, SHA-256 metadata, and summaries go only to unique,
  non-overwriting repository-external staging runs. Parsed descriptions redact
  unnecessary phone and email details.
- Dry-run reads business-table counts before and after and never writes
  `job_postings` or `job_changes`; only source verification metadata is recorded.

### Source and live status

The first factual source is now verified: Nuro's official Careers page links jobs by
Greenhouse `gh_jid`, and the public Greenhouse Job Board API for board token `nuro`
returned the same native IDs. The external database contains one company and one
source profile, `nuro-greenhouse`. Its status is `verified`, while the base source
`enabled`, `collection_enabled`, and `publication_enabled` flags all remain 0.

The source fixture succeeded offline. A bounded live smoke then made one listing and
two detail requests, all HTTP 200 with no redirect, login, CAPTCHA, 401, 403, or 429.
The first manual inspection found entity-encoded Greenhouse markup leaking into the
normalized description. The text-cleaning order was corrected with a regression test,
and one bounded manual retry produced two clean plain-text descriptions. Both runs
used unique external staging directories and neither wrote a business table.

Continuous collection, test-job persistence, change/down detection, scheduling,
Hermes changes, public snapshots, frontend work, production merge, and deployment
remain outside Phase 3A.

### Phase 3A verification result

- `npm test` passed: the content negative fixture plus 12 database and 19 source
  unit tests (31 Python tests, 0 failures).
- A full CLI fixture acceptance run used
  `/tmp/robot-career-phase3a-acceptance-ChzcXP`: migrations 1–3 applied, two jobs
  parsed with zero network requests, five mode-`0600` artifacts written outside Git,
  and both `job_postings` and `job_changes` stayed at 0. The synthetic source remained
  `candidate` with source controls at 0.
- A read-only backup copy of the formal migration-2 database was upgraded in
  `/tmp/robot-career-phase3a-upgrade-NcCuXz`; only migration 3 applied, validation
  passed at version 3, controls stayed false, and all domain counts stayed 0.
- `npm run build` passed content, snapshot, Astro, and generated-output checks. It
  retained the previously documented empty-career-collection/schema warnings.
- Before the real-source run, the formal database was backed up without overwrite to
  `/root/robot-data/backups/career-pre-phase3a-live-20260718T114724Z.sqlite3`.
  The formal `/root/robot-data/staging/career.sqlite3` then migrated from version 2
  to 3 and passed integrity, foreign-key, checksum, permission, and schema validation.
- Formal row counts changed from company/source/job/change `0/0/0/0` to `1/1/0/0`.
  The only factual additions are Nuro and its source registration; `job_postings` and
  `job_changes` remained empty across fixture and both live runs.
- The accepted live run is
  `/root/robot-data/raw/career-sources/nuro-greenhouse/20260718T122539530494Z-2d52325342`.
  It parsed native Job IDs `7442056` and `7442057`; no duplicate job key, unstable
  URL, field shift, or residual HTML markup was found. Missing employment type and
  publication time remain null rather than inferred.
- `git diff --check` passed. No database, staging artifact, log, credential, or
  temporary acceptance file is tracked by Git.

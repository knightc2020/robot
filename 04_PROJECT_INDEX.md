# Project Index

## Current application

| Path | Purpose |
|---|---|
| `package.json` | Astro/npm scripts and runtime dependencies |
| `package-lock.json` | Locked npm dependency graph |
| `astro.config.mjs` | Astro, MDX, Tailwind, and bilingual routing configuration |
| `src/content.config.ts` | Required publication status and extensible provenance/review schema |
| `src/content/cn/research/` | Chinese research Markdown/MDX source |
| `src/content/en/research/` | English research Markdown/MDX source |
| `src/content/cn/career/` | Chinese career collection; intentionally empty after Phase 1 credibility cleanup |
| `src/content/en/career/` | English career collection; intentionally empty after Phase 1 credibility cleanup |
| `src/pages/cn/index.astro` | Chinese homepage and public quantitative claims |
| `src/pages/en/index.astro` | English homepage and public quantitative claims |
| `src/pages/{cn,en}/career/` | Static career index and detail routes |
| `src/pages/{cn,en}/research/` | Static research index and detail routes |
| `src/pages/research-news/` | Alternate research feed and detail routes |
| `src/lib/content-governance.ts` | Single `isPublishableContent()` predicate reused by all public content entry points |
| `src/layouts/ArticleLayout.astro` | Article shell using governed metadata and feedback components |
| `src/components/ContentMetadata.astro` | Shared bilingual source, date, and truthful review-status display |
| `src/components/FeedbackFlywheel.astro` | Feedback links with non-automatic, non-verification handling notice |
| `public/ppt/` | Static weekly-review presentation assets |
| `scripts/content-check.mjs` | Deterministic pre-build status, provenance, duplicate, claim, route, and redirect gate |
| `scripts/content-check.test.mjs` | Temporary negative fixture test proving violations fail and cleanup recovers |
| `scripts/verify-build.mjs` | Post-build route and withdrawn-content leakage verification |
| `vercel.json` | Permanent redirects for withdrawn and duplicate legacy URLs; development branch only until authorized merge |
| `career-intelligence/migrations/` | Checksummed SQLite migrations through Phase 3B job tracking |
| `career-intelligence/schema/v1/` | JSON Schema bundle for the seven logical entity contracts |
| `career-intelligence/README.md` | Explicit-path database, safety-control, backup, and atomic-snapshot commands |
| `scripts/career_db.py` | Python standard-library SQLite adapter and CLI for runtime, migration, validation, controls, backup/restore, and atomic snapshots |
| `scripts/career_db_test.py` | Path/mode, schema/checksum, whitelist, WAL/concurrency, migration lock, backup/restore, Astro, and snapshot tests |
| `scripts/career_sources_cli.py` | Phase 3A source verification plus Phase 3B collection-control and one-shot collect CLI |
| `scripts/career_sources/` | Shared source adapters, HTTP stop controls, identity/hash model, external staging, and Phase 3B tracking |
| `scripts/career_sources_test.py` | Offline fixture, identity, path, bounds, stop-condition, verification, and zero-business-write tests |
| `scripts/career_tracking_test.py` | Offline baseline, change transition, failure-protection, idempotency, and summary tests |
| `tests/fixtures/career_sources/` | Synthetic, credential-free source adapter fixtures; never factual source records |
| `scripts/verify-career-snapshot.mjs` | Build-time ordinary-file, inventory, path, and checksum verification for the current public snapshot |
| `src/data/career-public/` | Git-owned empty public snapshot: ordinary `current.json` plus immutable complete entity versions |
| `src/lib/career-public-snapshot.ts` | Astro static loader using only repository-owned JSON imports |

## Phase 0 controls

| Path | Purpose |
|---|---|
| `00_PROJECT_HARNESS.md` | Operating rules and phase gates |
| `01_CURRENT_STATE.md` | Evidence-backed baseline and Phase 0 report |
| `02_DECISION_LOG.md` | Architectural and governance decisions |
| `03_WORK_QUEUE.md` | Authorized and pending work |
| `04_PROJECT_INDEX.md` | Navigation across code, content, and controls |
| `05_DATA_DICTIONARY.md` | Current fields and future logical entities |
| `06_SOURCE_REGISTRY.md` | Source governance and verified-registration status |
| `07_ACCEPTANCE_CRITERIA.md` | Phase and product acceptance gates |
| `08_OPERATIONS_RUNBOOK.md` | Safe local operations, deployment, Hermes, and rollback notes |
| `docs/CAREER_INTELLIGENCE_REFACTOR_PLAN.md` | Goals, phases, execution rules, and target architecture |
| `docs/CONTENT_PROVENANCE_REGISTER.md` | Phase 1 claim/evidence decisions and withdrawn URL policy |
| `docs/DUPLICATE_CONTENT_REVIEW.md` | Seven arXiv duplicate groups, canonical choices, and redirect results |
| `docs/PHASE_2_STORAGE_EVALUATION.md` | Staging, backup, concurrency, querying, export, restore evaluation and SQLite decision |
| `docs/PHASE_2_DATA_MODEL.md` | Seven logical contracts mapped to every application database table |
| `docs/阶段3A_官方招聘源接入与采集验证MVP.md` | Phase 3A implementation, CLI, staging contract, safety limits, source status, and next boundary |
| `docs/PHASE_3A_SOURCE_RECONNAISSANCE_PLAN.md` | Source-selection and compliance reconnaissance companion for Phase 3A |
| `docs/阶段3B_三来源岗位持续跟踪MVP.md` | Phase 3B baseline, change rules, CLI, summary, cron example, and real-run result |

## Phase 1 removed paths retained in Git history

- Two career survey/salary MDX files.
- Two bilingual actuator BOM/interview MDX files.
- The public article generated from the legacy test payload and root `test-payload.json`.
- Ten duplicate Chinese arXiv Markdown files listed in `docs/DUPLICATE_CONTENT_REVIEW.md`.

## External operational locations

| Location | Purpose |
|---|---|
| `/root/.hermes/config.yaml` | Hermes configuration; secret-bearing and never copied into Git |
| `/root/.hermes/cron/jobs.json` | Hermes scheduled-job definitions |
| `/root/.hermes/logs/` | Hermes agent/gateway logs |
| `/root/.hermes/state/` | Automation state markers |
| `/root/hermes-workspace/` | Restricted arXiv automation workspace; not a Git checkout |
| `/etc/systemd/system/hermes-gateway.service` | System Hermes gateway unit |

## Worktree and backup layout

| Path | Branch/role | Modification rule |
|---|---|---|
| `/root/robot` | `master`; production/weekly Hermes worktree | No Codex refactor development; only authorized production sync/operations |
| `/root/robot-career-refactor` | `refactor/career-intelligence`; Codex development | All current refactor documentation, code, and tests belong here |
| `/root/hermes-workspace` | Hermes arXiv isolated workdir | Preserve current behavior; arXiv publisher writes remote `master` via API |
| `/root/robot-data` | Restricted Phase 2.1 career runtime; empty staging DB, runtime directories, and validated backup | Outside Git; mode `0700` directories and `0600` database/backup; never read by Astro/Vercel |
| `/root/robot-backups/config` | Restricted local configuration backups | Mode `0700`; never commit; copy only through an approved dated procedure |
| `/root/robot-backups/data` | Restricted local data backups | Mode `0700`; staging/production namespaces required later |
| `/root/robot-backups/logs` | Restricted local run-log backups | Mode `0700`; define retention before use |

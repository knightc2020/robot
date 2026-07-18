# Work Queue

Last updated: 2026-07-18 UTC

## Phase 0 closeout

- [x] Inventory OS, disk, runtime versions, repository, branch, and remote.
- [x] Confirm clean starting Git state.
- [x] Create `refactor/career-intelligence` from the untouched baseline.
- [x] Create `pre-career-intelligence-refactor-2026-07-18` on the baseline commit.
- [x] Inventory Astro content, career pages, production delivery, Hermes, and legacy data claims.
- [x] Identify demonstration/unverified-data candidates without deleting them.
- [x] Document minimum staging/production isolation.
- [x] Run final build/test checks; build passed with documented baseline warnings and no test script exists.
- [x] Review the final staged Git diff; it contains only Phase 0 control documentation.
- [x] Commit only Phase 0 control documentation.
- [x] Push branch and pre-refactor tag; verify remote state.
- [x] Stop after Phase 0 report.

## Phase 0.5 closeout

- [x] Read required Phase 0 control documents.
- [x] Confirm clean starting worktree and remote refactor branch parity.
- [x] Refresh remote references and fast-forward/synchronize local `master`.
- [x] Restore `/root/robot` to clean `master`.
- [x] Create `/root/robot-career-refactor` on `refactor/career-intelligence` with Git worktree.
- [x] Inventory all current Hermes references to the production, development, and research workdirs.
- [x] Diagnose the Hermes health-status disagreement without restart or workflow changes.
- [x] Verify UTC/NTP and document the Singapore conversion policy.
- [x] Create empty restricted backup directories without copying secrets.
- [x] Update only the five authorized project control documents.
- [x] Run `npm ci`, production build, worktree checks, and final diff review.
- [x] Commit and push Phase 0.5 documentation on the refactor branch.
- [x] Stop before Phase 1.

## Phase 1 closeout

- [x] Create the claim/evidence register and record unsupported public assertions.
- [x] Remove unsupported homepage, feedback, salary, survey, interview, BOM, and test-payload content.
- [x] Preserve 28 old detail URLs through permanent source-controlled redirects.
- [x] Require explicit publication status and reuse one public-route predicate everywhere.
- [x] Add structured source/date/review metadata and one bilingual metadata component.
- [x] Remove the user-visible legacy confidence label without inventing review claims.
- [x] Review seven duplicate arXiv groups, keep seven canonical pages, and remove ten duplicate files.
- [x] Add deterministic content checks, a negative fixture test, and post-build leakage verification.
- [x] Run `npm run content:check`, `npm run content:test`, `npm run build`, and route/output checks.
- [x] Review final diff, create one scoped Phase 1 commit, and push only the refactor branch.
- [x] Stop before Phase 2; do not merge, deploy, or alter Hermes.

## Phase 2 closeout

- [x] Recover from the interrupted session and confirm the worktree contained no partial Phase 2 source changes.
- [x] Evaluate staging isolation, backup/restore, concurrency, query, and snapshot requirements before storage selection.
- [x] Select SQLite for the bounded single-host batch workload and record PostgreSQL re-evaluation gates.
- [x] Define seven version 1 logical entity contracts and map them to every physical application table.
- [x] Add checksummed migration 1 with all required entity, alias, pipeline, review, relation, control, and migration-ledger tables.
- [x] Default collection and publication independently off while supporting explicit reasoned future changes.
- [x] Add a non-overwriting validated backup flow and consistent public snapshot flow with validated immutable versions and atomic `current` replacement.
- [x] Test WAL, two concurrent readers, reads during a write, busy timeout, waiting writers, migration write exclusion, consistent snapshot reads, append-only history, backup restore, and snapshot replacement.
- [x] Run content governance tests and the Astro production build without changing public content.
- [x] Keep all factual tables empty; add no collector, schedule, operational database, master change, Hermes change, or production deployment.
- [x] Review the final diff, create one scoped Phase 2 commit, and push only `refactor/career-intelligence`.

## Phase 2.1 closeout

- [x] Establish `/root/robot-data/{raw,staging,exports,logs,backups}` outside Git with mode `0700`.
- [x] Create, migrate, validate, back up, restore-test, and permission-check the empty `staging/career.sqlite3` without factual records.
- [x] Replace the experimental Node SQLite implementation with a Python standard-library adapter and regression suite.
- [x] Add migration 2 so every explicit safety-control change is auditable and the singleton cannot be deleted.
- [x] Publish an empty, six-file, repository-owned entity snapshot using strict DTO allowlists, complete validation, immutable versions, and atomic ordinary `current.json` replacement.
- [x] Prove Astro and Vercel builds consume only repository files and never depend on `/root/robot-data`.
- [x] Remove only identified Phase 2 test directories from `/tmp`; preserve the formal staging database and backup.
- [x] Run data tests, content checks, negative tests, Astro build, and `git diff --check`.
- [x] Create one scoped Phase 2.1 commit and push only `refactor/career-intelligence`.
- [x] Stop before Phase 3; do not collect, merge, deploy, or alter `/root/robot` or Hermes.

## Phase 3A closeout

- [x] Preserve and review the existing uncommitted Phase 3A work.
- [x] Record branch, worktree, baseline tests, and the formal external database migration state.
- [x] Add a checksummed migration for the disabled source profile and append-only verification-run ledger without seeding factual records.
- [x] Establish the shared adapter interface and unified staging-job DTO.
- [x] Fully parse one synthetic Greenhouse-compatible fixture without network access.
- [x] Implement stable native-ID/normalized-URL job keys and content-only hashes.
- [x] Implement repository-external, unique, non-overwriting raw/parsed staging output.
- [x] Add registration, list, fixture/live-smoke dry-run, and manual verify CLI commands.
- [x] Enforce explicit live confirmation, one-list/two-detail bounds, stop conditions, and zero business-table writes.
- [x] Update Phase 3A state, decisions, operations, source-registry, README, ignore rules, and stage documentation.
- [x] Trace Nuro from its official Careers page to its public Greenhouse board, register it disabled, run the authorized fixture and bounded live smoke, inspect two jobs, and manually mark it `verified`.
- [x] Keep `job_postings` and `job_changes` at zero and keep base collection, source collection, and publication controls disabled after verification.
- [x] Stop before continuous collection, test-job persistence, change/down detection, scheduling, Hermes, frontend, publication, or deployment.

## Later-phase backlog

- Next phase: select three verified sources for 7—14 days of bounded continuous observation, isolated test-job writes, new/change/down detection, and minimal scheduling.
- Phase 4: JD parsing, deduplication, change history, and review queue.
- Phase 5: eight job families and normalized skill dictionary.
- Phase 6: evidence-linked project template library.
- Phase 7: career website information architecture and pages.
- Phase 8: isolated Hermes schedules, quality gates, retries, and reports.
- Phase 9: staging, rollback test, sampling, and production acceptance.

## Blockers and open questions

- Evidence for the existing survey, supplier interviews, salary tables, and BOM figures has not been found.
- Vercel project/dashboard configuration and preview-environment isolation have not been inspected.
- Direct GitHub API and weekly-worktree writes to `master` still bypass a career publication quality gate.
- Vercel preview behavior for feature-branch pushes remains unverified.
- Backup retention, rotation, encryption, and restore testing are not implemented.
- The Phase 1 gate is not active in production until an authorized merge to `master`.
- The empty Phase 2.1 staging database is external to Git and not connected to production; both controls are disabled.
- Backup retention, encryption, off-host replication, and a production restore rehearsal are not yet defined.
- Current Hermes research output does not yet emit the new structured source/review metadata and would be blocked by the gate.
- Retained historical arXiv analyses remain pending human review even though their paper identities are sourced.

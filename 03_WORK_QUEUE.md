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

## Phase 1 — pending explicit authorization

1. Create a claim/evidence ledger for every affected homepage and article assertion.
2. Define quarantine and redirect behavior for unsupported/duplicate content.
3. Remove or neutralize unsupported `340+`, `50+`, survey, interview, and verification claims.
4. Correct confidence-label semantics and Chinese localization.
5. Add source URL/update requirements and deterministic content-governance checks.
6. Canonicalize the seven same-source arXiv duplicate groups without breaking URLs blindly.
7. Build and preview; conduct human review before any production proposal.

## Later-phase backlog

- Phase 2: logical/physical data model and migrations.
- Phase 3: official career-source registry and three-company collector pilot.
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
- No test harness or data-quality command exists yet.

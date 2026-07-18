# Operations Runbook

## Safety boundary

The two Git worktrees share a repository but have separate purposes. Vercel serves GitHub `master`, and existing Hermes jobs can publish to `master`. Do not merge/push production changes, trigger deployment, or run publishing jobs without explicit authorization.

- `/root/robot`: production/legacy Hermes worktree, always `master`.
- `/root/robot-career-refactor`: Codex development worktree, always `refactor/career-intelligence` until an authorized merge.
- Never perform Codex refactor development directly in `/root/robot`.

## Local development

```bash
cd /root/robot-career-refactor
npm ci
npm run dev
```

Default Astro development behavior may bind a local port. Do not expose it publicly without an approved staging plan.

## Deterministic content and build validation

```bash
cd /root/robot-career-refactor
npm test --if-present
npm run content:check
npm run content:test
npm run career:db:test
npm run career:sources:test
npm run career:snapshot:check
npm run build
git status --short --branch
git diff --stat
git diff --check
```

There is still no general lint/typecheck framework. Phase 1 adds a narrow deterministic content test and quality gate:

- `content:check` reads source files and fails on publication-state, source, duplicate, forbidden-claim, fixture, route-filter, or redirect defects.
- `content:test` creates an isolated temporary invalid fixture, proves it fails, removes it, and proves the clean control passes.
- `build` runs `content:check`, Astro, then verifies generated routes and scans output for withdrawn content. It does not call external networks or AI APIs and does not mutate source content.

A failing content gate blocks the build. Fix the reported source/metadata issue; do not bypass, auto-delete, or weaken the rule to publish.

Phase 0.5 clean-install baseline: `npm ci` succeeded, but npm reported 13 dependency vulnerabilities (2 low, 4 moderate, 7 high). Do not run `npm audit fix` or `--force` as an unreviewed operational shortcut; assess and test dependency changes in a separately authorized phase.

## Career database operations

Phase 2.1 provides a formal empty staging runtime. Database, backup, restore, and
runtime paths are explicit, absolute, outside Git, and environment-specific. Do not
substitute a path under `/root/robot`, this refactor worktree, or Hermes. Public
snapshot output is the sole exception: it must equal the repository-owned
`src/data/career-public` path, which is validated separately and contains JSON only.

```bash
cd /root/robot-career-refactor
npm run career:db -- runtime-init --root /root/robot-data
npm run career:db -- runtime-validate --root /root/robot-data
npm run career:db -- migrate --database /root/robot-data/staging/career.sqlite3
npm run career:db -- validate --database /root/robot-data/staging/career.sqlite3
npm run career:db -- controls --database /root/robot-data/staging/career.sqlite3 \
  --collection enabled --reason "Explicit later-phase authorization reference" \
  --actor "approved-operator"
npm run career:db -- backup --database /root/robot-data/staging/career.sqlite3 \
  --output /root/robot-data/backups/YYYY-MM-DD-career.sqlite3
npm run career:db -- restore --backup /root/robot-data/backups/YYYY-MM-DD-career.sqlite3 \
  --database /root/robot-data/staging/YYYY-MM-DD-restore-test.sqlite3
npm run career:db -- validate \
  --database /root/robot-data/staging/YYYY-MM-DD-restore-test.sqlite3
npm run career:db -- controls --database /root/robot-data/staging/career.sqlite3 \
  --publication enabled --reason "Approved empty snapshot refresh" \
  --actor "approved-operator"
npm run career:db -- snapshot --database /root/robot-data/staging/career.sqlite3 \
  --output /root/robot-career-refactor/src/data/career-public --replace
npm run career:db -- snapshot-validate \
  --output /root/robot-career-refactor/src/data/career-public
npm run career:db -- controls --database /root/robot-data/staging/career.sqlite3 \
  --publication disabled --reason "Snapshot refresh complete" \
  --actor "approved-operator"
```

- Collection and publication default off and must be enabled independently with an
  explicit value, actor, and reason. Migration 2 records each update in
  `system_control_events`. Phase 2.1 leaves both disabled.
- Backup output is installed only after full validation and never overwrites an
  existing path; choose a new dated destination.
- Restore output also refuses overwrite. Remove a disposable restore-test file only
  after its independent `validate` succeeds; never remove the formal staging file.
- Snapshot publication requires `publication enabled`, emits only approved rows and
  allowlisted fields, builds in a same-parent temporary directory, validates every
  file/count/checksum/path, and renames a complete immutable version before current
  changes. Updating existing `current.json` requires `--replace` and uses atomic
  replacement; `current.json` and all referenced files must be regular repository
  files, never symlinks.
- The enable/export/disable example is an operational sequence, not authorization to
  publish. A failed export must still be followed by an explicit disable command.
- Never copy the SQLite database, raw records, logs, or an external snapshot target
  into Astro source. Astro imports the reviewed public DTO files only.

## Phase 3A source verification operations

Source verification uses `npm run career:sources`. Both the database and staging
directory must be explicit absolute paths outside Git. Do not use `/root/robot`,
Hermes paths, the repository, or a symlink as output. The full synthetic fixture
setup is documented in `docs/阶段3A_官方招聘源接入与采集验证MVP.md`.

```bash
cd /root/robot-career-refactor
npm run career:sources -- list \
  --db /absolute/external/path/career.sqlite3
npm run career:sources -- dry-run \
  --db /absolute/external/path/career.sqlite3 \
  --staging-dir /absolute/external/path/career-source-staging \
  --source-id SOURCE_ID \
  --mode fixture
```

Fixture mode performs no network access. A live smoke is a separate, explicit action:

```bash
npm run career:sources -- dry-run \
  --db /absolute/external/path/career.sqlite3 \
  --staging-dir /absolute/external/path/career-source-staging \
  --source-id SOURCE_ID \
  --mode live-smoke \
  --confirm-live
```

- Before live smoke, manually establish the company-homepage-to-career-entry chain,
  record allowed domains, and review robots, terms, login, and captcha status.
- The command makes one listing and at most two detail requests, serially, with a
  minimum three-second same-domain interval. It never paginates or runs all sources.
- Stop and leave the source unverified on 401, 403, 429, login/captcha, unknown-domain
  redirects, unrecognized structures, or evidence of access restrictions. Do not
  retry around or bypass the barrier.
- Review raw and parsed output in the unique external run directory. Do not copy raw
  pages, parsed JSONL, summaries, or the SQLite database into Git.
- Dry-run writes only source verification metadata. It must report equal before/after
  counts for `job_postings` and `job_changes`.
- `verify --confirm` requires a successful fixture and live run plus manual evidence.
  It leaves global/source collection, base `enabled`, and publication controls off.

The formal database was at migration 2 when Phase 3A development began. It was backed
up without overwrite and migrated to version 3 before the Nuro run; never edit the
migration ledger or overwrite either retained backup.

## Preview

```bash
cd /root/robot-career-refactor
npm run preview
```

Preview is local only. Vercel preview deployment behavior is not documented or verified.

## Current production delivery

1. Content/code reaches GitHub `master`.
2. Vercel builds the Astro site.
3. Vercel serves `www.robotcareer.cloud`; the apex redirects to `www`.
4. HTTPS is managed at Vercel.

Do not use empty commits or direct GitHub API writes as a deployment method for refactor work.

## Development-to-production flow

1. Develop and test only in `/root/robot-career-refactor` on `refactor/career-intelligence`.
2. Run `npm ci`, `npm run build`, content/data quality checks, `git diff --check`, and human review.
3. Commit and push only the feature branch.
4. Use review/preview and an explicit authorization before merging to `master`.
5. Production is updated through the approved `master` path; never copy development files manually into `/root/robot`.
6. After an authorized remote `master` change, synchronize `/root/robot` only when clean and only with fetch plus fast-forward.
7. Verify Vercel production and retain a rollback reference. Phase 0.5 performs none of these production merge/deploy steps.

Phase 1 also performs no merge or deployment. Its quality gate affects Vercel only after an explicitly authorized merge into `master`.

## Content publication rules

1. All public content must declare exact `status: published`; other or missing states receive no list entry or detail route.
2. Published content requires structured external source URLs, publication/update dates, source type, and truthful review status.
3. `pending_review` is publishable only as an explicitly visible review state; it must never be presented as human-reviewed or source-verified.
4. Same-language arXiv IDs, DOIs, and canonical source URLs must be unique. Intentional bilingual pairs are allowed.
5. Test, fixture, demo, and synthetic publication payloads remain outside `src/content`.
6. Withdrawn URLs are maintained in `vercel.json`; all current rules are permanent and must point to an internal canonical/hub destination.

The full claim decisions and duplicate mappings are in `docs/CONTENT_PROVENANCE_REGISTER.md` and `docs/DUPLICATE_CONTENT_REVIEW.md`.

## Git baseline and rollback reference

- Baseline commit: `7a9a746aef367fb2297ff809978fd7289071835a`.
- Backup tag: `pre-career-intelligence-refactor-2026-07-18`.
- Development branch: `refactor/career-intelligence`.

Rollback must be rehearsed in staging before production. A tag is a Git reference, not a data/database backup.

## Hermes operations

Sanitized locations:

- executable: `/usr/local/bin/hermes`
- configuration: `/root/.hermes/config.yaml`
- cron definitions: `/root/.hermes/cron/jobs.json`
- cron outputs: `/root/.hermes/cron/output/`
- logs: `/root/.hermes/logs/`
- state: `/root/.hermes/state/`
- gateway unit: `/etc/systemd/system/hermes-gateway.service`

Read-only health checks:

```bash
hermes --version
hermes cron status
systemctl status hermes-gateway.service --no-pager
journalctl -u hermes-gateway.service --no-pager
```

The apparent status disagreement is resolved: the scheduler is a 60-second in-process thread inside the system gateway. Host-level status sees PID `2161712` and a fresh ticker heartbeat; only PID-isolated sandbox checks incorrectly report the gateway absent. Use systemd, a host-level `hermes cron status`, and heartbeat age together. Do not restart the gateway to correct sandbox-only output.

Existing jobs must not be manually triggered during the refactor baseline:

- arXiv job: workdir `/root/hermes-workspace`; creates bilingual research Markdown via GitHub REST API directly on remote `master`.
- weekly review: workdir `/root/robot`; creates HTML, updates the Chinese homepage link, builds, commits, and pushes `master`.

Worktree collisions are now isolated, but both jobs can still change the production branch while development is in progress. Fetch and review remote divergence before any future merge.

The active Hermes arXiv publisher does not yet emit the Phase 1 `sourceUrls`, `updatedAt`, and `reviewStatus` contract. If the quality gate is later merged to production, a legacy-format Hermes commit can make the Vercel build fail. This is the intended fail-closed behavior, but the workflow must be updated in a separately authorized Hermes phase; do not bypass the gate or edit `/root/.hermes` during Phase 1.

## Phase 1 rollback

- Development rollback reference before Phase 1: `7ed3928`.
- Before merge, abandon/revert only the scoped feature-branch commit; `/root/robot` and production are unaffected.
- After a future authorized merge, use `git revert` of the Phase 1 commit through the reviewed production workflow. Do not reset shared history.
- Redirect removal is part of the same revert, so verify old URL behavior during any rollback rehearsal.

## Phase 2 rollback

- Before production use, revert scoped feature-branch code through Git; production
  and `/root/robot` remain unaffected. Do not delete the formal staging database or
  its backup as a source-code rollback shortcut.
- After migrations are used in a later environment, never downgrade by deleting or
  editing migration-ledger rows. Stop writers, take a new non-overwriting backup,
  validate restore, and use a reviewed forward migration or restore procedure.
- Public snapshot rollback regenerates or atomically replaces ordinary `current.json`
  to reference a previously validated repository version; external symlinks are
  forbidden and no Phase 2.1 snapshot is connected to production.

## Logs and diagnostics

- No local application runtime log exists because the website is statically hosted by Vercel.
- Build output is console-only unless deliberately captured outside Git.
- Vercel build/runtime logs require dashboard/provider access and were not inspected.
- Hermes logs are local; never paste secrets or full environment output into issues or project documentation.

## Time policy

- Host timezone remains `Etc/UTC`; NTP is active and the system clock is synchronized.
- Store database and machine timestamps in UTC.
- Include an explicit timezone in operational logs and reports.
- Render weekly reports in `Asia/Singapore` or `Asia/Shanghai` (UTC+8) as selected by report scope.
- Do not change the host timezone merely for report presentation.

## Backup roots

The following local directories exist as `root:root` with mode `0700`:

```text
/root/robot-backups/config/
/root/robot-backups/data/
/root/robot-backups/logs/
```

They are empty at the Phase 0.5 baseline. Future backups must use dated, non-overwriting names, remain outside Git, avoid printing contents, and define retention and restore tests before production reliance.

The Phase 2.1 career-data backup uses the separate restricted path
`/root/robot-data/backups/career-phase-2.1-initial.sqlite3`. It is a validated mode
`0600` regular file. The older `/root/robot-backups` baseline remains unchanged.

## Current staging layout

```text
/root/robot-career-refactor/           # current refactor branch worktree
/root/robot/                            # current master/weekly automation worktree
/root/robot-data/raw/                   # restricted future raw input; empty
/root/robot-data/staging/               # empty migrated career.sqlite3 only
/root/robot-data/exports/               # restricted non-public export workspace; empty
/root/robot-data/logs/                  # restricted future data logs; empty
/root/robot-data/backups/               # validated formal staging backup
/root/robot-backups/                    # existing Phase 0.5 backup root; unchanged
```

All five `/root/robot-data` directories are mode `0700`; the database and formal
backup are mode `0600`. A production namespace does not exist and must not be
inferred from this staging layout. Define distinct credentials, paths, retention,
and restore ownership before any future production authorization.

## Incident stop conditions

Stop automation and require review when:

- a source changes layout or returns unexpected authentication/consent pages;
- provenance fields or raw snapshots are missing;
- duplicate rate spikes;
- parser output violates schema;
- a job changes after previously being marked closed;
- a publish command targets `master` unexpectedly;
- staging and production paths/credentials cannot be distinguished;
- secrets appear in output or generated files.

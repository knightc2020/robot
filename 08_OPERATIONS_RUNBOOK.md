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

## Deterministic validation available at baseline

```bash
cd /root/robot-career-refactor
npm test --if-present
npm run build
git status --short --branch
git diff --stat
git diff --check
```

There is no defined test/lint/typecheck script. At baseline, `npm run build` is the only application validation command.

Phase 0.5 clean-install baseline: `npm ci` succeeded, but npm reported 13 dependency vulnerabilities (2 low, 4 moderate, 7 high). Do not run `npm audit fix` or `--force` as an unreviewed operational shortcut; assess and test dependency changes in a separately authorized phase.

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

## Future staging layout recommendation

Proposed, not created in Phase 0:

```text
/root/robot-career-refactor/           # current refactor branch worktree
/root/robot/                            # current master/weekly automation worktree
/root/robot-data/staging/              # staging raw/normalized DB and snapshots
/root/robot-data/production/           # production DB and snapshots
/root/robot-logs/staging/               # staging run logs
/root/robot-logs/production/            # production run logs
/root/robot-backups/                    # created restricted backup root
```

Use distinct credentials, database paths/services, log paths, and Vercel environments. These paths are recommendations only and do not exist at baseline.

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

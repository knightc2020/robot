# Operations Runbook

## Safety boundary

This repository is production-adjacent: Vercel serves GitHub `master`, and existing Hermes jobs can publish to `master`. Do not merge/push production changes, trigger deployment, or run publishing jobs without explicit authorization.

## Local development

```bash
cd /root/robot
npm ci
npm run dev
```

Default Astro development behavior may bind a local port. Do not expose it publicly without an approved staging plan.

## Deterministic validation available at baseline

```bash
cd /root/robot
npm test --if-present
npm run build
git status --short --branch
git diff --stat
git diff --check
```

There is no defined test/lint/typecheck script. At baseline, `npm run build` is the only application validation command.

## Preview

```bash
cd /root/robot
npm run preview
```

Preview is local only. Vercel preview deployment behavior is not documented or verified.

## Current production delivery

1. Content/code reaches GitHub `master`.
2. Vercel builds the Astro site.
3. Vercel serves `www.robotcareer.cloud`; the apex redirects to `www`.
4. HTTPS is managed at Vercel.

Do not use empty commits or direct GitHub API writes as a deployment method for refactor work.

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

Known issue: systemd reports the gateway active while `hermes cron status` reports it not running. Do not add career schedules until this discrepancy and scheduler heartbeat are verified.

Existing jobs must not be manually triggered during the refactor baseline. The weekly job currently uses `/root/robot`; isolate its worktree before Monday execution can interact with development state.

## Logs and diagnostics

- No local application runtime log exists because the website is statically hosted by Vercel.
- Build output is console-only unless deliberately captured outside Git.
- Vercel build/runtime logs require dashboard/provider access and were not inspected.
- Hermes logs are local; never paste secrets or full environment output into issues or project documentation.

## Future staging layout recommendation

Proposed, not created in Phase 0:

```text
/root/robot-worktrees/development/     # refactor branch
/root/robot-worktrees/automation/      # clean automation branch/worktree
/root/robot-data/staging/              # staging raw/normalized DB and snapshots
/root/robot-data/production/           # production DB and snapshots
/root/robot-logs/staging/               # staging run logs
/root/robot-logs/production/            # production run logs
/root/robot-backups/                    # dated, access-controlled backups
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

# Phase 2.1 Runtime Hardening Record

Date: 2026-07-18 UTC

## Scope and runtime

Phase 2.1 fixes only Phase 2 operational gaps. It does not register a source,
collect a job, start Phase 3, modify production, or deploy.

The external runtime root is `/root/robot-data`. Its `raw`, `staging`, `exports`,
`logs`, and `backups` directories are `root:root`, mode `0700`, and are outside the
Git repository. The empty staging database is
`/root/robot-data/staging/career.sqlite3`, a mode-`0600` regular file. It contains
migrations 1 and 2, the control singleton and control audit events, and zero factual
domain, pipeline-run, or review records. Both safety switches are disabled.

The validated, non-overwriting backup is
`/root/robot-data/backups/career-phase-2.1-initial.sqlite3`, mode `0600`. Restoring
it to a separate disposable path and running full validation succeeded; the formal
database and backup remain.

## SQLite API decision

All database operations use `scripts/career_db.py` and Python 3.12 standard-library
`sqlite3` (host runtime Python 3.12.3, SQLite 3.45.1). This covers runtime creation,
migration, checksum verification, controls, validation, online backup, restore, and
consistent-read snapshot export. The experimental Node `node:sqlite` implementation
is removed. The CLI/adaptor boundary and tests keep a future storage replacement
possible without coupling Astro to SQLite.

## Public delivery boundary

The only accepted public snapshot output is
`/root/robot-career-refactor/src/data/career-public`. A version contains exactly:

- `manifest.json`
- `companies.json`
- `jobs.json`
- `skills.json`
- `role-summary.json`
- `project-templates.json`

The publisher writes a same-parent temporary directory, validates exact inventory,
schema version, relative paths, record counts, SHA-256 checksums, and per-file field
allowlists, renames the complete version atomically, and finally atomically replaces
ordinary `current.json`. An existing descriptor requires `--replace`. Symlinks,
external targets, unexpected files/fields, and leftover temporary artifacts fail
validation. Astro uses static repository imports; the build verifier rejects
`/root/robot-data` in generated output.

Raw snapshot references, content hashes, internal review/audit data, errors/logs,
confidence values, extraction metadata, and local paths cannot enter the public DTO.
The committed snapshot contains empty entity arrays only.

## Verification

The Phase 2.1 suite covers external path and permission enforcement, schema and
migration checksums, default-off controls, strict DTO projection, internal-field
rejection, complete entity structure, two readers, reads during a write, WAL,
busy timeout, migration write exclusion, a consistent snapshot view, atomic current
replacement, backup non-overwrite, independent restore/validate, Astro static
loading, Vercel path independence, negative content fixtures, and the production
Astro build. Exact final commands/results are recorded in the Phase 2.1 closeout
commit and acceptance report.

## Remaining gates

Before Phase 3, obtain explicit authorization; review and enable only approved
official sources; define raw-snapshot retention, collection rate/terms/robots rules,
failure routing, and human review ownership; and retain the independent fail-closed
collection/publication controls. Backup retention, encryption, off-host copies, and
a production restore rehearsal remain later operational decisions.

# Career Intelligence Data Layer

Phase 2 defines the versioned, non-production data layer for career intelligence.
It does not collect, seed, publish, or render any company or job record.

## Layout

- `migrations/`: ordered SQLite migrations; applied migrations are checksummed.
- `schema/v1/`: versioned JSON Schema contracts for the seven domain entities.
- `../scripts/career-db.mjs`: explicit-path migration, controls, verification, backup, and public snapshot CLI.
- `../scripts/career-db.test.mjs`: migration, constraint, concurrency, backup, and export tests.

The database must be outside the Git worktree. Staging and production must use
different absolute paths; there is deliberately no default database location.

```bash
npm run career:db -- migrate --database /root/robot-data/staging/career.sqlite3
npm run career:db -- verify --database /root/robot-data/staging/career.sqlite3
npm run career:db -- backup --database /root/robot-data/staging/career.sqlite3 \
  --output /root/robot-backups/data/2026-07-18-career.sqlite3
npm run career:db -- controls --database /root/robot-data/staging/career.sqlite3 \
  --publication enabled --reason "Approved Phase N snapshot rehearsal"
npm run career:db -- snapshot --database /root/robot-data/staging/career.sqlite3 \
  --output /root/robot-data/staging/public-snapshot
npm run career:db -- snapshot --database /root/robot-data/staging/career.sqlite3 \
  --output /root/robot-data/staging/public-snapshot --replace
```

Backup destinations must not already exist. Public snapshots are built and fully
validated in an immutable temporary version directory, then made current through
an atomic symlink replacement. Updating an existing snapshot requires `--replace`;
old complete versions remain available for rollback. Snapshot roots must never be
written under `src/`, `public/`, or `dist/`.

Collection and publication default independently to disabled. The `controls`
command requires an explicit setting and reason; publication must be enabled before
the snapshot command will run. Phase 2 leaves both switches disabled in all real
environments and creates no operational database.

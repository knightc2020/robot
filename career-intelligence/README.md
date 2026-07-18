# Career Intelligence Data Layer

Phase 3B adds one-shot change tracking for the three verified Greenhouse sources to
the Phase 3A source-verification flow. It writes internal job/change state only after
explicit collection controls and `--confirm-write`; it does not install scheduling,
publish jobs, or deploy a public site.

## Layout

- `migrations/`: ordered SQLite migrations; applied migrations are checksummed.
- `schema/v1/`: versioned JSON Schema contracts for the seven domain entities.
- `../scripts/career_db.py`: Python standard-library SQLite adapter and explicit-path CLI.
- `../scripts/career_db_test.py`: runtime, migration, constraint, concurrency, backup, restore, DTO, Astro, and export tests.
- `../scripts/career_sources_cli.py`: source verification, collection controls, and one-shot tracking CLI.
- `../scripts/career_sources/`: shared adapters, safe HTTP client, identity model, external staging, and tracking service.
- `../scripts/career_sources_test.py`: offline migration, parsing, identity, bounds, stop-condition, and zero-business-write tests.
- `../scripts/career_tracking_test.py`: offline baseline, transition, failure-protection, idempotency, and summary tests.
- `../tests/fixtures/career_sources/`: synthetic, credential-free adapter fixtures.
- `../scripts/verify-career-snapshot.mjs`: build-time verification of repository-owned snapshot files.
- `../src/data/career-public/`: ordinary current descriptor and immutable public entity versions.

The database and runtime must be outside the Git worktree; there is deliberately no
default database path. The only permitted public snapshot output is the exact
repository-owned `src/data/career-public` directory.

```bash
npm run career:db -- runtime-init --root /root/robot-data
npm run career:db -- runtime-validate --root /root/robot-data
npm run career:db -- migrate --database /root/robot-data/staging/career.sqlite3
npm run career:db -- validate --database /root/robot-data/staging/career.sqlite3
npm run career:db -- backup --database /root/robot-data/staging/career.sqlite3 \
  --output /root/robot-data/backups/2026-07-18-career.sqlite3
npm run career:db -- restore --backup /root/robot-data/backups/2026-07-18-career.sqlite3 \
  --database /root/robot-data/staging/2026-07-18-restore-test.sqlite3
npm run career:db -- controls --database /root/robot-data/staging/career.sqlite3 \
  --publication enabled --reason "Approved Phase N snapshot rehearsal" \
  --actor "approved-operator"
npm run career:db -- snapshot --database /root/robot-data/staging/career.sqlite3 \
  --output /root/robot-career-refactor/src/data/career-public --replace
npm run career:db -- snapshot-validate \
  --output /root/robot-career-refactor/src/data/career-public
npm run career:db -- controls --database /root/robot-data/staging/career.sqlite3 \
  --publication disabled --reason "Snapshot rehearsal complete" \
  --actor "approved-operator"
```

Backup and restore destinations must not already exist. A public snapshot is built
in a same-parent temporary directory and must pass exact inventory, checksum, count,
path, and field-allowlist validation. Only then is the complete immutable version
renamed into `versions/` and ordinary `current.json` atomically replaced. Updating
an existing current descriptor requires `--replace`; symlinks and external targets
are rejected.

Collection and publication default independently to disabled. The `controls`
command requires an explicit setting, reason, and attributable actor; migration 2
records every update. Publication must be enabled before snapshot generation.
Phase 3A leaves both global switches disabled and source verification never enables
either one. Phase 3B explicitly enables collection only for its three allowlisted
verified sources; publication remains disabled globally and per source.

## Phase 3A source verification

Every database and staging path is explicit and outside Git. Nuro is the first
verified factual source after official-evidence review, fixture parsing, bounded live
smoke, and manual two-job inspection. Its company/source records exist only in the
external database; the checked-in Greenhouse-compatible fixture remains synthetic.

```bash
npm run career:sources -- list \
  --db /absolute/external/path/career.sqlite3
npm run career:sources -- dry-run \
  --db /absolute/external/path/career.sqlite3 \
  --staging-dir /absolute/external/path/career-source-staging \
  --source-id SOURCE_ID \
  --mode fixture
npm run career:sources -- dry-run \
  --db /absolute/external/path/career.sqlite3 \
  --staging-dir /absolute/external/path/career-source-staging \
  --source-id SOURCE_ID \
  --mode live-smoke \
  --confirm-live
npm run career:sources -- verify \
  --db /absolute/external/path/career.sqlite3 \
  --source-id SOURCE_ID \
  --actor REVIEWER_ID \
  --confirm
```

Live smoke is limited in code to one listing and two details, with no pagination.
It stops on 401, 403, 429, login/captcha signals, unknown-domain redirects, and
unrecognized structures. Raw pages, SHA-256 metadata, parsed JSONL, and the summary
are written under a unique non-overwriting run directory. Dry-runs record only
verification metadata; before/after row counts prove `job_postings` and `job_changes`
are unchanged. See `../docs/阶段3A_官方招聘源接入与采集验证MVP.md` for the complete
offline setup, source prerequisites, and safety limits.

## Phase 3B one-shot tracking

```bash
npm run career:sources -- collection-control \
  --db /root/robot-data/staging/career.sqlite3 \
  --source-id nuro-greenhouse \
  --source-id zipline-greenhouse \
  --source-id agility-robotics-greenhouse \
  --enable --actor phase3b-operator --confirm
npm run career:db -- controls \
  --database /root/robot-data/staging/career.sqlite3 \
  --collection enabled \
  --reason "Authorize Phase 3B collection for three verified sources" \
  --actor phase3b-operator
npm run career:sources -- collect \
  --db /root/robot-data/staging/career.sqlite3 \
  --staging-dir /root/robot-data/raw/career-sources \
  --all-verified --confirm-write
```

Each source receives one `content=true` list request and no detail requests. A failed
source does not advance missing/closed state. Daily JSON and Markdown summaries are
external and non-overwriting. See `../docs/阶段3B_三来源岗位持续跟踪MVP.md` for baseline,
transition, cron-example, and failure rules.

Public files are `manifest.json`, `companies.json`, `jobs.json`, `skills.json`,
`role-summary.json`, and `project-templates.json`. Only per-file allowlisted DTO
fields may appear. Raw snapshot references, content hashes, review/audit details,
errors, confidence values, parser metadata, and local paths are forbidden.

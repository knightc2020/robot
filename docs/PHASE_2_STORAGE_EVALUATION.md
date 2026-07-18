# Phase 2 Storage Evaluation

Date: 2026-07-18 UTC

## Decision context

The initial system targets 20 registered companies, 10 deterministic collectors,
and roughly 200–300 current job postings. Collection will be scheduled on one VPS,
while the public Astro site remains a static consumer of separately reviewed
exports. Phase 2 creates no company, source, job, skill, or project records.

## Requirements evaluated before selection

| Requirement | Phase 2 requirement | Verification |
|---|---|---|
| Staging isolation | Explicit absolute database path outside Git; no default path; separate staging and production paths | CLI rejects relative and in-worktree database/output paths |
| Backup | Consistent online copy, non-overwriting destination, restricted permissions, integrity verification | Test backs up an open WAL database and validates the restored copy |
| Concurrency | One scheduled writer at a time; concurrent readers; a second writer may wait briefly instead of losing data | WAL plus a 5-second busy timeout; test holds one write transaction and proves the second completes after release |
| Querying | Foreign keys, indexed source/job/status/time lookups, append-only change history | Migration assertions and queryable indexes |
| Export | Version-labelled public snapshot from approved rows only; publication requires its own explicit switch | Test proves a consistent database view, complete checksums/counts, and atomic `current` switching |
| Restore | Copy must open independently, pass `integrity_check`, and preserve foreign keys and migration history | Backup test reopens and verifies the copy |

## Selected storage: SQLite

SQLite is selected for the current single-host, batch-oriented stage. WAL supports
concurrent reads and a serialized writer; a single file makes staging separation,
dated backup, restore rehearsal, and local inspection straightforward. The standard
Phase 2.1 replaces Node 24's experimental `node:sqlite` implementation with the
Python 3.12 standard-library `sqlite3` module. The host provides Python 3.12.3,
SQLite 3.45.1, WAL, busy-timeout controls, transactions, and the online backup API.
The repository keeps all database operations behind one adapter/CLI and adds no
third-party database dependency.

PostgreSQL is not justified yet: there is no online application server, remote
multi-writer workload, high-availability requirement, or query scale that needs a
managed service. Re-evaluate before enabling collection if writers span processes
without orchestration, writers span hosts, lock waits exceed the bounded timeout,
the database must serve requests directly, or operational HA/replication becomes a
requirement.

## Safety and publication boundary

- Operational database, raw, staging, log, backup, and non-public export files live
  outside Git and outside Astro inputs. The reviewed public DTO snapshot is an
  explicit exception: ordinary JSON files live under `src/data/career-public` so
  Astro/Vercel never follows a VPS path.
- `system_controls` defaults `collection_enabled` and `publication_enabled` to `0`.
  The switches can be changed independently only through an explicit command with
  a recorded reason; Phase 2 tests the mechanism but leaves real environments off.
- No seed migration creates factual domain records.
- Raw collection, parsing, review, snapshot publication, and public-site generation
  remain separate commands. The snapshot contains only rows meeting explicit
  review/publication predicates and refuses to run while publication is disabled.
- `job_changes` is append-only; update and delete triggers fail closed.
- Backups always refuse overwrite. Snapshot generation writes a temporary immutable
  directory, verifies every checksum and record count, renames it into `versions/`,
  and atomically replaces ordinary `current.json`. Updating it requires `--replace`;
  symlinks and external targets are rejected.

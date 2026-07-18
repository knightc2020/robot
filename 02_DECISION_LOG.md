# Decision Log

## D-001 — Phase 0 is documentation-only

- Date: 2026-07-18
- Status: accepted
- Decision: Phase 0 may inventory infrastructure, create Git safety references, and add/update control documentation only.
- Consequence: no public content, runtime, scheduler, database, or production deployment changes are included.

## D-002 — Preserve the existing delivery stack

- Date: 2026-07-18
- Status: accepted for planning
- Decision: retain Astro, npm, GitHub, and Vercel as the website delivery path unless a later phase demonstrates a narrow need for change.
- Rationale: the requested career system can be added through data pipelines and generated static outputs without rewriting the full site.

## D-003 — Treat current unsupported quantitative claims as unverified

- Date: 2026-07-18
- Status: accepted for Phase 1 planning
- Decision: claims without traceable raw evidence and source records are candidates for quarantine/removal, regardless of current `verified` or `estimated` labels.
- Consequence: current public metadata is not accepted as proof.

## D-004 — Do not fabricate a 20-company registry in Phase 0

- Date: 2026-07-18
- Status: accepted
- Decision: the source registry starts with governance fields and observed legacy sources only. Company entries require later verification of official career/ATS URLs.
- Consequence: Phase 0 honestly reports 0/20 verified career companies.

## D-005 — Separate scheduling from deterministic processing

- Date: 2026-07-18
- Status: accepted as target architecture
- Decision: Hermes will schedule and orchestrate approved commands; versioned programs will fetch, parse, normalize, validate, and export data deterministically.
- Consequence: Hermes prompts must not directly invent or publish job records.

## D-006 — A shared development/scheduler checkout is unsafe

- Date: 2026-07-18
- Status: accepted risk; remediation deferred
- Decision: record the existing `/root/robot` shared-workdir condition and require isolated worktrees before career schedules are enabled.
- Consequence: no new career Hermes job may use the active developer worktree.

## D-007 — Database choice is deferred to Phase 2

- Date: 2026-07-18
- Status: deferred
- Decision: document logical entities now but do not choose SQLite/PostgreSQL, an ORM, or migrations until access patterns, staging isolation, and backup requirements are evaluated.

## D-008 — Production deployment remains manual and explicitly authorized

- Date: 2026-07-18
- Status: accepted
- Decision: feature-branch pushes and local builds are allowed by the phase plan; merging/pushing production content to `master` or invoking Vercel production deployment requires separate authorization.

## D-009 — Separate production and Codex worktrees

- Date: 2026-07-18
- Status: accepted and implemented in Phase 0.5
- Decision: `/root/robot` is fixed to `master` for existing production-adjacent Hermes operations; `/root/robot-career-refactor` is fixed to `refactor/career-intelligence` for Codex development.
- Consequence: Codex must not perform refactor development in `/root/robot`. Both worktrees share one Git object store, so branch and remote operations still require coordination.

## D-010 — Preserve current Hermes business paths

- Date: 2026-07-18
- Status: accepted for Phase 0.5
- Decision: keep `/root/hermes-workspace` and all current Hermes job definitions unchanged. Worktree isolation must not rewrite or disable current business workflows.
- Consequence: the weekly job continues to use `/root/robot`, and the arXiv job continues direct GitHub API writes to `master`.

## D-011 — Keep the VPS on UTC

- Date: 2026-07-18
- Status: accepted
- Decision: retain `Etc/UTC` because the clock is synchronized and NTP is active. Persist data timestamps in UTC and convert only for user/report presentation.
- Consequence: weekly career reports should explicitly use `Asia/Singapore` or `Asia/Shanghai` rather than relying on host local time.

## D-012 — Treat sandbox Hermes status as non-authoritative

- Date: 2026-07-18
- Status: accepted
- Decision: a Hermes status command inside a PID-isolated development sandbox cannot establish host process liveness. Confirm with host-level status plus ticker heartbeat and systemd state.
- Consequence: do not restart Hermes merely to make sandbox and host output look identical.

## D-013 — Create restricted backup roots without copying secrets

- Date: 2026-07-18
- Status: accepted and implemented
- Decision: create empty `config`, `data`, and `logs` backup roots under `/root/robot-backups`, owned by root with mode `0700`.
- Consequence: later backup procedures must be additive, dated, non-overwriting, access-controlled, and must never commit secret-bearing files to Git.

## D-014 — Remove unsupported public claims instead of relabeling them

- Date: 2026-07-18
- Status: accepted and implemented in Phase 1
- Decision: remove survey, interview, salary, BOM, coverage, and validation claims when no locatable primary evidence exists. Do not replace them with new numbers or downgrade them to an ambiguous estimate.
- Consequence: the four unsupported career/BOM articles and the test-payload-generated article are absent from public collections; homepages use non-quantified current-state language.

## D-015 — Publication status is explicit and centralized

- Date: 2026-07-18
- Status: accepted and implemented in Phase 1
- Decision: require one of `draft`, `review`, `published`, or `archived`, with no default. Every public content entry point must use `isPublishableContent()` and only exact `published` entries receive routes.
- Consequence: hiding an item from a list also prevents direct detail generation; missing status fails validation rather than defaulting public.

## D-016 — Separate review status from legacy confidence labels

- Date: 2026-07-18
- Status: accepted and implemented in Phase 1
- Decision: stop rendering `confidence_level` and model governance with explicit `reviewStatus` values. Retained historical research is `pending_review`; Phase 1 does not assert human review or source verification.
- Consequence: the user-visible `estimated` label is eliminated while schema compatibility remains for non-public legacy records.

## D-017 — Canonicalize duplicate sources within each language

- Date: 2026-07-18
- Status: accepted and implemented in Phase 1
- Decision: permit one published page per normalized arXiv ID, DOI, or canonical source URL per language. Intentional bilingual pairs may share a source.
- Consequence: ten Chinese duplicates were removed and redirect to seven canonical pages. The quality gate blocks future same-language recurrence.

## D-018 — Preserve withdrawn URLs through source-controlled permanent redirects

- Date: 2026-07-18
- Status: accepted and implemented on the development branch
- Decision: use `vercel.json` permanent redirects for removed demo/test and duplicate routes. Career articles target their language career home; BOM/test content targets its language research home; duplicates target canonical pages.
- Consequence: redirect behavior is reviewable and reversible in Git but will not affect production until an authorized deployment.

## D-019 — Make deterministic content governance a build prerequisite

- Date: 2026-07-18
- Status: accepted and implemented in Phase 1
- Decision: `npm run build` must run the provenance/status/duplicate gate before Astro and verify the generated output afterward. Checks must not use external networks, AI APIs, auto-delete, or modify source content.
- Consequence: non-compliant content fails local and Vercel builds once this change reaches the production branch.

## D-020 — Select SQLite for the single-host batch data layer

- Date: 2026-07-18
- Status: accepted and implemented in Phase 2
- Decision: use a versioned SQLite database in WAL mode with foreign keys, full synchronous writes, and a 5-second busy timeout. Keep operational database paths explicit, absolute, outside Git, and isolated by environment.
- Rationale: the initial 20-company/200–300-job target uses one orchestrated VPS writer and static-site consumers; it does not require an online multi-host database service.
- Re-evaluation gate: reassess PostgreSQL before collection if writers span hosts, bounded lock waits are insufficient, direct online queries are required, or HA/replication becomes necessary.

## D-021 — Keep seven logical contracts and a complete normalized physical schema

- Date: 2026-07-18
- Status: accepted and implemented in Phase 2
- Decision: version the seven required entity contracts as JSON Schema and implement them as physical tables plus `skill_aliases`, project relation tables, `pipeline_runs`, `review_queue`, `system_controls`, and `schema_migrations`.
- Consequence: contracts do not substitute for storage; every application table is mapped in `docs/PHASE_2_DATA_MODEL.md`, while no factual seed rows are created.

## D-022 — Make collection and snapshot publication independent fail-closed controls

- Date: 2026-07-18
- Status: accepted and implemented in Phase 2
- Decision: both switches default off but may be changed independently by an explicit CLI command that records actor and reason. No real Phase 2 environment is enabled.
- Consequence: future collectors and public snapshot publication can be authorized separately without changing the schema, while a disabled publication switch blocks snapshot generation.

## D-023 — Publish snapshots through validated immutable versions and an atomic pointer

- Date: 2026-07-18
- Status: accepted and implemented in Phase 2
- Decision: a public snapshot reads one database transaction, selects only approved/published rows, writes an immutable temporary version directory, verifies checksums/counts, renames it into `versions/`, then atomically switches `current`. Existing `current` requires explicit `--replace`.
- Consequence: consumers never observe a partially written snapshot; old complete versions remain available for controlled rollback. Database backup remains non-overwriting and is validated before atomic installation.

## D-024 — Serialize migrations and retain append-only job history

- Date: 2026-07-18
- Status: accepted and implemented in Phase 2
- Decision: apply each checksummed migration under `BEGIN IMMEDIATE`, which excludes concurrent writers while allowing WAL readers. Prevent update/delete of `job_changes` through database triggers.
- Consequence: schema transitions cannot interleave with collectors, and source observation history cannot be silently rewritten.

## D-025 — Authorize only Phase 2.1 runtime hardening

- Date: 2026-07-18
- Status: accepted and implemented on `refactor/career-intelligence`
- Decision: establish and validate the empty external staging runtime, remove the experimental SQLite API risk, harden public snapshot DTOs and delivery, and stop before Phase 3.
- Consequence: no real recruitment data, collector, schedule, production merge, deployment, `/root/robot` change, or Hermes change is authorized.

## D-026 — Use Python standard-library SQLite for data operations

- Date: 2026-07-18
- Status: accepted and implemented in Phase 2.1
- Decision: replace the Node `node:sqlite` implementation with the isolated `scripts/career_db.py` adapter using Python 3.12 standard-library `sqlite3` for migrations, validation, safety controls, backup, restore, and snapshot export.
- Rationale: the host runtime provides Python 3.12.3 with SQLite 3.45.1 and the online backup API; this removes the Node experimental-API warning without adding a package dependency.
- Consequence: the CLI boundary and regression suite remain replaceable, but database behavior no longer depends on Node's experimental module.

## D-027 — Keep deployable snapshots as repository-owned ordinary files

- Date: 2026-07-18
- Status: accepted and implemented in Phase 2.1; supersedes any Phase 2 interpretation that `current` is a symlink
- Decision: publish the six-file entity snapshot only under `src/data/career-public`, retain immutable complete version directories, and atomically replace ordinary `current.json` after validation. Never create a link to `/root/robot-data` or another external target.
- Consequence: Astro and Vercel consume only Git-owned files, builds do not require VPS-local paths, and an incomplete temporary version cannot become current.

## D-028 — Enforce a strict public DTO allowlist and audited controls

- Date: 2026-07-18
- Status: accepted and implemented in Phase 2.1
- Decision: define per-file public field allowlists in the export adapter, reject any unknown or forbidden internal key, and append every safety-control update to `system_control_events` through migration 2 triggers.
- Consequence: raw paths, hashes, review details, errors, confidence values, and local paths cannot cross the public boundary; future collection and publication enablement remain independent, explicit, attributable, and default-off.

## D-029 — Validate the Phase 3A business loop before a production platform

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3A
- Decision: implement only disabled source registration, a shared adapter boundary, offline fixture parsing, bounded live-smoke support, repository-external staging, and dry-run/verification commands.
- Consequence: Phase 3A adds no scheduler, daemon, queue, browser automation, monitoring platform, frontend, or production collector.

## D-030 — Complete one adapter fixture before expanding to three sources

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3A
- Decision: first complete the Greenhouse-compatible standard ATS fixture. Expand to at most three representative real sources only after the first source completes official-evidence review and live smoke.
- Consequence: Phase 3A does not invent company or source URLs. Expansion beyond the synthetic fixture began only after Nuro completed official-evidence review and bounded live smoke.

## D-031 — Keep dry-run out of formal job and change tables

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3A
- Decision: fixture and live-smoke dry-runs may append source-verification metadata and write external staging files, but may not insert or update `job_postings` or `job_changes`.
- Consequence: every run records before/after counts, and database constraints require them to be equal.

## D-032 — Use source-native identity before normalized URLs

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3A
- Decision: construct job identity from `source_id` plus the official/ATS native job ID when available, otherwise from `source_id` plus the normalized detail URL. Use `content_hash` only for change detection.
- Consequence: content edits do not create new job identities, while meaningful non-tracking URL parameters remain available for URL-based identity.

## D-033 — Verification never enables collection or publication

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3A
- Decision: `verified` is a manually confirmed source state requiring successful fixture and live runs plus recorded evidence; it does not change any collection, base-source, global, or publication switch.
- Consequence: an HTTP 200, parser success, or `verify --confirm` cannot start collection or publication.

## D-034 — Defer continuous runs and scheduling to the next phase

- Date: 2026-07-18
- Status: accepted
- Decision: continuous 7—14 day observation, test-job-table writes, new/change/down detection, and minimal scheduling belong to the next separately authorized phase.
- Consequence: Phase 3A ended after Nuro completed fixture, explicitly confirmed bounded live smoke, manual review, and verification; no continuous run or scheduler was added.

## D-035 — Treat the first complete snapshot as a baseline

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3B
- Decision: when a tracked source has no persisted jobs, import its complete successful snapshot as a baseline and record `baseline_import_count` without generating `added` events.
- Consequence: the 280 jobs that predated tracking are not misrepresented as newly posted on the baseline date; subsequent unseen job keys generate `added` normally.

## D-036 — Close only after two consecutive successful absences

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3B
- Decision: the first absence in a complete successful source snapshot changes an open job to `missing`; only a second consecutive absence in another complete successful snapshot changes it to `closed`.
- Consequence: a single source-side delay or transient omission cannot immediately close a job, and a returning missing/closed identity generates `reopened`.

## D-037 — Never infer absence from a failed source run

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3B
- Decision: each verified Greenhouse source receives exactly one `content=true` list request per run and no detail requests. Request, barrier, parsing, duplicate, or completeness failure records a source failure and skips all missing/closed evaluation for that source.
- Consequence: network or schema failures cannot be converted into a false mass closure; other successful sources in the same one-shot run can still advance.

## D-038 — Enable collection narrowly and keep publication off

- Date: 2026-07-18
- Status: accepted and implemented in Phase 3B
- Decision: allow source collection only for the three explicitly allowlisted, manually verified Greenhouse sources, require an explicit source-control command plus audited global collection control, and keep global/source publication disabled.
- Consequence: Phase 3B can write internal job/change tables without publishing jobs or authorizing a fourth source, new adapter, frontend, or scheduler installation.

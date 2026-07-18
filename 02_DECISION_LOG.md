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

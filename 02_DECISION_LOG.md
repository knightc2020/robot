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

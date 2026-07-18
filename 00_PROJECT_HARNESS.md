# RoboMatrix Career Intelligence Project Harness

## Mission

Upgrade the current static career-navigation column into a trustworthy "robotics career intelligence and capability development system" without rewriting unrelated parts of the site.

Target relationship:

`company -> job posting -> job family -> skill requirement -> portfolio evidence -> youth action plan`

## Active stage

- Active stage: Phase 3A accepted — first official recruitment source verified; Phase 3B is not authorized.
- Phase 0, Phase 0.5, Phase 1, Phase 2, and Phase 2.1 are complete on `refactor/career-intelligence`.
- The accepted Phase 3A boundary permits disabled source registration, offline fixtures, and explicitly confirmed bounded live smoke only; continuous collection and scheduling remain unauthorized.
- Public content, production deployment, job/change-table writes, `/root/robot`, and Hermes must remain unchanged.

## Non-negotiable controls

1. Inventory before modification; one phase per authorized work cycle.
2. Finish each phase with tests, `git diff` review, project-state updates, one scoped commit, a phase report, and a stop for approval.
3. Do not delete or overwrite files whose purpose or provenance is uncertain.
4. Never print or document API keys, tokens, passwords, private keys, or complete environment files.
5. Never publish demo, inferred, estimated, or AI-generated records as verified facts.
6. External data must retain source URL, collected time, observed update time, and retrieval result.
7. Keep collection, raw storage, parsing, analysis, quality assurance, and publication as separate layers.
8. Hermes owns scheduling, orchestration, retries, and exception routing; deterministic processing belongs in versioned programs.
9. A failed quality gate blocks publication.
10. Production deployment requires explicit authorization and a tested rollback path.
11. Prefer the existing Astro/Git/Vercel stack unless a later decision record approves a narrow addition.

## Phase gate checklist

- [ ] Authorized phase and scope recorded in `02_DECISION_LOG.md`.
- [ ] Starting branch, status, and production impact checked.
- [ ] Existing user changes preserved.
- [ ] Implementation and data changes limited to the active phase.
- [ ] Deterministic tests/build checks run and results recorded.
- [ ] `git diff` and `git diff --stat` reviewed.
- [ ] `01_CURRENT_STATE.md`, `03_WORK_QUEUE.md`, and affected control files updated.
- [ ] One scoped commit created.
- [ ] Remote push attempted; failures reported truthfully.
- [ ] No production deployment performed without explicit authorization.

## Data publication gate

Publication is forbidden unless all of the following are true:

- source is registered and enabled;
- source URL and timestamps are present;
- the record is not a duplicate;
- parsing validation passes;
- required fields and provenance pass schema checks;
- status transitions are consistent with the previous observation;
- a reviewer or an approved deterministic rule has cleared the record;
- the publish output contains no secrets or private applicant data.

## Repository boundaries

- Project repository: `/root/robot`
- Production branch: `master`
- Refactor branch: `refactor/career-intelligence`
- Production site: `https://www.robotcareer.cloud/`
- Current production delivery: GitHub `master` to Vercel.
- Hermes state is outside the repository under `/root/.hermes`; only sanitized operational facts may be copied into project documentation.

# Career Intelligence Refactor Plan

## Goal

Transform RoboMatrix/robotcareer.cloud's static career-navigation column into a continuously maintained robotics career intelligence and capability development system.

Core relationship:

`company -> job posting -> job family -> skill requirement -> portfolio evidence -> youth action plan`

## Initial outcome targets

- 20 priority companies registered with verified official sources.
- 10 companies collected reliably.
- 200–300 valid job descriptions.
- 8 robotics job families.
- 50–100 normalized skills.
- 12 portfolio project templates.
- Daily recruitment-change monitoring.
- Weekly career-intelligence reporting.
- Rebuilt career-navigation pages.
- Hermes scheduling and exception handling.

## Execution rules

1. Inventory first and change second.
2. Execute one phase per authorization; never perform the entire refactor in one change.
3. End every phase with tests, diff review, state-document updates, a scoped commit, a phase report, and a stop.
4. Preserve unknown files and existing user changes.
5. Do not expose secrets or full environment files.
6. Do not represent demonstration, inferred, estimated, or model-generated data as verified reality.
7. Retain source URL, collection time, and source update time for all external data.
8. Separate collection, parsing, analysis, quality assurance, and publication.
9. Hermes schedules and orchestrates; deterministic programs process data.
10. Failed quality checks block publication.
11. Production deployment requires explicit authorization.
12. Do not rewrite unrelated site architecture; reuse Astro/Git/Vercel where practical.

## Target layered architecture

```text
Official company/ATS sources
        |
        v
source registry + deterministic collectors
        |
        v
immutable raw snapshots + retrieval metadata
        |
        v
deterministic parsers and normalizers
        |
        v
structured career database + change history
        |
        v
quality gates + duplicate checks + review queue
        |
        v
approved static exports/reports
        |
        v
Astro preview -> authorized production deployment

Hermes: schedules commands, observes outcomes, retries safely,
routes exceptions, and composes reports from approved data.
```

## Phase plan

### Phase 0 — inventory, Git backup, and baseline

Identify project structure, stack, production delivery, Hermes, data flow, unverified/demo content, databases, and risks. Create project controls, backup tag, development branch, build baseline, and scoped documentation commit. Do not alter public content or deploy.

### Phase 1 — credibility governance

Remove or quarantine unsupported surveys/interviews and public quantitative claims, correct confidence labels and update/source fields, and resolve duplicate content through a reversible, URL-aware process.

### Phase 2 — career intelligence data model

Implement versioned schema and migrations for:

- `companies`
- `career_sources`
- `job_postings`
- `skills`
- `job_skill_relations`
- `job_changes`
- `project_templates`

Choose storage only after staging, backup, concurrency, and export requirements are tested.

### Phase 3 — recruitment collection framework

Register official company career pages and official ATS endpoints. Pilot three companies with deterministic adapters, immutable raw snapshots, respectful access controls, health metrics, and no publication.

### Phase 4 — JD parsing and change detection

Extract normalized fields, detect duplicates and changes, manage active/closed/missing states, store evidence excerpts, and route uncertain cases to manual review.

### Phase 5 — job families and skill dictionary

Define eight reviewed robotics job families and 50–100 versioned skills/aliases. Map claims to exact JD evidence and prevent silent model-generated canonical terms.

### Phase 6 — portfolio project library

Build at least 12 project templates linked to job families and skills, with deliverables, acceptance evidence, prerequisites, and achievable youth action plans.

### Phase 7 — career-navigation page rebuild

Create:

- career overview;
- current job postings;
- company career maps;
- job-family graph;
- skill graph;
- portfolio lab;
- career intelligence reports.

Continue to generate static public outputs from approved data where feasible.

### Phase 8 — Hermes scheduling

Expose narrow, versioned commands for collection, parsing, validation, export, and reporting. Add isolated workdirs, schedules, timeouts, locks, idempotency, quality gates, exception queues, logs, and weekly summaries. Hermes must never bypass the publish gate.

### Phase 9 — testing and staged release

Add deterministic fixtures, parser regression tests, source-contract tests, content-quality tests, manual sampling, preview/staging, production backup, rollback rehearsal, and formal acceptance before deployment.

## Verification strategy

- Unit tests for parsers, normalizers, hashes, and state transitions.
- Fixture tests built from stored source snapshots with retrieval metadata.
- Contract tests per official source adapter.
- Duplicate and provenance audits over the entire dataset.
- Build tests for Astro generated outputs.
- Manual review samples by company, job family, language, and change type.
- Staging end-to-end run with publication disabled.
- Production backup and rollback rehearsal before launch.

## Phase 0 findings that constrain later work

- The site is currently static Astro with no backend or database.
- Vercel serves production from GitHub `master`.
- Existing Hermes research automation can write directly to `master`.
- One Hermes job shares the developer checkout.
- Career content has only two static articles and contains unsupported survey/salary claims.
- Homepage and BOM content contain unsupported sample/interview claims.
- Seven same-source Chinese arXiv duplicate groups exist.
- No automated test or provenance gate exists.

These constraints make credibility cleanup and worktree/scheduler isolation prerequisites for trustworthy career collection and publication.

## Out of scope until separately authorized

- Deleting or changing public content in Phase 0.
- Production deployment.
- Collecting real job postings.
- Creating synthetic company/JD/skill records.
- Selecting or provisioning a database.
- Adding Hermes career schedules.
- Rewriting the full site framework.

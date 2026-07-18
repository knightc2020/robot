# Acceptance Criteria

## Phase 0 acceptance

- [x] Environment, disk, runtimes, repository, branch, remote, and starting changes inventoried.
- [x] Production role and current Vercel delivery identified.
- [x] Pre-refactor tag and refactor branch created from a clean baseline.
- [x] Frontend/backend, commands, runtime managers, proxy, domain, HTTPS, database, migrations, logs, schedules, and Hermes inventoried.
- [x] Career/research/source/demo-data files and current data flow documented.
- [x] Demonstration/unverified-data candidate list created without deletion.
- [x] Minimal production/development isolation recommendations documented.
- [x] Required project-control files created without secrets.
- [x] Build passed; absent test script and existing Astro warnings are recorded.
- [x] Final diff contains only Phase 0 documentation.
- [ ] Scoped commit exists.
- [ ] Branch and backup tag are pushed or the precise push blocker is recorded.
- [x] No Phase 1 content change or production deployment occurred.

## Initial product targets

- 20 verified companies in the source registry.
- 10 stable official-source collectors.
- 200–300 valid, source-backed job postings.
- 8 reviewed robotics job families.
- 50–100 normalized skills.
- At least 12 evidence-oriented portfolio project templates.
- Daily recruitment change monitoring.
- Weekly career-intelligence report.
- Rebuilt career-navigation pages.
- Controlled Hermes scheduling with quality gates and exception handling.

## Per-record quality gate

A job posting is valid only when:

1. It comes from an enabled official source.
2. Company and source-native job identity are present.
3. Source URL, collection time, source update time when available, and raw snapshot reference are retained.
4. Required fields pass schema validation.
5. Duplicate matching and content hash checks pass.
6. Parser version and extraction evidence are recorded.
7. Job status is supported by observations, not guessed.
8. Model-assisted fields remain reviewable and are never represented as source facts.
9. The record passes manual review or an explicitly approved deterministic rule.

## Publication acceptance

- Collection, parsing, analysis, and publishing run as separate commands/artifacts.
- Failed or quarantined records cannot enter generated site content.
- A preview build succeeds and representative records are manually checked.
- Production data and logs are isolated from staging.
- Backup and rollback are tested.
- Production merge/deployment is explicitly approved.

## Current gap summary

| Target | Baseline |
|---|---|
| Registered career companies | 0 |
| Stable career collectors | 0 |
| Structured job postings | 0 |
| Job families | 0 normalized |
| Standard skills | 0 normalized |
| Project templates | 0 |
| Career database | none |
| Career Hermes schedules | none |
| Automated quality tests | none |

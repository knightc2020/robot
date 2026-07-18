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
- [x] Scoped commit exists.
- [x] Branch and backup tag are pushed or the precise push blocker is recorded.
- [x] No Phase 1 content change or production deployment occurred.

## Phase 1 acceptance

- [x] Claim/evidence ledger covers homepage samples, career surveys, BOM interviews/costs, feedback/database wording, legacy confidence labels, test payload, and duplicate arXiv content.
- [x] Unsupported statements are absent from public source files and generated output.
- [x] Two career articles, two BOM articles, and one generated test article no longer produce public details.
- [x] The unused root test payload is deleted and no production/Hermes reference remains.
- [x] Seven duplicate-source groups were reviewed by normalized arXiv ID; ten files were removed and seven canonical pages retained.
- [x] All 28 withdrawn detail URLs have permanent redirect definitions.
- [x] Missing or non-published status cannot appear in lists or static detail routes.
- [x] Source/date/review fields exist in schema and a shared bilingual component renders only present, truthful metadata.
- [x] Published content has at least one valid external structured source URL and no placeholder/self-only source.
- [x] `npm run content:check` and the deliberate failure/recovery fixture test pass.
- [x] `npm run build` invokes the quality gate and post-build verifier; Chinese and English pages build successfully.
- [x] Build output contains no withdrawn article body or user-visible legacy estimate label.
- [x] No dependency upgrade, audit fix, Hermes change, production merge, or deployment occurred.
- [x] One scoped Phase 1 commit is pushed to `origin/refactor/career-intelligence`.

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

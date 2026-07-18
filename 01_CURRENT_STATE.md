# Current State — Phase 0 Baseline

Baseline date: 2026-07-18 UTC

Production worktree: `/root/robot`

Refactor development worktree: `/root/robot-career-refactor`

Assessment scope: inventory only; no public-content or production change.

## 1. Environment

| Item | Observed state |
|---|---|
| Operating system | Ubuntu 24.04.4 LTS, Linux 6.8, x86_64 |
| Disk | 96 GB filesystem, approximately 56 GB free (42% used at baseline) |
| Node.js | v24.12.0 |
| npm | 11.6.2 |
| Python | 3.12.3 system Python; Hermes uses its own Python 3.11.15 environment |
| Git | 2.43.0 |
| Hermes | Hermes Agent v0.18.2 at `/usr/local/bin/hermes` |

## 2. Git and backup state

- Starting state was clean: `master` matched `origin/master` at `7a9a746` with no uncommitted changes.
- Remote: `https://github.com/knightc2020/robot.git`.
- Refactor branch created: `refactor/career-intelligence`.
- Pre-refactor annotated tag created on the untouched baseline: `pre-career-intelligence-refactor-2026-07-18`.
- No checkpoint commit was needed because the starting worktree was clean.
- Phase 0 is limited to the project-control documentation listed in `04_PROJECT_INDEX.md`.
- Phase 0 commit `71255d4`, the refactor branch, and the pre-refactor tag were pushed and verified.

## 3. Current architecture

- Static bilingual site built with Astro 5, MDX, Tailwind CSS 4, and TypeScript configuration.
- npm with `package-lock.json` is the package manager.
- Source content is file-based Markdown/MDX under `src/content/{cn,en}/{research,career}`.
- Page generation uses Astro content collections and static routes.
- There is no current backend API, application server, database, ORM, migration directory, or database schema.
- Historical Git commits show an Astro write API/webhook existed briefly and was removed in commit `82b95a9`; it is not part of the current runtime.
- Build command: `npm run build`.
- Development command: `npm run dev`.
- Local preview command: `npm run preview`.
- No automated test script, lint script, or type-check script is defined in `package.json` at baseline.

## 4. Production and deployment

- `https://robotcareer.cloud` redirects to `https://www.robotcareer.cloud/`.
- The public endpoint and career pages return Vercel response headers; HTTPS and edge delivery are managed by Vercel, not by an Nginx/Caddy service in this repository.
- No running Docker container, PM2 installation, local Astro/Node process, project-specific systemd unit, or project-specific Nginx/Apache/Caddy configuration was found on the VPS.
- The VPS checkout still participates in production workflows because Hermes can push repository changes. It is therefore operationally production-adjacent even though it does not serve web traffic.
- No dedicated staging branch, staging worktree, staging database, staging port, project log directory, or project backup directory was found.
- No repository-local Vercel project metadata was found. Vercel preview behavior and dashboard-side environment separation remain unverified.

## 5. Content inventory and current data flow

- 27 content files exist under `src/content`.
- Career content consists of two published static files: one Chinese salary article and one English career-map article.
- There are no company records, career-source records, job postings, normalized skills, job changes, or project templates.
- Current article flow is:

  1. A person or automation creates/updates Markdown or MDX.
  2. The file is committed to GitHub `master`.
  3. Vercel builds Astro.
  4. Astro validates frontmatter, reads content collections, and emits static HTML.
  5. Vercel publishes the build to the public domain.

- Because publication is Git-driven, a direct push to `master` can change production without a separate data-quality gate.
- `status: published` is the only content-level publication filter on career/research index pages. Detail static paths are generated from all collection entries, so a non-published detail may still be built if its URL is known.
- No article contains an `updated` frontmatter field at baseline.

## 6. Hermes current role

- The system Hermes gateway service is enabled and reported active by systemd.
- `hermes cron status` simultaneously reports that the gateway is not running. This health-check disagreement must be resolved before relying on new schedules.
- Active jobs at baseline:

  - `Fetch arXiv Papers` every 720 minutes. It reads arXiv `cs.RO`, generates Chinese research content, and uses the GitHub API to write directly to repository `master`.
  - `Weekly Robotics Research Review` at `00:30 UTC` every Monday. Its work directory is `/root/robot` and its prompt can build, commit, and push to `master`.

- Hermes is not currently generating career content or collecting job postings.
- The weekly job sharing `/root/robot` with the refactor worktree is a branch-collision risk.
- Hermes logs are under `/root/.hermes/logs`, cron definitions under `/root/.hermes/cron`, and system-service logs are available through the system journal. Credentials/configuration remain outside Git.

## 7. Demonstration or unverified data candidates

This is a candidate list only. Nothing was removed in Phase 0.

| Data/content | Public location | Code/data file | Provenance status | Recommended Phase 1 treatment | Removal risk |
|---|---|---|---|---|---|
| `340+` frontline engineer samples | Chinese and English homepages | `src/pages/cn/index.astro`, `src/pages/en/index.astro` | No source artifact found | Remove or replace with sourced, dated metric | Homepage layout/copy change; low code risk |
| `50+` supplier interviews | Chinese and English homepages | same homepage files | No interview register or evidence found | Remove claim pending proof | Homepage credibility change; low code risk |
| `340` anonymous Chinese survey responses and salary table | Chinese career article | `src/content/cn/career/robotics-salary-2025.mdx` | No raw survey, methodology package, offer URLs, or consent record found | Unpublish/quarantine; retain in Git history | Existing career section may become empty |
| `210` anonymous global survey responses and salary table | English career article | `src/content/en/career/robotics-career-map-2025.mdx` | No raw survey or source URLs found | Unpublish/quarantine; retain in Git history | English career section may become empty |
| 12 supplier interviews and actuator BOM numbers | Chinese/English research articles | both `humanoid-actuator-bom-2025.mdx` files | Generic source label only; no evidence links or interview register | Quarantine or downgrade until evidence is registered | Affects flagship research copy and homepage cards |
| “all feedback is cross-verified and entered into database” | Article footers | `src/components/FeedbackFlywheel.astro` | No database or review workflow exists | Correct copy to match actual process | Changes trust/feedback messaging |
| Raw `estimated` badge on Chinese pages | Published article detail/news UI | `src/layouts/ArticleLayout.astro`, `src/pages/research-news/index.astro`, content frontmatter | Enum is rendered without localization or definition | Localize and define semantics; reassess defaults | Broad visual/content-label change |
| Test article payload marked `published` | Repository root, not directly rendered | `test-payload.json` | Clearly a legacy test fixture; no source URL | Move to explicit test fixtures or remove after dependency check | Historical tooling may reference filename |
| Duplicate arXiv articles | Chinese research/news routes | multiple `src/content/cn/research/arxiv-*.md` files | Source URLs prove duplicate source identity | Select canonical record and redirect/unpublish duplicates | Existing public URLs and search indexing |

Confirmed same-source duplicate groups in Chinese research content:

- arXiv `2602.23287`: 5 files.
- arXiv `2602.22243`: 2 files.
- arXiv `2602.23832`: 2 files.
- arXiv `2603.02291`: 2 files.
- arXiv `2605.04649`: 2 files.
- arXiv `2605.05241`: 2 files.
- arXiv `2605.06662`: 2 files.

## 8. Security and operational risks

1. Direct automation writes to `master`, which bypasses a preview and quality-review branch.
2. The weekly Hermes job uses the same checkout as active development.
3. Hermes service status is inconsistent between systemd and the Hermes CLI.
4. The repository has no automated tests, lint, source-provenance validator, duplicate detector, or publication gate.
5. Public claims imply a database and validation process that do not exist in the current codebase.
6. Career and BOM claims lack auditable source material.
7. All detail pages are included in static paths regardless of publication status.
8. No project-specific staging, backups, logs, or rollback rehearsal is documented.
9. The current arXiv automation records only the last URL, which is insufficient for robust duplicate prevention.
10. `node_modules`, build output, and the production-adjacent checkout coexist in one VPS path, increasing accidental-operations risk.

## 9. Minimal development/production isolation recommendation

Do not migrate production in Phase 0. Before collection work begins:

1. Keep `/root/robot` as the clean production/automation worktree on `master`; never use it for Codex refactor development.
2. Use `/root/robot-career-refactor` for Codex development on `refactor/career-intelligence`.
3. Give each future Hermes publisher its own clean worktree or GitHub-API-only flow pinned to an explicit branch.
4. Use a separate preview branch/project environment; keep `master` production-only.
5. Store career collection raw data and normalized data outside `src/content`; publish only reviewed exports.
6. Use separate staging and production database files/services, credentials, logs, and backup paths when a database is introduced.
7. Add a pre-publication command that validates schema, provenance, duplicates, and status transitions before any commit targeting `master`.

## 10. Recommended Phase 1 plan

1. Freeze direct edits to the identified candidate files while creating an evidence ledger.
2. Define a reversible status for unsupported public claims (`draft`/`quarantined`) before removing visible copy.
3. Remove or neutralize unsupported homepage metrics and methodology assertions.
4. Quarantine the two career articles and two BOM articles unless evidence is supplied.
5. Localize and document confidence labels; stop defaulting missing evidence to a publishable-looking estimate.
6. Canonicalize same-source articles with a URL-preservation/redirect decision.
7. Add required `source_url`, `collected_at`, and `updated`/`observed_at` governance fields before republishing.
8. Add build plus deterministic content-quality checks and review the preview output.

Expected Phase 1 file range:

- `src/pages/cn/index.astro`
- `src/pages/en/index.astro`
- `src/content/cn/career/robotics-salary-2025.mdx`
- `src/content/en/career/robotics-career-map-2025.mdx`
- `src/content/cn/research/humanoid-actuator-bom-2025.mdx`
- `src/content/en/research/humanoid-actuator-bom-2025.mdx`
- `src/layouts/ArticleLayout.astro`
- `src/pages/research-news/index.astro`
- `src/components/FeedbackFlywheel.astro`
- `src/content.config.ts`
- duplicate `src/content/cn/research/arxiv-*.md` groups listed above
- `test-payload.json` after reference verification
- new deterministic governance tests/fixtures and documentation

## 11. Phase 0 validation result

- `npm test --if-present`: exited successfully, but no test script exists and no tests ran.
- `npm run build`: passed and generated 59 static pages.
- Existing build warnings were retained as baseline findings:

  - Astro could not create four collection JSON schema files under `.astro/collections/...` and proceeded without them.
  - the `_stub.md` glob loaders for `src/content/en` and `src/content/cn` found no matching files.

- These warnings were not fixed in Phase 0 because that would change application configuration outside the documentation-only scope.

## 12. Phase 0.5 isolation and runtime baseline

Recorded on 2026-07-18 UTC without changing public content, production business files, or Hermes configuration.

### Final worktree layout

| Path | Branch/purpose | Baseline state |
|---|---|---|
| `/root/robot` | `master`; production/legacy Hermes worktree | Clean and synchronized with `origin/master` at isolation time |
| `/root/robot-career-refactor` | `refactor/career-intelligence`; Codex development | Clean before Phase 0.5 documentation changes |
| `/root/hermes-workspace` | Hermes arXiv task workspace | Preserved; not a Git worktree and not migrated |
| `/root/robot-backups` | Local restricted backups | Created empty with root ownership and mode `0700` |

No Hermes path references `/root/robot-career-refactor`.

### Hermes write paths

- `Fetch arXiv Papers` runs with workdir `/root/hermes-workspace`. It generates matching Chinese and English Markdown and writes them directly to GitHub repository `master` through the GitHub REST API. It does not use the local `/root/robot` Git checkout.
- `Weekly Robotics Research Review` runs in `/root/robot`. It reads committed research Markdown/MDX, generates/overwrites dated HTML under `public/ppt/`, updates `src/pages/cn/index.astro`, runs `npm run build`, commits, and pushes `master`.
- The weekly task is the only current task found that operates directly in `/root/robot`. It may run concurrently with Codex, but the separate development worktree prevents working-tree collisions.
- Direct remote writes to `master` remain a production and branch-divergence risk; worktree isolation does not create a publication quality gate.

### Hermes health conclusion

- The system service runs PID `2161712` with `HERMES_HOME=/root/.hermes`.
- The built-in cron scheduler is a 60-second ticker thread inside the gateway process; it is not a separate daemon.
- Host-level `hermes cron status` reports the gateway and ticker healthy, and the heartbeat/last-success files update every minute.
- The earlier false “gateway is not running” result occurred only inside the Codex PID-isolated sandbox, which cannot see the host gateway PID. It was not caused by a different configuration path, a separate cron component, or a broken production process.
- No restart or repair was performed.

### Time baseline

- VPS timezone: `Etc/UTC`.
- System clock synchronized: yes; NTP service active; RTC stored in UTC.
- Example observation: `2026-07-18T03:49:38+00:00` equals `2026-07-18T11:49:38+08:00` in `Asia/Singapore` (also UTC+8 for `Asia/Shanghai`).
- UTC on the server is normal and should remain the storage/logging baseline. Reports should render explicit `Asia/Singapore` or `Asia/Shanghai` times.
- The tag `pre-career-intelligence-refactor-2026-07-18` used the UTC baseline date. Singapore was also already on 2026-07-18, so the date is unambiguous.

### Backup baseline

- `/root/robot-backups/config`, `/root/robot-backups/data`, and `/root/robot-backups/logs` exist.
- Parent and child directories are `root:root` with mode `0700`.
- They were intentionally left empty in Phase 0.5. No environment file, token, key, or secret-bearing Hermes configuration was copied.

### Phase 0.5 dependency/build baseline

- A clean `npm ci` in `/root/robot-career-refactor` installed 347 packages successfully.
- npm reported 13 dependency vulnerabilities: 2 low, 4 moderate, and 7 high. No automated audit fix was run because dependency upgrades are outside Phase 0.5 and may introduce breaking changes.
- `npm run build` passed and generated 59 static pages.
- The same pre-existing collection schema and missing `_stub.md` warnings recorded in Phase 0 remained. They were not changed in this safety-only phase.

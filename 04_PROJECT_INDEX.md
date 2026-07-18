# Project Index

## Current application

| Path | Purpose |
|---|---|
| `package.json` | Astro/npm scripts and runtime dependencies |
| `package-lock.json` | Locked npm dependency graph |
| `astro.config.mjs` | Astro, MDX, Tailwind, and bilingual routing configuration |
| `src/content.config.ts` | Article and career frontmatter schemas |
| `src/content/cn/research/` | Chinese research Markdown/MDX source |
| `src/content/en/research/` | English research Markdown/MDX source |
| `src/content/cn/career/` | Chinese career content; one file at baseline |
| `src/content/en/career/` | English career content; one file at baseline |
| `src/pages/cn/index.astro` | Chinese homepage and public quantitative claims |
| `src/pages/en/index.astro` | English homepage and public quantitative claims |
| `src/pages/{cn,en}/career/` | Static career index and detail routes |
| `src/pages/{cn,en}/research/` | Static research index and detail routes |
| `src/pages/research-news/` | Alternate research feed and detail routes |
| `src/layouts/ArticleLayout.astro` | Article metadata, raw confidence badge, and feedback component |
| `src/components/FeedbackFlywheel.astro` | Feedback links and database/cross-validation claims |
| `public/ppt/` | Static weekly-review presentation assets |
| `test-payload.json` | Legacy published-status API test payload; current API no longer exists |

## Phase 0 controls

| Path | Purpose |
|---|---|
| `00_PROJECT_HARNESS.md` | Operating rules and phase gates |
| `01_CURRENT_STATE.md` | Evidence-backed baseline and Phase 0 report |
| `02_DECISION_LOG.md` | Architectural and governance decisions |
| `03_WORK_QUEUE.md` | Authorized and pending work |
| `04_PROJECT_INDEX.md` | Navigation across code, content, and controls |
| `05_DATA_DICTIONARY.md` | Current fields and future logical entities |
| `06_SOURCE_REGISTRY.md` | Source governance and verified-registration status |
| `07_ACCEPTANCE_CRITERIA.md` | Phase and product acceptance gates |
| `08_OPERATIONS_RUNBOOK.md` | Safe local operations, deployment, Hermes, and rollback notes |
| `docs/CAREER_INTELLIGENCE_REFACTOR_PLAN.md` | Goals, phases, execution rules, and target architecture |

## External operational locations

| Location | Purpose |
|---|---|
| `/root/.hermes/config.yaml` | Hermes configuration; secret-bearing and never copied into Git |
| `/root/.hermes/cron/jobs.json` | Hermes scheduled-job definitions |
| `/root/.hermes/logs/` | Hermes agent/gateway logs |
| `/root/.hermes/state/` | Automation state markers |
| `/root/hermes-workspace/` | Restricted arXiv automation workspace; not a Git checkout |
| `/etc/systemd/system/hermes-gateway.service` | System Hermes gateway unit |

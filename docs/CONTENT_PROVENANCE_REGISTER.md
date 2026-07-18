# Content Provenance Register

Governance review date: 2026-07-18 UTC

Scope: public Astro pages and content present at the start of Phase 1. A statement in a page or frontmatter is not evidence for itself. Git history was reviewed for source artifacts, and sanitized searches covered repository files, relevant Hermes skills/job definitions, and likely local raw-data filenames. No survey response set, interview register, quote record, consent/methodology package, or locatable BOM source package was found.

## Claim and evidence ledger

| Public claim/content | Page(s) | Source file(s) at review start | Data type | Traceable source? | Evidence location | Phase 1 judgment | Treatment | Resulting page state |
|---|---|---|---|---|---|---|---|---|
| `340+ 一线工程师样本` / `340+ Engineer Respondents` | `/cn/`, `/en/` | `src/pages/cn/index.astro`, `src/pages/en/index.astro` | Sample-size claim | No | Claim text only; no raw survey or register in repository/history/local evidence search | Unsupported | Removed; replaced with non-quantified tracking/governance copy | Homepages remain published without the metric |
| `50+ 供应商深度访谈` / `50+ Supplier Interviews` | `/cn/`, `/en/` | same homepage files | Interview-count claim | No | Claim text only | Unsupported | Removed | Homepages remain published without the metric |
| `340 份匿名问卷` plus Chinese salary table and regional conclusions | `/cn/career/robotics-salary-2025/` | `src/content/cn/career/robotics-salary-2025.mdx` | Survey, salary and geographic comparison | No | No response set, methodology, offer URLs, consent record, or collection log | Demonstration/unverifiable publication | Content file removed; Git history retained | No detail route; permanent redirect to `/cn/career/` |
| `210 anonymous survey responses` plus global salary table | `/en/career/robotics-career-map-2025/` | `src/content/en/career/robotics-career-map-2025.mdx` | Survey and salary benchmarks | No | No response set, methodology, offer URLs, or collection log | Demonstration/unverifiable publication | Content file removed; Git history retained | No detail route; permanent redirect to `/en/career/` |
| Interviews with 12 suppliers and Chinese actuator BOM/cost percentages | `/cn/research/humanoid-actuator-bom-2025/`; alternate research-news route | `src/content/cn/research/humanoid-actuator-bom-2025.mdx` | Interview, quote and cost matrix | No | Git history only adds the article and later renames the author; no supporting artifacts or Hermes references | Unsupported flagship content | Content file removed; Git history retained | Both old detail routes redirect to `/cn/research/` |
| Interviews with 12 suppliers and English actuator BOM/cost percentages | `/en/research/humanoid-actuator-bom-2025/`; alternate research-news route | `src/content/en/research/humanoid-actuator-bom-2025.mdx` | Interview and cost matrix | No | Same evidence result as Chinese version | Unsupported flagship content | Content file removed; Git history retained | Both old detail routes redirect to `/en/research/` |
| All salary ranges, role premiums and cost matrices in the four files above | Same career/BOM pages | four removed MDX files | Quantitative salary/cost claims | No | No row-level source URLs or raw observations | Unsupported | Removed with their containing articles; no replacement numbers invented | Not present in public collections or build output |
| `所有反馈将经过交叉验证后纳入数据库` / `All submissions are cross-verified before integration` | Every article footer | `src/components/FeedbackFlywheel.astro` | Process/database assertion | No; no application database exists | Current architecture and repository inventory | False description of current process | Replaced with a statement that submissions are review leads and are not automatically verified or published | Footer remains without database/verification claim |
| User-visible `estimated` badge | Article details and `/research-news/` | legacy `confidence_level`, `src/layouts/ArticleLayout.astro`, `src/pages/research-news/index.astro` | Ambiguous confidence/status label | No defined review semantics; schema defaulted missing values to it | `src/content.config.ts` baseline | Misleading governance label | Removed from presentation and surviving frontmatter; replaced by explicit `reviewStatus` | Retained research shows `Pending review` / `待人工复核` |
| Published root `test-payload.json` | Repository root; not itself routed | `test-payload.json` | Legacy API test payload | Synthetic fixture | Git history adds it for the now-removed API workflow | Unused test artifact in unsafe location | Deleted; no production/Hermes reference was found | Cannot be scanned or published |
| Public article generated from the test payload | `/cn/research/2026-02-28T16-48-38-2026/`; alternate research-news route | `src/content/cn/research/2026-02-28T16-48-38-2026.md` | Synthetic/test article | No | Title, summary and body match the legacy payload; no source URL | Demonstration publication | Removed | Both old routes redirect to `/cn/research/` |
| Seven same-language duplicate arXiv source groups, including five files for `2602.23287` | Chinese research and research-news routes | 17 `src/content/cn/research/arxiv-*.md` files | Paper summaries sharing canonical source | Yes, for source identity only | arXiv URLs/IDs embedded in each file | Duplicate publication; article analysis itself remains pending review | Kept one canonical page per arXiv ID and language; removed 10 duplicate files | Old duplicate routes permanently redirect to canonical routes; see `DUPLICATE_CONTENT_REVIEW.md` |
| `12+` segment coverage and `3-Layer` validation methodology | `/cn/`, `/en/` | homepage files | Coverage/process metrics | No register or implemented validation workflow | Claim text only | Unsupported | Removed with the homepage statistics bar rewrite | Replaced by non-quantified source/status/update principles |

## Evidence search notes

- BOM files first appear in commit `57eb264`; commit `3dfe8ef` only changes the author name. No source package appears in their file history.
- Repository history repeats the unsupported statements but contains no underlying survey/interview data. Repetition in Git is not independent evidence.
- Relevant Hermes skill and cron searches found no reference to the career salary files, BOM files, surveys, interviews, or `test-payload.json`.
- A restricted filename search found only the production/development copies of the same article files, not raw survey or supplier material.
- Public arXiv links establish paper identity, not the correctness of every generated interpretation. All retained summaries therefore use `reviewStatus: pending_review`.

## Withdrawn URL policy

`vercel.json` contains source-controlled permanent redirects (`permanent: true`, implemented by Vercel as 308):

- Chinese career demonstration article -> `/cn/career/`
- English career demonstration article -> `/en/career/`
- Chinese/English BOM primary and research-news routes -> corresponding language research home
- Published test-payload article primary and research-news routes -> `/cn/research/`
- Twenty duplicate arXiv routes -> their language- and route-equivalent canonical pages

The redirects take effect only after an explicitly authorized merge/deployment. This Phase 1 branch does not change production.

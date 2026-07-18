# Career Source Registry

Baseline date: 2026-07-18 UTC

## Progress

- Verified career-company sources: **1 / 20**.
- Stable company collectors: **0 / 10**.
- Registered factual career-company sources: **1** (`nuro-greenhouse`).
- Offline adapter fixtures passing: **1** (`standard_ats_greenhouse_v1`, synthetic Greenhouse-compatible JSON).
- Accepted live smoke sources: **1** (`nuro-greenhouse`; one repair retry is retained as a separate non-overwriting run).
- No collector is enabled. Verification records source identity and parser acceptance only.

## Registration requirements

| Field | Requirement |
|---|---|
| `source_id` | Stable internal identifier |
| `company_id` | Canonical company foreign key |
| `source_url` | Exact official company/ATS endpoint |
| `source_type` | official career page, official ATS API/feed, or approved official export |
| `collection_method` | deterministic adapter name |
| `scope` | jobs/regions included and excluded |
| `verified_at` | UTC time official ownership was verified |
| `collected_at` | UTC time of each retrieval |
| `source_updated_at` | Source-provided update time when available |
| `terms_review` | robots/terms/access assessment and date |
| `enabled` | false until verification and parser tests pass |
| `health` | never_run, healthy, degraded, blocked, paused, retired |
| `owner` | accountable maintainer |
| `allowed_domains` | exact company/official ATS hostname allowlist; unknown redirects stop |
| `adapter_name` | versioned shared adapter implementation |
| `external_id_strategy` | native job ID first, normalized detail URL fallback |
| `collection_enabled` | false throughout Phase 3A |
| `publication_enabled` | false throughout Phase 3A |

## Current observed sources and claims

| Source ID | Scope | Location | Source URL/evidence | Status | Publish permission |
|---|---|---|---|---|---|
| `research_arxiv_cs_ro` | Research papers, not careers | Hermes arXiv publisher | arXiv `cs.RO` RSS and article URLs | Active legacy automation | Existing research-only scope |
| `legacy_cn_salary_survey` | Chinese salary/career article | `src/content/cn/career/robotics-salary-2025.mdx` | No raw survey or offer URLs found | Unverified legacy claim | Block for new publication/reuse |
| `legacy_en_salary_survey` | English career article | `src/content/en/career/robotics-career-map-2025.mdx` | No raw survey or offer URLs found | Unverified legacy claim | Block for new publication/reuse |
| `legacy_supplier_interviews` | Actuator BOM research | Chinese/English BOM articles | No interview register or evidence URLs found | Unverified legacy claim | Block for new publication/reuse |

## Verified career-company sources

| Source ID | Company | Official evidence | Listing endpoint / type | Allowed domains | Verification result | Enabled |
|---|---|---|---|---|---|---|
| `nuro-greenhouse` | Nuro | `https://www.nuro.ai/careers` exposes Greenhouse `gh_jid` jobs | `https://boards-api.greenhouse.io/v1/boards/nuro/jobs?content=true`; `standard_ats` / Greenhouse | `boards-api.greenhouse.io`, `www.nuro.ai` | Fixture passed; bounded live smoke passed; native IDs `7442056` and `7442057` manually reviewed; verified 2026-07-18 UTC | Base/source collection 0; publication 0 |

## Candidate-company entry template

Use one section/table row per company only after confirming the official endpoint:

```text
source_id:
company_id:
official_career_url:
official_ats_url:
regions:
source_type:
collection_method:
verified_at:
terms_review:
enabled: false
health: never_run
notes:
```

Search-engine results, aggregator reposts, copied job boards, model-generated URLs, and guessed ATS endpoints are not acceptable as official sources.

## Phase 3A fixture and source status

The checked-in Greenhouse-compatible fixture uses only reserved `.invalid` domains,
synthetic IDs `900001`/`900002`, and invented job text clearly labelled for offline
tests. It proves adapter behavior but is not a registry source, official evidence,
or permission to access any Greenhouse tenant.

`official_html_v1` and `official_json_v1` currently establish only the common adapter
contract. They have no source-specific fixture or real-source success claim. A factual
source stays `candidate` after fixture or HTTP 200; only the manual verified workflow
can change status, and it cannot enable collection or publication.

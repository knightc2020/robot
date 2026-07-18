# Career Source Registry

Baseline date: 2026-07-18 UTC

## Progress

- Verified career-company sources: **0 / 20**.
- Stable company collectors: **0 / 10**.
- This file deliberately does not invent company entries. Official career and ATS URLs must be verified in a later authorized phase.

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

## Current observed sources and claims

| Source ID | Scope | Location | Source URL/evidence | Status | Publish permission |
|---|---|---|---|---|---|
| `research_arxiv_cs_ro` | Research papers, not careers | Hermes arXiv publisher | arXiv `cs.RO` RSS and article URLs | Active legacy automation | Existing research-only scope |
| `legacy_cn_salary_survey` | Chinese salary/career article | `src/content/cn/career/robotics-salary-2025.mdx` | No raw survey or offer URLs found | Unverified legacy claim | Block for new publication/reuse |
| `legacy_en_salary_survey` | English career article | `src/content/en/career/robotics-career-map-2025.mdx` | No raw survey or offer URLs found | Unverified legacy claim | Block for new publication/reuse |
| `legacy_supplier_interviews` | Actuator BOM research | Chinese/English BOM articles | No interview register or evidence URLs found | Unverified legacy claim | Block for new publication/reuse |

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

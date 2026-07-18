# 阶段 3A：官方招聘源接入与采集验证 MVP

状态：阶段 3A 已完成；第一个真实来源 `nuro-greenhouse` 已人工 verified
日期：2026-07-18 UTC

## 1. 本阶段目标

本阶段只验证一个最小闭环：登记官方招聘来源、从 fixture 或受控真实页面
取得列表和最多两个详情、生成稳定职位身份、保存原始响应，并输出统一的
staging 结构。它不是生产采集平台，也不写入正式岗位或岗位变化表。

仓库在阶段开始时没有已核验机器人公司清单，`companies` 和
`career_sources` 均为空。离线能力审核后，本轮从 Nuro 官网 Careers 页面
建立到其 Greenhouse 招聘端点的证据链，登记并验证了一个真实来源。来源
验证没有开启采集或发布，也没有向岗位和岗位变化表写入记录。

## 2. 已实现内容

- migration 3 增加 `career_source_profiles` 和只追加的
  `source_verification_runs`；
- 来源默认 `candidate`，来源级采集和发布开关固定为关闭；
- 建立统一 adapter 接口：`parse_listing`、`extract_detail_links`、
  `parse_detail`、`extract_external_job_id`、`normalize_detail_url`；
- Greenhouse `standard_ats` adapter 完成合成 fixture 列表和详情解析；
- `official_html` 和 `official_json` 建立最小接口，但没有伪造真实来源，
  当前也没有可宣称完成的来源级 fixture；
- fixture dry-run 完全离线；
- live smoke 必须显式传入 `--confirm-live`，并限制为一个列表请求和两个
  详情请求；
- 原始响应、解析结果和运行摘要只能写到仓库外 staging；
- `verify` 只改变来源状态，不能开启采集、基础来源 `enabled` 或发布；
- dry-run 只写来源验证运行元数据，不写 `job_postings` 和 `job_changes`。

## 3. 当前支持的来源类型

| 来源类型 | adapter | 当前能力 | 真实来源状态 |
|---|---|---|---|
| `standard_ats` | `standard_ats_greenhouse_v1` | Greenhouse 公开 JSON 列表/详情；fixture 已通过 | `nuro-greenhouse` 已 live smoke 并人工 verified |
| `official_html` | `official_html_v1` | 统一接口和保守的 HTML 解析骨架 | 无合适已核验来源，不宣称可用 |
| `official_json` | `official_json_v1` | 统一接口和通用 JSON 解析骨架 | 无合适已核验来源，不宣称可用 |

本阶段只完整跑通第一个 adapter 和第一个真实来源。只有此闭环稳定后，
才考虑增加第二、第三个代表性来源。

## 4. 职位身份和统一结果

职位身份优先为：

```text
<source_id>:external:<external_job_id>
```

没有稳定原生 ID 时回退为：

```text
<source_id>:url:<normalized_detail_url>
```

URL 标准化会：

- 移除 fragment；
- 移除 `utm_*`、`gclid`、`fbclid`、`ref` 等跟踪参数；
- 保留可能影响岗位身份的其他查询参数；
- 规范协议、域名、默认端口和末尾斜杠；
- 在 staging 中同时保留请求 URL、最终 URL、详情 URL 和 canonical URL。

`content_hash` 只覆盖规范化后的标题、地点、部门、雇佣类型、描述和发布
时间，用于后续变化检测，不参与职位主键。

统一结果位于 `parsed_jobs.jsonl`，字段为：`source_id`、`company_id`、
`external_job_id`、`job_key`、`title`、`location`、`department`、
`employment_type`、`description`、`detail_url`、`canonical_url`、
`published_at`、`content_hash`、`fetched_at`，并附请求/最终 URL 和身份策略。
不存在的字段保持空值，不做猜测。解析后的描述会去除非必要电话和邮箱。

## 5. Fixture dry-run

以下命令创建一次性的仓库外测试运行，使用的公司和域名均为明确标注的
合成 fixture，不代表真实来源：

```bash
cd /root/robot-career-refactor
phase3a_root="$(mktemp -d /tmp/robot-career-phase3a-XXXXXX)"

npm run career:db -- runtime-init --root "$phase3a_root"
npm run career:db -- migrate \
  --database "$phase3a_root/staging/career.sqlite3"

npm run career:sources -- register-company \
  --db "$phase3a_root/staging/career.sqlite3" \
  --company-id fixture-company \
  --display-name "Synthetic Fixture Company" \
  --official-website-url https://company.example.invalid \
  --official-career-url https://company.example.invalid/careers

npm run career:sources -- register \
  --db "$phase3a_root/staging/career.sqlite3" \
  --source-id fixture-greenhouse \
  --company-id fixture-company \
  --source-name "Synthetic Greenhouse Fixture" \
  --official-careers-url https://company.example.invalid/careers \
  --listing-url "https://boards-api.example.invalid/v1/boards/fixture/jobs?content=true" \
  --source-type standard_ats \
  --ats-vendor greenhouse \
  --allowed-domain boards-api.example.invalid \
  --allowed-domain job-boards.example.invalid \
  --adapter-name standard_ats_greenhouse_v1 \
  --external-id-strategy native_job_id \
  --owner offline-test \
  --notes "Synthetic fixture only; not a factual source"

npm run career:sources -- dry-run \
  --db "$phase3a_root/staging/career.sqlite3" \
  --staging-dir "$phase3a_root/raw/career-sources" \
  --source-id fixture-greenhouse \
  --mode fixture
```

fixture 模式网络请求计数必须为零。每次运行创建唯一 `run_id`，已存在的
运行目录或文件会被拒绝，不会静默覆盖。

## 6. 真实来源登记和 live smoke

真实来源必须先从仓库外数据库中显式登记。所有 URL、域名和人工审核状态
必须来自实际核验，不得照抄 fixture 值或猜测 ATS 租户。

```bash
npm run career:sources -- dry-run \
  --db /absolute/external/path/career.sqlite3 \
  --staging-dir /absolute/external/path/career-source-staging \
  --source-id REAL_SOURCE_ID \
  --mode live-smoke \
  --confirm-live
```

本轮使用现有 `--confirm-live` 明确执行了 Nuro 来源。官网入口为
`https://www.nuro.ai/careers`，最终列表为
`https://boards-api.greenhouse.io/v1/boards/nuro/jobs?content=true`。请求未遇到
登录、验证码、401、403、429 或未知域重定向。

live smoke 固定限制：

- 一个列表页；
- 最多两个详情页；
- 不自动翻页，不循环，不批量运行所有来源；
- 单线程，同域请求间隔至少三秒；
- 401、403、429、登录、验证码、未知域重定向或无法识别结构时立即停止；
- 不绕过访问控制，不使用浏览器自动化，不访问申请流程；
- 不写 `job_postings`、`job_changes` 或公开快照。

## 7. Staging 输出

```text
<staging_dir>/
  <source_id>/
    <run_id>/
      listing.html 或 listing.json
      detail_001.html 或 detail_001.json
      detail_002.html 或 detail_002.json
      parsed_jobs.jsonl
      run_summary.json
```

`run_summary.json` 保存：请求 URL、最终 URL、重定向链、HTTP 状态、内容
类型、抓取时间、原始字节数、SHA-256、adapter/parser 版本、请求计数、
解析数量、失败原因，以及 dry-run 前后两个业务表的行数证明。

数据库和 staging 都必须是绝对路径并位于 Git 工作树外；生产工作树、
Hermes 目录、符号链接 staging 和宽泛系统目录会被拒绝。

## 8. 人工验证

只有 fixture 与 live smoke 均成功，且官网闭环、robots、条款、登录、
验证码、身份稳定性和人工解析结果检查均有记录后，才允许执行：

```bash
npm run career:sources -- verify \
  --db /absolute/external/path/career.sqlite3 \
  --source-id REAL_SOURCE_ID \
  --actor REVIEWER_ID \
  --confirm
```

`verified` 不等于开启采集。该命令执行后 `career_sources.enabled`、
`career_source_profiles.collection_enabled` 和 `publication_enabled` 仍为 0。

## 9. 安全底线

1. 数据库路径显式、绝对且位于仓库外。
2. 原始数据和 staging 位于仓库外且只新建、不覆盖。
3. 默认不联网，live smoke 需要 `--confirm-live`。
4. 不绕过登录、验证码、403、429 或明显反爬限制。
5. dry-run 不写正式岗位表和岗位变化表。

## 10. 本阶段不做

不实现调度器、常驻服务、任务队列、全量翻页、高频采集、浏览器自动化、
Workday 适配、登录/验证码绕过、复杂权限审批、前端、自动发布、生产监控
或大规模插件/adapter 版本体系。

## 11. 后续阶段

下一阶段只建议：选择三个已核验来源连续运行 7—14 天；写入隔离的测试
岗位表；识别新增、变化和下架；增加最小调度能力。本阶段不提前实现这些
能力。

## 12. 第一个真实来源开发与验收报告

### 来源证据链

- 公司：Nuro；官网：`https://www.nuro.ai/`；
- 官网招聘入口：`https://www.nuro.ai/careers`；
- 官网岗位链接使用稳定的 Greenhouse `gh_jid`；
- 列表端点：`https://boards-api.greenhouse.io/v1/boards/nuro/jobs?content=true`；
- ATS / adapter：Greenhouse / `standard_ats_greenhouse_v1`；
- 请求允许域名：`boards-api.greenhouse.io`、`www.nuro.ai`；
- Nuro 与 Greenhouse robots 检查均未禁止本次公开 API 路径；Greenhouse
  Job Board API 文档说明公开 GET 不需要认证；
- 实际请求没有登录、验证码、401、403、429 或重定向。

### 正式数据库升级和注册

- 正式数据库：`/root/robot-data/staging/career.sqlite3`；
- 非覆盖备份：
  `/root/robot-data/backups/career-pre-phase3a-live-20260718T114724Z.sqlite3`；
- migration：2 → 3；升级后 `validate` 通过；
- 升级前 company/source/job/change 行数：`0/0/0/0`；
- 最终行数：`1/1/0/0`；
- `nuro-greenhouse` 先以 `candidate`、三个启用值全 0 登记；人工验收后仅
  状态改为 `verified`，三个启用值仍为 0。

### 执行命令

```bash
npm run career:sources -- dry-run \
  --db /root/robot-data/staging/career.sqlite3 \
  --staging-dir /root/robot-data/raw/career-sources \
  --source-id nuro-greenhouse \
  --mode fixture

npm run career:sources -- dry-run \
  --db /root/robot-data/staging/career.sqlite3 \
  --staging-dir /root/robot-data/raw/career-sources \
  --source-id nuro-greenhouse \
  --mode live-smoke \
  --confirm-live

npm run career:sources -- verify \
  --db /root/robot-data/staging/career.sqlite3 \
  --source-id nuro-greenhouse \
  --actor phase3a-human-review \
  --confirm
```

### Live smoke 和两个岗位

验收 run 为
`/root/robot-data/raw/career-sources/nuro-greenhouse/20260718T122539530494Z-2d52325342`。
它只请求一个列表和两个详情，三次响应均为 HTTP 200，解析两个岗位：

| external_job_id | job_key | title | location | department | employment_type | description | content_hash |
|---|---|---|---|---|---|---|---|
| `7442056` | `nuro-greenhouse:external:7442056` | Associate Fleet Technician, Bay Area | California - Santa Clara; California - SF | Fleet Operations | `null` | 5,917 字符纯文本，内容正常，无标签残留 | `ec725713883e2caccf989c4297c9ad15041916d9a8d9141df6285394e73fae3c` |
| `7442057` | `nuro-greenhouse:external:7442057` | Associate Fleet Technician, Houston (Overnight) | Texas - Depot 2 | Fleet Operations | `null` | 5,838 字符纯文本，内容正常，无标签残留 | `9659bbd7583bfe9447ebbcc774faaa7ad2bcbccd4ebdb5b20fdf8448dea1e709` |

两个岗位的 `detail_url` 和 `canonical_url` 分别为
`https://nuro.ai/careersitem?gh_jid=7442056` 和
`https://nuro.ai/careersitem?gh_jid=7442057`。这些 URL 由官方 Greenhouse
响应提供，保留影响身份的 `gh_jid`。两个 ID、URL 和详情原始 SHA-256 在
人工重试前后均一致，没有重复岗位或字段错位。来源未提供结构化
`employment_type` 和 `published_at`，因此保持空值。

第一次 live 输出暴露了 Greenhouse 实体编码 HTML 标签未被完全清除的
问题。只调整了现有 `plain_text` 的解码/解析顺序并增加一个回归测试，
19 项来源测试通过；随后用新 run_id 进行一次同样受限的人工重试。首次
和重试产物都保留在独立仓库外目录，没有覆盖。

fixture、首次 live 和验收 live 的 `job_postings` 与 `job_changes` 前后都
是 0。最终来源为 `verified`；基础 `enabled`、`collection_enabled` 和
`publication_enabled` 仍全部为 0。阶段 3A 因此按“第一个真实来源已
verified”完成，不提前开展连续采集、岗位入库、变化/下架识别或调度。

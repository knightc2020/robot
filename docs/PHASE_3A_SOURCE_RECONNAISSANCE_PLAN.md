# 阶段 3A：官方招聘源注册与受控采集验证

状态：侦察方案已执行；Nuro 已完成真实来源登记、受限 live smoke 和人工验证
范围：官方来源注册、离线 fixture 验证和显式确认的极低频 live smoke 机制
明确禁止：连续或全量采集、写入真实 JD、自动启用、启动阶段 3B、修改 `master`、修改 Hermes、部署生产

## 1. 首批三种招聘源结构的选择标准

先跑通一个结构清晰的来源；只有第一个来源完成 fixture 和 live smoke 后，
才扩展到最多三个代表性来源。仓库当前没有已核验的机器人公司清单，因此
不得为凑数编造公司、官网或 ATS URL。

### 1.1 `official_html`

特征：

- 公司官方静态或半静态 HTML 招聘页面；
- 列表页和详情页均返回稳定 HTML；
- 岗位详情具有独立 URL；
- 不依赖登录、验证码或复杂客户端状态；
- 可通过明确选择器识别列表、分页和岗位 ID。

### 1.2 `standard_ats`

特征：

- 公司官网明确链接到 Greenhouse、Lever、Ashby 等 ATS 租户；
- 存在公开 JSON 接口或结构化页面；
- ATS 租户与公司身份能够形成官网闭环；
- 原生 requisition/job ID 稳定；
- Workday 等复杂来源必须单独评估，本阶段不默认支持。

### 1.3 `official_json`

特征：

- 公司官方、自建且公开 JSON/API 驱动的招聘页面；
- 接口由公司官网招聘页面直接使用或明确链接；
- 数据接口不要求登录、私有签名、验证码或规避访问控制；
- 不逆向私有、加密或登录接口。

“无需复杂 JavaScript”只是三类来源共同的准入条件，不是来源类型。

共同准入条件：

- 能从公司官网证明其官方身份；
- 无需登录或接受求职者专属协议；
- robots 和条款允许拟议访问；
- 可以限制为低频、单线程、小样本；
- 存在稳定岗位标识；
- 与机器人职业情报目标相关。

排除聚合站、搜索引擎缓存、第三方转载和身份无法核实的来源。

## 2. 官方来源核验方法

核验从公司主域名开始：

1. 定位官网招聘入口。
2. 记录官网到最终招聘列表的完整跳转链。
3. 核对最终域名、TLS、公司名称、品牌标识和 ATS 租户名称。
4. ATS 来源必须由公司官网直接链接或由公司官方页面明确声明。
5. 记录核验时间、核验人和证据摘要。
6. 无法形成官网闭环的来源保持 `candidate`，不得标记 `verified`。

建议保留：

- 官网主页；
- 官网招聘入口；
- 最终招聘列表 URL；
- ATS 供应商及租户标识；
- 核验方法；
- 核验证据引用；
- 核验时间与审核人。

## 3. Robots、登录、频率和合规边界

公司域名和 ATS 域名分别检查：

- `robots.txt`；
- 服务条款；
- 隐私政策；
- 自动化访问限制；
- 登录、Cookie 同意和地区限制。

`robots.txt` 是站点访问偏好信号，不是法律授权证明，也不能替代服务条款
和人工判断。状态处理规则：

- `disallowed`：禁止访问；
- `unclear` 或 `manual_review_required`：禁止自动采集；
- `allowed` 或 `not_found`：仍须记录网站条款和人工判断；
- 程序不得自动作出法律合规结论。

禁止：

- 登录、注册或使用求职者账户；
- 绕过验证码、WAF、限流或访问控制；
- 探测未公开接口；
- 采集申请人、招聘人员或其他个人信息；
- 访问申请流程和内部候选人系统。

建议默认限制：

- 每个域名并发数：1；
- 请求间隔：至少 3–5 秒；
- 遵守 `Retry-After`；
- dry-run 最多一个列表页和两个详情页；
- 出现 401、403、429、验证码或条款变化时立即停止；
- 不自动重试合规类失败。

## 4. 列表、详情、分页和唯一 ID 识别

### 4.1 岗位列表

识别：

- 岗位卡片或列表项；
- 详情页链接；
- 标题、地点、部门和更新时间；
- 总数和过滤参数；
- 列表是否包含完整数据或仅包含摘要。

### 4.2 详情页

确认：

- canonical URL；
- 岗位原生编号；
- 标题、地点、描述和发布时间；
- 页面是否需要额外公开接口；
- 列表与详情之间的身份对应关系。

### 4.3 分页

需要区分：

- `page=N`；
- `offset/limit`；
- cursor 或 next token；
- `next` 链接；
- 无限滚动接口。

必须设置最大页数、重复 cursor 检测和重复岗位 ID 检测。

### 4.4 唯一 ID

优先级：

1. ATS 原生 requisition/job ID；
2. 页面或结构化数据中的明确岗位 ID；
3. 稳定 canonical URL；
4. 经审核的来源原生字段组合。

`content_hash` 只用于变更检测，不能替代稳定岗位 ID。

## 5. 原始快照目录和命名规则

MVP 目录：

```text
<staging_dir>/<source_id>/<run_id>/
```

文件结构：

```text
listing.html 或 listing.json
detail_001.html 或 detail_001.json
detail_002.html 或 detail_002.json
parsed_jobs.jsonl
run_summary.json
```

规则：

- `run_id` 由 UTC 时间、来源 ID 和随机后缀组成；
- 文件只能新建，禁止覆盖；
- 岗位 ID 必须转换为安全文件名；
- `run_summary.json` 记录 URL、时间、HTTP 状态、内容类型、adapter 版本和 checksum；
- 原始内容与汇总元数据分离；
- 日志不得包含 Cookie、Token 或完整敏感响应头；
- 原始快照不得进入 Git 或公开快照。

## 6. 两层 Dry-run 和少量样本机制

分为两层。

### 6.1 Fixture dry-run

使用仓库内合成 fixture：

- 不访问网络；
- 验证列表、详情、分页和岗位 ID 解析；
- 验证错误、空响应和重复 ID 处理；
- 验证不会写入正式数据库或公开快照。

### 6.2 Live smoke dry-run

必须另行取得明确授权。

每个来源最多：

- 一个列表页；
- 两个详情页；
- 单域名串行访问；
- 不自动翻页；
- 不写入 `job_postings` 或 `job_changes`；
- 不自动启用来源；
- 只写仓库外 staging 目录；
- 必须显式传入数据库和 staging 路径；
- 必须显式传入 `--confirm-live`；
- 不允许隐式批量运行所有来源。

允许生成：

- 仓外原始快照；
- 来源结构报告；
- 候选字段报告；
- 解析错误摘要；
- ID 和分页判断结果。

不得在报告中复制完整 JD 正文。

## 7. Verified 的严格定义

页面返回 HTTP 200 或解析成功都不等于 verified。来源必须同时满足：

- 可以从公司官方网站招聘入口追溯；
- 最终域名属于公司或明确的 ATS 厂商；
- 不要求登录、身份认证或验证码；
- robots 状态和网站条款状态已经记录；
- 列表页和详情页可稳定访问；
- 能获得稳定的原生职位 ID，或经确认的稳定规范 URL；
- fixture dry-run 成功；
- live smoke dry-run 成功；
- adapter 测试通过且未出现 schema drift；
- 解析结果经过人工确认；
- CLI `verify` 命令收到明确确认。

任一条件缺失时保持 `candidate`。无法稳定识别岗位时进入人工复核或
`blocked`，不得标记 verified。

## 8. 来源注册表补充字段

建议为 `career_sources` 补充以下字段。

### 身份和结构

- `official_entry_url`
- `canonical_list_url`
- `structure_type`
- `ats_vendor`
- `tenant_key`
- `adapter_key`
- `adapter_version`
- `detail_url_pattern`
- `native_id_strategy`
- `pagination_type`
- `page_size_hint`

### 官方核验

- `verification_method`
- `verification_evidence_ref`
- `verified_by`
- `verified_at`

### 合规审核

- `robots_url`
- `robots_checked_at`
- `robots_result`
- `terms_url`
- `terms_checked_at`
- `login_required`
- `allowed_scope_json`
- `compliance_status`
- `compliance_owner`
- `compliance_notes`

### 运行限制

- `minimum_interval_ms`
- `max_concurrency`
- `max_pages_per_run`
- `request_timeout_ms`
- `retry_policy_json`
- `last_dry_run_at`
- `last_dry_run_result`

来源默认：

```text
enabled = 0
verification_status = candidate
compliance_status = pending
```

字段变更必须使用新 migration，不得修改已有 migration 或其 checksum。解析规则保存在版本化 adapter 中，注册表只保存 adapter 标识和版本。

## 9. 采集和发布开关

fixture 和 live smoke 都是验证运行，不是正式采集。阶段 3A preflight 必须
同时确认：

```text
collection_enabled = 0
publication_enabled = 0
source.collection_enabled = 0
source.publication_enabled = 0
```

任一条件不满足即拒绝 dry-run。`blocked`、`retired` 不得执行 live smoke；
`paused` 只有经过单独人工恢复流程后才能再次执行。阶段 3A 不提供正式采集
启用或自动发布能力，也不配置定时任务或 Hermes 作业。禁止调用 snapshot
命令或修改仓库内公开快照。

## 10. 验收标准、风险和回滚

### 10.1 验收标准

- 一个结构清晰的 adapter 已通过完整 fixture；有合适来源时再扩展到最多三个；
- 真实来源只有形成官网闭环证据后才可登记为待验证候选；
- live smoke 前完成 robots、条款、登录要求和访问频率检查；
- 注册表新增字段通过 migration 和 checksum 验证；
- 新来源默认禁用；
- 合成 Greenhouse fixture 离线 dry-run 通过；
- 若联网样本另行获批，其范围不超过一个列表页和两个详情页；
- `job_postings`、`job_changes` 及其他真实 JD 表保持为空；
- `publication_enabled` 始终关闭；
- 未生成新的公开快照；
- 数据测试、负向测试、备份恢复测试和 `git diff --check` 通过；
- 未修改 `master`、`/root/robot`、Hermes 或生产环境。

### 10.2 主要风险

- 官网与 ATS 租户归属误判；
- robots 和服务条款解释错误；
- JavaScript 接口或分页规则变化；
- 岗位 ID 不稳定；
- 限流、验证码或区域限制；
- 意外采集个人信息；
- dry-run 范围失控；
- 采集开关未及时关闭；
- 内部字段进入公开边界。

### 10.3 回滚方式

1. 暂停来源并关闭来源级采集开关。
2. 回滚 adapter 或配置，保留状态和验证审计记录。
3. 保留历史原始快照、manifest 和日志，不把删除证据作为默认回滚动作。
4. 只有发现敏感信息、错误采集或收到明确合规要求时，才进入单独审批的受控删除流程。
5. 必要时使用阶段开始前的非覆盖备份恢复数据库。
6. 运行完整 `validate`、开关和业务表零写入检查。
7. 通过 Git revert 撤销阶段 3A 代码和 migration，不重写共享历史。
8. 确认公开快照、`master`、Hermes 和生产环境未发生变化。

## 阶段退出条件

阶段 3A 完成后必须停止并提交验收报告。未经单独批准，不得进入真实 JD 采集、批量分页、解析入库或阶段 3B。

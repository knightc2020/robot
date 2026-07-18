# 阶段 3B：三来源岗位持续跟踪 MVP

状态：开发和第一次真实基线完成；等待 7—14 天自然变化观察

日期：2026-07-18 UTC

## 1. 目标与边界

阶段 3B 只跟踪 `nuro-greenhouse`、`zipline-greenhouse` 和
`agility-robotics-greenhouse`。它复用已验证的
`standard_ats_greenhouse_v1`，验证岗位新增、内容变化、连续缺失、关闭和
重新开放，不增加来源或 ATS 类型，也不开发前端、队列、常驻服务、消息推送、
AI 分析或正式发布。

Greenhouse 的 `jobs?content=true` 响应已包含正文、部门、地点、metadata、
发布时间、Job ID 和 canonical 职位 URL。因此正常运行每个来源只请求一次
列表 API，详情请求为 0，不翻页。

## 2. 数据模型和基线规则

migration 4 复用 `job_postings`、`job_changes` 和 `pipeline_runs`：

- `job_postings.job_id` 保存 `job_key`；
- `source_native_id` 保存 Greenhouse Job ID；
- `source_url` 保存详情 URL；
- `first_collected_at` / `last_collected_at` 对应 first/last seen；
- `lifecycle_status=active/missing/closed` 对应 open/missing/closed；
- 新增 `department_text`、`canonical_url`、`consecutive_missing_count`；
- `job_changes` 支持 `added/updated/missing/closed/reopened`，并引用现有
  `pipeline_runs.run_id`。

第一次成功快照按来源定义为 baseline。历史已存在岗位写入 `job_postings`，
但不生成大量 `added` 事件；运行摘要使用 `baseline_import_count` 单独记录。

## 3. 变化定义

- `added`：非基线运行出现数据库不存在的 `job_key`；
- `updated`：同一 `job_key` 的 hash 或受跟踪字段发生变化；
- `missing`：来源完整成功，但一个 open 岗位第一次未出现；
- `closed`：同一岗位连续第二次在该来源的成功完整快照中未出现；
- `reopened`：missing 或 closed 岗位再次出现。

`changed_fields_json` 记录具体字段名，包括 title、location、department、
employment_type、description、detail_url、canonical_url 和 published_at。
正常且未变化的岗位只更新 last seen，不产生事件。

来源请求、访问检查、结构解析或完整性检查失败时，本次来源记录失败，且不会
增加该来源任何岗位的 missing count，也不会生成 missing/closed。其他成功来源
仍可正常处理。

## 4. 明确开关

publication 始终保持关闭。采集前只允许显式开启三个 allowlist 来源：

```bash
cd /root/robot-career-refactor
npm run career:sources -- collection-control \
  --db /root/robot-data/staging/career.sqlite3 \
  --source-id nuro-greenhouse \
  --source-id zipline-greenhouse \
  --source-id agility-robotics-greenhouse \
  --enable \
  --actor phase3b-operator \
  --confirm

npm run career:db -- controls \
  --database /root/robot-data/staging/career.sqlite3 \
  --collection enabled \
  --reason "Authorize Phase 3B collection for three verified sources" \
  --actor phase3b-operator
```

`collection-control` 不会修改 global 或 source publication。`collect` 同时要求：
global collection 为 1、global publication 为 0、来源 verified、来源 base/source
collection 为 1、来源 publication 为 0。

## 5. 一次性 CLI

```bash
cd /root/robot-career-refactor
npm run career:sources -- collect \
  --db /root/robot-data/staging/career.sqlite3 \
  --staging-dir /root/robot-data/raw/career-sources \
  --all-verified \
  --confirm-write
```

未传 `--confirm-write` 时，命令在任何网络或业务表写入前拒绝。也可重复传
`--source-id` 运行 allowlist 子集。数据库和 staging 必须是仓库外的显式绝对
路径。

每个来源写入独立、唯一、不覆盖的 run 目录；每日摘要写入：

```text
/root/robot-data/raw/career-sources/daily-summaries/YYYY-MM-DD/
  summary.json
  summary.md
```

同一 UTC 日期的摘要目录已存在时命令拒绝覆盖，因此每天最多进行一次正式运行。

## 6. 第一次真实基线

执行前创建了不覆盖备份：

`/root/robot-data/backups/career-pre-phase3b-baseline-20260718T132025Z.sqlite3`

migration 从 3 升到 4，保留 3 家公司、3 个来源和 8 条 Phase 3A 验收记录；
integrity、foreign key、checksum 和权限 validate 通过。

真实运行 ID：

`phase3b-20260718T132452151113Z-7d88443f3f`

| 公司 | Phase 3A 观察值 | 真实基线 | 结果 |
|---|---:|---:|---|
| Nuro | 约 95 | 95 | 成功 |
| Zipline | 约 131 | 131 | 成功 |
| Agility Robotics | 约 54 | 54 | 成功 |
| 合计 | 约 280 | 280 | 成功 |

三次列表请求均成功，详情请求 0；280 个岗位全部为 active，job key 和同来源
native ID 均无重复，正文未发现 `<p>`、`</...>` 或 `&lt;` 残留。基线没有写入
`job_changes`，摘要记录 `baseline_import_count=280` 和“本次未发现岗位变化”。

只读随机抽样各两条包括：Agility Robotics 的 `6019178004` / `5997167004`、
Nuro 的 `7733212` / `7638789`、Zipline 的 `7795633003` / `7795650003`。
六条均有稳定 job key、详情/canonical URL、正文和地点；部门存在时正确落列，
Greenhouse metadata 未提供 employment type 时保持 null。另按工程/研发标题
检查了 Agility `5997167004`、Nuro `7577458` 和 Zipline `7765099003`，三家公司
均至少有一条工程相关岗位。

## 7. 离线验证

`scripts/career_tracking_test.py` 使用 `.invalid` 域名和内存 HTTP 页面，验证：

- baseline 不生成 added；
- 新岗位 added；
- description/title/location 修改和 changed_fields；
- missing 后第二次缺失 closed；
- 单来源失败不增加 missing count；
- closed 再出现 reopened；
- confirm-write、外部路径和 publication 开关；
- 相同 external ID 跨来源不冲突；
- 相同快照重复运行幂等；
- JSON/Markdown 摘要和不覆盖行为。

测试不访问真实网络。

## 8. VPS cron 示例（仅示例，未安装）

以下示例每天 UTC 02:00 运行一次，使用 `flock` 防重叠，日志写到仓库外。`%`
已按 crontab 规则转义：

```cron
0 2 * * * /usr/bin/flock -n /root/robot-data/logs/career-phase3b.lock /usr/bin/bash -lc 'cd /root/robot-career-refactor && PATH=/root/.nvm/versions/node/v24.12.0/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /root/.nvm/versions/node/v24.12.0/bin/npm run career:sources -- collect --db /root/robot-data/staging/career.sqlite3 --staging-dir /root/robot-data/raw/career-sources --all-verified --confirm-write >> /root/robot-data/logs/career-phase3b-$(/usr/bin/date -u +\%F).log 2>&1'
```

本轮未执行 `crontab`、`systemctl` 或守护进程安装。

## 9. 当前限制和下一步

- 真实环境目前只有第一份基线，尚无自然发生的真实 added/updated/missing/
  closed/reopened；这些转换已由离线快照测试证明，不能人工修改正式库伪造。
- 日摘要按 UTC 日期只允许一个正式运行；失败后是否重跑需人工检查并选择新的
  运维策略，本 MVP 不自动重试。
- employment type 只读取 Greenhouse metadata 的明确值；不存在时保持 null，
  不猜测。
- 没有安装 cron，没有消息通知，没有公开快照或前端读取这些岗位。

下一步仅观察三个来源 7—14 天，核验自然变化、失败保护和连续两次缺失规则；
不在本阶段提前开发技能分析、作品映射或前端。

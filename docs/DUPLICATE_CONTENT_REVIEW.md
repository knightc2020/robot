# Duplicate Content Review

Review date: 2026-07-18 UTC

Scope: the seven same-source groups identified in Chinese research content. Source identity was established from normalized arXiv URLs/IDs, not titles. Each file generated two public detail forms: `P = /cn/research/{slug}/` and `N = /research-news/cn/{slug}/`.

Cross-language pairs are not treated as duplicates: one Chinese and one English page may share a paper when they are intentional translations. The deterministic quality gate enforces one canonical arXiv ID, DOI, or normalized source URL per language.

## arXiv 2602.22243

Original source: `https://arxiv.org/abs/2602.22243`

| Slug/file | Title | Published | Size/completeness | Review result |
|---|---|---:|---:|---|
| `arxiv-2602-22243` | SODA-CitrON：基于在线聚类的多模态异构传感器静态目标关联新框架 | 2026-02-28 | 1,780 bytes; structured source field and source-ID slug | **Canonical** |
| `arxiv-1772334967` | SODA-CitrON：基于在线聚类的多模态传感器静态目标数据关联新算法 | 2026-03-01 | 1,921 bytes; longer, but timestamp slug and no structured source field | Removed; P/N redirect to canonical |

Recommendation/result: keep `arxiv-2602-22243` because the source-ID URL is stable and its metadata is more regular. The longer generated interpretation was not merged without editorial review.

## arXiv 2602.23287 — five-file priority review

Original source: `https://arxiv.org/abs/2602.23287`

| Slug/file | Title | Published | Size/completeness | Review result |
|---|---|---:|---:|---|
| `arxiv-2602-23287` | 从受限操控到自由灵动：界面感知轨迹重构助力残障人士操控高自由度机器人 | 2026-02-28 | 1,703 bytes; structured source field and source-ID slug | **Canonical** |
| `arxiv-1772335777` | 打破接口枷锁：基于接口感知轨迹重构的辅助机器人高效学习 | 2026-03-01 | 1,976 bytes | Removed; P/N redirect to canonical |
| `arxiv-1772336924` | 意图重构：让低维交互界面实现高维机器人精准控制 | 2026-03-01 | 1,871 bytes | Removed; P/N redirect to canonical |
| `arxiv-1772356557` | 突破限制：面向低维控制接口的辅助机器人轨迹重构算法 | 2026-03-01 | 1,789 bytes | Removed; P/N redirect to canonical |
| `arxiv-1772399776` | 界面感知轨迹重构：让受限演示“进化”为高效机器人策略 | 2026-03-02 | 2,544 bytes; longest generated analysis | Removed; P/N redirect to canonical |

Recommendation/result: keep the source-ID slug. Although one timestamp version is longer, there is no reviewed editorial basis for combining AI-generated interpretations; stable source identity and metadata win over raw length.

## arXiv 2602.23832

Original source: `https://arxiv.org/abs/2602.23832`

| Slug/file | Title | Published | Size/completeness | Review result |
|---|---|---:|---:|---|
| `arxiv-1772442953` | OmniTrack：基于物理一致性引导的人形机器人通用运动追踪框架 | 2026-03-02 | 1,533 bytes; byte-identical pair, first slug | **Canonical** |
| `arxiv-1772442962` | Same title | 2026-03-02 | 1,533 bytes; byte-identical duplicate | Removed; P/N redirect to canonical |

Recommendation/result: retain the first identical file and redirect the second.

## arXiv 2603.02291

Original source: `https://arxiv.org/abs/2603.02291`

| Slug/file | Title | Published | Size/completeness | Review result |
|---|---|---:|---:|---|
| `arxiv-1772638926` | 最新机器人研究突破：Goal-Oriented Semantic Communication for ISAC-Enab... | 2026-03-04 | 1,233 bytes; truncated title | Removed; P/N redirect to canonical |
| `arxiv-1772682221` | 用于 ISAC 支持的机器人避障的面向目标的语义通信 | 2026-03-05 | 1,384 bytes; complete title and fuller record | **Canonical** |

Recommendation/result: keep the more complete, non-truncated record.

## arXiv 2605.04649

Original source: `https://arxiv.org/abs/2605.04649`

| Slug/file | Title | Published | Size/completeness | Review result |
|---|---|---:|---:|---|
| `arxiv-1778168473` | 触觉增强：迈向亚毫米精度精密装配的新范式 | 2026-05-07 | 2,102 bytes; earlier and fuller | **Canonical** |
| `arxiv-1778211670` | 触觉引导的精密装配：突破亚毫米级插入难题 | 2026-05-08 | 1,668 bytes | Removed; P/N redirect to canonical |

Recommendation/result: keep the earlier, more complete record.

## arXiv 2605.05241

Original source: `https://arxiv.org/abs/2605.05241`

| Slug/file | Title | Published | Size/completeness | Review result |
|---|---|---:|---:|---|
| `arxiv-1778254872` | DexSim2Real：利用基础模型实现通用灵巧操作的虚实迁移 | 2026-05-08 | 1,522 bytes | Removed; P/N redirect to canonical |
| `arxiv-1778298071` | 基于视觉语言模型的DexSim2Real：实现灵巧操作的零样本虚实迁移 | 2026-05-09 | 1,620 bytes; fuller title and content | **Canonical** |

Recommendation/result: keep the more complete record.

## arXiv 2605.06662

Original source: `https://arxiv.org/abs/2605.06662`

| Slug/file | Title | Published | Size/completeness | Review result |
|---|---|---:|---:|---|
| `arxiv-1778341273` | 基于V2X技术的社会机器人多机协作架构 | 2026-05-09 | 1,931 bytes; earlier and fuller | **Canonical** |
| `arxiv-1778384475` | 基于V2X的机器人多机协同系统：迈向智能交通互联新范式 | 2026-05-10 | 1,786 bytes | Removed; P/N redirect to canonical |

Recommendation/result: keep the earlier, more complete record.

## Aggregate result

- Reviewed: 17 files across 7 source identities.
- Retained: 7 canonical Chinese pages.
- Removed: 10 duplicate files, eliminating 20 generated detail routes.
- Redirected: every removed primary and research-news URL to the corresponding canonical route through `vercel.json`.
- Remaining canonical summaries are still marked `pending_review`; duplicate removal does not certify their analysis.

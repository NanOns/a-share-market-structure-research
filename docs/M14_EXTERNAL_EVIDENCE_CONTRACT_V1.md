# M14-04 外部证据/涨停原因合同 V1

- 阶段：`M14-04-REASONS`
- 合同 ID：`M14_EXTERNAL_EVIDENCE_V1_0`
- 设计基线：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 14.1、14.2、14.3 节及第 22.9 节
- 当前能力状态：`UNAVAILABLE`

## 1. 能力与空态

`EXTERNAL_EVIDENCE` 独立于 `HOT_RANKINGS`。热榜成功不推导原因可用；当前没有通过来源、条款、正文、事件时间和首次发现时间核验的原因来源，因此只能返回：

```json
{
  "dataset": "EXTERNAL_EVIDENCE",
  "capability_status": "UNAVAILABLE",
  "unavailable_reason": "NO_VERIFIED_REASON_SOURCE",
  "source_ids": [],
  "batch_id": null,
  "source_as_of": null,
  "items": [],
  "post_hoc_items": []
}
```

空态不得渲染为“无原因”、不得填 0、不得从热榜或本地快照推测原因，也不得阻塞本地主流程。

## 2. 证据字段

准入后每条证据必须同时保留 `evidence_id`、`source_id`、`security_id`、`event_time`、`published_at`、`first_seen_at`、`text_hash`、`raw_ref` 和受限纯文本摘要。来源、事件和发现时间分别表达，不把抓取时间伪装成事件时间。

`LATEST` 允许展示最新已验证证据；`AS_OF` 只允许 `published_at` 和 `first_seen_at` 都不晚于 `as_of` 的条目。晚于 `as_of` 的内容只能进入独立的 `post_hoc_items`，不能进入严格历史结果。时间缺失或未来时间一律不进入严格 `AS_OF`。

## 3. 隔离与开放项

本阶段不抓取原因、不建立在线原因生产批次、不启用 API38 或 UI。后续来源准入必须独立记录许可、字段完整率、正文哈希、时间语义、代码映射、重复内容和 10 个交易日观察；来源条款未明确时保持 `UNAVAILABLE`。

`personal_research_only=true`、`publication_enabled=false` 是硬约束；不得写入 TDX 或改变本地 `analysis_snapshot`。

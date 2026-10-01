# A07 Historical AS_RECORDED Adjusted Price 任务卡 R2｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**Audit：** `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE`  
**优先级：** P2 Parallel

## 1. 目标

明确回答：

> 对历史 adjusted price / QFQ，我们能否证明“当时系统实际知道的版本”？

## 2. 三类 lineage

必须区分：

```text
AS_RECORDED
RECONSTRUCTED_CORRECTED
CURRENT_RECOMPUTED
```

禁止混用。

## 3. Source

盘点：

```text
GBBQ snapshots
BaoStock factors
manual records
historical local adjusted artifacts
receipts
Git history
```

## 4. First availability

AS_RECORDED 必须同时具备：

```text
first_available_at
source_revision
knowledge_time
immutable source bytes
```

缺任何一个：

```text
不能声称 AS_RECORDED
```

## 5. Historical scope

对 pre-capture 历史：

```text
无法证明 first availability
→ capability permanently blocked
```

不能因为今天可查询 target date 就倒填。

## 6. Go-forward capture

新增自动 capture：

```text
source revision
observed_at
received_at
GBBQ/provider/manual identity
```

未来逐日自然积累。

## 7. Price basis consumers

至少盘点：

```text
V4-05 Replay
V4-12 Structure/Anchor
Forward outcome
support/retention
```

标明哪些允许：

```text
RECONSTRUCTED_CORRECTED
```

哪些必须：

```text
AS_RECORDED
```

## 8. 不阻塞 V4-12 engineering

V4-12 可实现 price-basis转换接口，但不能把 A07 未证明 capability 宣称已通过。

## 9. 验收

至少：

```text
cash dividend
split/bonus
rights issue
same-day revision
historical unavailable
go-forward real capture
```

结束：

```text
A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

真实 future observations 继续积累，不等待固定天数。

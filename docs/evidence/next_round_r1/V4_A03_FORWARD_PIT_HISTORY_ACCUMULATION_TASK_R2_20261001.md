# A03 Forward PIT History Accumulation 任务卡 R2｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**Audit：** `FORWARD_PIT_HISTORY_ACCUMULATION`  
**优先级：** P1 Parallel

## 1. 目标

建立真正可持续的：

```text
Forward PIT Daily Builder
```

从接受起点开始每日不可变追加。

## 2. 核心原则

```text
观察到什么就保存什么
未观察到绝不补造
晚到 source 不倒填 first_available_at
revision 只追加
```

## 3. Daily publication

每个交易日：

```text
target_trade_date
observed_at
received_at
source_revision
first_available_at
source bytes/hash
identity/calendar binding
publication_id
```

## 4. Detector

必须有：

```text
MISSING_EXPECTED_SOURCE
LATE_SOURCE
SOURCE_REVISION
SCHEMA_DRIFT
DUPLICATE_CAPTURE
TARGET_DATE_MISMATCH
CALENDAR_GAP
IDENTITY_GAP
```

## 5. Revision

同日新 revision：

```text
旧 publication immutable
新 publication append
latest projection 单独生成
```

不能覆盖旧 PIT。

## 6. First availability

只有真实 capture/accepted source 能生成：

```text
first_available_at
```

历史 queryable 但今天补抓：

```text
RECONSTRUCTED_CORRECTED
```

不得倒填知识时点。

## 7. Current starting point

当前正式 Data Head：

```text
2026-09-30
```

A03 可以从下一 session 开始真实积累。

如果执行时已有 10/1 或之后完成交易日，可真实捕获并形成 candidate；没有则只完成 automation，不等待未来天数。

## 8. Automation

必须提供：

```text
daily command
idempotent retry
crash recovery
partial source failure behavior
```

## 9. 与 DM01 区分

DM01 = Canonical Data Head 增量。

A03 = PIT observation/history availability ledger。

不得混为同一 publication identity。

## 10. Consumer

当前未独立接受的 PIT capability：

```text
不得自动赋予 V4-05/V4-08/Forward consumer 新权限
```

## 11. 验收

至少：

```text
synthetic late-source
real accepted baseline
same-day revision
missing source
schema drift
duplicate capture
clean checkout
immutable replay
```

结束：

```text
A03_FORWARD_PIT_BUILDER_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

真实观察积累继续自然发生，不阻塞其他阶段。

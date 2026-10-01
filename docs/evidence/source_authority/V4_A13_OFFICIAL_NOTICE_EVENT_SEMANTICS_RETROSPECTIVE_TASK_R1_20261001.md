# A13｜V4-08 Official Notice Event Semantics Retrospective 任务卡 R1｜2026-10-01

**Work Package：** `WP-A13-OFFICIAL-NOTICE-EVENT-SEMANTICS`  
**基线 HEAD：** `a43d663a0cc62d48f65a1160fae9c50874d86548`  
**优先级：** P1 Evidence Governance  
**当前业务 Head：** 默认 KEEP，除非本任务独立证明真实业务结果受污染。

## 1. 背景

A12-R2 回溯发现 V4-08 R3 source evidence 中部分文件/capture id 使用 `*_suspension`，但真实公告语义并不是“已上市股票停牌”。

已确认：

```text
SH.603302 → IPO 暂缓发行
SH.688688 → 暂缓上市
SZ.300728 → IPO 发行暂缓
```

因此存在：

```text
FILENAME / CAPTURE-ID SEMANTICS
!=
ACTUAL EVENT SEMANTICS
```

## 2. 当前外部判断

V4-08 R3 的 `NOT_LISTED_AT_TARGET` 实际判定来自：

```text
target active exchange catalogue absence
```

这些 notice 仅被挂在：

```text
dated_lifecycle_evidence
```

builder 明确：

```text
available dated issuance or lifecycle evidence is attached
without inferring legal termination
```

所以当前没有证据表明错误命名直接改变 accepted business membership/result。

但 evidence governance 本身必须修。

## 3. 目标

建立统一：

```text
OFFICIAL_EVENT_SEMANTICS_V1
```

禁止以后根据：

```text
filename
capture id
关键词“暂停/暂缓”
```

直接推断：

```text
TRADING_SUSPENSION
```

## 4. Event Type

至少区分：

```text
LISTED_STOCK_TRADING_SUSPENSION
LISTED_STOCK_RESUMPTION
IPO_ISSUANCE_POSTPONEMENT
IPO_LISTING_POSTPONEMENT
IPO_TERMINATION
DELISTING_PHASE
RISK_WARNING_CHANGE
LISTING
CODE_CHANGE
OTHER_OFFICIAL_NOTICE
UNKNOWN_EVENT_SEMANTICS
```

## 5. 历史 raw bytes 不改名、不覆盖

禁止删除或重命名既有 frozen raw source：

```text
SH_603302_suspension.pdf
SH_688688_suspension.html
SZ_300728_suspension.pdf
...
```

这些路径已经进入历史 hash binding。

新增 sidecar：

```text
OFFICIAL_NOTICE_EVENT_SEMANTICS_AMENDMENT_R1.json
```

逐文件声明：

```text
old_capture_id
raw artifact/hash
actual_event_type
security key
event effective date
source published date
semantic evidence
consumer permissions
```

## 6. 全量 inventory

不能只修发现的三个。

扫描：

```text
data/v4/source_evidence/**
reports/** source capture manifests
```

所有 suspension/resumption/listing/issuance/delisting/risk-warning/code-change 命名对象。

逐项对照：

```text
filename semantic
capture-id semantic
document actual semantic
consumer semantic
```

## 7. Consumer Inventory

至少扫描：

```text
V4-01 identity/lifecycle
V4-02 Trading Status/ST/Special Phase
V4-08 identity admission
V4-08 PIT membership
A12 sample matrix
DM01
```

标记：

```text
BUSINESS_DECISION
SUPPORTING_EVIDENCE
DIAGNOSTIC_ONLY
NOT_CONSUMED
```

## 8. 三个已确认对象的反事实

对：

```text
SH.603302
SH.688688
SZ.300728
```

执行：

### Old
包含误命名 notice。

### Counterfactual
完全移除这些 notice，只保留 target-day official active catalogue、exchange query 和其他正确 source。

重新执行 admission。

如果仍：

```text
NOT_LISTED_AT_TARGET
```

且 downstream business digest 全相同，才可宣布：

```text
NO_BUSINESS_IMPACT
```

## 9. 若无业务影响

正式候选：

```text
V4_08_ACCEPTED_HEAD = KEEP
EVIDENCE_SEMANTICS_AMENDMENT_REQUIRED = YES
BUSINESS_REBUILD_REQUIRED = NO
```

只追加 semantic sidecar / consumer policy / negative tests。

## 10. 若有业务影响

若任何 accepted business output 依赖错误语义：

```text
bounded replay
old/new diff
downstream cascade
Accepted Head amendment candidate
```

不得隐藏。

## 11. Runtime Guard

禁止：

```python
if "suspension" in filename:
    event = TRADING_SUSPENSION
```

必须读取 accepted semantic sidecar/parser result。

`UNKNOWN_EVENT_SEMANTICS` 不得进入 trading-status truth。

## 12. Tests

至少：

```text
IPO issuance postponement named *_suspension
→ NOT trading suspension

IPO listing postponement
→ NOT trading suspension

real listed-stock suspension
→ TRADING_SUSPENSION

real resumption
→ RESUMPTION

unknown wording
→ UNKNOWN_EVENT_SEMANTICS

filename-only inference
→ REJECT
```

## 13. Accepted Head

默认：

```text
no Accepted Head movement
```

除非 counterfactual 证明 business output 真变化。

## 14. Registry

`OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS` 保持 OPEN，直到独立外部验收。

Codex 最大允许：

```text
A13_OFFICIAL_NOTICE_EVENT_SEMANTICS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止自行：

```text
V4_08_REACCEPTED
NO_BUSINESS_IMPACT_ACCEPTED
```

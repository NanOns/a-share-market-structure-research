# Existing Accepted Fields Owner Registry Scoped Bootstrap 任务卡 R1｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**Audit：** `OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS`  
**优先级：** P1 Parallel / Production Gate  
**不阻塞：** V4-11 / V4-12 engineering

## 1. 目标

把既有已接受字段逐字段迁入新的 Source Authority Owner Registry，避免未来 Global mandatory adoption 时出现“旧合法 authority 没有 owner entry”。

Scope：

```text
OHLC
Volume
Amount
QFQ
Security Identity
Special Phase
Sector Membership
```

## 2. 禁止 bulk accept

绝对禁止：

```text
for all fields:
  EXTERNALLY_ACCEPTED=true
```

每字段必须独立审计：

```text
历史 scope
go-forward scope
PIT semantics
degraded capability
consumer scope
source family
```

## 3. 每字段矩阵

至少：

```text
field_id
current accepted contract
accepted head
source authority
historical mode
effective scope
allowed consumers
known limitations
external acceptance evidence
artifact SHA
```

## 4. OHLC / Volume / Amount

确认 TDX authority 的：

```text
field scope
actual bar semantics
market/board coverage
```

Amount A 与普通成交额不是同一字段，禁止混淆。

## 5. QFQ

正式 owner 必须保持：

```text
GBBQ canonical
```

BaoStock adjustment factor 不能借机升级。

历史 AS_RECORDED 问题由 A07 独立处理。

## 6. Security Identity

必须继承 A11 limitation：

```text
HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED
```

不能把 historical reconstructed provider facts 洗成 local-TDX truth。

## 7. Special Phase

绑定现有 accepted phase policy 和 source evidence。

UNKNOWN capability 保留。

## 8. Sector Membership

必须区分：

```text
current mutable provider snapshot
project-first-observed PIT
accepted V4-08 membership source
```

禁止 current snapshot 回填历史。

## 9. Registry candidate

新增 versioned candidate：

```text
V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE
```

但本轮不得使它成为 active global mandatory trust root。

## 10. Global adoption

本任务只形成 scoped bootstrap candidate。

禁止：

```text
global_mandatory_adoption = true
production = true
shadow = true
```

## 11. 验收

逐字段 owner negative tests：

```text
wrong scope
wrong consumer
wrong hash
wrong historical mode
wrong external evidence
supplemental self-promotion
```

结束：

```text
OWNER_REGISTRY_SCOPED_BOOTSTRAP_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

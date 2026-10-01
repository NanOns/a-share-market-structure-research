# A05｜V4-08 B2 Current-Snapshot Scoped Amendment Promotion 任务卡｜2026-10-02

**优先级：** P1 Parallel  
**外部裁决：** `PASS_CURRENT_SNAPSHOT_ONLY`

## 1. 目标

正式登记 2026-09-24 A05 exact legacy producer 对 V4-08 B2 的 current-snapshot scoped capability amendment。

## 2. Scope

唯一允许：

```text
trade_date = 2026-09-24
scope = CURRENT_SNAPSHOT_ONLY
AS_RECORDED = false
historical_PIT_equivalent = false
```

## 3. 禁止

绝对禁止：

```text
把 9/24 snapshot 当成 9/30 membership
改写 9/30 V4_08 accepted B2
宣称历史 PIT membership 已恢复
启用 Amount-A warm branch
```

## 4. Head 形式

建议创建独立：

```text
V4_08_B2_CURRENT_SNAPSHOT_CAPABILITY_AMENDMENT_R1
```

不要把它做成替代 `V4_08_ACCEPTED_HEAD` 的完整头。

## 5. 必须绑定

```text
A05 acceptance record
R3 B2 replay
541-sector full diff
10 zero-member sectors
normal quote universe = 5464
original algorithm/parameter SHA
external audit authority
```

## 6. Reader

读取方必须显式要求：

```text
CURRENT_SNAPSHOT_20260924
```

否则不得自动注入后续日期。

## 7. 完成状态

```text
V4_08_B2_CURRENT_SNAPSHOT_SCOPED_AMENDMENT_PROMOTED
```

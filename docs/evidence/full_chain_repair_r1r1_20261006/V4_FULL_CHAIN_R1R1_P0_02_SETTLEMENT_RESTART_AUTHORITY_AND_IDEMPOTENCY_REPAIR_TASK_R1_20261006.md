# V4 Full-Chain R1R1｜P0-02 Settlement Restart Authority + Queue Exact Idempotency 定点修复任务卡 R1｜2026-10-06

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 执行基线: `efe2d0c5f2b0d94878929120521fa48982e3cf56`
- 性质: P0-02 窄修复；禁止返工其他六个 PASS 项

## 1. Freeze

```text
P0-01 = PASS_KEEP
P1-03 = PASS_KEEP
P1-04 = PASS_KEEP
P1-05 = PASS_KEEP
P1-06 = PASS_KEEP
P2-07 = PASS_KEEP
```

本轮只修 P0-02 residual。

## 2. 修复 A｜Restart 必须 exact-read activation_head

删除/替换以下 selector 语义：

```python
SELECT payload,digest FROM facts WHERE kind='activation'
rows[-1]
```

正式流程：

```text
SELECT authority_id
FROM activation_head
WHERE singleton=1
```

必须 exactly one row。

再：

```text
SELECT payload,digest
FROM facts
WHERE kind='activation'
AND id=:authority_id
```

并校验：
- activation fact 存在且唯一
- payload digest exact
- payload.authority_id == activation_head.authority_id
- authority_binding exact bytes/size/sha
- external acceptance exact
- grant exact
- runtime dependency = accepted V5 successor
- dependency_set_digest exact
- storage identity exact

禁止：
`rows[-1] / MAX(rowid) / created_at max / mtime / latest glob / filename sort`

多 activation 合法场景必须支持：

```text
facts: A, B
activation_head: B
restart selects B
```

旧 A 保留历史，不删除。

若 head 缺失、head target fact 缺失、digest 错、binding 错，一律 fail closed。

## 3. 修复 B｜Queue exact idempotency

`enqueue()` 当前 `INSERT OR IGNORE` 后必须 exact readback。

至少比较：

```text
queue_key
evaluation_source_digest
due_kind
due_id
```

同时重新从 due/enrollment 计算 frozen queue identity：

```text
namespace
model_contract_id
state_lineage_id
enrollment_id
horizon
due_trade_date
outcome_contract_id
```

与 queue_key 一致。

相同 => idempotent retry。

不同 => `QUEUE_IDEMPOTENCY_CONFLICT`。

不得 silent ignore。

优先只改 application layer；若现有 schema 足够，不新增 migration。

## 4. Required tests

必须新增：

```text
A01 activations A/B + head=B -> select B
A02 activations A/B + head=A -> select A
A03 activation facts exist but head missing -> reject
A04 head target activation fact missing -> reject
A05 activation digest corrupt -> reject
A06 authority binding wrong -> reject

Q01 same exact enqueue retry -> same row
Q02 same queue PK but different due_id -> reject
Q03 same queue PK but different due_kind -> reject
Q04 recomputed queue identity mismatch -> reject
Q05 corrected source digest -> new evaluation revision remains valid
```

重跑已有：
- settlement queue suite
- two-connection CAS
- V3 obligation rejection
- V5 restart-after-stop
- publication rollback
- unknown due calendar extension
- P0-01 capability tests
- P1-03 DB-integrity tests

## 5. Protected State

必须保持：

```text
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
Production = false
Focus = false
Default UI cutover = false
FEP_PRODUCTION = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
V4_16..V4_22 formal Accepted Head = absent
```

## 6. A08 不得在本任务关闭

```text
A08_CURRENT_RUNTIME = OPEN_EXTERNAL_REAUDIT
```

保持原状态。

P0-02 修完后，如果 A08 仍 OPEN：

```text
PURE_CORE_STOCK / R25 / First Real Shadow
继续 WAIT/BLOCK
```

这是正确 fail-closed。

## 7. Evidence

输出目录建议：

```text
reports/full_chain_repair_r1r1_20261006/
```

至少：
- ENTRY_BASELINE.json
- ACTIVATION_HEAD_SELECTION_PROOF.json
- QUEUE_IDEMPOTENCY_PROOF.json
- NEGATIVE_MATRIX.json
- TARGETED_TEST_SUMMARY.json
- PASS_KEEP_READBACK.json
- PROTECTED_STATE_READBACK.json
- CANDIDATE_SEAL.json
- COMPLETION_REPORT.md

## 8. 成功状态

只有全部通过才允许：

```text
P0_02_R1R1 =
CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

不得自报：
`FULL_CHAIN_EXTERNAL_PASS / FIRST_REAL_SHADOW_AUTHORIZED / PRODUCTION_READY`

下一步：独立定点验收 P0-02。

**文档结束**

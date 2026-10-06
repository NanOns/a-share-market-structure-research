# V4 Full-Chain R1R1｜P0-02 最终独立外部验收审计 R1｜2026-10-06

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 修复任务基线: `efe2d0c5f2b0d94878929120521fa48982e3cf56`
- 候选提交: `9923897d1a9288a2fab4736b79aa24fee4f6a3f8`
- 当前远端 HEAD: `b7ca247745976aa390387a0701601b00ac0d8498`
- 任务卡: `V4_FULL_CHAIN_R1R1_P0_02_SETTLEMENT_RESTART_AUTHORITY_AND_IDEMPOTENCY_REPAIR_TASK_R1_20261006.md`

## 1. 唯一结论

```text
P0_02_R1R1_FINAL_EXTERNAL_AUDIT = PASS

P0-01 = PASS_KEEP
P0-02 = PASS
P1-03 = PASS_KEEP
P1-04 = PASS_KEEP
P1-05 = PASS_KEEP
P1-06 = PASS_KEEP
P2-07 = PASS_KEEP

FULL_CHAIN_SEVEN_REPAIR = EXTERNAL_ENGINEERING_PASS_7_OF_7

FIRST_REAL_SHADOW_AUTHORIZED = false
PRODUCTION = false
FOCUS_CUTOVER = false
DEFAULT_UI_CUTOVER = false
```

七项全链路代码修复至此 7/7 工程外审关闭。

## 2. Remote publication

`b7ca247...` 相对候选 `9923897...` 只新增：

```text
reports/full_chain_repair_r1r1_20261006/GIT_PUBLICATION_RECEIPT.json
```

没有在 remote-readback 之后继续修改业务代码。

## 3. Activation restart authority

原 blocker：

```python
SELECT payload,digest FROM facts WHERE kind='activation'
rows[-1]
```

已替换为：

```text
activation_head(singleton=1)
→ exact authority_id
→ exact facts(kind='activation', id=authority_id)
```

并校验：

```text
exactly one head
exactly one target activation fact
activation fact digest
payload.authority_id
authority binding
external acceptance
grant authority id
V5 dependency digest
storage identity
environment identity
```

A01/A02 已证明：

```text
activation facts = [A,B]
head=B -> select B

activation facts = [A,B]
head=A -> select A
```

即 selector 服从 accepted head，不依赖插入顺序 / rowid / “最新文件”。

A03～A06 对 head 缺失、fact 缺失、digest corruption、wrong binding/identity 均 fail closed。

裁决：

```text
ACTIVATION_HEAD_SELECTION = PASS
```

## 4. Queue exact idempotency

`enqueue()` 现在执行：

```text
INSERT OR IGNORE
→ exact readback
→ compare:
   queue_key
   evaluation_source_digest
   due_kind
   due_id
→ reload frozen due/enrollment
→ recompute queue identity
```

冲突：

```text
QUEUE_IDEMPOTENCY_CONFLICT
```

Q01～Q05 覆盖：
- exact retry
- same PK / different due_id
- same PK / different due_kind
- recomputed frozen identity mismatch
- corrected evaluation source creates second evaluation revision

校正 source 仍保持：

```text
evaluation_revision = 2
first_observed_id = original result
two durable queue rows by different source digest
```

裁决：

```text
QUEUE_EXACT_IDEMPOTENCY = PASS
```

## 5. Tests

最终定点：

```text
103 passed
0 failed
0 skipped
0 introduced failures
```

入口回归：

```text
43 passed
1 inherited known debt
0 introduced failures
```

继承债务：

```text
tests.test_r25_packet::test_f12_valid_latest_decoy
```

与 P0-02 无关，保持单独审计跟踪。

## 6. PASS_KEEP

以下实现/合同保持原结论：

```text
P0-01
P1-03
P1-04
P1-05
P1-06
P2-07
```

P0-02 为刷新 exact dependency bindings 修改的共享 runtime 文件属于本任务合法范围，没有发现越权修改其他六项业务语义。

## 7. Protected State

保持：

```text
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
V4_16..V4_22 formal Accepted Head = absent
TDX = no write
```

## 8. 为什么仍不能启动 First Real Shadow

七项 repair 已关闭，但 Current Audit Head 仍有：

```text
A08_CURRENT_RUNTIME = OPEN_EXTERNAL_REAUDIT
affected capability = V4_09_N01_CURRENT_RUNTIME_PREWATCH
blocks_affected_capability_in_shadow = true
```

而 P0-01 已正确建立：

```text
PURE_CORE_STOCK
→ V4_09_N01_CURRENT_RUNTIME_PREWATCH
```

因此当前 runtime 应继续 fail closed。

这不是 P0-02 未修好，而是下一道独立治理门。

**最终状态：`P0_02_R1R1_FINAL_EXTERNAL_AUDIT = PASS`**

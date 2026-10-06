# V4 A08 Current Runtime Acceptance｜治理传播与 R25 Re-entry 任务卡 R1｜2026-10-06

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 执行基线: `b7ca247745976aa390387a0701601b00ac0d8498`
- 外部依据:
  - `V4_FULL_CHAIN_R1R1_P0_02_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md`
  - `V4_A08_CURRENT_RUNTIME_INDEPENDENT_EXTERNAL_REAUDIT_R1_20261006.md`

## 1. 任务性质

```text
NO V4-09 BUSINESS ALGORITHM REPAIR
NO PREWATCH RULE CHANGE
NO NEW MODEL/PARAMETER
NO PRODUCTION CUTOVER

TASK =
VERSIONED_GOVERNANCE_PROPAGATION_OF_A08_CURRENT_RUNTIME_EXTERNAL_PASS
```

目标是把已独立外审通过的 A08 current runtime 状态，版本化传播到机器可消费的 Current Audit / capability / runtime dependency 链。

## 2. Immutable / PASS_KEEP

不得覆盖或修改既有历史字节：

```text
data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json
config/v4_cross_stage_current_audit_authority_v3.json
config/v4_16_runtime_capability_resolution_v1.json
config/v4_16_runtime_dependencies_v5.json
config/v4_16_runtime_activation_authority_v4.json

P0-02 R1R1 candidate/final evidence
V4_09 historical accepted head/artifact
V4_09 current producer business logic
P0-01 / P1-03 / P1-04 / P1-05 / P1-06 / P2-07
```

若后续 runtime 必须引用新 dependency identity，一律建立 successor，不允许改写旧 V5/R4R3 作为历史。

## 3. 第一步：exact reference inventory

先扫描所有正式代码/config/test/evidence 中对以下对象的 exact 引用：

```text
V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3
V4_CROSS_STAGE_CURRENT_AUDIT_AUTHORITY_V3
v4_16_runtime_capability_resolution_v1
V4_16_RUNTIME_DEPENDENCIES_V5
v4_16_runtime_activation_authority_v4
v4_16_r25_packet_preflight_v3
scripts/v4_16_go_forward_shadow_runtime_r4r3.py
scripts/run_v4_16_settlement_v2.py
```

输出：

```text
STALE_REFERENCE_INVENTORY.json
```

必须区分：
- historical exact binding: 保留
- active R25/runtime path: 必须 successor
- tests/evidence only: 不作为 runtime authority

禁止全局字符串替换。

## 4. Current Audit Head successor

创建版本化 successor（建议 V4，实际编号按仓库 allocator/治理规则确认）：

```text
V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4
```

从 V3 复制全部 canonical issue，唯一允许的业务状态变化：

```text
A08_CURRENT_RUNTIME:
  current_state:
    OPEN_EXTERNAL_REAUDIT
    ->
    ACCEPTED_SCOPED

  blocks_affected_capability_in_shadow:
    true
    ->
    false

  blocks_shadow_entry:
    true
    ->
    false
```

保持：

```text
affected_capabilities = [V4_09_N01_CURRENT_RUNTIME_PREWATCH]
blocks_production_cutover_for_scope = true
blocks_v4_16_runtime_activation = false
formal_consumer_permission_granted_by_this_head = false
requires_real_observation_accumulation = false
```

`current_authority` / evidence bindings 必须 exact bind 新外部审计 MD。

A04 两个 blocker 不得改变：

```text
A04_H21_CONSUMER = ACCUMULATION_CONTINUES
A04_HISTORICAL_AMOUNT_A = BLOCKED_AFFECTED_SCOPE
```

其他 open audit 状态不得借机关闭。

## 5. Current Audit Authority successor

建立 successor authority（建议 V4）并 exact bind：
- Current Audit Head successor
- 本次独立外审
- predecessor V3 bytes
- stage current authority

继续声明：

```text
business_runtime_authority = false
automatic_stage_permission = false
production = false
focus = false
shadow = false
```

Audit registry 只移除 blocker，不直接 grant Shadow。

## 6. Capability Resolution successor

建立：

```text
v4_16_runtime_capability_resolution_v2
```

要求：

```text
PURE_CORE_STOCK
→ V4_09_N01_CURRENT_RUNTIME_PREWATCH
```

依赖图保持。

重新从新 Current Audit Head 投影 blocking issues。

预期：

```text
A08_CURRENT_RUNTIME 不再进入 effective shadow blockers
```

但：

```text
AMOUNT_A_H21_FORMAL_CONSUMER
HISTORICAL_AMOUNT_A_FORMAL_CONSUMER
```

仍分别受 A04 对应 blocker 约束。

必须保留：

```text
permission_granted = false
```

resolver 只是 admission/blocker evaluator。

## 7. Runtime dependency successor

因为 V5 与 P0-02 final audit 已 exact-bound，禁止改 V5。

创建：

```text
V4_16_RUNTIME_DEPENDENCIES_V6
```

至少 successor-bind：
- new current audit head/authority
- capability resolution v2
- unchanged accepted data / V4-15 / owner heads
- P0-02 accepted durable settlement contract
- P1-03 integrity migration
- R4R2 go-forward input authority
- existing source/clock/slot/storage contracts

所有 unchanged bindings 必须 byte-identical。

## 8. Runtime / settlement successor policy

当前 R4R3 settlement-only controller 明确要求：

```text
V4_16_RUNTIME_DEPENDENCIES_V5
```

不得为了 V6 直接改写已经审计通过的 R4R3 bytes。

若 V6 需要新的 active runtime：
- 创建 R4R4 或等价 successor；
- 新启动/新 activation 使用 V6；
- 已有 V5 obligation 仍由历史 V5/R4R3 settlement path 可恢复；
- 不得让 successor 使既存 settlement obligations 失去可结算性。

如果仓库尚无真实 V5 obligations：

```text
REAL_SHADOW_OBSERVATIONS=0
```

也不能删除 historical restart path。

## 9. Activation / R25 packet successor

创建 versioned successors，而不是覆盖：

```text
runtime activation authority
R25 packet preflight
R25 packet builder/validator
```

新的 disabled activation candidate 必须反映：

```text
A08_CURRENT_RUNTIME no longer a shadow capability blocker
```

但仍：

```text
runtime_authorized = false
real_shadow_authorized = false
production = false
focus = false
V4_16 = false
```

直到新的 R25 external activation acceptance 明确授予。

## 10. Required tests

至少验证：

### A08 propagation
```text
new head exact binds external audit
A08 current_state = ACCEPTED_SCOPED
A08 shadow blocker = false
A08 production blocker = true
```

### Capability
```text
PURE_CORE_STOCK:
  no A08 blocker

AMOUNT_A_H21_FORMAL_CONSUMER:
  still blocked by A04_H21_CONSUMER

HISTORICAL_AMOUNT_A_FORMAL_CONSUMER:
  still blocked by A04_HISTORICAL_AMOUNT_A
```

### Fail closed
- unknown newly blocking issue
- stale V3 head fed to V2 resolver
- mismatched head sha
- stale resolver in V6 dependencies
- V5 grant passed to V6 controller
- V6 grant passed to V5 historical controller
- external audit binding tamper

### PASS_KEEP
- P0-02 restart A01/A02
- queue Q01/Q05
- P1-03 direct DB integrity
- V4-09 current business vectors
- immutable historical V4-09 artifact

## 11. Protected State

必须继续：

```text
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

FIRST_REAL_SHADOW_AUTHORIZED = false
runtime_authorized = false
real_shadow_authorized = false
production = false
focus = false

FEP_PRODUCTION = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
```

不得创建 V4_16 formal Accepted Head。

## 12. Completion evidence

建议：

```text
reports/a08_current_runtime_propagation_20261006/
  ENTRY_BASELINE.json
  STALE_REFERENCE_INVENTORY.json
  A08_HEAD_SUCCESSOR_DIFF.json
  CAPABILITY_RESOLUTION_PROOF.json
  DEPENDENCY_SUCCESSOR_PROOF.json
  HISTORICAL_V5_COMPATIBILITY_PROOF.json
  NEGATIVE_MATRIX.json
  TARGETED_TEST_SUMMARY.json
  PROTECTED_STATE_READBACK.json
  CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

## 13. 成功状态

只能自报：

```text
A08_CURRENT_RUNTIME_PROPAGATION =
CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

R25_REENTRY =
READY_FOR_PACKET_REBUILD_OR_EXTERNAL_ACTIVATION_AUDIT
```

不得自报：

```text
FIRST_REAL_SHADOW_PASS
PRODUCTION_READY
V4_16_ACCEPTED
```

完成后交回独立审计。

**文档结束**

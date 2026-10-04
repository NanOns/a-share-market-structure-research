# DM01-R4R1｜PIT Lineage + Real Forward Evidence Repair Independent External Audit R1｜2026-10-05

## 0. Audit Target
Repository: `NanOns/a-share-market-structure-research`
Branch: `codex/v4-system-reform`
Baseline: `862a59c397f1aff1f58acd372ec9048d7b9c508f`
Audited HEAD: `54a214167cfd4414901d2002b0a3cf5da45f4e36`
Tested source: `f664d13a83260eae959f851fc5d8723d2eb59416`
Tested tag: `codex/dm01-r4r1-pit-lineage-tested-source-20261005`

## 1. Unique External Decision

```text
DM01_R4R1_EXTERNAL_AUDIT = PARTIAL_PASS_R4R2_REQUIRED

DM01_R4_LINEAGE_COMPOSITION = PASS_EXTERNAL
DM01_R4_REAL_FORWARD_EVIDENCE_GATE = PASS_EXTERNAL
DM01_R4_FIRST_AVAILABILITY_SEMANTICS = PASS_EXTERNAL
DM01_R4_PROMOTED_HEAD_LINEAGE = PASS_EXTERNAL

DM01_R4_CALENDAR_AUTHORITY_DESIGN = PASS_KEEP
DM01_R4_CURRENT_V2_PARENT_ROLLOVER = PASS_KEEP
DM01_R4_ALL_NINE_DAILY_WIRING = PASS_KEEP
DM01_R4_ROUTINE_V2_PROMOTION_CORE = PASS_KEEP
DM01_R4_FUTURE_SESSION_WAIT_GATE = PASS_KEEP
DM01_R4_TESTED_SOURCE_GOVERNANCE = PASS
DM01_R4_PROTECTED_STATE = PASS
DM01_R4_CLEAN_REGRESSION = PASS_SCOPED_NO_NEW_FAILURES

R25_TARGET_SESSION_BINDING_VALIDATOR = PASS_CORE
R25_DAILY_INPUT_SCHEMA_BRIDGE_INTEGRATION = FAIL_P0
R25_PACKET_PREFLIGHT_BRIDGE_PARITY = FAIL_P0
R25_BRIDGE_PRODUCER_PATH = FAIL_P0

DM01_R4_GO_FORWARD_RUNTIME = BLOCKED_PENDING_R4R2_R25_BRIDGE_INTEGRATION
R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_TARGET_SESSION_PACKAGE = NOT_CREATED
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0

NEXT = DM01_R4R2_R25_TARGET_SESSION_BRIDGE_INTEGRATION_REPAIR
```

R4R1 不需要推倒重来。四个原 lineage P0 已真正修复；剩余问题是新 exact target-session PIT bridge 与既有 R25 daily-input / preflight 路径没有一起升级。

## 2. Original R4R1 P0s｜PASS

### Lineage composition
R4R1 已区分：
`TARGET_SESSION_PIT_OBSERVATION`、
`INHERITED_ACCEPTED_PARENT_RECONSTRUCTED`、
`DERIVED_FROM_MIXED_PARENT_AND_TARGET`、
`STATIC_ACCEPTED_AUTHORITY_KNOWN_BEFORE_TARGET`。

历史 period rows 保持 inherited bytes；mixed artifacts 使用
`MIXED_ACCEPTED_PARENT_PLUS_TARGET_PIT` 且 `AS_RECORDED=false`。

### Real forward evidence
`promote()` 已硬性要求：
`candidate.real_forward_evidence == true`。
simulation 不能冒充 real。

### First availability
same-day capture/receive 不再自动变成 first-availability proof。
当前 `accepted_first_availability_authorities=[]`，所以没有显式 accepted authority 时始终保持 false。

### Promoted head lineage
新 V2 head 不再整体写成纯 PIT，而是：
`knowledge_lineage=MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT`,
`AS_RECORDED=false`,
`first_available_at_target_proven=false`，
同时单独保存 target-session source / receipts / observation / real-forward evidence。

## 3. R25 Target Binding Validator｜PASS_CORE

`validate_r25_binding()` 会 exact-readback：
- parent / child Data Head
- candidate
- target trade date
- source manifest
- all-nine receipts
- target-session observation receipt
- parent/child digest
- component artifacts
- whole-head mixed lineage
- current accepted child head
- real-forward evidence
- accepted R4 envelope
- exact next session
- parent context
- independent cross-component postcheck

engineering bridge 不能授予 R25。

## 4. New P0｜Formal Daily-Input Contract Still Uses Old Schema

Runtime consumer `scripts/v4_16_go_forward_input_authority.py` 已新增：

```python
preview = exact_read(root, daily_binding)
require(isinstance(preview.get('target_session_pit_binding'), dict),
        'R25_EXACT_TARGET_SESSION_BINDING_REQUIRED')
validate_r25_binding(root, preview['target_session_pit_binding'])
```

但是正式合同 `config/v4_16_go_forward_input_authority_v1.json` 的 `required_fields` 仍没有：

`target_session_pit_binding`

因此形成：

```text
formal producer contract != runtime consumer contract
```

一个严格按 V1 合同生成的 daily input 仍可能被 runtime loader 拒绝。

```text
R25_DAILY_INPUT_SCHEMA_BRIDGE_INTEGRATION = FAIL_P0
```

不得原地篡改历史 accepted V1，应创建 versioned successor / additive accepted extension。

## 5. New P0｜Independent R25 Preflight Does Not Validate the Bridge

`scripts/validate_r25_preflight.py` 仍只检查：

```python
set(contract['required_fields']) <= daily.keys()
```

它没有要求 `target_session_pit_binding`，也没有调用 exact bridge validator。

于是未来可能出现：

```text
R25 independent preflight
→ PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

actual GoForwardInputAuthority
→ R25_EXACT_TARGET_SESSION_BINDING_REQUIRED
```

这违反“独立 preflight 必须覆盖真实启动 admission”的原则。

```text
R25_PACKET_PREFLIGHT_BRIDGE_PARITY = FAIL_P0
```

## 6. New P0｜No Formal Bridge Producer Bound to R25 Packet Path

R4R1 当前有：
- pure validator
- engineering bridge fixture

但尚没有正式 production path 将：

```text
promoted V2 target-session evidence
→ DM01_R25_TARGET_SESSION_PIT_BINDING_R4R1_V1
→ daily_input.target_session_pit_binding
→ R25 packet/preflight
```

完整串起来。

现有 `tests/test_r25_packet.py` vector 也没有该字段。

因此 bridge 目前还是“validator + engineering fixture”，不是正式 producer→daily input→preflight→runtime consumer 链。

```text
R25_BRIDGE_PRODUCER_PATH = FAIL_P0
```

## 7. Regression Gap

R4R1 scoped regression覆盖 `tests/v4_dm01_r4` 和 `tests/v4_dm01_r4r1`，
但没有包含 `tests/test_r25_packet.py`，
尽管 R4R1 改动了 `scripts/v4_16_go_forward_input_authority.py` 并新增 R25 admission 条件。

R4R2 必须把 R25 suite 纳入 exact tested-source regression。

## 8. Tested Source / Protected State

Tag 精确指向 tested source：
`f664d13a83260eae959f851fc5d8723d2eb59416`。

当前 HEAD 只比 tested source 多 1 个 evidence closure commit。

`V4_STAGE_ACCEPTED_HEAD` 与 baseline byte-identical。
`V4_DATA_ACCEPTED_HEAD` 与 baseline byte-identical。

没有创建 real target package、real Shadow DB 或 real observation。

## 9. Regression

```text
total = 2021
passed = 1992
failed = 26
skipped = 3
errors = 0
introduced_failures = []

R4 passed = 25
R4R1 passed = 15
```

26 个失败与 baseline 完全一致。

另有一个独立 HTTP/DuckDB file-lock reproducibility flake，保持 nonblocking independent debt，不归因于 DM01 numerical runtime。

## 10. PASS_KEEP Boundary for R4R2

禁止重开：
- lineage composition
- real_forward_evidence gate
- first-availability semantics
- mixed whole-head lineage
- calendar authority
- current V2 parent
- all-nine wiring
- R3/R3_3 kernels
- component/cross postchecks
- CAS promotion
- future WAIT
- Stage/Data protected state
- Production/Shadow/Focus=false

## 11. Required R4R2 Scope

只修：
1. versioned REAL daily-input schema requires `target_session_pit_binding`;
2. formal bridge producer;
3. daily input exact bridge binding;
4. independent R25 preflight bridge validation;
5. preflight/runtime exact contract parity;
6. R25 packet positive/negative vectors;
7. no real packet before accepted target-session input exists.

## 12. Current State

```text
DM01_R4R1 = LINEAGE_REPAIR_PASS_EXTERNAL_SCOPED
DM01_R4 = NOT_YET_FINAL_EXTERNAL_ACCEPTED_RUNTIME

R25 = WAIT_ACCEPTED_DAILY_INPUT
REAL_TARGET_SESSION_PACKAGE = NOT_CREATED
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0

NEXT = DM01_R4R2_R25_TARGET_SESSION_BRIDGE_INTEGRATION_REPAIR
```

# V4-11 R5 独立外部验收报告 R1｜2026-10-02

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计远端 HEAD：** `1c46d6681ba1d0540551bcc0f75b35c545ff2769`  
**R5 implementation / clean tested commit：** `a8635c6802dc31e3c879207cd470bd63021e35ca`  
**父 Stage Head：** `V4_00_TO_V4_10_ACCEPTED`  
**Data Head：** `2026-09-30`

# 1. 唯一总裁决

```text
V4_11_R5_EXTERNAL_ACCEPTANCE =
PASS_CAPABILITY_SCOPED_ENGINEERING

R5A_OWNER_INPUT_AUTHORITY = PASS
R5B_D2_SEALED_OWNER_BRIDGE = PASS_ENGINEERING
STATE_EVENT_V1 = PASS_ENGINEERING

LAUNCH_CONFIRM =
ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY

RECOVERY_TURN =
ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY

STRONG_PULLBACK =
DIAGNOSTIC_ONLY_NOT_FORMAL

TREND_CONTINUE =
DIAGNOSTIC_ONLY_NOT_FORMAL

HISTORICAL_AS_RECORDED_EVENT_EVIDENCE =
NOT_PROVEN

EVENT_EVIDENCE =
RECONSTRUCTED_LEFT_CENSORED

FULL_D0_D1_D2_DAG =
NOT_IMPLEMENTED

V4_12_STRUCTURE_SUPPORT =
NOT_IMPLEMENTED

V4_11_ACCEPTED_HEAD_PROMOTION =
AUTHORIZED_WITH_EXACT_SCOPE

V4_STAGE_ACCEPTED_HEAD_PROMOTION =
AUTHORIZED_TO_V4_00_TO_V4_11_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
KEEP_2026_09_30

V4_12_STAGE_ENTRY =
AUTHORIZED_AFTER_PROMOTION_VALIDATOR_PASS

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

这是工程能力/阶段验收，不是收益有效性、生产投放或完整 D0/D1/D2 DAG 验收。

# 2. 提交与 evidence seal

R5 实现提交：

```text
a8635c6802dc31e3c879207cd470bd63021e35ca
fix(v4): restore accepted owner input authority and rebuild R5 D2 events
```

最终 handoff：

```text
1c46d6681ba1d0540551bcc0f75b35c545ff2769
docs(v4): seal R5 clean regression and external re-audit handoff
```

后一提交只新增 handoff、manifest、clean/full-repo evidence，没有业务源码修改。当前 GitHub 无额外 combined-status/workflow-run，因此本报告不声称 CI 背书。

# 3. R5A Owner Input Authority｜PASS

2026-09-28 对已接受 V4-07 / V4-09 做 exact parity：

```text
row_scope                 = 5222
business_mismatches       = 0
quality_mismatches        = 0
unknown_reason_mismatches = 0
formal_t_minus_1_known    = 0
```

证明 R5 target-date adapter 能重放 accepted `BASE_SEED_V1` 与 `STOCK_PREWATCH_V1`，而不是另造语义。

正式 t-1 边界已恢复：

```text
close_t_minus_1 =
UNKNOWN(ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE)

ma20_t_minus_1 =
UNKNOWN(ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE)
```

9/29 两字段 UNKNOWN 共 10,446；9/30 共 10,448；formal known count 均为 0。R4 中 raw/adjusted bar → reconstructed t-1 → BASE_SEED 的越权路径已退出 formal chain。

`actual_bar` 恢复 accepted dated-status 三值语义：

```text
ACTUAL_TRADED -> TRUE
SUSPENDED     -> FALSE
unknown/conflict -> UNKNOWN
```

`price_identity_READY` 重新验证 canonical security_id、symbol、board、trade_date、security type、candidate publication identity 与 `historical_as_recorded_claim=false`；membership 不再无条件 TRUE。

独立 oracle：

```text
status = PASS
adapter_helpers_called_for_expected = false
accepted_owner_algorithms = true
formal_t_minus_1_known_count = 0
```

独立重新执行 accepted Core、Seed、PREWATCH、RPS、status 与 identity，不是 adapter 自证。

因此：

```text
R5A_OWNER_INPUT_AUTHORITY = PASS
```

# 4. R5B Sealed D2 Authority｜PASS

`sealed_owner_authority_r5` 对进入 D2 的：

```text
SEED
PREWATCH
core_price_damage
risk
delta3
suspended
CONFIRMED
scenario
```

分别绑定 R5A sealed owner publication、accepted dated status 与 frozen R4 D0，并校验 publication、producer、parameter、source-output digest、value、quality、date、universe。

禁止：

```text
serialized input self-assert authority
raw/calculation fallback
unsealed helper fallback
reconstructed-known 替代 owner UNKNOWN
```

独立 D2 owner-input oracle：

```text
status = PASS
rows = 10447
adapter_helpers_used_for_expected = false
```

8 类字段各检查 10,447 行，总 authority field checks = 83,576。

因此：

```text
R5B_D2_SEALED_OWNER_BRIDGE = PASS_ENGINEERING
```

# 5. V4-10 reducer 未被偷改

R5 adapter 对 accepted reducer/provenance 继续 AST 校验：

```text
normalized business AST exact = true
exact rule order = true
exact thresholds = true
```

只允许 candidate namespace、sealed-owner wiring、reconstructed knowledge timestamp、frozen R4 D0 admission 差异。

# 6. `current_v4_10_protected_gate = FAIL` 不是回归失败

clean receipt 中该字段为 FAIL，但源码明确要求：

```python
current_v10["checks"]["P19_protected"] == "FAIL"
```

否则抛出：

```text
HISTORY_OR_CURRENT_AUTHORITY_BOUNDARY_CHANGED
```

所以这是：

```text
EXPECTED_FAIL_CLOSED_HISTORICAL_AUTHORITY_BOUNDARY
```

而不是 V4-10 stage 损坏。不得为了“全绿”修改旧 protected binding。

# 7. D0 capability scope

9/30 frozen D0：

```text
overall TRUE/FALSE/UNKNOWN = 166 / 4671 / 387

LAUNCH_CONFIRM:
TRUE 124 / FALSE 4872 / UNKNOWN 228

RECOVERY_TURN:
TRUE 63 / FALSE 4769 / UNKNOWN 392

STRONG_PULLBACK:
UNKNOWN 5224

TREND_CONTINUE:
UNKNOWN 5224
```

因此只有 LAUNCH_CONFIRM / RECOVERY_TURN 可以进入正式 V4-11 capability map；Pullback/Trend 继续 diagnostic-only。

R4 scenario lineage 残留也已修正为真实 R4A sealed parent，并保留 R3B diagnostic seal。

# 8. D2 / STALE 结果

9/30：

```text
maturity:
CONFIRMED 135
PREWATCH  164
NONE      4925

final eligibility:
TRUE      117
FALSE     751
UNKNOWN   4356

freshness:
FRESH 868
STALE 4356
```

UNKNOWN/STALE 增加不是失败。R4 使用了未授权 t-1 信息；R5 删除非法能力后必须恢复 UNKNOWN。验收指标是 `CONTRACT_AUTHORITY_PARITY`，不是 UNKNOWN 最小化。

所有 STALE 均要求 required UNKNOWN + exact producer + exact publication + root cause，并硬检查：

```text
producer_wiring_missing = 0
unsealed_helper_source = 0
generic_coefficient_gate = 0
raw_reconstruction_fallback = 0
accepted_t_minus_1_known_count = 0
```

因此当前 STALE 是明确 capability limitation，不是接线未完成。

# 9. STATE_EVENT_V1｜PASS_ENGINEERING

9/30 effective events：

```text
NEW_CONFIRMED = 33
NONE          = 508
UNKNOWN       = 4683
```

Event quality：

```text
KNOWN                             = 541
UNKNOWN_CURRENT_D2_REQUIRED_FACTS = 4356
UNKNOWN_PRIOR_D2_REQUIRED_FACTS   = 327
```

验证：

```text
UNKNOWN/STALE prior != FALSE
UNKNOWN current D2 不产生确定性 NEW_CONFIRMED
same-day revision predecessor invariant = true
NEW_CONFIRMED 需要 valid prior-session state
```

所以：

```text
STATE_EVENT_V1 = PASS_ENGINEERING
```

但历史证据仍是：

```text
RECONSTRUCTED_LEFT_CENSORED
AS_RECORDED = false
```

不得声称 historical first-availability/PIT event 已证明。

# 10. R4 → R5 变化是修复结果

9/29：

```text
rows restored reconstructed-known t-1 -> accepted UNKNOWN = 5046
Seed value changed     = 365
Seed quality changed   = 1297
PREWATCH changed       = 3953
D2 business changed    = 3852
```

9/30：

```text
rows restored reconstructed-known t-1 -> accepted UNKNOWN = 5047
Seed value changed     = 459
Seed quality changed   = 1404
PREWATCH changed       = 3939
D2 business changed    = 3893
Event changed rows     = 3244
```

同时：

```text
D0_business_changed = false
thresholds_changed = false
t_minus_1_capability_expanded = false
```

说明 R5 是实质性 authority 修复，不是文案修补。

# 11. Clean checkout

```text
tested_commit =
a8635c6802dc31e3c879207cd470bd63021e35ca

2067 passed
2 skipped
0 failures
0 errors
new_deselects = []
```

并且：

```text
git clean before/after
protected heads unchanged
migrations 001–027
fresh disposable PostgreSQL only
temporary cluster cleaned
configured/production DB not used
```

R5 clean readback：

```text
parity rows      = 5222
owner input rows = 10447
prior D2 rows    = 5223
current D2 rows  = 5224
event rows       = 5224
```

全部 PASS。

# 12. Full repository collection

仍仅有既有：

```text
tests/upgrade_m14/test_online_batches.py
tests/upgrade_m2/test_api.py
```

分类：

```text
PREEXISTING_NON_MAINLINE_M14_M2_COLLECTION
```

对应源码相对 R5 baseline 未变，仓库也没有声称 full repository runtime PASS。

处理：

```text
KEEP_SEPARATE_NON_MAINLINE_AUDIT_ITEMS
```

不阻断 V4-11，不宣布已修复。

# 13. V4-11 Accepted Head 允许的精确 scope

```text
CONFIRMATION_LAUNCH_CONFIRM =
ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY

CONFIRMATION_RECOVERY_TURN =
ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY

CONFIRMATION_STRONG_PULLBACK =
DIAGNOSTIC_ONLY_NOT_FORMAL

CONFIRMATION_TREND_CONTINUE =
DIAGNOSTIC_ONLY_NOT_FORMAL

D2_SEALED_OWNER_BRIDGE =
ENGINEERING_ACCEPTED

STATE_EVENT_V1 =
ENGINEERING_ACCEPTED_RECONSTRUCTED_LEFT_CENSORED_SCOPE

HISTORICAL_AS_RECORDED_EVENT =
NOT_PROVEN

FULL_D0_D1_D2_DAG =
NOT_IMPLEMENTED

V4_12_STRUCTURE_SUPPORT =
NOT_IMPLEMENTED
```

禁止泛化成 FULL_CONFIRMATION / FULL_DAG / PRODUCTION_READY。

# 14. Heads

Promotion Validator PASS 后允许：

```text
V4_STAGE_ACCEPTED_HEAD:
V4_00_TO_V4_10_ACCEPTED
->
V4_00_TO_V4_11_ACCEPTED
```

同时：

```text
V4_DATA_ACCEPTED_HEAD = KEEP 2026-09-30
```

Stage Head 前进不是 Data Head 前进。

# 15. 下一阶段真实定义

当前最高合同 §78：

```text
V4-12 =
Structure / Anchor / Support
```

交付：

```text
D1 algorithms
coordinate rebasing
breakout
pullback
recovery
Anchor / support / acceptance
```

DAG 硬边界：

```text
D1 inputs = F0[t] + t-1 frozen Anchor/event
D1 must not read D2[t]
new Anchor created at t cannot self-confirm at t
earliest support/path use = t+1
```

# 16. 下一步授权

本次只授权：

```text
V4_11 Accepted Head Promotion
→ Stage Head = V4_00_TO_V4_11_ACCEPTED
→ V4_12 Structure / Anchor / Support Stage Entry
```

不得把 V4-12 runtime implementation 与未经复核的 promotion mutation 混在同一提交。

最终：

```text
V4_11_EXTERNAL_ACCEPTANCE =
PASS_CAPABILITY_SCOPED_ENGINEERING
```

# V4 R4 独立外部验收审计 R1｜2026-10-02

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计远端 HEAD：** `1dee36ae83fb63b6a7fe57e05ccb63bb1e0c5099`  
**R4 clean checkout tested commit：** `fc4d204012bca642d1b0beed7f2f098d6efea86c`  
**上一轮外审基线：** `65774de20108beafaa15c0b557b4cd2ee58edb29`  
**当前 Stage Head：** KEEP `V4_00_TO_V4_10_ACCEPTED`  
**当前 Data Head：** KEEP `2026-09-30`

---

# 1. 唯一总裁决

```text
V4_R4_EXTERNAL_ACCEPTANCE = BLOCKED_R5

V4_11_R4A_ADJUSTMENT_BASIS_PARITY =
PASS

V4_11_D0_CONFIRMATION =
PASS_SCOPED_FORMAL_CANDIDATE

LAUNCH_CONFIRM =
FORMAL_CANDIDATE_PASS

RECOVERY_TURN =
FORMAL_CANDIDATE_PASS

STRONG_PULLBACK =
DIAGNOSTIC_ONLY_KEEP

TREND_CONTINUE =
DIAGNOSTIC_ONLY_KEEP

V4_11_R4B_D2_UPSTREAM_OWNER_INPUT =
FAIL_P0

V4_11_R4B_D2_REDUCER_AST =
PASS_ENGINEERING

V4_11_R4B_EVENT_ENGINE_MECHANICS =
PASS_ENGINEERING_OUTPUT_REPLAY_REQUIRED

V4_11_ACCEPTED_HEAD =
NOT_AUTHORIZED

V4_12_RUNTIME =
NOT_AUTHORIZED
```

**本轮唯一新的主线 P0：**

```text
UNAUTHORIZED_T_MINUS_1_OWNER_INPUT_RECONSTRUCTION
```

R4 已经正确修复上一轮的 adjustment-basis P0；不得返工 R4A。

---

# 2. 当前提交与回归状态

当前远端 HEAD：

```text
1dee36ae83fb63b6a7fe57e05ccb63bb1e0c5099
```

R4 clean checkout 绑定：

```text
tested_commit = fc4d204012bca642d1b0beed7f2f098d6efea86c

2043 passed
2 skipped
0 failures
0 errors
```

`fc4d204... -> 1dee36a...` 仅新增 R4 handoff / clean evidence，不包含新的业务实现修改。

GitHub 当前：

```text
combined statuses = []
workflow runs = []
```

因此本次独立验收依据为仓库源码、accepted heads、versioned contracts、independent receipts 与静态交叉复核，不声称存在额外 CI 背书。

---

# 3. Full-repository collection blocker 的处置

R4 额外全仓 collection 仍存在两项既有问题：

```text
tests/upgrade_m14/test_online_batches.py
tests/upgrade_m2/test_api.py
```

仓库已经明确记录：

```text
BLOCKED_PREEXISTING_M14_M2_COLLECTION
full_repository_runtime_pass_claim = false
```

本次分类为：

```text
PREEXISTING_NON_V4_11_MAINLINE_AUDIT_ITEMS
```

它们不作为本次阻断 V4-11 的理由，也不得拿来掩盖本轮真正的 D2 owner-input P0。

---

# 4. R4A｜正式通过

上一轮 P0 是 R3 把：

```text
qfq_mul + qfq_add
```

错误作为 adjustment identity。

R4 已恢复已接受 V4-03 语义：

```text
adjustment_basis_id
=
price_basis + adjustment_source_revision
```

## 4.1 9/24 exact parity

`reports/v4_11_r4a/V4_03_EXACT_PARITY_R1.json`

```text
row_scope                 = 5222
Stock Core fields         = 39
business mismatches       = 0
quality mismatches        = 0
unknown-reason mismatches = 0
identity mismatches       = 0
numeric tolerance         = 1e-12
```

真实 coefficient-change pairs：

```text
13,844
```

证明：

```text
qfq_mul/qfq_add 改变
+
price_basis/revision 不变
=
仍可比较
```

## 4.2 独立边界

```text
same accepted basis + different affine coefficients
→ EVALUABLE

different price basis
→ MIXED_ADJUSTMENT_IDENTITY

different adjustment_source_revision
→ MIXED_ADJUSTMENT_IDENTITY

missing revision
→ ADJUSTMENT_UNKNOWN

unsupported adjustment
→ ADJUSTMENT_UNKNOWN
```

独立边界测试：

```text
9 passed
```

## 4.3 Target facts 独立算术复核

2026-09-29：

```text
universe = 5223
source slots = 141021
mismatches = 0
```

2026-09-30：

```text
universe = 5224
source slots = 141048
mismatches = 0
```

独立 verifier：

```text
producer_invoked_for_arithmetic = false
```

并明确：

```text
provider_unavailable_claim = false
current_local_file_absence_used_as_provider_evidence = false
missing_fact_cast_to_false = false
```

## 4.4 完整 source-window oracle

```text
2026-09-29 source slots = 673767
2026-09-30 source slots = 679120
adapter_helpers_invoked = false
status = PASS
```

### R4A 裁决

```text
V4_11_R4A = PASS
```

以后不得再返工 R4A adjustment-basis 主线，除非出现新的独立证据。

---

# 5. D0 Confirmation｜Scoped PASS

9/30 D0：

```text
overall:
TRUE     = 166
FALSE    = 4671
UNKNOWN  = 387

LAUNCH_CONFIRM:
TRUE     = 124
FALSE    = 4872
UNKNOWN  = 228

RECOVERY_TURN:
TRUE     = 63
FALSE    = 4769
UNKNOWN  = 392
```

继续保留：

```text
STRONG_PULLBACK = DIAGNOSTIC_ONLY
TREND_CONTINUE  = DIAGNOSTIC_ONLY
```

### D0 裁决

```text
V4_11_D0_CONFIRMATION =
PASS_SCOPED_FORMAL_CANDIDATE
```

正式能力只包括：

```text
LAUNCH_CONFIRM
RECOVERY_TURN
```

---

# 6. P0｜D2 upstream 越过已接受 V4-07 owner-input authority

当前：

```text
src/v4/confirmation_d2_upstream_r4.py
```

执行：

```python
previous_factors =
    compute_core(observations[:-1], sid, asof=t_minus_1)

previous_close =
    observations[-2].bar.close

seedfacts["close_t_minus_1"] =
    previous_close

seedfacts["ma20_t_minus_1"] =
    previous_factors["ma20"].value
```

随后输入：

```text
BASE_SEED_V1._eval
```

这些 facts 会参与：

```text
reclaim_before
reclaim_now
reclaim
trend_early
S2
base_seed_state
```

所以不是 metadata。

---

# 7. 已接受 V4-07 明确禁止这样做

已外部接受的：

```text
src/v4/base_seed.py
```

明确冻结：

```python
# R4.1 Core Profile has no accepted t-1 close/MA20 fields.
# Do not rebuild them from raw bars.

facts["close_t_minus_1"] =
    UNKNOWN("ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE")

facts["ma20_t_minus_1"] =
    UNKNOWN("ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE")
```

这是正式 source-authority boundary。

---

# 8. A02 amendment 没有授权 t-1 扩权

后续 A02 scoped acceptance 对 V4-07 的 amendment 仍绑定同一：

```text
src/v4/base_seed.py
sha256 =
0fa1b11f0d342731cf3658379f6ae14982b3861509daf2e949e197a722aac1d7
```

并声明：

```text
unchanged algorithms / parameters
```

A02 补的是 Accepted RPS history / downstream replay，不是新的 accepted t-1 close/MA20 producer。

因此不存在正式授权：

```text
raw/adjusted bars
→ reconstruct close_t_minus_1
→ reconstruct ma20_t_minus_1
→ feed BASE_SEED_V1 formally
```

---

# 9. 为什么这是 P0

R4B 自己声明：

```text
business_rules =
EXACT_ACCEPTED_V4_10_AST_EXTRACT;
THRESHOLDS_UNCHANGED

exact_owner_runtime includes:
src/v4/base_seed.py

admission_changes_only:
- VERSIONED_REAL_CANDIDATE_MODE
- SEALED_SOURCE_FILE_LEDGER
- CONFIRMED_CANDIDATE_CAPABILITY
- ACTUAL_RECONSTRUCTED_KNOWLEDGE_TIMESTAMP
- CANDIDATE_IDENTITIES
```

其中没有：

```text
NEW_T_MINUS_1_BASE_SEED_SOURCE_CAPABILITY
```

所以当前属于：

```text
OWNER_INPUT_AUTHORITY_DRIFT
```

不是普通 admission adaptation。

---

# 10. 同轮必须收紧的两个 owner-input 语义

## 10.1 actual_bar

accepted V4-07：

```text
ACTUAL_TRADED -> TRUE
SUSPENDED     -> FALSE
other/unknown -> UNKNOWN
```

R4 adapter 当前更接近以 raw bar presence 赋值。

R5 必须恢复 formal dated-status authority。

## 10.2 price_identity_READY

accepted V4-07 `_identity_fact` 会验证：

```text
security_id
symbol
board
trade_date
profile publication identity
historical_as_recorded_claim
```

R4 adapter 当前近似：

```text
target slot has_actual_bar
```

这把 identity authority 压缩成了 bar readiness。

R5 必须恢复 versioned、source-bound、可独立复核的 identity fact。

这两项先归类：

```text
P1_OWNER_INPUT_PARITY_REQUIRED
```

与 t-1 P0 同一轮修复，不另开阶段。

---

# 11. 当前 D2 / Event 数量不能直接接受

当前 R4 D2：

```text
final eligibility:
TRUE    = 501
FALSE   = 3113
UNKNOWN = 1610

freshness:
FRESH = 3614
STALE = 1610
```

当前 Event：

```text
NEW_CONFIRMED             = 88
CONFIRMATION_INVALIDATED  = 1
NONE                      = 3498
UNKNOWN                   = 1637
```

V4-10 reducer AST、规则顺序和阈值本身已经复核通过。

问题在 reducer 上游：

```text
SEED / PREWATCH owner inputs
```

t-1 reconstructed facts 可以改变：

```text
BASE_SEED
→ PREWATCH
→ D2
→ Event
```

所以这些数量必须在 owner-input 修正后重放。

---

# 12. Event Engine 本体处置

R4 Event mechanics 已证明：

```text
UNKNOWN/stale prior != FALSE
same-day revision predecessor invariant = true
NEW_CONFIRMED semantics invariant = true
prior evidence = reconstructed / left-censored
AS_RECORDED = false
```

因此：

```text
EVENT_ENGINE_MECHANICS = PASS_ENGINEERING
EVENT_OUTPUT_REPLAY_REQUIRED
```

不重写 Event 核心规则。

---

# 13. P1｜Scenario matrix lineage 残留

当前 R4 capability matrix 对 LAUNCH/RECOVERY 仍写：

```text
reason = R3A_SEALED_TARGET_FACT_SET
```

实际父生产者已经是 R4A。

这是 lineage metadata defect，不改变 D0 业务结果，但不能进入最终 Accepted Head。

R5B 必须绑定真实 R4A seal 的 path / sha256 / contract_id / status。

---

# 14. 本轮不重开的内容

全部 KEEP：

```text
V4-10 Accepted
R4A adjustment-basis parity
R4A target-fact source arithmetic
D0 LAUNCH/RECOVERY detector
R3B Pullback/Trend capability scoping
A02 scoped amendments
A05 scoped amendment
A04 go-forward producer scope
A03/A06/A07/Owner/Reader consolidation
V4-10 reducer AST
Event predicate mechanics
```

---

# 15. 下一轮只需要两张卡

```text
R5A
V4-07 / V4-09 Owner Input Authority Parity Repair

R5B
D2 + Event Rebuild + Final Capability Closure
```

---

# 16. Heads 与权限

```text
V4_DATA_ACCEPTED_HEAD =
KEEP 2026-09-30

V4_STAGE_ACCEPTED_HEAD =
KEEP V4_00_TO_V4_10_ACCEPTED

V4_11_ACCEPTED_HEAD =
NOT AUTHORIZED

V4_12_RUNTIME =
NOT AUTHORIZED

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

---

# 17. 最终结论

```text
V4_R4_EXTERNAL_ACCEPTANCE = BLOCKED_R5

R4A = PASS
D0 LAUNCH/RECOVERY = PASS_SCOPED
D2 upstream = BLOCKED_P0_OWNER_INPUT_AUTHORITY_DRIFT
D2 reducer = PASS_ENGINEERING
Event mechanics = PASS_ENGINEERING
Event outputs = REPLAY_REQUIRED
```

R5 外审通过后，才可以另发：

```text
V4-11 Accepted Head Promotion
→ V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
→ V4-12 Stage Entry
```

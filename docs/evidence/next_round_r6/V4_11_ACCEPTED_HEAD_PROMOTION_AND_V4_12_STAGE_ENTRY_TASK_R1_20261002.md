# V4-11 Accepted Head Promotion + V4-12 Structure / Anchor / Support 入场任务卡 R1｜2026-10-02

**前置外部裁决：** `V4_11_EXTERNAL_ACCEPTANCE_PASS_R5_CAPABILITY_SCOPED_ENGINEERING`  
**审计 sealed HEAD：** `1c46d6681ba1d0540551bcc0f75b35c545ff2769`  
**Accepted implementation：** `a8635c6802dc31e3c879207cd470bd63021e35ca`  
**父阶段：** `V4_00_TO_V4_10_ACCEPTED`  
**任务性质：** Promotion + V4-12 Stage Entry only  
**禁止：** 本任务实现 V4-12 runtime

# 1. 唯一执行顺序

```text
Step 1  读取并验证 R5 独立外部验收
Step 2  生成 V4_11_ACCEPTED_HEAD candidate
Step 3  独立 V4-11 Promotion Validator
Step 4  Validator PASS 后写正式 V4_11_ACCEPTED_HEAD
Step 5  更新 V4_STAGE_ACCEPTED_HEAD
        V4_00_TO_V4_10_ACCEPTED
        ->
        V4_00_TO_V4_11_ACCEPTED
Step 6  生成 V4-12 Structure / Anchor / Support Stage Entry
Step 7  独立 post-promotion readback
Step 8  commit + push
Step 9  STOP
```

禁止把 Accepted Head mutation 与 V4-12 未审计业务实现混在同一提交。

# 2. V4-11 Accepted Head

创建：

```text
data/v4/V4_11_ACCEPTED_HEAD.json
```

至少：

```text
contract_id =
V4_11_ACCEPTED_HEAD_V1

stage =
V4-11

status =
ENGINEERING_PASS_CAPABILITY_SCOPED

external_acceptance =
EXTERNALLY_ACCEPTED

external_acceptance_decision =
V4_11_EXTERNAL_ACCEPTANCE_PASS_R5_CAPABILITY_SCOPED_ENGINEERING

implementation_commit =
a8635c6802dc31e3c879207cd470bd63021e35ca

audited_sealed_head =
1c46d6681ba1d0540551bcc0f75b35c545ff2769
```

# 3. Capability map 必须精确

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

禁止 promotion 时把 scoped capability 扩大成 ALL_CONFIRMATION_FORMAL / FULL_DAG_PASS。

# 4. 必须精确绑定的 evidence

至少绑定：

```text
reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json

reports/v4_11_r5a/V4_07_V4_09_EXACT_OWNER_PARITY.json
reports/v4_11_r5a/INDEPENDENT_OWNER_INPUT_ORACLE.json
reports/v4_11_r5a/OWNER_INPUT_AUTHORITY_MATRIX.json
reports/v4_11_r5a/R5A_SEALED_OWNER_PRODUCER_SET.json

reports/v4_11_r5/V4_11_R5_D2_ADAPTER_AST_EVIDENCE.json
reports/v4_11_r5/INDEPENDENT_D2_OWNER_INPUT_ORACLE.json
reports/v4_11_r5/RESIDUAL_UNKNOWN_ATTRIBUTION.json
reports/v4_11_r5/R4_TO_R5_BUSINESS_DIFF.json
reports/v4_11_r5/V4_11_R5_D2_READBACK.json
reports/v4_11_r5/V4_11_R5_EVENT_REPLAY.json
reports/v4_11_r5/V4_11_R5_SCENARIO_CAPABILITY_MATRIX.json
reports/v4_11_r5/V4_11_R5_CLEAN_CHECKOUT.json
reports/v4_11_r5/FULL_REPOSITORY_COLLECTION.json
reports/v4_11_r5/V4_11_ACCEPTANCE_CANDIDATE.json

docs/evidence/next_round_r6/
V4_11_R5_INDEPENDENT_EXTERNAL_ACCEPTANCE_R1_20261002.md
```

# 5. Parent exact binding

父阶段：

```text
data/v4/V4_10_ACCEPTED_HEAD.json
```

当前 Global Stage Head 必须：

```text
accepted_stage_range =
V4_00_TO_V4_10_ACCEPTED
```

禁止从过期 Stage Head promotion。

# 6. Data Head 必须 KEEP

Promotion 前后：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

exact unchanged，且：

```text
accepted_trade_date =
2026-09-30
```

禁止把 Stage Head 晋升包装成 Data Head 更新。

# 7. R5 promotion hard gates

Promotion Validator 至少重新检查：

```text
P01 R5A parity row_scope = 5222
P02 R5A business mismatch = 0
P03 R5A quality mismatch = 0
P04 R5A UNKNOWN-reason mismatch = 0
P05 formal t-1 known count = 0
P06 independent owner oracle PASS
P07 sealed owner publication exact
P08 independent D2 owner-input oracle PASS
P09 D2 owner input count = 10447 per field
P10 raw reconstruction fallback = 0
P11 unsealed helper source = 0
P12 producer wiring missing = 0
P13 generic coefficient gate = 0
P14 R4A frozen D0 exact
P15 LAUNCH/RECOVERY scope exact
P16 Pullback/Trend remain diagnostic-only
P17 reducer normalized AST exact
P18 reducer thresholds/rule order exact
P19 Event UNKNOWN safety PASS
P20 Event evidence remains reconstructed-left-censored
```

任何一项 FAIL，禁止 promotion。

# 8. Clean regression gates

绑定：

```text
tested_commit =
a8635c6802dc31e3c879207cd470bd63021e35ca

2067 passed
2 skipped
0 failures
0 errors
new_deselects = []
```

并重新 readback：

```text
R5 parity rows = 5222
owner input rows = 10447
prior rows = 5223
current rows = 5224
event rows = 5224
```

# 9. V4-10 protected gate 特殊语义

不得把：

```text
current_v4_10_protected_gate = FAIL
```

错误解释为 V4-10 stage failure。

必须验证其仍等价于：

```text
EXPECTED_FAIL_CLOSED_HISTORICAL_AUTHORITY_BOUNDARY
```

并与 `scripts/verify_v4_r5_clean_checkout.py` frozen expectation 一致。

禁止为了报告“全绿”修改旧 protected binding。

# 10. M14 / M2

保持：

```text
R5_FULL_REPOSITORY_PREEXISTING_M14_COLLECTION
R5_FULL_REPOSITORY_PREEXISTING_M2_UNTRACKED_PUBLICATION_DEPENDENCY
```

分类：

```text
PREEXISTING_NON_MAINLINE
```

要求：

```text
source unchanged
resolution_claim = false
full_repository_runtime_pass_claim = false
```

不阻断 V4-11 promotion，也不得在本任务偷偷关闭。

# 11. Promotion Validator

新增 versioned read-only validator，建议至少：

```text
P01 schema/stage/external decision
P02 parent V4-10 exact
P03 implementation commit exact
P04 audited sealed head descendant
P05 external acceptance doc exact
P06 R4A seal exact
P07 R5A parity exact
P08 owner oracle exact
P09 R5A seal exact
P10 D2 AST evidence exact
P11 D2 owner oracle exact
P12 residual attribution exact
P13 business diff exact
P14 D2 readback exact
P15 Event replay exact
P16 capability matrix exact
P17 clean checkout exact
P18 Data Head unchanged
P19 Dev Baseline unchanged
P20 PIT membership accepted head unchanged
P21 scoped accepted heads unchanged
P22 permissions all false
P23 capability map exact
P24 historical AS_RECORDED not overclaimed
P25 diagnostic scenarios not promoted
P26 M14/M2 stay separate unresolved
P27 idempotent promotion
P28 clean detached validation
```

Validator 本身 versioned + hash-bound。

# 12. Global Stage Head

只有 Validator PASS 后：

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

从：

```text
V4_00_TO_V4_10_ACCEPTED
```

推进：

```text
V4_00_TO_V4_11_ACCEPTED
```

新增至少：

```text
v4_11_binding
v4_11_status
v4_11_external_acceptance
v4_11_capabilities
v4_12_entry
```

必须保留此前所有 accepted/scoped/open 字段，禁止重建缩水版 Stage Head。

# 13. 权限继续关闭

Accepted Head 与 Stage Head：

```text
production_permission = false
shadow_production_permission = false
focus_cutover_permission = false
global_mandatory_adoption = false
```

Stage acceptance != production permission。

# 14. V4-12 Stage Entry 正式定义

依据当前最高合同 §78：

```text
V4-12 =
Structure / Anchor / Support
```

核心交付：

```text
D1 algorithms
coordinate rebasing
breakout
pullback
recovery
Anchor / support / acceptance
```

Stage Entry 必须引用：

```text
A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md
```

至少绑定：

```text
§10J
§10K
§10L
§13A
§31
§34A
§49A
§72
§78
§81.4
```

# 15. V4-12 DAG 边界

必须冻结：

```text
D1 allowed inputs =
F0[t]
+
t-1 frozen Anchor/event
```

禁止：

```text
D2[t]
same-day Final State
same-day Event diff
Focus
UI
future outcome
same-day newly-created Anchor as confirmation evidence
```

硬规则：

```text
new Anchor at t
→ can be emitted as new D1 event

new Anchor at t
→ cannot support/confirm itself at t

earliest path/support test =
t+1
```

# 16. V4-12 contract surface

Stage Entry 至少登记：

```text
STRUCTURE_EVENT_V1

Anchor schema/identity
Anchor coordinate identity
Anchor rebasing rules
Anchor lifecycle
invalidation AST
breakout AST
pullback AST
recovery AST

producer registry
field registry
parameter registry
machine AST
UNKNOWN semantics
time roles
input schema
output schema
machine vectors
```

没有这些，不得启动正式 V4-12 runtime implementation。

# 17. Breakout contract seed

只冻结合同，不在本任务实现：

```text
no active breakout event:

C > prior_high20 + 0.1*ATR20
AND
CLV >= 0.7

→ BREAKOUT_TENTATIVE
→ create PRIOR_HIGH Anchor
```

已有事件：

```text
BROKEN/INVALIDATED
→ FAILED_BREAKOUT

HELD_CONFIRMED
or >=2 consecutive evaluable sessions C>=anchor_upper
→ BREAKOUT_ACCEPTED

today touches anchor
→ TESTING

else
→ retain BREAKOUT_TENTATIVE
```

创建日不能 accepted。

# 18. Pullback contract seed

只允许 t-1 frozen event/Anchor：

```text
no prior valid rise/breakout/impulse
→ NOT_PULLBACK

BROKEN/INVALIDATED
→ PULLBACK_FAILED

HELD_CONFIRMED
→ PULLBACK_HELD

RECLAIMED/HELD_TENTATIVE
→ PULLBACK_RECLAIMED

touch by anchor type
→ PULLBACK_TO_MA / BREAKOUT / IMPULSE

post-event peak drawdown without touch
→ PULLBACK_IN_PROGRESS

otherwise
→ NOT_PULLBACK
```

UNKNOWN 不默认 FALSE。

# 19. Recovery contract seed

顺序：

```text
RECOVERY_FAILED
RECOVERY_CONFIRMED
ANCHOR_RECLAIM
MA20_RECLAIM
RELATIVE_RECOVERY
BOUNCE_ONLY
NONE
```

`RECOVERY_CONFIRMED` 要求冻结 recovery line 后至少 2 个连续可评估会话守住。创建日不得追认确认。

# 20. Coordinate / Rebase 前置

Anchor 必须显式冻结：

```text
anchor_price_basis
adjustment_source_revision
creation coordinate
current comparison coordinate
rebase lineage
corporate-action transition
unsupported adjustment behavior
```

禁止再次用 qfq_mul/qfq_add coefficient equality 当 price identity。

继承 R4A accepted basis：

```text
price_basis + adjustment_source_revision
```

# 21. 本任务完成状态

只允许：

```text
V4_11_ACCEPTED_HEAD_PROMOTION = PASS
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY = AUTHORIZED
```

禁止：

```text
V4_12_IMPLEMENTED
D1_PASS
FULL_D0_D1_D2_PASS
STRUCTURE_SUPPORT_ACCEPTED
```

# 22. 完成后 STOP

```text
commit
push
STOP
```

等待独立外部验收 promotion + stage entry，通过后再发 V4-12 implementation 任务。

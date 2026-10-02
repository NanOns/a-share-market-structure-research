# V4-12 R2｜Source Authority / Producer Registry Repair Task｜2026-10-02

**优先级：** P0 Contract Authority  
**基线 HEAD：** `b475002697bb3c5d91fab1ba44852b31d0d1da29`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`  
**R6R1：** EXTERNAL PASS / DO NOT REOPEN  
**V4-12 R1 AST / 69 vectors：** KEEP unless authority repair requires metadata/source guards  
**任务性质：** CONTRACT REPAIR ONLY  
**V4-12 runtime：** FORBIDDEN

# 1. 目标

修复 V4-12 R1 的：

```text
Field Registry
Producer Registry
Time-role Registry
Input Schema
Coordinate Authority
Completeness Matrix
```

使每一个字段满足：

```text
logical field
→ exact accepted source field
→ exact producer_contract_id
→ exact accepted/scoped head
→ exact source/publication identity
→ exact time role
→ exact quality/UNKNOWN semantics
```

禁止：

```text
unknown field
→ default CORE_FACTOR_V1
```

# 2. Authority Reconciliation Matrix

新增：

```text
reports/v4_12_r2/V4_12_R2_INPUT_AUTHORITY_RECONCILIATION.json
```

每个非 D1-output field 至少记录：

```text
logical_field
field_role:
  UPSTREAM_ACCEPTED
  D1_LOCAL_DERIVATION
  FROZEN_PRIOR_D1
  BLOCKED_CAPABILITY

accepted_source_field
accepted_source_stage
accepted_head_path
accepted_head_sha256
producer_contract_id
producer_version
parameter_set_id
source_namespace
trade_date_semantics
time_role
unit
quality_semantics
raw_reconstruction_allowed
target_publication_available
blocked_reason
consumer_definitions[]
consumer_machine_rules[]
```

# 3. V4-02 / Data Head authority

以下 family 从正式 Canonical/Adjustment lineage 绑定：

```text
O
H
L
C
price_basis
adjustment_source_revision
adjustment identity metadata
accepted adjustment transform source
```

至少绑定：

```text
data/v4/V4_02_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
config/v4_02_canonical_daily_pit_contract_v3.json
```

以及当前 Data Head 的 exact component refs。

不得把 coordinate/adjustment authority 绑定到 V4-03 Pure-Core Head。

# 4. Anchor Coordinate Contract 重新绑定

修复：

```text
config/v4_12_anchor_coordinate_contract_v1.json
```

当前错误：

```text
accepted_authority =
data/v4/V4_03_ACCEPTED_HEAD.json
```

R2 必须改为：

```text
Historical Adjustment / Canonical Adjusted source authority
+
V4-02 accepted lineage
+
current V4_DATA_ACCEPTED_HEAD
```

如 transform producer 当前仍不足以正式提供：

```text
alpha
beta
```

则必须：

```text
alpha/beta =
BLOCKED_WITH_EXPLICIT_REASON
```

不能标成 CORE_FACTOR。

继续保持：

```text
basis identity =
price_basis + adjustment_source_revision

qfq_mul/qfq_add equality != identity
```

# 5. V4-03 exact factor mapping

禁止一个泛化：

```text
CORE_FACTOR_V1
```

覆盖所有 fields。

从：

```text
config/v4_03_algorithm_contracts_v1.json
data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json
```

解析 exact output owner。

至少显式映射：

```text
ATR20 logical
→ atr20
→ CORE_FACTOR_V1.PRICE_TECHNICAL

CLV logical
→ clv
→ CORE_FACTOR_V1.CLV

MA20 logical
→ ma20
→ exact accepted producer

MA60 logical
→ ma60
→ exact accepted producer

prior_high20
→ prior_high20
→ CORE_FACTOR_V1.PRICE_TECHNICAL

amount_ratio20
→ amount_ratio20
→ exact accepted producer

rel_market_1
→ rel_market_1
→ exact accepted producer

ret1
→ ret1
→ exact accepted producer

slope20
→ slope20
→ CORE_FACTOR_V1.SLOPE
```

大小写 alias 必须显式记录：

```text
logical_field
accepted_source_field
```

禁止 runtime lower()/case guess。

# 6. delta3 必须改绑 RPS

当前错误：

```text
delta3
→ CORE_FACTOR_V1
```

正式：

```text
logical delta3
→ rps5_delta3
→ RPS_DELTA_V1
```

必须绑定：

```text
data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json
```

以及目标日 exact publication。

必须保留：

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
historical_first_availability_proven = false
```

不得 raw reconstruct。

对于：

```text
prior_delta3
```

若使用 t-1 RPS accepted publication，必须精确绑定 previous market session publication/digest/time role；否则继续 blocked。

# 7. near_high20_state 改绑 V4-04

当前错误：

```text
near_high20_state
→ CORE_FACTOR_V1
```

正式 owner：

```text
POSITION_STATE_V1
```

绑定：

```text
data/v4/V4_04_ACCEPTED_HEAD.json
config/v4_04_field_registry_v2.json
```

若目标日期没有正式可消费 V4-04 publication：

```text
target_publication_available = false
BLOCKED_WITH_EXPLICIT_REASON
```

禁止通过 V4-03/K线重算后冒充 V4-04 accepted output。

# 8. D1 local derivations 不得伪装 F0

以下至少改为：

```text
D1_LOCAL_DERIVATION
```

```text
distance_zone
evaluable
observation_close_view
start_price_view
endpoint_price_view
```

以及任何实际由 Machine AST/coordinate view 派生的字段。

Field Registry 必须使用明确 D1 producer，例如：

```text
V4_12_MACHINE_AST_V1
V4_12_COORDINATE_VIEW_V1
```

不得继续 `F0_ACCEPTED / CORE_FACTOR_V1`。

# 9. Session counters ownership

重新分类：

```text
post_creation_sessions
pivot_left_count
pivot_right_count
```

必须明确：

```text
market calendar authority
source dates
D1 local counter producer
availability rule
missing/suspension handling
same-day revision handling
```

若是 D1 runtime-local：

```text
source_namespace = D1_LOCAL_DERIVATION
```

而不是外部 F0 fact。

# 10. prior_range20_atr｜P0

当前没有 V4-03 accepted output。

R2 二选一：

## Option A｜新 D1 derived contract

冻结：

```text
formula
source fields
window contract
include/exclude current
price coordinate
ATR denominator
time role
quality/UNKNOWN
parameter identity
independent vectors
```

source fields 必须已有 accepted authority。

## Option B｜Block

若当前 authority 不足：

```text
prior_range20_atr =
BLOCKED_WITH_EXPLICIT_REASON

RANGE_UPPER =
FORMAL_BLOCKED_INPUT_CAPABILITY
```

禁止 raw fallback。

# 11. Pivot source contract｜P0

当前：

```text
pivot_low
pivot_low_strict
```

不能继续标 CORE_FACTOR。

必须冻结 D1 pivot detector contract：

```text
left actual evaluable sessions = 2
right actual evaluable sessions = 2
strict lower than all left/right lows
equal lows do not qualify
pivot_date
confirmation_date
available_date
available_at
no backfill
UNKNOWN behavior
```

如果 history authority 未满足：

```text
PIVOT_LOW =
BLOCKED_WITH_EXPLICIT_REASON
```

禁止 raw history 越权。

# 12. prior historical views

R1 已 block：

```text
atr_prior_view
prior_high_view
prior_delta3
pivot_low_strict
```

R2 必须同步修正 field row producer identity。

不得：

```text
capability=BLOCKED
但 producer_contract_id=CORE_FACTOR_V1
```

若成功绑定 t-1 accepted publication才能解除 block。

# 13. slope20 unit parity

Accepted V4-03：

```text
slope20 =
(MA20[t]-MA20[t-5])/ATR20

unit = dimensionless
```

修复：

```text
V4-12 slope20 unit = dimensionless

range_anchor_abs_slope20_max unit = dimensionless
```

数值 `0.1` 不改。

新增 owner-unit parity validator。

# 14. requiredness 改为 consumer-specific

不要再用 blanket：

```text
required = true
```

表达整个模块。

至少增加：

```text
globally_required
required_by[]
```

例如：

```text
close_t_minus_1 / ma20_t_minus_1
required_by = [recovery.MA20_RECLAIM]

ret1
required_by = [recovery.BOUNCE_ONLY]

near_high20_state
required_by = [breakout.APPROACHING]
```

保证 branch-local UNKNOWN 不无条件污染其他可判分支。

# 15. RANGE_UPPER semantic reconciliation

当前：

```text
creation_rule =
range_anchor_qualified AND breakout_trigger
```

必须对照 §41A.2 输出机器 disposition：

```text
CONTRACT_EXACT
AUTHORIZED_NARROWING
REMOVE_EXTRA_TRIGGER
```

若保留 `breakout_trigger`，必须绑定明确 authority，不得由实现者自行加门。

# 16. Dynamic MA source event

`FROZEN_REGISTERED_RISE` 必须枚举：

```text
allowed_source_event_types[]
source_event_contract_id
required maturity/status
available_at rule
creation identity
invalidation linkage
```

无法冻结则：

```text
MA20_DYNAMIC
MA60_DYNAMIC
=
BLOCKED_WITH_EXPLICIT_REASON
```

# 17. Output enum cleanup

`state_enum_registry` 去重。

新增：

```text
len(list) == len(set(list))
```

不得改变合法 enum 含义。

# 18. Producer Authority Parity hard gate

新增：

```text
reports/v4_12_r2/V4_12_R2_PRODUCER_AUTHORITY_PARITY.json
```

每一个：

```text
source_namespace = F0_ACCEPTED
```

的 field 必须满足其一：

### exact accepted mapping

```text
accepted_head exists
accepted_source_field exists
producer_contract_id exact
unit compatible
time role compatible
publication/source identity specified
```

### explicit block

```text
BLOCKED_WITH_EXPLICIT_REASON
```

最终：

```text
unresolved_false_accepted_claims = 0
generic_CORE_FACTOR_fallback_count = 0
```

# 19. Coordinate Authority Audit

新增：

```text
V4_12_R2_COORDINATE_AUTHORITY_AUDIT.json
```

必须证明：

```text
anchor coordinate authority
!= V4-03 Pure-Core Head
```

并绑定 exact Historical Adjustment / V4-02 / Data Head lineage。

检查：

```text
price_basis
adjustment_source_revision
alpha/beta source
corporate-action transition
same-day revision
unsupported conversion
```

# 20. R1 → R2 AST diff

生成：

```text
V4_12_R1_TO_R2_AST_DIFF.json
```

目标：

```text
business rule AST unchanged
```

允许变化：

```text
source guards
field aliases
producer identity
unit metadata
required_by
blocked capability metadata
```

如 business AST 必须改变，逐 node 给 authority/reason/vector impact，不得静默。

# 21. Independent vectors

重新执行 R1 69 vectors。

新增至少：

```text
A01 delta3 -> rps5_delta3/RPS_DELTA_V1 only
A02 near_high20 -> POSITION_STATE_V1 only
A03 unknown F0 cannot default CORE_FACTOR
A04 internal distance_zone cannot be F0
A05 alpha/beta cannot be CORE_FACTOR
A06 prior_range20_atr unowned -> blocked
A07 pivot unowned -> blocked or exact D1 owner
A08 slope20 unit parity
A09 alias exact source mapping
A10 branch-required UNKNOWN does not globally poison unrelated branch
A11 missing accepted owner -> UNKNOWN/block
A12 raw bars cannot grant accepted source authority
```

expected 必须独立构造。

# 22. Completeness Matrix R2

以下只有 authority parity PASS 后才能标 `FROZEN`：

```text
field_registry
producer_registry
time_role_registry
coordinate contract
input schema
required/source capability
```

否则：

```text
BLOCKED_WITH_EXPLICIT_REASON
```

不得按“文件存在”判 completeness。

# 23. 保持不变

不得修改：

```text
AGENTS.md
V4_11_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_12 Stage Entry
R6R1 evidence

Breakout/Pullback/Recovery/Support business order
24 parameter values
production/shadow/focus permissions
```

# 24. 禁止

```text
V4-12 runtime implementation
src/v4 D1 engine
schema migration
D2 integration
V4-13
Stage Head -> V4-12
Data Head advance
production/shadow/focus/global adoption
raw reconstruction to repair missing authority
```

# 25. Clean validation

至少：

```text
R6R1 still PASS
protected heads byte-identical
R1 69 vectors PASS
new authority vectors PASS
parameter literal audit PASS
DAG audit PASS
producer authority parity PASS
coordinate authority audit PASS
unit parity PASS
enum uniqueness PASS
no src/v4 runtime diff
no migration
```

# 26. 完成状态

只允许：

```text
V4_12_R2_CONTRACT_AUTHORITY_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

完成后：

```text
commit + push
STOP
```

等待独立外审。

不得自行授权 V4-12 runtime。

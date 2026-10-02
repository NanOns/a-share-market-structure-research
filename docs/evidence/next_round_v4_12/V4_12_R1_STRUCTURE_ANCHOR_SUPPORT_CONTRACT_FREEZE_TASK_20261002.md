# V4-12A｜Structure / Anchor / Support Contract Freeze Task R1｜2026-10-02

**优先级：** P0 Contract Completeness  
**父阶段：** V4-11 Accepted  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`  
**任务性质：** CONTRACT_DESIGN / FREEZE ONLY  
**禁止：** V4-12 runtime implementation

# 1. 目标

完成 V4-12 实现前的 §81.4 Contract Completeness：

```text
field registry
producer registry
time-role registry
input/output schema
machine AST
parameter instance
source capability semantics
UNKNOWN semantics
independent vectors
coordinate/rebase contract
```

完成后才能申请 V4-12 runtime implementation。

# 2. 权威章节

必须绑定当前最高合同：

```text
§10J Basic Breakout
§10K Basic Pullback
§10L Recovery
§13A DAG
§31 Final State Reducer interface
§34A Event boundary
§41A0 Anchor Price Coordinate / Re-Anchor
§41A Anchor
§41B Bullish Impulse
§41C Support / Acceptance State
§41D Acceptance / Retention
§49A common coordinate / benchmark separation where applicable
§72 Parameter Governance
§78 Stage Table
§81.4 Contract Completeness
§87A Field Registry
```

# 3. 必须生成的 versioned contracts

至少：

```text
config/v4_12_structure_event_contract_v1.json
config/v4_12_anchor_schema_v1.json
config/v4_12_anchor_coordinate_contract_v1.json
config/v4_12_support_state_contract_v1.json
config/v4_12_retention_contract_v1.json
config/v4_12_field_registry_v1.json
config/v4_12_producer_registry_v1.json
config/v4_12_time_role_registry_v1.json
config/v4_12_input_schema_v1.json
config/v4_12_output_schema_v1.json
config/v4_12_parameter_set_v1.json
config/v4_12_machine_ast_v1.json
config/v4_12_machine_vectors_v1.json
```

以及：

```text
reports/v4_12_r1/V4_12_R1_CONTRACT_FREEZE.json
reports/v4_12_r1/V4_12_R1_PARAMETER_LITERAL_AUDIT.json
reports/v4_12_r1/V4_12_R1_DAG_EDGE_AUDIT.json
reports/v4_12_r1/V4_12_R1_INDEPENDENT_VECTOR_ORACLE.json
reports/v4_12_r1/V4_12_R1_CONTRACT_COMPLETENESS_MATRIX.json
```

# 4. Allowed / Forbidden

允许：

```text
config/v4_12_*.json
reports/v4_12_r1/*
docs/evidence/next_round_v4_12/*
contract-only validation scripts
contract-only tests
```

禁止：

```text
src/v4 V4-12 runtime detector implementation
DB schema migration
D1 production publisher
D2 integration
Stage Head advance
Data Head advance
Focus/UI cutover
```

# 5. Anchor 类型冻结

`STRUCTURE_EVENT_V1` V1 至少支持：

```text
PRIOR_HIGH
BREAKOUT_LEVEL
RANGE_UPPER
BULLISH_IMPULSE_BODY
BULLISH_IMPULSE_LOW
MA20_DYNAMIC
MA60_DYNAMIC
PIVOT_LOW
GAP_ZONE
```

每类必须登记：

```text
source event
creation rule
available date/time
fixed vs dynamic
price basis
required fields
UNKNOWN behavior
invalidation relation
earliest test date
```

禁止看图事后随意画线。

# 6. Anchor time availability

必须冻结：

```text
new Anchor at t
→ cannot support/confirm itself at t

earliest normal test =
t+1
```

特殊：

```text
PIVOT_LOW:
左右各2日确认
最早 pivot_date + 2 个实际可评估会话注册
available_date = confirmation date
不得倒填

GAP_ZONE:
L[t] > H[t-1]
zone = [H[t-1], L[t]]
注册日不得参与支撑验证

Bullish Impulse Anchor:
创建日冻结
最早次日测试
```

# 7. Anchor coordinate / rebase

Anchor 必须保存：

```text
anchor_id
security_id
anchor_trade_date
anchor_raw_lower
anchor_raw_upper
anchor_price_basis
adjustment_contract_id
adjustment_source_identity
adjustment_source_revision
adjustment_asof
anchor_basis_trade_date
frozen_transform_coefficients
source_event_id
source_fact_digest
creation_coordinate
current_comparison_coordinate
rebase_lineage
corporate_action_transition
```

原始 Anchor 永不回写。

观察日：

```text
P_view(t) =
alpha * P_anchor + beta
```

必须保证：

```text
anchor
current price
ATR
return
breach depth
support zone
```

处于同一 price basis。

禁止：

```text
旧 QFQ anchor number
直接比较新复权基准 current price

qfq_mul/qfq_add coefficient equality
充当 price identity
```

转换失败：

```text
state = UNKNOWN
reason = PRICE_BASIS_MISMATCH
```

# 8. Bullish Impulse AST

冻结：

```text
body = C - O

body_atr =
body / ATR20[t-1 converted to current price coordinate]

range_atr =
(H-L) / ATR20[t-1 converted]

core_bullish_impulse =
body_atr >= 1
AND range_atr >= 1
AND CLV >= 0.7
AND amount_ratio20 >= 1.2
AND rel_market_1 > 0
```

保存：

```text
open
body_mid
close
low
high
BODY zone = [O, (O+C)/2]
LOW zone  = [L,L]
```

一字板 CLV UNKNOWN 时该分支不能强行 TRUE。turnover 不进入正式资格。

# 9. Support State AST

只评估 t-1 已存在 Anchor。

统一 observation coordinate：

```text
zone=[lo,hi]
atr=converted ATR20[t-1] > 0
```

冻结：

```text
touch =
L <= hi + 0.25*atr
AND
H >= lo - 0.25*atr

close_breach =
C < lo - 0.5*atr

deep_breach =
C < lo - 1.5*atr

eod_reclaim =
touch
AND C >= hi
AND CLV >= 0.5
```

严格顺序：

```text
1 terminal INVALIDATED/BROKEN -> no revival
2 deep_breach OR 2 consecutive evaluable close_breach -> BROKEN
3 first close_breach -> BREACHED_SHALLOW
4 qualified separated retest + reclaim -> HELD_CONFIRMED
5 reclaim after TESTING/BREACHED or first touch reclaim -> RECLAIMED
6 RECLAIMED + >=1 actual session held -> HELD_TENTATIVE
7 prior HELD_* retouch no reclaim -> RETESTING
8 touch -> TESTING
9 distance <= 1*atr -> APPROACHING
10 otherwise retain valid prior or IDLE
```

缺失/停牌/换基失败：

```text
UNKNOWN observation
preserve prior state
stale = true
```

不得当 FALSE，也不得让未知会话完成连续计数。

# 10. Breakout AST

无 active breakout：

```text
C > prior_high20 + 0.1*ATR20
AND CLV >= 0.7
→ BREAKOUT_TENTATIVE
→ PRIOR_HIGH Anchor

else near_high20 == NEAR
→ APPROACHING

else evaluable
→ NO_BREAKOUT
```

已有事件：

```text
BROKEN/INVALIDATED -> FAILED_BREAKOUT

HELD_CONFIRMED
OR >=2 consecutive evaluable post-creation sessions C>=anchor_upper
-> BREAKOUT_ACCEPTED

today touches -> TESTING

otherwise -> BREAKOUT_TENTATIVE
```

创建日不能 accepted。

# 11. Pullback AST

只读 t-1 frozen valid event/Anchor：

```text
no prior valid rise/breakout/impulse -> NOT_PULLBACK
BROKEN/INVALIDATED -> PULLBACK_FAILED
HELD_CONFIRMED -> PULLBACK_HELD
RECLAIMED/HELD_TENTATIVE -> PULLBACK_RECLAIMED
touch -> PULLBACK_TO_MA/BREAKOUT/IMPULSE
post-event peak drawdown no touch -> PULLBACK_IN_PROGRESS
else evaluable -> NOT_PULLBACK
```

UNKNOWN 不得压成 NOT_PULLBACK。

# 12. Recovery AST

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

规则至少：

```text
RECOVERY_CONFIRMED:
冻结 recovery line 后
>=2 consecutive evaluable sessions held

ANCHOR_RECLAIM:
old Anchor 当日 EOD reclaim

MA20_RECLAIM:
C[t-1] <= MA20[t-1]
AND C[t] > MA20[t]

RELATIVE_RECOVERY:
delta3 previous <=0
→ current >3
AND rel_market_1 >0

BOUNCE_ONLY:
ret1 >0
```

关键 authority：

```text
close_t_minus_1 / ma20_t_minus_1
当前 accepted capability unavailable
```

因此必须：

```text
DO_NOT_RECONSTRUCT_FROM_RAW_BARS

missing prior core fields
→ UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE
```

不能重犯 V4-11 R4 错误。

# 13. Retention / Acceptance

冻结：

```text
impulse_retention_k =
(C[t0+k]-base)/(C[t0]-base)
k=1/3
```

全部价格换到同一 observation basis。

```text
denominator <=0 -> NOT_APPLICABLE
unknown -> UNKNOWN
```

禁止 epsilon。

`acceptance_state`：

```text
UNKNOWN
BROKEN
PENDING
ACCEPTED
NOT_ACCEPTED
```

`ACCEPTED` 要求：

```text
post-event 2 consecutive evaluable sessions
C >= anchor_upper
```

一次上涨不能等价为接受。

# 14. Parameter set

所有 AST literal 必须有：

```text
parameter_id
或明确数学常数/枚举依据
```

至少登记：

```text
breakout_atr_buffer = 0.1
breakout_clv_min = 0.7
acceptance_consecutive_sessions = 2

impulse_body_atr_min = 1.0
impulse_range_atr_min = 1.0
impulse_clv_min = 0.7
impulse_amount_ratio20_min = 1.2

support_touch_atr_buffer = 0.25
support_close_breach_atr = 0.5
support_deep_breach_atr = 1.5
support_approach_atr = 1.0
support_reclaim_clv_min = 0.5
support_break_consecutive_sessions = 2

range_anchor_window = 20
range_anchor_range_atr_max = 4
range_anchor_abs_slope20_max = 0.1

pivot_left_sessions = 2
pivot_right_sessions = 2

recovery_delta3_threshold = 3
```

全部：

```text
ENGINEERING_CANDIDATE
not profitability validated
```

# 15. Producer / time-role registry

每个字段记录：

```text
producer_contract_id
parameter_set_id
source namespace
trade_date
time role t / t-1
required/optional
publication identity
quality
UNKNOWN reason family
output digest
formal/diagnostic
```

D1 只允许：

```text
F0[t]
t-1 frozen Anchor/event
```

禁止：

```text
D2[t]
same-day final state
same-day state event
Focus
UI
Supplemental feedback
future outcome
```

# 16. Independent vectors

至少覆盖：

```text
B01 breakout exact threshold -epsilon/exact/+epsilon
B02 creation day cannot accepted
B03 t+1/t+2 accepted path

P01 no prior event
P02 broken prior
P03 held prior
P04 unknown prior != false

R01 MA20 prior input unavailable -> UNKNOWN
R02 relative recovery threshold boundaries
R03 recovery creation day cannot confirmed

S01 first touch reclaim
S02 first shallow breach
S03 two consecutive breach -> BROKEN
S04 missing day breaks consecutive count
S05 reclaim -> tentative hold -> retest -> confirmed
S06 terminal broken cannot revive

A01 cash dividend rebase
A02 bonus shares rebase
A03 rights issue rebase
A04 conversion impossible -> PRICE_BASIS_MISMATCH
A05 original Anchor bytes unchanged
A06 same-day revision

T01 pivot +2 availability
T02 gap registration day cannot test
T03 impulse next-day earliest test

D01 perturb D2[t] -> D1 unchanged
D02 perturb Focus/UI -> D1 unchanged
D03 future data -> rejected
D04 same-day new Anchor -> cannot self-support
```

Expected values 必须由独立 oracle 生成，不能调用 implementation helper 生成 expected。

# 17. Contract completeness matrix

每一项只允许：

```text
FROZEN
or
BLOCKED_WITH_EXPLICIT_REASON
```

不得：

```text
TODO
TBD silently
IMPLEMENTATION_WILL_DECIDE
```

例如 accepted t-1 close/MA20 仍缺 authority 时，受影响分支必须：

```text
FORMAL_BLOCKED_INPUT_CAPABILITY
```

不得重建。

# 18. 验收状态

本任务最终只可：

```text
V4_12_R1_CONTRACT_FREEZE_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

禁止：

```text
V4_12_RUNTIME_IMPLEMENTED
V4_12_ACCEPTED
FULL_D0_D1_D2_PASS
Stage Head -> V4_12
```

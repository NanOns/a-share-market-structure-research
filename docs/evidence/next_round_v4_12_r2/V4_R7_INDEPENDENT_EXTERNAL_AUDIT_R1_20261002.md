# V4 R7 独立外部验收审计 R1｜2026-10-02

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**R7 起始 HEAD：** `2e3e811eb08d7e350e27c4c1e2767ba91160ef98`  
**R7 tested source commit：** `e8fa4f6cce76f09d79abf79656fc952b99cfb01d`  
**当前远端 HEAD：** `b475002697bb3c5d91fab1ba44852b31d0d1da29`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

# 1. 唯一总裁决

```text
V4_R7_EXTERNAL_AUDIT =
PARTIAL_PASS_V4_12_R2_SOURCE_AUTHORITY_REPAIR_REQUIRED

R6R1_GOVERNANCE_REPLAY_CLEANUP = PASS

V4_12_R1_MACHINE_AST = PASS_KEEP
V4_12_R1_PARAMETER_LITERAL_COVERAGE = PASS_KEEP
V4_12_R1_INDEPENDENT_VECTOR_ORACLE = PASS_KEEP
V4_12_R1_DAG_BOUNDARY = PASS_KEEP

V4_12_R1_SOURCE_PRODUCER_REGISTRY = FAIL_P0
V4_12_R1_CONTRACT_COMPLETENESS = BLOCKED_FALSE_COMPLETENESS

V4_12_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED

V4_STAGE_ACCEPTED_HEAD = KEEP_V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = KEEP_2026_09_30

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

本轮主问题不是状态机业务规则，而是 **source authority / producer ownership 错绑**。数学上可计算不等于已有正式 producer 权限。

# 2. R6R1 正式通过

## G01

当前 `AGENTS.md` 与：

```text
1c46d6681ba1d0540551bcc0f75b35c545ff2769:AGENTS.md
```

独立对比：

```text
exact = true
bytes = 1616
sha256 = fe3ca08043743023f23d5767bf8d3570e2dc4a72c7215056a2daba53a0ea7a77
```

R6 未授权第10条已真正移除。

## G02

`prepare_v4_11_promotion_r1.py` 已改为：

```text
repo-first exact validation
+
explicit --bundle-dir bootstrap
+
missing repo bundle and no source
→ R6_EXTERNAL_BUNDLE_SOURCE_REQUIRED
```

未再发现固定 `D:/Users/...`、`C:/Users/...`、`~/Desktop/...` 路径。

因此：

```text
R6R1_GOVERNANCE_REPLAY_CLEANUP = PASS
```

不再重开。

# 3. Protected heads / scope

R7 前后以下全部 byte-identical：

```text
V4_11_ACCEPTED_HEAD
d8d96dce... -> d8d96dce...

V4_STAGE_ACCEPTED_HEAD
80c58f2f... -> 80c58f2f...

V4_DATA_ACCEPTED_HEAD
38e7c9b6... -> 38e7c9b6...

V4_12 Stage Entry
ceec544a... -> ceec544a...
```

同时：

```text
no src/v4 runtime implementation
no schema migration
no D2 integration
no Stage Head advance
no Data Head advance
```

scope discipline PASS。

# 4. Clean / tests

```text
tested_source_commit =
e8fa4f6cce76f09d79abf79656fc952b99cfb01d

targeted tests:
110 passed
0 failed
0 errors
0 skipped
0 deselected

independent vector oracle:
69 / 69 PASS
```

最终 HEAD `b475002...` 仅比 tested source 多 evidence-only commit，没有业务合同改变。

当前没有额外 GitHub status/workflow，因此不声称 CI 背书。

# 5. 可以保留的 V4-12 R1 内容

以下全部 KEEP：

```text
D1[t] allowed =
F0[t] + t-1 frozen Anchor/event

D2[t] / same-day Final State / Focus / UI / future
不得进入 D1

new Anchor t
不能 t 当日自证
最早 t+1 path/support test
```

坐标原则：

```text
basis identity =
price_basis + adjustment_source_revision

qfq coefficient equality != identity
original Anchor immutable
```

Breakout / Pullback / Recovery / Support 的主要 rule order 与最高合同一致。

Recovery 对 `MA20_RECLAIM` 使用 `require_known`，不会把缺失 t-1 owner 字段吞成 FALSE。

Parameter literal audit：

```text
24 parameters
293 AST leaves
0 unbound literals
```

69 个 independent vectors 全 PASS。

因此这些不需要下一轮重写。

# 6. P0 根因：默认 CORE_FACTOR fallback

当前生成器 `scripts/freeze_v4_12_contracts_r1.py` 的外部字段 owner 逻辑，本质上是：

```python
producer =
STRUCTURE_EVENT_V1 if prior/frozen
else CORE_FACTOR_V1
```

只有少数 OHLC / counters 再特判。

结果是：

> 只要一个字段不是 frozen Anchor，也没有被硬编码例外，就会被默认登记成 CORE_FACTOR_V1。

这不是 source-authority reconciliation。

# 7. V4-03 exact output 对账

Accepted V4-03 有 47 个正式 outputs。与 V4-12 相关的真实字段包括：

```text
amount_ratio20
atr20
clv
ma20
ma60
prior_high20
rel_market_1
ret1
rps5_delta3
slope20
```

不是任意 V4-12 input 都属于 V4-03。

# 8. delta3 错绑

当前：

```text
delta3
→ CORE_FACTOR_V1
```

正式 V4-03 output：

```text
rps5_delta3
producer = RPS_DELTA_V1
unit = percentage_points
```

而且 V4-11 R5 已明确：

```text
logical delta3
→ accepted RPS history rps5_delta3
→ reconstruction_allowed = false
```

正式 scoped authority：

```text
data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json
```

覆盖到 2026-09-30。

因此当前 V4-12 owner 错误。

# 9. near_high20_state 错绑

当前：

```text
near_high20_state
→ CORE_FACTOR_V1
```

Accepted V4-04 registry 明确：

```text
near_high20_state
producer_contract_id = POSITION_STATE_V1
stage = V4-04
```

正式 owner：

```text
data/v4/V4_04_ACCEPTED_HEAD.json
config/v4_04_field_registry_v2.json
```

如果目标日没有可消费正式 publication，必须 block，不得自己重算后冒充 V4-04 accepted output。

# 10. alpha / beta 错绑

当前：

```text
alpha
beta
→ CORE_FACTOR_V1
```

但它们属于：

```text
Anchor basis → observation basis
```

的 Historical Adjustment / coordinate transform。

§41A0 明确 QFQ coordinate conversion 由 Historical Adjustment Contract 冻结。

所以 alpha/beta 不能属于 Pure-Core factor owner。

# 11. D1 local derivations 被错标成 F0

当前至少：

```text
distance_zone
evaluable
observation_close_view
start_price_view
endpoint_price_view
```

被登记为：

```text
CORE_FACTOR_V1 / F0_ACCEPTED
```

但它们实际是 D1 local derivations / coordinate views。

Producer Registry 自己已经写：

```text
distance_zone = max(lo-C, C-hi, 0)
evaluable = accepted actual bar + source/basis + prior ATR quality
```

说明 R1 Field Registry 与 Producer Registry 自相矛盾。

# 12. prior_range20_atr 没有 accepted owner

当前：

```text
prior_range20_atr
→ CORE_FACTOR_V1
→ ACCEPTED_BINDING_REQUIRED_BEFORE_RUNTIME
```

但遍历 V4-03 accepted 47 outputs：

```text
prior_range20_atr = absent
```

它又直接决定 RANGE_UPPER。

所以必须：

```text
新建正式 D1 derived contract
or
BLOCKED_WITH_EXPLICIT_REASON
```

不得 runtime 自己从 raw K 线随手补算。

# 13. Pivot owner 不成立

当前：

```text
pivot_low
pivot_low_strict
→ CORE_FACTOR_V1
```

但它们不是 V4-03 output。

最高合同把 PIVOT_LOW 定义为：

```text
左右各2实际可评估会话
严格低点
pivot_date + 2 才可注册
不可倒填
```

它应当是 D1 pivot detector/session-window contract，或者在 authority 未冻结前显式 blocked。

当前只 block `pivot_low_strict`、却没有 block `pivot_low`，不完整。

# 14. prior-view 字段虽然 block，但 producer identity 仍错误

R1 已显式 block：

```text
atr_prior_view
prior_high_view
prior_delta3
pivot_low_strict
```

方向正确。

但 field row 仍写：

```text
producer_contract_id = CORE_FACTOR_V1
```

这会误导 runtime 认为“已有 old Core producer，只是暂时没接”。

必须改为真实 candidate source owner / prior-view derivation / blocked owner。

# 15. Coordinate Contract authority 绑错 stage

当前：

```text
config/v4_12_anchor_coordinate_contract_v1.json
accepted_authority =
data/v4/V4_03_ACCEPTED_HEAD.json
```

但 coordinate/affine authority 属于：

```text
Historical Adjustment
Canonical Adjusted Daily
V4-02/Data Head adjustment lineage
```

当前 Data Head 已正式绑定：

```text
ADJUSTED_DAILY
RAW_DAILY
PERIOD_ADJUSTED
...
```

所以 V4-03 Pure-Core Head 不能充当 Anchor affine coordinate source authority。

# 16. Generic CORE_FACTOR 粒度过粗

即使字段确实属于 V4-03，accepted producer 也更精确：

```text
atr20 -> CORE_FACTOR_V1.PRICE_TECHNICAL
clv -> CORE_FACTOR_V1.CLV
slope20 -> CORE_FACTOR_V1.SLOPE
rps5_delta3 -> RPS_DELTA_V1
```

§81.4 要求 producer/time semantics，下一轮必须绑定 exact producer identity，而不是 family fallback。

# 17. Alias 必须显式

当前 logical names：

```text
ATR20
CLV
MA20
MA60
```

Accepted output IDs：

```text
atr20
clv
ma20
ma60
```

可以保留逻辑别名，但必须显式记录：

```text
logical_field
accepted_source_field
```

不能由 runtime 靠大小写猜测。

# 18. slope20 unit 错误

Accepted V4-03：

```text
slope20 =
(MA20[t]-MA20[t-5]) / ATR20

unit = dimensionless
```

V4-12 当前 field registry：

```text
ATR_per_actual_session
```

错误。

对应：

```text
range_anchor_abs_slope20_max
```

参数单位也应为：

```text
dimensionless
```

数值 0.1 不需要改变。

# 19. Blanket required=true 语义不足

当前大量外部 input：

```text
required = true
```

但状态机是 branch-specific。

例如：

```text
close_t_minus_1 / ma20_t_minus_1
只对 MA20_RECLAIM 必需

ret1
只对 BOUNCE_ONLY 必需
```

需要 `required_by[]` 或等价机制，否则可能把局部 UNKNOWN 错扩散到整个 V4-12。

# 20. Output enum registry 重复

当前 state enum registry 含重复值，例如：

```text
UNKNOWN
INVALIDATED
RETESTING
HELD_TENTATIVE
HELD_CONFIRMED
```

不影响 R1 AST 结果，但正式 contract registry 应 deduplicate，并建立唯一性 gate。

# 21. RANGE_UPPER source event 需明确

当前：

```text
RANGE_UPPER creation_rule =
range_anchor_qualified AND breakout_trigger
```

最高合同 §41A.2 明确的是：

```text
prior20 range/ATR <= 4
AND abs(slope20) <= 0.1
```

同时要求每个 Anchor 有明确来源事件。

下一轮必须明确：

```text
range qualification 即注册 RANGE_UPPER
还是
只在 range breakout event 时注册
```

如果保留额外 breakout_trigger，必须给 contract authority，不能由实现者自行加门。

# 22. Dynamic MA source event 仍未冻结

当前：

```text
MA20_DYNAMIC / MA60_DYNAMIC
source_event = FROZEN_REGISTERED_RISE
```

但 `FROZEN_REGISTERED_RISE` 没有枚举实际允许的 event type。

必须冻结：

```text
allowed_source_event_types
source contract/version
available_at
creation identity
invalidation linkage
```

否则 MA dynamic anchor 入口仍是开放语义。

# 23. 当前 Completeness Matrix 不能接受

当前 Matrix 把：

```text
field_registry
producer_registry
required facts/source capability
```

都标成 `FROZEN`，并给总状态 PASS。

由于多个 owner 身份错误：

```text
V4_12_R1_CONTRACT_COMPLETENESS =
BLOCKED_FALSE_COMPLETENESS
```

不是“文件不齐”，而是“错误 source ownership 被标成已冻结”。

# 24. 下一轮 KEEP

不得无故重写：

```text
R6R1 cleanup
V4-11 Accepted Head
Stage/Data Heads
V4-12 Stage Entry

Breakout rule order
Pullback rule order
Recovery rule order
Support state order
Retention formula
Anchor immutability principle
basis identity principle
DAG forbidden edges
24 parameter values
69 independent vectors
literal audit framework
```

# 25. 下一轮唯一主线

只做：

```text
V4-12 R2
Source Authority / Producer Registry Repair
```

目标：

```text
每个 upstream input
= exact accepted owner/source field/producer/time/publication

每个 internal field
= explicit D1 local derivation

无正式 authority 的 required field
= BLOCKED_WITH_EXPLICIT_REASON
```

完成后再外审是否允许 V4-12 runtime。

# 26. Heads / permissions

继续：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_12_RUNTIME = NOT AUTHORIZED

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

# 27. 最终结论

```text
R6R1 = EXTERNAL_PASS

V4_12_R1_AST_AND_VECTOR_DESIGN = KEEP

V4_12_R1_CONTRACT_AUTHORITY = BLOCKED_R2

NEXT =
V4_12_R2_SOURCE_AUTHORITY_REGISTRY_REPAIR

NO_RUNTIME_IMPLEMENTATION
```

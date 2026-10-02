# V4-12 R10B｜D1 Runtime Engine R1 Implementation Task｜2026-10-02

**前置：** R10A `V4_12_RUNTIME_ENGINEERING_ENTRY_R1_READY`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`  
**任务性质：** Scoped Engineering Runtime Implementation  
**Production / Shadow / Focus：** FORBIDDEN

# 1. 目标

实现 V4-12 D1 Structure / Anchor / Support 的第一版真实运行时引擎，严格消费已经冻结并外审通过的合同，不在 runtime 中维护第二套业务语义。

目标不是“把 UNKNOWN 变少”，而是证明：

```text
frozen contract
→ deterministic runtime
→ fail-closed input binding
→ append-only candidate outputs
→ independent replay parity
```

# 2. 代码位置

遵循现有仓库 `src/workbench_analysis` 结构，建议拆分：

```text
src/workbench_analysis/v4_12_ast_runtime.py
src/workbench_analysis/v4_12_structure_engine.py
src/workbench_analysis/v4_12_anchor_runtime.py
src/workbench_analysis/v4_12_structure_io.py
```

实际命名可按仓库惯例调整，但职责必须分离。

禁止 Runtime import：

```text
tests/*
scripts/validate_v4_12_*
FixtureExpressionVerifier
R8/R9 oracle helper
```

生产 runtime 与测试/审计 oracle 必须独立。

# 3. Frozen contract loader

Runtime 只允许读取 R10A Entry 明确 hash-bind 的：

```text
config/v4_12_machine_ast_v1.json
config/v4_12_field_registry_v1.json
config/v4_12_producer_registry_v1.json
config/v4_12_time_role_registry_v1.json
config/v4_12_parameter_set_v1.json
config/v4_12_input_schema_v1.json
config/v4_12_output_schema_v1.json
config/v4_12_anchor_schema_v1.json
config/v4_12_anchor_coordinate_contract_v1.json
config/v4_12_structure_event_contract_v1.json
config/v4_12_support_state_contract_v1.json
config/v4_12_retention_contract_v1.json
config/v4_12_time_counter_contract_v2.json
```

启动时：

```text
digest mismatch
→ fail closed
```

不得自动改合同。

# 4. Runtime AST evaluator

实现独立三值 AST evaluator：

```text
TRUE
FALSE
UNKNOWN
```

必须覆盖 frozen AST 用到的全部 op：

```text
and
or
not
eq
gt/ge/lt/le
add/sub/mul/div
abs
require_known
ordered_select
field
parameter
enum
math_constant
```

要求：

```text
UNKNOWN never coerced to FALSE
ordered_select 遇到更高优先级 UNKNOWN 时按 frozen policy STOP_WITH_UNKNOWN
除零 / 非法输入 / missing required
→ UNKNOWN + explicit reason
```

Runtime evaluator 与 validator fixture 不能共享实现代码。

# 5. Runtime input binder

实现 Field Registry 驱动的 binder。

每个 input 必须输出：

```text
logical_field
value
quality
reason
source_namespace
producer_contract_id
source_publication_id
source_digest
trade_date
time_role
```

规则：

```text
UPSTREAM_ACCEPTED:
只消费 registry 允许的 accepted publication

BLOCKED_CAPABILITY:
永远不能 runtime 自行重算升级

FROZEN_PRIOR_D1:
只允许读取 previous-market-session accepted/candidate D1 snapshot
同日 revision 不能充当前 prior

D1_LOCAL_DERIVATION:
只由 runtime 冻结规则计算

D1_OUTPUT:
只由当前 AST 输出
```

# 6. 禁止 raw fallback

至少对以下建立 hard gate：

```text
ATR20
CLV
MA20
MA60
prior_high20
amount_ratio20
rel_market_1
ret1
slope20
near_high20_state
alpha
beta
prior_range20_atr
pivot_low
pivot_low_strict
```

当 capability blocked：

```text
value = null
quality = UNKNOWN
reason = exact blocked reason
```

禁止：

```text
从 raw OHLC 自算
读取 V4-11 candidate 代替 accepted owner
换 provider
从未来日补历史
```

# 7. Session counters

实现：

```text
post_creation_market_sessions
post_creation_evaluable_sessions
held_count
breach_count
recovery_held_count
pivot_left_count
pivot_right_count
separated_sessions
test_count
```

必须逐条符合：

```text
V4_12_SESSION_COUNTER_V2
```

尤其：

```text
market age 与 evaluable count 分离
missing/suspension 不增 evaluable count
missing 打断 consecutive chain
same-day revision 不重复计数
quality correction 替换同日 membership
calendar unavailable -> market age UNKNOWN
```

# 8. Anchor lifecycle

实现 Contract-Scoped Candidate Anchor 对象，至少包含：

```text
anchor_id
security_id
anchor_trade_date
available_date
available_at
anchor_type
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
quality
reason
```

规则：

```text
original Anchor immutable
same-day revision append/replace observation view, not rewrite original fact
new Anchor cannot self-confirm
active anchor selection不得改变 episode-bound invalid_if
```

当前 `alpha/beta` capability blocked 时：

```text
cross-basis comparison
→ UNKNOWN / PRICE_BASIS_MISMATCH or exact blocked reason
```

不得临时使用 qfq coefficient equality 代替 transform authority。

# 9. Event / Support / Acceptance runtime

实现：

```text
breakout_state
pullback_state
recovery_state
support_state
acceptance_state
retention_value / quality
```

必须直接由 frozen AST/contract 驱动。

至少输出：

```text
state
quality
reason
matched_rule_id
input_digest
contract_digest
parameter_set_id
prior_state_ref
source_event_ref
anchor_ref
```

# 10. Candidate persistence

本轮只做 project-managed append-only candidate artifacts，不做正式 Stage Head / Production 表切换。

至少输出：

```text
reports/v4_12_runtime_r1/
  V4_12_D1_RUNTIME_CANDIDATE.jsonl
  V4_12_ANCHOR_CANDIDATE.jsonl
  V4_12_EVENT_CANDIDATE.jsonl
  V4_12_TRANSITION_CANDIDATE.jsonl
  V4_12_RUNTIME_READBACK.json
  V4_12_RUNTIME_CAPABILITY_MATRIX.json
```

每个 artifact：

```text
atomic write
deterministic ordering
stable digest
idempotent rerun
no overwrite of prior revision facts
```

如果仓库已有更合适 staging 目录，可按惯例使用，但必须有 manifest/readback。

# 11. Synthetic parity gate

Runtime 必须独立执行：

```text
69 amended business vectors
12 R2 authority vectors
R2.1 sequence vectors
time-domain negative vectors
corporate-action coordinate vectors
DAG perturbation vectors
```

要求：

```text
runtime output
==
frozen expected
```

不是调用 validator 得到答案，而是 runtime 自己跑。

# 12. Real scoped replay

用当前 accepted Data Head：

```text
2026-09-30
```

进行 full research-universe scoped replay。

要求：

```text
读取真实 accepted source publication
逐字段 binder
不因为 blocked capability 而伪造值
```

输出至少：

```text
universe_count
per-field:
  KNOWN
  UNKNOWN
  BLOCKED_CAPABILITY
  reason counts

per-output:
  state distribution
  UNKNOWN reason distribution

anchors_created
events_created
support observations
acceptance states
```

重要：

> 真实 replay 大量 UNKNOWN 可以是正确结果。

不得为了降低 UNKNOWN：

```text
改阈值
raw recompute
偷用 V4-11 candidate
替换 authority
```

# 13. Prior D1 bootstrap

当前不存在正式 previous-session accepted V4-12 D1 publication。

因此 2026-09-30 real replay 必须明确：

```text
prior_D1_history_status =
NO_ACCEPTED_PRIOR_D1_PUBLICATION
```

允许：

```text
无 prior event 的分支
新事件 candidate creation
```

不得：

```text
事后回算 9/29 D1
并伪装成当时 accepted prior
```

如果为了工程 replay 构建 reconstructed prior：

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
只能 diagnostic
不能作为 formal proof
```

# 14. Same-day revision

Runtime 必须支持同一 trade_date 多 revision：

```text
r1 -> r2 -> r3
```

约束：

```text
prior_session_state 始终来自 t-1
same-day revision 不变成 prior
session counters 不重复增长
Anchor 原始记录不被 revision 回写
transition 记录 append-only
```

# 15. DAG hard gate

Runtime namespace 只能读：

```text
F0[t]
t-1 frozen D1
frozen calendar
frozen contract/parameter
```

必须拒绝：

```text
D2[t]
same-day Final State
state_events
Radar
Focus
UI
Forward outcomes
future dates
same-day newly created Anchor 作为 confirmation evidence
```

建立 negative tests。

# 16. Storage schema boundary

本轮不做正式生产 migration。

可冻结候选 schema manifest，字段至少覆盖最高合同：

```text
stock_structure_events
stock_structure_anchors
stock_structure_event_transitions
structure observations
```

但正式 DB migration / canonical write 权限留到 Runtime Engine 外审通过后。

# 17. Performance / determinism

记录：

```text
full-universe row count
wall-clock
peak memory if available
artifact bytes
deterministic digest
rerun digest equality
```

不要求优化到最终生产指标，但不得出现明显 O(N^2) 全市场交叉扫描。

# 18. Independent validator

新增独立 validator，不 import runtime internal helper：

```text
scripts/validate_v4_12_runtime_r1.py
```

至少独立检查：

```text
contract hashes
input source authority
no raw fallback
same-day prior isolation
counter readback
state distributions
UNKNOWN attribution
append-only identity
idempotency
DAG forbidden inputs
artifact digest
```

# 19. Protected heads

全轮保持：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_11_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

禁止创建：

```text
data/v4/V4_12_ACCEPTED_HEAD.json
```

# 20. 禁止

```text
D2 integration
Final State reducer
Radar
Focus
Validation Cohort
Production
Shadow production
Global mandatory adoption
V4-13
Stage Head advance
Data Head advance
```

# 21. 完成状态

只允许：

```text
V4_12_D1_RUNTIME_ENGINE_R1_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

完成：

```text
commit + push
STOP
```

等待独立外审。

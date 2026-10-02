# V4-12 R12A｜Multi-Anchor State Contract V2 Freeze｜2026-10-02

**基线 HEAD：** `5bc34c907bd5d39f322c315db34c7788d61f0bbc`  
**R11：** Single-Anchor Persisted Chain PASS KEEP  
**任务性质：** Multi-Anchor Contract Amendment / No Business Threshold Change

# 1. 目标

修复 R11 新发现的 cardinality P0：

```text
Runtime 可以创建多个 Anchor
但 persisted D1 state 只能保存一个 Anchor
```

R12A 只冻结 Multi-Anchor 状态模型与投影边界。

# 2. V1 不得原地修改

保留：

```text
config/v4_12_frozen_snapshot_contract_v1.json
```

新增：

```text
config/v4_12_frozen_snapshot_contract_v2.json
```

建议 contract_id：

```text
V4_12_FROZEN_D1_CANDIDATE_SNAPSHOT_V2
```

# 3. Top-level snapshot

每个 security snapshot 至少：

```text
snapshot_id
security_id
trade_date
revision
available_at

common_facts
global_state_observations

anchor_states[]

active_anchor_id
active_anchor_selection_quality
active_anchor_selection_reason

knowledge_lineage
AS_RECORDED
formal_accepted

contract_digest
entry_digest
source_runtime_manifest_digest
```

# 4. anchor_states[]

每个元素至少：

```text
anchor_id
anchor
event
facts
counter_state
counter_state_digest

state_observations:
    pullback
    recovery
    support
    acceptance

last_known_support_state
invalidation_facts
validity
stale

created_this_session
owning_episode_id
```

# 5. Anchor 不因 active selector 被裁剪

必须冻结：

```text
all anchors remain persisted
until contract-defined terminal lifecycle permits historical closure
```

`active_anchor_id` 是只读投影。

# 6. Merge 规则

```text
prior anchor_states
+
same-day newly created anchors
=
current anchor_states
```

同 anchor_id 复用 immutable Anchor fact；不同 anchor_id 平行存在。

# 7. New Anchor 时序

same-day new Anchor：

```text
created_this_session = true
post_creation_market_sessions = 0
post_creation_evaluable_sessions = 0
held_count = 0
breach_count = 0
recovery_held_count = 0
test_count = 0

support = IDLE
cannot self-confirm
```

# 8. Owning episode binding

每个 event/episode 必须冻结：

```text
owning_anchor_id
```

active_anchor 改变不得改变 owning_anchor。

# 9. active_anchor selector

继承 frozen：

```text
not invalidated
distance_to_C / ATR ascending
anchor_trade_date descending
anchor_id ascending
```

不得第二套顺序。

# 10. Selector UNKNOWN

冻结：

```text
0 eligible anchors
→ active_anchor_id = null
  quality = KNOWN
  reason = NO_ACTIVE_ANCHOR

1 eligible anchor
→ select directly

>1 eligible anchors
且 ranking keys 全可比较
→ deterministic select

>1 eligible anchors
任一必要 coordinate / ATR 不可比较
→ active_anchor_id = null
  quality = UNKNOWN
  reason = ACTIVE_ANCHOR_SELECTION_UNKNOWN
```

禁止数组 first-item fallback。

# 11. Security-level projection

Top-level：

```text
active_anchor_id
anchor_view_asof_t
support_state
acceptance_state
retest_count
last_known_support_state
invalidation_facts
```

来自 selected active Anchor。

完整 `anchor_states[]` 始终保留。

# 12. Transition identity

Anchor-specific transition 必须包含：

```text
security_id
anchor_id
event_id
machine
trade_date
revision
from_state
to_state
```

logical identity 至少绑定：

```text
security_id + anchor_id + machine + trade_date
```

# 13. Global vs per-anchor machines

显式冻结：

```text
GLOBAL:
breakout / same-day structure creation

PER_ANCHOR:
pullback
recovery
support
acceptance
retention when event-specific
retest counters
invalidation
```

现有 AST 只支持 one-anchor context 时，R12B 对每个 anchor 构造 overlay 重复执行相同 frozen AST，不改阈值。

# 14. Contract validator

至少拒绝：

```text
scalar-only anchor snapshot
duplicate anchor_id
anchor/event mismatch
event owning anchor mutation
active selector order mutation
active selector first-item fallback
transition missing anchor_id
new anchor inherited nonzero counters
```

# 15. Protected

不得修改：

```text
R8/R9 contracts
machine AST
parameters
field authority
R10A Runtime Entry
R11 V1 snapshot contract
R11 evidence
Stage/Data Heads
```

# 16. 完成状态

只允许：

```text
V4_12_R12A_MULTI_ANCHOR_STATE_CONTRACT_V2_READY
```

local contract gate PASS 后进入 R12B。

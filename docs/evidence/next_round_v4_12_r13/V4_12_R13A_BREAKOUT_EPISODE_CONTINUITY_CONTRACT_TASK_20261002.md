# V4-12 R13A｜Breakout Episode Continuity Contract Freeze｜2026-10-02

**基线 HEAD：** `a74c42671774a6df389e78c014f9218844f74539`  
**R12 Multi-Anchor：** PASS KEEP  
**任务性质：** P0 Breakout lifecycle contract repair  
**业务阈值：** 禁止修改

# 1. 唯一目标

修复：

```text
breakout 被定义成 global machine
但 global common facts 不读取 t-1 breakout episode
```

导致的跨日 lifecycle 缺失。

# 2. 不允许返工

KEEP：

```text
Snapshot V2 anchor_states[]
per-anchor support/acceptance/pullback/recovery/retention
active selector
owning episode
R11 fresh-process snapshot mechanism
R8 Source Authority
R9 Time Counter
69 / 33 / 12 / 10 vectors
```

# 3. 新增 Breakout Episode Contract

新增 versioned contract，例如：

```text
config/v4_12_breakout_episode_contract_v1.json
```

contract_id：

```text
V4_12_BREAKOUT_EPISODE_CONTINUITY_V1
```

# 4. 强制拆分

## 4.1 Creation Detector

只在：

```text
active_breakout_episode == NONE
```

时运行 no-event 分支：

```text
breakout_trigger
near_high20
```

输出：

```text
BREAKOUT_TENTATIVE
APPROACHING
NO_BREAKOUT
UNKNOWN
```

## 4.2 Existing Episode Lifecycle

存在 active breakout episode 后，禁止再走 no-event 创建逻辑。

只运行 frozen AST existing-event 分支：

```text
FAILED_BREAKOUT
BREAKOUT_ACCEPTED
TESTING
BREAKOUT_TENTATIVE
UNKNOWN
```

# 5. Owner Anchor

§10J 明确新 breakout 产生：

```text
PRIOR_HIGH Anchor
```

因此优先冻结：

```text
Basic Breakout Episode
owning_anchor_type = PRIOR_HIGH
```

`BREAKOUT_LEVEL` 继续作为完整 Structure Anchor 保存。

若项目选择不同但等价 owner 规则，必须同时满足：

```text
唯一
deterministic
不是 active_anchor
不是数组 first item
与 §10J 一致
可独立验证
```

# 6. Episode Identity

至少：

```text
breakout_episode_id
event_id
security_id
owning_anchor_id
created_trade_date
state
validity
prior_episode_ref
last_observation_ref
```

owning Anchor 不因 active display Anchor 改变。

# 7. Prior binding

t 日 Existing Episode 必须从：

```text
t-1 Snapshot
```

冻结并恢复：

```text
prior_breakout_exists = true
prior_support_state
post_creation_market_sessions
post_creation_evaluable_sessions
held_count
touch / zone context
hard invalidation
owning anchor/event identity
```

禁止：

```text
binder.bind(security_id, None)
```

作为 Existing Episode lifecycle 的 prior source。

# 8. Duplicate creation guard

必须冻结：

```text
active breakout episode exists
→ breakout_trigger today cannot create a second breakout episode
```

只有：

```text
no active episode
```

才可创建。

终止后的 later trigger 可以建立新 episode。

# 9. Same-day revision

t 的：

```text
r1 / r2 / r3
```

共享：

```text
t-1 breakout_episode predecessor
```

same-day revision parent 不得变成 prior-session state。

# 10. Security-level Basic Breakout Projection

正式 Security candidate 必须提供：

```text
basic_breakout_state
breakout_episode_id
breakout_owner_anchor_id
breakout_projection_quality
breakout_projection_reason
```

与 frozen output schema 对齐。

# 11. Transition identity

Episode lifecycle transition：

```text
security_id
breakout_episode_id
event_id
owning_anchor_id
trade_date
revision
from_state
to_state
prior_session_state_ref
```

在没有 episode 的：

```text
APPROACHING / NO_BREAKOUT
```

detector observation 可以没有 event/anchor。

# 12. Breakout Episode terminal semantics

至少冻结：

```text
FAILED_BREAKOUT
```

为当前 episode terminal observation。

terminal episode 不再阻止未来新的 breakout trigger 建立新 episode。

不得删除历史 episode evidence。

# 13. Contract hard vectors

至少：

```text
C01 no event/no trigger -> NO_BREAKOUT
C02 no event/near -> APPROACHING
C03 trigger -> tentative + owner
C04 existing tentative -> retained tentative
C05 touch -> TESTING
C06 2 holds -> ACCEPTED
C07 broken/invalidated -> FAILED
C08 failed + later trigger -> new episode
C09 active + trigger true -> no duplicate
C10 active display switch -> owning Anchor unchanged
C11 r1/r2/r3 same t-1 predecessor
C12 unknown evaluability -> UNKNOWN/no creation
```

# 14. Independent contract gate

必须拒绝：

```text
existing episode without t-1 ref
active episode + duplicate creation
owner_anchor = active_anchor implicit alias
transition without episode identity
same-day revision as prior-session predecessor
BREAKOUT_ACCEPTED on creation day
UNKNOWN treated as no-event FALSE
```

# 15. Protected

不得修改：

```text
R8/R9 contracts
machine AST thresholds/order
parameter values
R10A Runtime Entry
R11 evidence
R12 Snapshot V2 contract/evidence
Stage/Data Heads
```

如需要 snapshot extension：

```text
新增 version / extension contract
```

不得回写 R12 V2 evidence。

# 16. 完成状态

只允许：

```text
V4_12_R13A_BREAKOUT_EPISODE_CONTINUITY_CONTRACT_READY
```

local gate PASS 后进入 R13B。

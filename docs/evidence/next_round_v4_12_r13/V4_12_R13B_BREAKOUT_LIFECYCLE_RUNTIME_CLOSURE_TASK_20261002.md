# V4-12 R13B｜Breakout Lifecycle Runtime Closure｜2026-10-02

**前置：** R13A Contract local PASS  
**任务性质：** Scoped engineering lifecycle closure  
**Stage/Data Heads：** KEEP

# 1. 目标

让 `Basic Breakout State` 真正实现：

```text
no active event detector
→ creation
→ persisted episode
→ t+1 lifecycle
→ TESTING / ACCEPTED / FAILED
→ terminal
→ later new episode
```

# 2. Runtime 结构

MultiAnchor Runtime 继续：

```text
common F0 bind once
anchor_states[] independent
active selector independent
```

新增/修复：

```text
breakout episode state
```

不能把整个 MultiAnchor Runtime 推翻。

# 3. Existing Episode Context

存在 breakout episode 时：

```text
load t-1 owning Anchor state
build breakout-owner overlay
restore t-1 breakout state
run same frozen breakout AST
```

必须使：

```text
prior_breakout_exists = KNOWN TRUE
```

来自 t-1 frozen episode，而不是人工 hardcode。

# 4. No-event Detector

只有：

```text
no active breakout episode
```

才运行：

```text
breakout_trigger
near_high20
```

并决定是否创建新 episode。

# 5. Creation

首次 trigger：

```text
basic_breakout_state =
BREAKOUT_TENTATIVE

owner Anchor =
R13A frozen owner rule

creation day:
cannot TESTING by same-day new Anchor
cannot BREAKOUT_ACCEPTED
```

# 6. Duplicate creation

硬门：

```text
active episode exists
AND breakout_trigger = TRUE
```

必须：

```text
0 new breakout episodes
0 duplicate owner Anchor for Basic Breakout lifecycle
```

原有 Structure Anchor 集合不被裁剪。

# 7. Existing lifecycle

至少证明：

```text
T0 trigger
  -> BREAKOUT_TENTATIVE

T+1 no touch/no acceptance
  -> BREAKOUT_TENTATIVE

T+1 touch
  -> TESTING

after 2 consecutive evaluable holds
  -> BREAKOUT_ACCEPTED

owner Anchor BROKEN/INVALIDATED
  -> FAILED_BREAKOUT
```

全部来自 frozen AST existing-event branch。

# 8. After terminal

FAILED episode：

```text
kept as historical evidence
active_breakout_episode = NONE
```

之后新的 valid trigger：

```text
new breakout_episode_id
new owning Anchor
```

不得复活旧 episode。

# 9. General active_anchor independence

必须证明：

```text
security active_anchor
```

可以是：

```text
Impulse / Gap / other Structure Anchor
```

但：

```text
Basic Breakout Episode owner
```

仍保持创建时 owning Anchor。

# 10. Same-day revisions

同一 trade_date：

```text
r1 / r2 / r3
```

都读取同一个：

```text
t-1 breakout episode ref
```

若 r2 source correction 撤销 current breakout observation：

```text
append revision evidence
```

不得重写 t-1。

# 11. Security projection

正式 candidate/readback 至少：

```text
basic_breakout_state
breakout_episode_id
breakout_owner_anchor_id
breakout_projection_quality
breakout_projection_reason
```

并与：

```text
global_state_observations.breakout
```

一致。

# 12. Transition

Breakout transition 必须携带：

```text
episode_id
event_id
owning_anchor_id
from_state
to_state
```

不再接受：

```text
global breakout transition
anchor_id = null
event_id = null
```

当 observation 是无 episode 的 APPROACHING/NO_BREAKOUT 时除外。

# 13. Independent persisted oracle

禁止调用 Runtime breakout projection helper 生成 expected。

Hand-written path 至少：

```text
E01-E12
```

并通过 fresh-process：

```text
day T write
→ process exit
→ day T+1 read
```

验证。

# 14. Regression

全部继续通过：

```text
316 R12 scoped tests or equivalent superseding suite
11 active selector vectors
12 R12 hard cases
69 business vectors
33 sequence steps
12 authority vectors
10 time-domain vectors
R11 persisted/output tests
```

# 15. Real replay

2026-09-29 → 2026-09-30：

```text
raw_fallback = 0
provider_replacement = 0
V4_11_candidate_substitution = 0
AS_RECORDED = false
formal_accepted = false
```

真实数据 capability 不足时继续 UNKNOWN。

# 16. Heads / 禁止

保持：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

禁止：

```text
V4_12_ACCEPTED_HEAD
V4-13
D2
Radar
Focus
Production
Shadow
formal DB migration
```

# 17. 完成状态

只允许：

```text
V4_12_R13B_BREAKOUT_LIFECYCLE_RUNTIME_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

统一 commit + push 后 STOP。

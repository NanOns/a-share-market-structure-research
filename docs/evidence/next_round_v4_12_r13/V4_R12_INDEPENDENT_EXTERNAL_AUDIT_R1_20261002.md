# V4 R12 独立外部验收审计 R1｜2026-10-02

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**R12 基线 HEAD：** `5bc34c907bd5d39f322c315db34c7788d61f0bbc`  
**R12 tested source：** `a145312256c4f5b5fb98409dc28ad4b0e10589cf`  
**当前远端 HEAD：** `a74c42671774a6df389e78c014f9218844f74539`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

# 1. 唯一总裁决

```text
V4_R12_EXTERNAL_AUDIT =
PARTIAL_PASS_R13_BREAKOUT_EPISODE_CONTINUITY_REQUIRED

R12_MULTI_ANCHOR_SNAPSHOT_V2 =
PASS_KEEP

R12_PER_ANCHOR_STATE_CONTINUITY =
PASS_KEEP

R12_ACTIVE_ANCHOR_SELECTOR =
PASS_KEEP

R12_OWNING_EPISODE_BINDING =
PASS_KEEP

R12_GLOBAL_BREAKOUT_LIFECYCLE =
FAIL_P0

R12_BREAKOUT_DUPLICATE_CREATION_GUARD =
FAIL_P0

R12_BASIC_BREAKOUT_SECURITY_PROJECTION =
FAIL_P1

V4_12_RUNTIME_EXTERNAL_ACCEPTANCE =
BLOCKED_R13

V4_12_STAGE_ACCEPTED_HEAD =
NOT_AUTHORIZED
```

R12 不是推倒重来。Multi-Anchor 的 cardinality、per-anchor counters/state、active selector、owning episode、fresh-process persistence 均已真实实现。

剩余唯一核心缺口是：

> `Basic Breakout State` 被 R12 定义为 security/global machine，但它没有消费昨天的 breakout episode；因此“已有 breakout 事件”的 TESTING / ACCEPTED / FAILED / 保留 TENTATIVE 分支没有真正跨日闭环。

---

# 2. R12 已通过并 KEEP 的内容

## 2.1 Snapshot V2

新增：

```text
config/v4_12_frozen_snapshot_contract_v2.json
```

使用：

```text
anchor_states[]
```

而不是 R11 的标量 `anchor/event`。

V1 未被原地修改。

## 2.2 MultiAnchorEngine

真实 Runtime 已落地：

```text
src/workbench_analysis/v4_12_multi_anchor_engine.py
src/workbench_analysis/v4_12_multi_anchor_state.py
src/workbench_analysis/v4_12_frozen_snapshot_v2.py
```

不是仅脚本 evidence。

## 2.3 多 Anchor 跨日

Synthetic 已证明：

```text
2026-09-23:
2 anchors

2026-09-29:
old anchors + 2 new breakout anchors
= 4 anchors

2026-09-30:
4 anchors retained
```

满足：

```text
old ∪ new
```

而不是覆盖。

## 2.4 Per-anchor 独立

每个 Anchor 独立保存：

```text
counter_state
support
acceptance
pullback
recovery
retention
invalidation
last_known_support
owning event
```

一个 Anchor 失效不再删除另一个。

## 2.5 active_anchor selector

已真实实现：

```text
not invalidated
distance_to_C / ATR ASC
anchor_date DESC
anchor_id ASC
```

并有 11 个独立 literal vectors：

```text
ZERO
SOLE_BAD_COORDINATE
DISTANCE
DATE_TIE
ID_TIE
TERMINAL_EXCLUDED
UNKNOWN_COORDINATE
UNKNOWN_ATR
ZERO_ATR
UNKNOWN_ELIGIBILITY
REVERSED_ARRAY
```

多个候选不可比较时：

```text
ACTIVE_ANCHOR_SELECTION_UNKNOWN
```

没有 first-item fallback。

## 2.6 Owning Episode

`owning_anchor_id / owning_episode_id` 与 active display Anchor 分离。

active selector 切换不会改 episode 的 owning Anchor。

以上全部 KEEP。

---

# 3. 测试与 seal

R12 handoff：

```text
316 tests
0 failures
0 errors
0 skipped
5 deselected
```

tested source：

```text
a145312256c4f5b5fb98409dc28ad4b0e10589cf
```

最终 HEAD：

```text
a74c42671774a6df389e78c014f9218844f74539
```

tested source → final HEAD 只变化：

```text
reports/v4_12_runtime_r12/R12_RUNTIME_HANDOFF.json
reports/v4_12_runtime_r12/R12_TEST_RESULTS.xml
```

没有测试后业务代码变化。

GitHub 当前：

```text
statuses = []
workflow runs = []
```

因此不声称 CI 背书。

---

# 4. 新 P0｜breakout 被定义成 global，但 global 不读 prior snapshot

V2 Contract：

```text
global_machines = [
  breakout,
  same_day_creation
]

per_anchor_machines = [
  pullback,
  recovery,
  support,
  acceptance,
  retention
]
```

也就是说：

```text
breakout
```

没有进入 per-anchor lifecycle。

---

# 5. MultiAnchorEngine 的 global breakout 明确不绑定昨天状态

当前：

```python
prior = self.binder.prior(prior_snapshot, security_id)

common = self.binder.bind(
    security_id,
    None
)

base = self.evaluate_context(
    security_id,
    common,
    None,
    create=True
)
```

注意：

```text
prior 已读取
```

但 global common bind 明确传：

```text
prior_snapshot = None
```

因此 Global Breakout 使用的 common facts 中：

```text
prior_breakout_exists
prior_support_state
post_creation_* context
...
```

不会来自昨天的 Snapshot V2。

---

# 6. Field Registry 又明确要求 breakout 必须读 t-1 D1

`prior_breakout_exists`：

```text
field_role = FROZEN_PRIOR_D1
time_role = T_MINUS_1
required_by =
  breakout.BREAKOUT_ACCEPTED
  breakout.FAILED_BREAKOUT
  breakout.RETAIN_TENTATIVE
  breakout.TESTING
```

这不是 optional decoration。

它正是已有 breakout 生命周期的核心输入。

---

# 7. Machine AST 证明已有事件分支全部依赖 prior_breakout_exists

Breakout AST 顺序：

```text
1 evaluable false -> UNKNOWN

2 prior_breakout_exists
  AND prior_support_state BROKEN/INVALIDATED
  -> FAILED_BREAKOUT

3 prior_breakout_exists
  AND old enough
  AND (HELD_CONFIRMED OR held_count >= 2)
  -> BREAKOUT_ACCEPTED

4 prior_breakout_exists
  AND old enough
  AND touch
  -> TESTING

5 prior_breakout_exists
  -> BREAKOUT_TENTATIVE

6 breakout_trigger
  -> BREAKOUT_TENTATIVE

7 near_high20 == NEAR
  -> APPROACHING
```

所以：

```text
没有 t-1 prior_breakout_exists
```

就不可能正确运行“已有事件”分支。

---

# 8. 最高合同 §10J 明确要求这条跨日生命周期

§10J：

```text
无活动breakout事件：
触发 -> BREAKOUT_TENTATIVE + PRIOR_HIGH Anchor

已有事件：
BROKEN/INVALIDATED -> FAILED_BREAKOUT
HELD_CONFIRMED / 2连续可评估守住 -> BREAKOUT_ACCEPTED
touch -> TESTING
否则 -> BREAKOUT_TENTATIVE
```

因此：

```text
breakout 不是纯当日 detector
```

它同时是跨日 episode state machine。

---

# 9. 9/29 创建成功不代表 9/30 lifecycle 成功

R12 synthetic 在 9/29 可以创建：

```text
PRIOR_HIGH
BREAKOUT_LEVEL
```

是因为 Anchor creation loop 直接检查：

```text
breakout_trigger
```

但这不能证明：

```text
9/30 Basic Breakout State
```

知道 9/29 已经存在 breakout event。

这是两个不同问题：

```text
creation detector
!=
existing event lifecycle
```

---

# 10. 另一个 P0｜已有 active breakout 时没有阻止重复创建

最高合同：

```text
无活动 breakout 事件
才执行新 breakout 创建
```

但当前 global creation：

```text
base.evaluate_context(... create=True)
```

不会使用 prior breakout episode。

只要下一天：

```text
breakout_trigger = TRUE
```

就仍可能再次创建：

```text
PRIOR_HIGH
BREAKOUT_LEVEL
```

即：

```text
existing active breakout
+ breakout_trigger still true
→ duplicate breakout episode creation
```

这与 §10J 的 no-active-event gate 冲突。

---

# 11. R12 validator 为什么没发现

R12 validator 对 Multi-Anchor 的 hand-written BOOK 重点验证：

```text
anchor count
per-anchor states
active selector
owning episode
transition identities
```

但没有给：

```text
basic_breakout_state
```

定义一条 hand-written 跨日 lifecycle oracle。

R12 real replay 全 UNKNOWN 也无法暴露该问题。

所以：

```text
316 PASS
```

不能证明 Breakout Continuity 正确。

---

# 12. P1｜security projection 没有正式 basic_breakout_state

V2 `security_projection` 当前包括：

```text
active_anchor_id
anchor_view_asof_t
support_state
acceptance_state
retest_count
last_known_support_state
invalidation_facts
basic_pullback_state
basic_recovery_state
```

缺：

```text
basic_breakout_state
```

而 frozen output schema / §10J 要求它属于 V4-12 的正式结构输出。

当前只在：

```text
global_state_observations.breakout
```

保存一个 observation，不等于完成 security-level API projection。

---

# 13. R13 修复原则

不返工：

```text
Snapshot V2 cardinality
MultiAnchorEngine common-F0-once
per-anchor overlays
active selector
owning episode
R11 fresh-process mechanism
R11 transition/output closure
R8/R9 authority and time semantics
```

只修：

```text
Breakout Episode Continuity
```

---

# 14. 正确架构：Detector 与 Episode Lifecycle 分离

冻结两层：

## Breakout Creation Detector

仅在：

```text
NO_ACTIVE_BREAKOUT_EPISODE
```

时允许：

```text
breakout_trigger
near_high20
```

决定：

```text
BREAKOUT_TENTATIVE / APPROACHING / NO_BREAKOUT
```

## Breakout Episode Lifecycle

一旦创建 breakout event：

```text
owning Anchor 固定
```

后续每市场日从 t-1 frozen episode 读取：

```text
prior_breakout_exists = true
prior_support_state
held_count
post_creation_market_sessions
touch
...
```

运行现有 frozen breakout AST 的 existing-event 分支。

---

# 15. Basic Breakout Episode 的 owning Anchor

最高合同 §10J 明确：

```text
breakout trigger
→ PRIOR_HIGH Anchor
```

因此建议冻结：

```text
Basic Breakout Episode owner Anchor type =
PRIOR_HIGH
```

`BREAKOUT_LEVEL` 可以继续作为独立 Structure Anchor 保存，但：

```text
Basic Breakout State
```

不能在每天随机切到另一 Anchor。

如果实现方认为不能直接冻结 PRIOR_HIGH owner，则必须在 R13A 给出与 §10J 一致的等价、唯一、可验证 owner 规则；禁止数组首项或 active_anchor 替代。

---

# 16. Breakout Episode Snapshot

R13 Snapshot extension 至少保存：

```text
breakout_episode:
  episode_id
  event_id
  owning_anchor_id
  created_trade_date
  state
  validity
  prior_episode_ref
  last_observation_ref
```

同日 revision：

```text
r1 / r2 / r3
```

都使用同一个：

```text
t-1 breakout episode
```

不得 r1 -> r2 作为 prior-session state。

---

# 17. 必测状态链

至少：

```text
E01 no event + no trigger
→ NO_BREAKOUT

E02 no event + near high
→ APPROACHING

E03 no event + trigger
→ BREAKOUT_TENTATIVE
→ create PRIOR_HIGH owner
→ same-day cannot accept

E04 existing tentative + no touch
→ BREAKOUT_TENTATIVE

E05 existing + touch
→ TESTING

E06 existing + 2 consecutive evaluable holds
→ BREAKOUT_ACCEPTED

E07 owning Anchor BROKEN/INVALIDATED
→ FAILED_BREAKOUT

E08 failed episode + later new trigger
→ new episode allowed

E09 active existing episode + trigger still TRUE
→ NO duplicate episode

E10 general active_anchor switches to impulse/gap
→ breakout owning Anchor unchanged

E11 same-day r1/r2/r3
→ same t-1 breakout predecessor

E12 missing/evaluable UNKNOWN
→ UNKNOWN observation
→ no fabricated new event
```

---

# 18. Transition

Breakout lifecycle transition 必须带：

```text
event_id
owning_anchor_id
from_state
to_state
prior_session_state_ref
```

不得继续：

```text
global_breakout_has_null_anchor_and_event = true
```

对于：

```text
APPROACHING / NO_BREAKOUT
```

这种尚无 episode 的 detector observation，可以没有 event/anchor。

一旦进入：

```text
BREAKOUT_TENTATIVE / TESTING / BREAKOUT_ACCEPTED / FAILED_BREAKOUT
```

必须绑定 episode identity。

---

# 19. Real replay

真实 2026-09-29 → 09-30 当前仍可：

```text
0 breakout episodes
UNKNOWN
```

只要 formal capability 仍 blocked。

不得为了让 breakout 状态变丰富而：

```text
raw recompute
provider replacement
V4-11 candidate substitute
```

---

# 20. 当前 Heads

保持：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_11_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

仍禁止：

```text
V4_12_ACCEPTED_HEAD
V4-13 Runtime
D2
Radar
Focus
Production
Shadow
formal DB migration
```

---

# 21. 下一步

```text
R13A
Breakout Episode Continuity Contract Freeze

→ local gate PASS

R13B
Breakout Lifecycle Runtime Closure

→ unified commit + push
→ STOP
```

R13 外审通过后，才允许：

```text
V4-12 scoped engineering Accepted Head Promotion
Stage Head -> V4_00_TO_V4_12_ACCEPTED
V4-13 Stage Entry
```

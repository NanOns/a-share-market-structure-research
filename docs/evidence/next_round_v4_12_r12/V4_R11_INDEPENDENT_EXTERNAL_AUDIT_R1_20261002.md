# V4 R11 独立外部验收审计 R1｜2026-10-02

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**R11 基线 HEAD：** `7d35478780003d866faf85a730d0bb3b86af1134`  
**tested source：** `025bbe7dbb8302c614fc315ec1830aeb19da6087`  
**当前远端 HEAD：** `5bc34c907bd5d39f322c315db34c7788d61f0bbc`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

# 1. 唯一总裁决

```text
V4_R11_EXTERNAL_AUDIT =
PARTIAL_PASS_R12_MULTI_ANCHOR_CLOSURE_REQUIRED

R11A_PERSISTED_FROZEN_D1_CHAIN =
PASS_SINGLE_ANCHOR_SCOPE

R11B_TRANSITION_OUTPUT_PROJECTION =
PASS_SINGLE_ANCHOR_SCOPE

V4_12_MULTI_ANCHOR_PERSISTENCE =
FAIL_P0

V4_12_PER_ANCHOR_STATE_CONTINUITY =
FAIL_P0

V4_12_ACTIVE_ANCHOR_SELECTOR =
NOT_IMPLEMENTED_P0

V4_12_RUNTIME_EXTERNAL_ACCEPTANCE =
BLOCKED_R12

V4_12_STAGE_ACCEPTED_HEAD =
NOT_AUTHORIZED
```

R11 已真正修复 R10 的跨日落盘链，并完成 Observation / Transition、retest_count、invalidation_facts、last_known_support_state 的单 Anchor 闭环。

新的阻塞来自更高一层合同边界：

> 最高合同要求“每个 Anchor 分别跟踪，active_anchor 只是展示投影”；当前 Runtime 仍然只有单 Anchor 状态容器。

# 2. R11A｜Persisted fresh-process chain 已真实落地

新增真实 Runtime：

```text
src/workbench_analysis/v4_12_frozen_snapshot.py
```

并修改 Binder / StructureEngine。

现在已经可完成：

```text
D1[t]
→ frozen snapshot bundle
→ process exit
→ fresh process
→ InputBinder.prior()
→ D1[t+1]
```

Snapshot bundle 具备 exact manifest / row digest / security index / counter state / facts / anchor-event / state observations / lineage。

same-day r1/r2/r3 也保持同一 t-1 predecessor。

这部分 KEEP。

# 3. R11B｜Observation / Transition 修复已成立

当前 Runtime 已拆分：

```text
state_observations
state_transitions
```

Transition 只对：

```text
breakout
pullback
recovery
support
acceptance
```

生成；retention 已排除。

生成条件：

```text
prior KNOWN
AND current KNOWN
AND current != prior
```

真实 2026-09-29 / 2026-09-30：

```text
state observation rows/day = 31,344
state transition rows/day = 0
```

# 4. Output projection 修复已成立

R11 已真实修复：

```text
retest_count
invalidation_facts
last_known_support_state
```

并验证 TESTING→RECLAIMED、RECLAIMED→HELD_TENTATIVE、known→missing、missing→resume、deep breach→invalidation facts。

这些在单 Anchor 范围内 PASS。

# 5. 测试与 seal

```text
290 PASS
0 FAIL
0 ERROR
0 SKIP
5 DESELECT
```

tested source：

```text
025bbe7dbb8302c614fc315ec1830aeb19da6087
```

最终 HEAD 只比 tested source 多 handoff/test evidence，无业务代码继续变化。

GitHub 当前无额外 status/workflow，不声称 CI 背书。

# 6. 新 P0｜Runtime 只持久化一个 Anchor

最高合同 §41A.3：

```text
每个 Anchor 分别跟踪
active_anchor 仅按冻结排序供页面展示
研究 episode invalid_if 使用创建时绑定 Anchor
不能随 active_anchor 切换
```

当前 Snapshot Contract V1 却是标量：

```text
anchor
event
counter_state
state_observations
```

没有 `anchor_states[]` / per-anchor state set。

# 7. Synthetic 已真实创建多个 Anchor

R11 synthetic 2026-09-23 实际创建：

```text
BULLISH_IMPULSE_BODY
BULLISH_IMPULSE_LOW
```

`anchors.jsonl` 有 2 条，`events.jsonl` 有 2 条。

多 Anchor 已经是 Runtime 真实情况，不是理论边界。

# 8. SnapshotMaterializer 只保存第一个

当前实现等价于：

```python
anchor =
    prior.anchor
    if prior has anchor
    else result['anchors'][0]
```

因此 creation day：

```text
2 anchors created
→ snapshot only retains anchors[0]
```

第二个 Anchor 不进入下一日状态链。

# 9. 更严重：已有旧 Anchor 时，新 Anchor 会被丢弃

只要存在 prior anchor，即使今天创建新的 breakout / impulse / gap anchor：

```text
snapshot 仍只保存 prior anchor
```

因此：

```text
old anchor exists
+ new anchor created today
→ new anchor not carried to tomorrow
```

这是 V4-12 核心 P0。

# 10. Validator 没覆盖多 Anchor

当前 independent validator 只保存：

```python
synthetic_anchor = r['anchor']
```

随后证明这个单一 Anchor 一直存在。

它没有验证：

```text
all created anchors survive
per-anchor counters survive
per-anchor support/acceptance survive
new anchors merge with old anchors
```

所以 R11 PASS 只能限定在 Single-Anchor Scope。

# 11. Binder / Engine 仍是单 Anchor 模型

SyntheticBinder 当前：

```text
anchor = prior[0]['anchor']
```

StructureEngine 当前：

```text
bound_anchor = bound.get('anchor')
active_anchor_id = bound_anchor.anchor_id
```

实际把 bound Anchor 直接当 active Anchor。

并没有真正执行 frozen：

```text
active_anchor_sort =
1. not invalidated
2. distance_to_C / ATR ascending
3. anchor_date descending
4. anchor_id ascending
```

因此：

```text
V4_12_ACTIVE_ANCHOR_SELECTOR = NOT_IMPLEMENTED
```

# 12. 为什么不能 Stage Accept

如果现在推进 V4-12 Accepted Head，系统只能正确处理“一只股票只有一个 Anchor”。

但正式生态允许：

```text
Impulse BODY
Impulse LOW
Prior High
Breakout Level
Gap
Pivot
Dynamic MA
...
```

同时存在。

单 Anchor 会造成：

```text
Anchor 丢失
Support / Retest 状态丢失
Episode invalidation 绑定错误
active display 与 owning Anchor 混淆
新事件无法进入旧结构集合
```

# 13. R12 修复原则

R12 不修改：

```text
R8 Source Authority
R9 Time Counter
R10A Runtime Entry
R11 persisted bundle机制
R11 transition predicate
R11 retest/invalidation/last-known projection
business AST
parameter values
```

只把：

```text
single-anchor runtime state
```

升级成：

```text
multi-anchor episode state set
```

# 14. Snapshot 必须升级为 V2

禁止原地修改 V1。

新增：

```text
V4_12_FROZEN_D1_CANDIDATE_SNAPSHOT_V2
```

V2 至少：

```text
anchor_states[]
```

每个 state 独立保存：

```text
anchor
event
facts
counter_state
state_observations
last_known_support_state
invalidation_facts
validity
```

# 15. 每个 Anchor 独立评价

Runtime：

```text
bind common F0 once

for each prior anchor:
    build anchor-specific overlay
    evaluate support / acceptance / pullback / recovery
    persist counters and transitions

evaluate same-day creation rules
append all new anchors
new anchor today = IDLE / no self-confirm
```

# 16. active_anchor 是投影，不是裁剪

所有 Anchor 都保留。

`active_anchor_id` 仅按 frozen sort 投影。

若多个候选的 ranking key 无法完整比较：

```text
active_anchor_id = null
ACTIVE_ANCHOR_SELECTION_UNKNOWN
```

不得数组 first-item fallback。

# 17. Episode invalidation 绑定 owning Anchor

active display Anchor 可以变化，但 event A 的 invalid_if 永远消费 A 的 owning Anchor。

Per-anchor transition identity 必须加入 `anchor_id/event_id`。

# 18. R12 必测

至少：

1. BODY + LOW 同日创建并跨日均保留；
2. 两 Anchor 独立 Support 状态；
3. 旧 Anchor + 新 Breakout Anchor 合并；
4. 一个 INVALIDATED，另一个有效；
5. active distance 排序；
6. date tie-break；
7. anchor_id tie-break；
8. selector UNKNOWN fail-closed；
9. active 切换不改 owning episode；
10. new anchor no self-confirm；
11. same-day revisions 共享同一 t-1 set；
12. real replay authority 不变；
13. R8–R11 regression 全部 KEEP。

# 19. Heads

继续：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

禁止 V4_12_ACCEPTED_HEAD / V4-13 / D2 / Radar / Focus / Production / Shadow / 正式 DB migration。

# 20. 下一步

```text
R12A
Multi-Anchor State Contract V2 Freeze

→ local contract gate PASS

R12B
Multi-Anchor Runtime + Active Selector E2E

→ unified commit + push
→ STOP
```

R12 外审通过后，再进入 V4-12 Accepted Head Promotion + V4-13 Stage Entry。

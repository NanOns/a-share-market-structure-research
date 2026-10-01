# V4-11 R3B｜Episode / Safety / LOO Input Closure 任务卡｜2026-10-02

**优先级：** P0 Mainline  
**依赖：** R3A 可并行开发，但最终 replay 必须绑定 R3A sealed producer set。  
**Stage/Data Head：** KEEP

## 1. 目标

闭环不能仅由普通日线 factor 直接产生的 required facts：

```text
pullback_episode_confirmed
common safety facts
current_with_loo_breadth_support
prior-session episode/state facts
```

## 2. Pullback Episode

必须从明确 upstream episode source 构造。

要求：

```text
episode_id
episode start
prior-session status
producer contract
parameter set
publication id
source publication ids
knowledge cutoff
```

不得从 same-day Final State 反推。

如果 exact legacy episode 无法从当前 accepted upstream 重构：

```text
STRONG_PULLBACK = DIAGNOSTIC_ONLY
```

不得造一个兼容值。

## 3. Common Safety

所有会令多个 scenario UNKNOWN 的 safety predicates 必须逐项绑定 producer。

禁止：

```text
一个 COMMON_SAFETY=true
```

代替多项原始事实。

必须保留 exact legacy predicate identity。

## 4. TREND same-day LOO

对：

```text
CURRENT_WITH_LOO_BREADTH_SUPPORT
```

做 dependency graph。

只有在证明：

```text
pure upstream
target-day cutoff known
不消费 V4-11 D0
不消费 V4-10 D2 current result
不消费 Focus
不形成 same-day feedback
```

时，才允许升级为 formal candidate producer。

否则继续：

```text
TREND_CONTINUE = DIAGNOSTIC_ONLY
```

这不阻止其他 scenario 工程接受。

## 5. Scenario Capability Matrix

输出：

```text
LAUNCH_CONFIRM
RECOVERY_TURN
STRONG_PULLBACK
TREND_CONTINUE
```

分别：

```text
FORMAL_CANDIDATE
DIAGNOSTIC_ONLY
BLOCKED_UPSTREAM
```

禁止用“V4-11整体可用/不可用”掩盖场景差异。

## 6. Negative Tests

至少：

```text
same-day D2 feedback rejected
Focus input rejected
future episode rejected
same-day revision cannot become prior-session episode
fake episode id rejected
wrong producer rejected
wrong parameter set rejected
LOO circular dependency detected
diagnostic-only cannot enter formal D0
```

## 7. 完成状态

只允许：

```text
V4_11_R3B_EPISODE_SAFETY_LOO_CANDIDATE_READY
```

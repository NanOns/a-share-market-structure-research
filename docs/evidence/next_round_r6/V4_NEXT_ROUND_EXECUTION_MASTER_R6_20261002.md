# V4 下一轮执行总调度卡 R6｜2026-10-02

**外部验收：** `V4_11_EXTERNAL_ACCEPTANCE_PASS_R5_CAPABILITY_SCOPED_ENGINEERING`  
**审计 HEAD：** `1c46d6681ba1d0540551bcc0f75b35c545ff2769`  
**Accepted implementation：** `a8635c6802dc31e3c879207cd470bd63021e35ca`

# 1. 本轮只有一张执行卡

```text
V4_11_ACCEPTED_HEAD_PROMOTION_AND_V4_12_STAGE_ENTRY_TASK_R1_20261002.md
```

不要并行执行 V4-12 runtime implementation。

# 2. 执行目标

```text
V4-11 Accepted Head
+
Stage Head
V4_00_TO_V4_10_ACCEPTED
→
V4_00_TO_V4_11_ACCEPTED
+
V4-12 Structure / Anchor / Support Stage Entry
```

# 3. 本轮不做

```text
V4-12 D1 implementation
Anchor runtime
Breakout runtime
Pullback runtime
Recovery runtime
V4-13
Production
Shadow
Focus cutover
Data Head advance
```

# 4. 为什么 promotion 与 V4-12 实现分开

V4-12 是新的 D1 source-authority / temporal-DAG 模块。

当前合同 §81.4 要求实现前先具备：

```text
field registry
AST
parameter instance
producer/time semantics
source capability
UNKNOWN behavior
independent vectors
```

同时 V4-10 → V4-11 promotion precedent 已明确：Accepted Head mutation 不与下一阶段未经审计业务实现混在同一提交。

# 5. Heads

Promotion Validator PASS 前：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_10_ACCEPTED
```

PASS 后：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_11_ACCEPTED
```

始终：

```text
V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

# 6. Capability scope 不得扩大

V4-11 Accepted Head 保留：

```text
LAUNCH_CONFIRM     formal engineering capability
RECOVERY_TURN      formal engineering capability
STRONG_PULLBACK    diagnostic-only
TREND_CONTINUE     diagnostic-only

Event historical evidence =
RECONSTRUCTED_LEFT_CENSORED

FULL_D0_D1_D2_DAG =
NOT_IMPLEMENTED
```

# 7. V4-12 Entry scope

当前最高合同：

```text
V4-12 =
Structure / Anchor / Support
```

D1：

```text
F0[t] + t-1 frozen Anchor/event
→ Structure detector / invalidation facts
```

硬禁：

```text
D2[t] → D1[t]
same-day new Anchor → same-day confirmation
Focus/UI → D1
future → D1
```

# 8. 权限

全程：

```text
production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

# 9. 完成条件

```text
promotion validator PASS
V4_11_ACCEPTED_HEAD exists and exact
Stage Head = V4_00_TO_V4_11_ACCEPTED
Data Head unchanged
V4-12 Stage Entry exact
post-promotion readback PASS
```

然后：

```text
commit
push
STOP
```

等待下一轮独立审计。

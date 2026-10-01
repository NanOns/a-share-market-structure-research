# V4 下一轮执行总调度卡 R3｜2026-10-02

**审计基线：** `V4_R2_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R2_20261002.md`  
**实现基线：** `d119c0526e44a819f85b4917159d3eeb5daadf2a` 的当前远端 descendant  
**Stage Head：** `V4_00_TO_V4_10_ACCEPTED`  
**Data Head：** `2026-09-30`

# 1. 本轮共 7 张执行卡

## P0 主线

1. `V4_11_R3A_TARGET_DATE_REQUIRED_FACT_PRODUCERS_TASK_20261002.md`
2. `V4_11_R3B_EPISODE_SAFETY_LOO_INPUT_CLOSURE_TASK_20261002.md`
3. `V4_11_R3C_REAL_FULL_MARKET_DAG_REPLAY_TASK_20261002.md`

## P1 并行

4. `V4_A02_DOWNSTREAM_AMENDMENT_PROMOTION_TASK_20261002.md`
5. `V4_A05_V4_08_B2_SCOPED_AMENDMENT_PROMOTION_TASK_20261002.md`
6. `V4_A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTANCE_TASK_20261002.md`

## P2 并行治理

7. `V4_PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATION_TASK_20261002.md`

# 2. 执行顺序

允许：

```text
R3A || R3B
A02 || A05 || A04 || Parallel Consolidation
```

随后：

```text
R3A + R3B sealed
→ R3C
```

R3C 必须最后做真实 full-market DAG replay。

# 3. 主线原则

本轮不再修：

```text
AMR20 vs Amount-A namespace
```

该问题已外部 PASS。

本轮解决：

```text
target-date required facts producer capability
```

# 4. UNKNOWN 原则

允许真实 UNKNOWN。

禁止：

```text
因 producer 没实现而全量 UNKNOWN
```

R3 结束后 UNKNOWN 只能来自合法数据/时间/能力边界。

# 5. V4-12

本轮：

```text
V4-12 runtime implementation = NOT AUTHORIZED
```

但 R3C 外部验收一旦 PASS：

```text
立即发 V4-11 Promotion + V4-12 Entry
```

不得等待 Forward 样本积累。

# 6. Heads

默认：

```text
V4_DATA_ACCEPTED_HEAD = KEEP 2026-09-30
V4_STAGE_ACCEPTED_HEAD = KEEP V4_00_TO_V4_10_ACCEPTED
```

A02/A05/A04 只能创建 scoped/amendment heads，不得冒充主 Stage Head。

# 7. 权限

全程：

```text
production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

# 8. 结束

Codex 完成 7 卡后：

```text
统一 commit + push
STOP
等待独立外部验收
```

禁止自行：

```text
V4_11_ACCEPTED
V4_STAGE_ACCEPTED_HEAD -> V4_11
V4_12 runtime
PRODUCTION_READY
```

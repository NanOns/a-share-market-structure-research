# V4 下一轮全量执行总调度卡 R1｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**当前 Stage Head：** `V4_00_TO_V4_10_ACCEPTED`  
**当前 Data Head：** `2026-09-30`  
**本轮原则：** 主线继续开发，跨阶段修复并行；任何治理/真实数据积累项都不得阻塞 V4-11 工程开发。

## 1. 本轮执行卡总数

```text
9 张执行卡
+ 1 张本总调度卡
```

### 主线 P0
1. `V4_11_CONFIRMATION_EVENTS_IMPLEMENTATION_TASK_R1_20261001.md`

### 并行 P0/P1
2. `V4_A02_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_TASK_R2_20261001.md`
3. `V4_A03_FORWARD_PIT_HISTORY_ACCUMULATION_TASK_R2_20261001.md`
4. `V4_A04_AMOUNT_A_FORMAL_AUTHORITY_TASK_R2_20261001.md`
5. `V4_A05_LEGACY_VALID_MEMBER_EXACT_PRODUCER_TASK_R2_20261001.md`
6. `V4_OWNER_REGISTRY_SCOPED_BOOTSTRAP_TASK_R1_20261001.md`

### 并行 P2
7. `V4_A06_BAOSTOCK_BINDING_TOLERANCE_TASK_R2_20261001.md`
8. `V4_A07_HISTORICAL_AS_RECORDED_ADJUSTED_PRICE_TASK_R2_20261001.md`
9. `V4_HISTORICAL_PUBLICATION_READER_DI_HARDENING_TASK_R1_20261001.md`

## 2. 并行规则

允许：

```text
V4-11
||
A02
||
A03
||
A04
||
A05
||
Owner Registry Bootstrap
||
A06
||
A07
||
Historical Reader Hardening
```

但必须满足：

```text
同一 migration number 不得并发抢占
同一 Accepted Head 不得被两个工作包写
同一 source artifact 不得覆盖
历史 Accepted Head 只读
```

统一 migration allocator 是唯一编号来源。

## 3. 主线优先级

资源冲突时顺序：

```text
V4-11
> A02
> A03/A04/A05/Owner Bootstrap
> A06/A07/Reader Hardening
```

## 4. V4-12 禁止提前执行

本轮不得：

```text
实现 V4-12 Structure / Anchor / Support
推进 Stage Head 到 V4-11
```

V4-11 完成后必须先独立外部验收，再发 V4-11 promotion + V4-12 entry。

## 5. Data Head 与 Stage Head

本轮所有工作包默认：

```text
V4_DATA_ACCEPTED_HEAD = KEEP 2026-09-30
V4_STAGE_ACCEPTED_HEAD = KEEP V4_00_TO_V4_10_ACCEPTED
```

A03 可以继续积累新 PIT source/candidate，但不得自行推进正式 Data Head。

## 6. Production 权限

全程：

```text
production = false
shadow = false
focus_cutover = false
global_mandatory_adoption = false
```

## 7. 统一结束状态

每张卡完成后：

```text
CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

不得自行：

```text
EXTERNALLY_ACCEPTED
PROMOTED
PRODUCTION_READY
```

## 8. 本轮外部验收

Codex 全部提交后，下一轮外部验收按：

```text
A. V4-11 主线
B. A02～A05 + Owner Bootstrap
C. A06/A07/Reader Hardening
```

分组审计，但可以同一次提交。

# V4 下一轮执行总调度卡 R2｜2026-10-01

**基线 HEAD：** `66ef2e342dd339cc9795c2d1fd774b8edec4c345`  
**外部审计：** `V4_NEXT_ROUND_10_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md`

## 1. 本轮执行组成

```text
5 张执行任务卡
+ 本总调度卡
```

1. `V4_11_R2_AMR20_AMOUNT_A_SEMANTIC_REPAIR_TASK_20261001.md`
2. `V4_A02_ACCEPTANCE_FORMALIZATION_AND_DOWNSTREAM_AMENDMENT_TASK_R1_20261001.md`
3. `V4_A04_R3_AMOUNT_A_FORMAL_AUTHORITY_CLOSURE_TASK_20261001.md`
4. `V4_A05_ACCEPTANCE_AND_V4_08_B2_CAPABILITY_AMENDMENT_TASK_R1_20261001.md`
5. `V4_PARALLEL_SCOPED_ACCEPTANCE_FORMALIZATION_A03_A06_A07_OWNER_READER_TASK_R1_20261001.md`

## 2. 主线

P0：

```text
V4-11 R2 semantic repair
```

必须优先。

V4-12 本轮禁止。

## 3. 可并行

允许：

```text
V4-11 R2
||
A02 formalization/amendment
||
A04 R3
||
A05/V4-08 B2 amendment
||
A03/A06/A07/Owner/Reader formalization
```

## 4. Heads

默认：

```text
V4_DATA_ACCEPTED_HEAD = KEEP 2026-09-30
V4_STAGE_ACCEPTED_HEAD = KEEP V4_00_TO_V4_10_ACCEPTED
```

不得因并行项 formalization 自动移动业务 Stage Head。

## 5. 依赖

A02 accepted RPS input 在 formalization PASS 后可供后续 candidate replay 使用，但 V4-05/V4-07/V4-09 amendment heads 不得自行 promotion。

A05 exact producer formalization 后，V4-08 B2 amendment 只生成 candidate。

A04 不得阻塞 V4-11 R2。

## 6. Permissions

始终：

```text
production=false
shadow=false
focus=false
global_mandatory_adoption=false
```

## 7. 结束

本轮全部完成后 STOP，等待独立外部验收。

若 V4-11 R2 PASS，下一轮才允许：

```text
V4-11 Accepted Head promotion
V4-12 Stage Entry
```

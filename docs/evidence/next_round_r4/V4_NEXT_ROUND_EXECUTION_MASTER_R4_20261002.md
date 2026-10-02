# V4 下一轮执行总调度卡 R4｜2026-10-02

**外部审计依据：** `V4_R3_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md`  
**审计 HEAD：** `65774de20108beafaa15c0b557b4cd2ee58edb29`  
**Stage Head：** KEEP `V4_00_TO_V4_10_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

# 1. 本轮仅 2 张任务卡

1. `V4_11_R4A_ADJUSTMENT_BASIS_PARITY_REPAIR_TASK_20261002.md`
2. `V4_11_R4B_REAL_DAG_REBUILD_CAPABILITY_CLOSURE_TASK_20261002.md`

# 2. 执行顺序

严格：

```text
R4A
→ 9/24 V4-03 exact parity PASS
→ seal R4A
→ R4B
```

不得并行跳过 parity gate。

# 3. 本轮 P0

唯一主 blocker：

```text
R3 使用 qfq_mul/qfq_add literal equality
替代已接受 V4-03
price_basis + adjustment_source_revision
```

必须先修这个 semantic mismatch。

# 4. 不重做

以下全部 KEEP，不得返工：

```text
V4-10
R3B capability scoping
A02 amendments
A05 V4-08 B2 scoped amendment
A04 go-forward producer acceptance
A03/A06/A07/Owner/Reader consolidation
```

# 5. Heads / 权限

全程：

```text
V4_DATA_ACCEPTED_HEAD = KEEP
V4_STAGE_ACCEPTED_HEAD = KEEP
V4_11_ACCEPTED_HEAD = NOT CREATE
V4_12 = NOT EXECUTE

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

# 6. 结束

R4A + R4B 完成后：

```text
统一 commit + push
STOP
等待独立外部验收
```

若下一轮外部验收 PASS，才执行：

```text
V4-11 Accepted Head Promotion
→ V4_STAGE_ACCEPTED_HEAD 到 V4-11
→ V4-12 Stage Entry
```

# V4 下一轮执行总调度卡 R5｜2026-10-02

**外审依据：** `V4_R4_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md`  
**当前审计 HEAD：** `1dee36ae83fb63b6a7fe57e05ccb63bb1e0c5099`  
**Stage Head：** KEEP `V4_00_TO_V4_10_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

---

# 1. 本轮仅两张任务卡

1. `V4_11_R5A_OWNER_INPUT_AUTHORITY_PARITY_REPAIR_TASK_20261002.md`
2. `V4_11_R5B_D2_EVENT_REBUILD_CAPABILITY_CLOSURE_TASK_20261002.md`

---

# 2. 严格执行顺序

```text
R5A
→ 9/28 V4-07 / V4-09 exact owner parity PASS
→ seal R5A
→ R5B
→ unified commit + push
→ STOP
→ independent external re-audit
```

---

# 3. 唯一 P0

```text
R4B 从 raw/adjusted window
重建 close_t_minus_1 / ma20_t_minus_1
并正式输入 BASE_SEED_V1

但 accepted V4-07 明确：
Do not rebuild them from raw bars.
```

本轮保留 accepted UNKNOWN boundary，不扩展 t-1 producer capability。

---

# 4. R4A 已通过，不得返工

KEEP：

```text
adjustment basis identity repair
9/24 V4-03 parity
9/29/30 target facts
LAUNCH/RECOVERY D0 detector
```

---

# 5. 其他 KEEP

不得重开：

```text
V4-10
R3B capability scoping
A02
A05
A04
A03/A06/A07/Owner/Reader
V4-10 reducer AST
Event predicate rules
```

---

# 6. Heads 与权限

```text
V4_DATA_ACCEPTED_HEAD = KEEP 2026-09-30
V4_STAGE_ACCEPTED_HEAD = KEEP V4_00_TO_V4_10_ACCEPTED
V4_11_ACCEPTED_HEAD = NOT CREATE
V4_12 = NOT EXECUTE

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

---

# 7. Full repo 既有问题

```text
M14
M2
```

若与基线完全相同：

```text
PREEXISTING_NON_MAINLINE
```

本轮不因此停掉 V4-11 修复，也不得假称已解决。

---

# 8. 结束条件

完成两张卡后：

```text
commit
push
STOP
```

下一轮外审通过后，才另发：

```text
V4-11 Accepted Head Promotion
V4_STAGE_ACCEPTED_HEAD -> V4_00_TO_V4_11_ACCEPTED
V4-12 Stage Entry
```

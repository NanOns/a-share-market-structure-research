# V4-15E4｜External Acceptance Reconciliation Independent Audit R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 审计对象：E4 最终外部验收落库与 E5 Entry Boundary 治理提交  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> Audited commit：`d38551ded26ed82a5362c942d8ce191cca5c04d1`  
> Parent：`848db27bfd2ede74ef1eac508f5454044d2211ce`

---

# 0. 唯一总裁决

```text
V4_15E4_EXTERNAL_ACCEPTANCE_RECONCILIATION_AUDIT =
PASS_FINAL

E4_EXTERNAL_VERDICT_ARCHIVAL =
PASS_EXACT

E4_ACCEPTANCE_SCOPE_PRESERVATION =
PASS

E4_EXPERIMENT_MUTATION =
NOT_FOUND

E5_ENTRY_BOUNDARY =
PASS

E5_STARTED =
false

E5_FORMAL_TASK_CARD =
NOT_YET_ISSUED

NEXT =
ISSUE_V4_15E5_EXPECTANCY_AWARE_PRIORITY_PROJECTION_TASK
```

本轮提交可以接受为 E4 外部验收后的正式治理收口。

它做的是：

```text
归档外部审计原文
+
绑定被审计 commit / parent
+
固定外部裁决
+
保留 E4 模型限制
+
明确 E5 准入边界
```

它没有执行：

```text
新训练
新打分
新数据库运行
新 OOS
模型晋级
Priority 修改
生产启用
E5 实施
```

---

# 1. Drive / Git 同步结果

Google Drive 当前 `00_项目基准与进度` 中，E4 后最新正式文件为：

```text
V4_15E4_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md
```

当前 Drive 尚未出现新的 E5 Implementation Task / Execution Master。

GitHub 当前 HEAD：

```text
d38551ded26ed82a5362c942d8ce191cca5c04d1
```

提交信息：

```text
docs(fep): reconcile E4 final external acceptance and E5 entry boundary
```

唯一父提交：

```text
848db27bfd2ede74ef1eac508f5454044d2211ce
```

正是上一轮 E4 被审计 HEAD。

因此：

```text
RECONCILIATION_PARENT_IDENTITY = PASS
```

---

# 2. 外部审计原文归档｜PASS_EXACT

仓库归档：

```text
reports/fep_e4_external_acceptance_r1/
V4_15E4_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md
```

记录：

```text
bytes = 16655
sha256 =
1696b2a7fe62e8f5582bc23c8437459703f15318bcc19c4cd20a2b671d83c0b3
```

已对上一轮实际生成的原始文件重新计算：

```text
bytes = 16655
sha256 =
1696b2a7fe62e8f5582bc23c8437459703f15318bcc19c4cd20a2b671d83c0b3
```

完全一致。

因此不存在：

```text
外部审计文件被 Codex 改写后再归档
只摘录部分裁决
替换原始审计正文
```

结论：

```text
EXTERNAL_AUDIT_AUTHORITY_ARCHIVE = PASS_EXACT_BYTES
```

---

# 3. 外部裁决复写｜PASS

`EXTERNAL_ACCEPTANCE_RECONCILIATION.json` 与 `EXTERNAL_ACCEPTANCE_SEAL.json` 正确保留：

```text
V4_15E4_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

FEP_TREE_CHALLENGER_ENGINEERING =
PASS_EXTERNAL_FIRST_PREWATCH_T1

CHALLENGER_EFFECTIVENESS =
MIXED

PRIMARY_EFFECTIVENESS_VS_E2 =
NO_INCREMENT

DIAGNOSTIC_EFFECTIVENESS_VS_E3 =
IMPROVED

E3_MODEL_EFFECTIVENESS =
NO_INCREMENT

REAL_OOS =
NOT_GRANTED

FIRST_OBSERVED =
NOT_GRANTED

MODEL_DISPLAY =
UNGRANTED

PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED
```

没有把：

```text
MIXED
```

改写成：

```text
INCREMENT
```

也没有把：

```text
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED
```

扩大成：

```text
MODEL_PASS
PRODUCTION_PASS
PRIORITY_PASS
```

结论：

```text
EXTERNAL_VERDICT_SEMANTIC_PRESERVATION = PASS
```

---

# 4. E4 结果与人口复核｜PASS

治理提交再次固定：

```text
E2 DATE_BALANCED_MAE = 0.025383327234252982
E3 DATE_BALANCED_MAE = 0.026498264228947403
E4 DATE_BALANCED_MAE = 0.025604081485067275
```

顺序：

```text
E2 < E4 < E3
```

因此正确解释仍然是：

```text
E4 improves on E3
but
E4 does not beat E2
```

可比较人口仍为：

```text
46 / 205
coverage = 22.439024390243903%
```

并保留：

```text
SEEN_OUTER_DIAGNOSTIC_ONLY = true
NEW_INDEPENDENT_OOS_EVIDENCE = false
CHAMPION = false
PROMOTION_EVIDENCE = false
```

结论：

```text
E4_EFFECTIVENESS_RECONCILIATION = PASS
```

---

# 5. 233 个 Binding / Git Readback｜PASS

治理脚本对：

```text
233 exact audited bindings
```

执行工作树 sealed binding 与 audited Git object 的对照。

结果：

```text
git_readback_count = 233
```

其中 231 项 raw Git bytes 与 sealed worktree bytes SHA256 直接一致。

有 2 项：

```text
data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json
data/v4/V4_03_ACCEPTED_HEAD.json
```

出现：

```text
raw_git_sha256 != sealed_worktree_sha256
```

但同时：

```text
audited_git_blob == filtered_worktree_blob
```

原因与证据形态符合 Windows line-ending / Git clean-filter 差异。

仓库没有把它们误报成 exact raw bytes，而是显式记录：

```text
exact_raw_git_bytes = false
raw_git_sha256
sealed_worktree_sha256
audited_git_blob
filtered_worktree_blob
```

这属于正确处理，而不是 hash 绕过。

结论：

```text
GIT_OBJECT_IDENTITY = PASS
RAW_BYTE_DIFFERENCE_DISCLOSURE = PASS
```

---

# 6. Regression Evidence Preservation｜PASS

治理提交没有重新包装成“仓库全绿”。

它保留：

```text
Targeted:
256 passed
1 skipped
0 failed

Scoped:
2615 passed
4 skipped
52 existing debt failures
0 introduced active failures
```

并再次校验：

```text
52 failed node identities
=
E3 previous known debt identities
```

两项 deselection 也保持完全一致：

```text
tests/v4_dm01_r4/test_runtime.py::test_current_real_v2_parent_and_future_wait

tests/test_v4_18_migration_contract.py::test_all_declared_tables_have_explicit_namespace_rules
```

同时明确：

```text
repository_all_green = false
new_test_run = false
CI_evidence = NO_RUN_NO_STATUS...
```

当前 GitHub commit 同样没有 workflow run / commit status。

结论：

```text
REGRESSION_EVIDENCE_RECONCILIATION = PASS
CI_OVERCLAIM = NOT_FOUND
```

---

# 7. Protected State｜PASS

本轮只新增：

```text
reports/fep_e4_external_acceptance_r1/*
scripts/reconcile_fep_e4_external_audit_r1.py
```

没有修改 Accepted Heads、Priority 或生产运行代码。

Readback：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_16_ACCEPTED_HEAD =
NOT_CREATED

R25 =
WAIT_ACCEPTED_DAILY_INPUT

accepted_experiment_unchanged =
true

new_model_fits =
0

new_model_scoring =
0

new_database_run =
false

TDX =
UNTOUCHED
```

结论：

```text
PROTECTED_STATE = PASS
```

---

# 8. AUDIT_NOTE_E4_01 处理｜PASS

上一轮要求：

```text
以后新的 effectiveness protocol
必须在 evaluation open 前冻结：
- effectiveness disposition rule
- primary metric
- tie-break
- promotion boundary
```

本轮没有反过来篡改 E4 历史协议。

而是正确记录为：

```text
OPEN_FOR_NEXT_EFFECTIVENESS_PROTOCOL
```

并明确：

```text
no retroactive E4 protocol edit
```

这正是正确的治理方式。

结论：

```text
AUDIT_NOTE_E4_01_RECONCILIATION = PASS
```

---

# 9. E5 Entry Boundary｜PASS

`E5_ENTRY_BOUNDARY.json` 明确：

```text
E5_ENTRY =
AUTHORIZED_NOT_BLOCKED_BY_E4

E5_started =
false

formal_task_card_received =
false
```

要求 E5 开始前冻结：

```text
effectiveness disposition rule
primary metric
tie-break
promotion boundary
priority projection boundary
shadow-only boundary
model evidence class
```

同时禁止：

```text
promotion from seen Outer
MODEL_DISPLAY from E4
PRIORITY_USE from E4
production grant from E4
retroactive PRIORITY_V1 rewrite
```

这与上一轮外部审计结论一致。

结论：

```text
E5_ENTRY_GOVERNANCE = PASS
```

---

# 10. 非阻断工程备注

`reconcile_fep_e4_external_audit_r1.py` 是一个明显的一次性 receipt builder：

```text
SOURCE =
D:/Users/lps/Desktop/阶段任务/...
```

并要求执行时：

```text
HEAD == 848db27...
```

在当前 reconciliation 完成之后，它不能被普通新 clone 直接重跑。

这不阻断本轮验收，因为：

1. 它没有被宣称为生产 runtime；
2. 归档 authority 已经进入仓库；
3. receipt 已封存；
4. 233 个 binding / Git object 证据已经保存；
5. 本轮职责是治理归档，不是构建可重复训练流水线。

但后续不得把此脚本当作：

```text
portable reproduction entrypoint
```

建议状态：

```text
AUDIT_NOTE_E4_RECON_01 =
PASS_NONBLOCKING_ONE_SHOT_RECEIPT_BUILDER
```

---

# 11. 最终矩阵

| Gate | Result |
|---|---|
| Drive latest authority sync | PASS |
| Reconciliation commit parent identity | PASS |
| External audit raw archive SHA256 | PASS_EXACT |
| External verdict semantic preservation | PASS |
| E2/E3/E4 metric ordering | PASS |
| 46/205 scope preservation | PASS |
| Seen Outer limitation preserved | PASS |
| 233 audited bindings | PASS |
| Git object identity | PASS |
| 2 newline raw-byte differences disclosed | PASS |
| Known 52 debt identities preserved | PASS |
| Existing deselections preserved | PASS |
| Repository-all-green overclaim | NOT FOUND |
| Accepted Head mutation | NOT FOUND |
| Priority V1 mutation | NOT FOUND |
| Model fit/scoring | 0 / 0 |
| New database run | false |
| TDX mutation | NOT FOUND |
| E5 implementation started | false |
| E5 boundary | PASS |
| GitHub CI | NO RUN / NO STATUS |

---

# 12. 最终状态与下一步

```text
V4_15E4_EXTERNAL_ACCEPTANCE_RECONCILIATION_AUDIT =
PASS_FINAL

E4 =
FORMALLY_CLOSED

E5_ENTRY =
AUTHORIZED

E5_STARTED =
false

CURRENT_BLOCKER =
NO_E5_FORMAL_TASK_CARD

NEXT =
ISSUE_V4_15E5_EXPECTANCY_AWARE_PRIORITY_PROJECTION_TASK
```

因此现在不应该继续“审计 E5 实现”，因为 E5 还没有开始。

下一正式动作应当是：

```text
发布 V4-15E5 Expectancy-aware Priority Projection
正式实施任务卡 + Execution Master
```

然后 Codex 才能进入 E5 实施。

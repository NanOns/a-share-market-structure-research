# FOCUS-07A-09 Tracking Union 硬门记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 13、38 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 6、7、10 节 |
| stage_contract | `PlannedDay` 明确携带 pending follow-up 与 due outcome key。计划构建和 core input closure 都检查来源、pending follow-up、due outcome 的每个来源实体均进入 tracking union；observation key 集合必须与 union 完全相等。来源选择合同换版时允许同一实体重新取 key，不静默丢失实体。 |
| evidence | `daily_plan.py` 新增 `require_tracking_coverage`；`core_input_closure.py` 在输入闭合和 observation 闭合两处应用。测试覆盖缺 pending、缺 due、重复 union key、合法合同 rekey，以及发布前遗漏 pending 的拒绝。Focus 定向测试 `80 passed, 355 deselected`。 |
| acceptance_result | `FULL_PASS / ENTITY_LEVEL_SOURCE_COVERAGE_GATE`。实体 coverage 硬门通过。episode observation 重入并存已由后续 `FOCUS_EPISODE_TRACKING_PLAN_V2` 独立完成合同与合成事务验收；真实多日发布及真实重入前瞻验收仍开放。 |
| next_stage | 07A-08 P12 日流水线接入已完成。继续在后续 accepted 来源日执行多日 writer rollback/readback；真实重入 episode 样本出现后按 `docs/FOCUS_07A_REENTRY_OVERLAP_V2_PROGRESS_20260924.md` 验收。 |

本阶段不修改已接受 Focus run/head、V3/V3.3 来源或 TDX 输入。

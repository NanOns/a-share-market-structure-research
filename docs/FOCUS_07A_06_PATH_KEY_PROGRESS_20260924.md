# FOCUS-07A-06 跨日 PathRequest 键修复记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 10、38 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 5～8 节 |
| stage_contract | 股票路径事实只按 `(security_id, PathRequest.start_trade_date)` 绑定；构建 observation 前，fact 键集合必须与请求键集合完全相等。持续 episode 的起点不得被替换成今日日期。 |
| evidence | `daily_builder.py` 已按 tracking context 的 episode 首日读取路径；新增 `path_fact_index.py` 对重复、缺失和额外路径事实执行硬门。定向测试验证第二日仍查首日起点、同一证券不同起点不合并、缺失/重复拒绝。Focus 测试 `72 passed, 355 deselected`。 |
| acceptance_result | `FULL_PASS / PATH_KEY_MAPPING_UNIT_SCOPE`；真实第二日端到端仍需 accepted 来源日与多日 writer。 |
| next_stage | 07A-07 动态历史窗口及真实长 episode 路径验证；随后完成 07A-03 多日 writer 的回滚和真实发布验收。 |

未修改旧 Focus run/head、V3/V3.3 来源或 TDX 输入。

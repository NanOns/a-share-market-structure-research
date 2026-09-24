# FOCUS-07A-05 Tracking Context 阶段记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 8、9、38 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 3～7 节 |
| stage_contract | `FOCUS_TRACKING_CONTEXT_V1`：每个 tracking key 绑定其计划 episode；今日有来源行则读取今日事实，已退出则通过 episode 首日的 VALID accepted head 读取冻结来源事实和合同。缺行、摘要错误、身份不符均失败，不用另一来源或另一 episode 代替。 |
| evidence | 新增 `src/focus_tracker/tracking_context.py`，分别实现批量读取已接受首日行与纯函数解析。3 项定向测试覆盖退出来源恢复、缺失/错误身份拒绝、新 episode 使用今日来源。 |
| acceptance_result | `FULL_PASS / CONTEXT_RESOLVER_UNIT_SCOPE`；数据库真实跨日调用仍待 07A-04 batch 接入和多日验收。 |
| next_stage | 07A-04：正式 observation builder 遍历 `plan.tracking_keys`，接入本 resolver，并处理历史 sector 篮子/strength、股票 PathRequest 与完整集合硬门。 |

本阶段只读取已接受历史身份，不改旧 run/head、来源算法或 TDX 输入。

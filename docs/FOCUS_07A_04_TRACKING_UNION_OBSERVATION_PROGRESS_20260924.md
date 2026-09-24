# FOCUS-07A-04 Tracking Union Observation 阶段记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 8～11、13、38 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 6、7、10 节 |
| stage_contract | Daily Builder 对 `plan.tracking_keys` 各生成一条 observation；今日来源行与历史 episode 来源上下文由 `FOCUS_TRACKING_CONTEXT_V1` 区分。stock fact 按 episode `PathRequest` 起点取值，manifest 和 builder 用同一 tracking sector/stock fact 集合与所需最早历史日期。`validate_core_input_closure` 继续执行 observation key 与 tracking union 完全相等的发布前硬门。 |
| evidence | `src/focus_tracker/daily_builder.py` 已改为遍历 tracking union；`src/focus_tracker/daily_manifest.py` 同步读取计划中的历史篮子、股票请求和动态起点。Focus 定向测试 69 passed；2026-09-23 真实输入只读探针输出 310 observations、310 source rows、`writes=0`，闭合摘要生成成功。 |
| acceptance_result | `IN_PROGRESS / CODE_PATH_READY_FIRST_DAY_REAL_PROBE_PASS`。本地当前只具备 2026-09-23 的真实 Focus head；尚无第二个已接受交易日可验证退出后 observation。历史 sector 成员集合变化时的 strength 能力也需真实多日检验。 |
| next_stage | 用次日已接受来源做只读 union 探针，验证退出股票和板块的 observation；完成 07A-03 多日 writer 后做真实前瞻发布。重入与旧 episode 同日并存已单列 `docs/audits/FOCUS_REENTRY_OVERLAP_AUDIT_20260924.md`，不由本次单 key 闭合覆盖。 |

本阶段没有改写旧 Focus run/head、V3/V3.3 来源或 TDX 输入。

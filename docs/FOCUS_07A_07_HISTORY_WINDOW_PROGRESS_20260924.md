# FOCUS-07A-07 动态历史窗口修复记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 11、38 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 6～8 节 |
| stage_contract | `FOCUS_HISTORY_WINDOW_V1`：每日 verified slice 起点为全部 PathRequest episode 起点与所需前置主交易会话中的最早日期。请求起点必须位于冻结主交易日历；不以固定自然日天数截断。可显式传入更长的前置 session 数，供后续 07B 谓词需求合同使用。 |
| evidence | `daily_builder.py` 与 `daily_manifest.py` 共用 `required_history_start`；4 项测试覆盖超过 14 自然日的长 episode、无股票请求、三会话 lookback、缺失起点和不足历史。Focus 定向测试 `76 passed, 355 deselected`。此前 2026-09-23 真实输入只读探针已生成 310 observation、`writes=0`；本次未执行发布。 |
| acceptance_result | `FULL_PASS / DYNAMIC_WINDOW_UNIT_SCOPE`。真实长 episode 的 Forward 验收待多日 writer 和持续 accepted 来源。 |
| next_stage | 回到 07A-03 多日 writer，复用现有 episode 并按每日 transition/anchor/observation 原子激活 head；随后接入 P12 日流水线并执行真实多日验收。 |

未修改旧 Focus run/head、来源算法或 TDX 输入。

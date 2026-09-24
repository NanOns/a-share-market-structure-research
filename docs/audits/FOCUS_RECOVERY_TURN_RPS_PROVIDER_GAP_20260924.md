# RECOVERY_TURN RPS20 历史 provider 审计项

| 字段 | 记录 |
|---|---|
| audit_item | `RECOVERY_TURN_INVALIDATION_PROVIDER_INCOMPLETE` |
| scope | 提供 PIT-safe 的逐交易日 `RPS20` 与 `rps20_delta3`，绑定当日 accepted universe、TDX 原生 QFQ 身份、主交易日历和完整横截面输入。 |
| applicable_upgrade | `FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 阶段门；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 4、7、9、10 节。 |
| stage_contract | `FOCUS_PIT_RPS20_HISTORY_V1` / `TDX_NATIVE_QFQ_RET20_V1`。仅读取逐日 accepted publication 的密封 bundle membership；20-session simple return 使用同一 QFQ 版本的 t 与 t−20 实际收盘，RPS 使用当日有限横截面的 average-tie rank/N；最小横截面 100、最少 120 个有界历史实际 bar、近期实际覆盖率至少 75%。缺身份、成员、历史或覆盖时 fail closed。 |
| evidence | `src/focus_tracker/pit_rps.py` 与 `tests/upgrade_v3/test_focus_07b_pit_rps.py`；每日 builder 最多读取 251 个 master sessions，provider digest 绑定窗口、accepted universes、bundle 与结果。测试覆盖 T−3、逐日 universe 变化、最小横截面、120-bar 缺口。精确提交 Focus 回归 153 passed；07B 套件 34 passed。 |
| acceptance_result | `CLOSED / PIT_PROVIDER_IMPLEMENTED_AND_UNIT_ACCEPTED`。代码 provider 闭合；真实连续日及实际 RECOVERY_TURN 终态仍须由后续 accepted market samples 验收。 |
| next_stage | 观察后续 accepted Focus 日期的 provider status/digest，并用真实 RECOVERY_TURN episode 验证 TRUE/FALSE/UNKNOWN invalidation 分支；不足时继续按 provider evidence 标记 UNKNOWN。 |

该结论表示历史 provider 代码和可复现测试完成，不表示所有来源日期都有 accepted PIT universe，也不把测试结果当成真实 Forward 样本。

# FOCUS-07C 算法验收记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 24～29、41 节；`docs/FOCUS_PATH_STATE_V2_DESIGN.md`。 |
| stage_contract | 版本化 V2 分类和 gap 语义必须保留高优先级 UNKNOWN 与低优先级已确认事实；V1 历史不变；新 observation 的 V2 证据须进入 digest、closure 和读 API。 |
| evidence | 07C-01～05 的阶段记录及 `reports/upgrade_m3/FOCUS_07C_V2_GAP_SEMANTICS_20260924.json`；本次定向执行 `python -m pytest -q tests/upgrade_v3/test_focus_07c_path_state_v2.py tests/upgrade_v3/test_focus_07c_gap_semantics.py tests/upgrade_v3/test_focus_03_observation.py tests/upgrade_v3/test_focus_03_core_input_closure.py`，27 passed。 |
| acceptance_result | `CONTRACT_AND_CODE_PASS / LIVE_V2_PUBLICATION_PENDING`。合同、反例、合成 gap、真实 24 日输入只读回算通过；尚无 V2 observation 正式落库及真实确认停牌复牌正样本，不判定完整 forward release pass。 |
| next_stage | 下一精确交易日 accepted publication 出现后，先执行 07A next-day writer 回滚演练，再正式提交并回读 V2 evidence、manifest、closure、head lineage 和 API。真实确认停牌复牌出现时独立验收 PATH 桥接；07A 五日门和到期 outcome 继续独立跟踪。 |

## 最低反例

| 情形 | 输入 | 预期与证据 |
|---|---|---|
| A | `STRUCTURE_DAMAGED=UNKNOWN`，`TREND_ACCELERATING=TRUE` | `PARTIAL`，主状态为空，已确认趋势加速保留，高优先级未知列出；`test_resolution_uses_versioned_order_not_json_object_key_order`。 |
| B | `STRUCTURE_DAMAGED=FALSE`，`TREND_ACCELERATING=TRUE` | `READY`，主状态为 `TREND_ACCELERATING`；`test_false_higher_priority_allows_lower_true_primary`。 |
| C | `STRUCTURE_DAMAGED=TRUE`，`TREND_ACCELERATING=TRUE` | `READY`，主状态为 `STRUCTURE_DAMAGED`，两项 TRUE 均留存；`test_higher_priority_true_wins_over_lower_true`。 |

## 真实输入与未闭合项

2026-09-24 已接受 publication 的新版 assembler 只读重建得到 117 条来源、397 个 tracking key、397 条 observation，closure 397/397；V2 解析为 READY 74、PARTIAL 243、UNAVAILABLE 80、AMBIGUOUS 0。来源身份不变，V2 manifest 为 `3ef5b6f4810968b6f9d68b88d0cdfd2c5ed17febf1830fe8f36ee6f6f68f5920`，与已持久化的 V1 manifest 不同。该回算写入数为 0，23/24 日 accepted head 和历史 observation 未改动。24 日 API 对旧 observation 返回 V2 null，符合兼容合同。现有本地标准化样本无确认停牌，不能据此接受真实复牌路径。

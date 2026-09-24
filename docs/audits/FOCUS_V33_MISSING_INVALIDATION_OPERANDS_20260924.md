# 独立审计项：V3.3 冻结失效 operand 缺失

| 字段 | 记录 |
|---|---|
| scope | 2026-09-24 accepted Focus observations 中 3 条 `MISSING_OR_INVALID_OPERAND`，与持续交易日验收分开核对。 |
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 18、22、40 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 16.2 节。 |
| stage_contract | V3.3 invalidation AST 只使用 signal-day 来源明确提供并冻结的 operand。缺少来源 operand 时，该叶节点和整体结果必须保持 `UNKNOWN`；不得由跟踪层推导自然语言阈值，也不得用 PHH20、MA20 或近期低点替代。 |
| evidence | PostgreSQL 只读回查确认 3 条 episode 分别为 `SH.600802`（首日 2026-09-23）、`SH.601208`（首日 2026-09-23）和 `SH.603558`（首日 2026-09-24），首日主类别均为 `TREND_CONTINUE`。其接受来源的 `factor_evidence` 均未提供 `trend_key_low`；对应冻结事实表没有该值，AST 证据显示 `close` 比较的 `expected=null`、reason=`MISSING_OR_INVALID_OPERAND`。三条记录均为 `UNKNOWN/DATA_UNAVAILABLE`，没有被误判为有效或失效。 |
| acceptance_result | `CLOSED / EXPECTED_UNKNOWN_SOURCE_OPERAND_ABSENT`。这 3 条是已解释且符合设计的来源事实缺失，不构成跟踪器实现缺陷；未知原因已持久化。此结论只关闭这 3 条记录的审计歧义，不声称 TREND_CONTINUE 的冻结阈值供给已经闭合。 |
| next_stage | 若将来要求该类 episode 可判定，须先由 V3.3 来源合同明确 `trend_key_low` 的定义、单位、首日生成规则和兼容性，再提升来源/冻结事实合同版本。之后的新 episode 才可进入该分支；既有 as-recorded 记录不得补猜或回写。 |

查询为 PostgreSQL `READ ONLY`；没有写入 episode facts、观察、accepted run/head 或来源数据。相关现行实现为 `src/focus_tracker/frozen_invalidation_facts.py` 和 `src/focus_tracker/predicates.py`。

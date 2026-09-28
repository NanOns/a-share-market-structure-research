# V4-03 R3 独立验收阻断修正记录（2026-09-28）

## 阶段合同与范围

- 治理输入：`docs/audits/V4_03_R3_INDEPENDENT_EXTERNAL_ACCEPTANCE_20260928.md`。
- 冻结业务合同：`docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md` §27；共同成员 delta 的定义见 §15。
- 本轮只关闭 Market Regime 原始量、可执行机器合同、PIT 候选标签和确定性基线验证。V4-01/V4-02 accepted identity、既有 47 字段公式、trend、Sector 范围阻断、V4-04/V4-05 均不扩展。

## 修正

1. `breadth_delta3` 在 t 与 t-3 的 PIT 共同成员中，进一步取两端 `ret1` 均可评估的同一集合，分别计算正收益比例再相减。输出共同成员数、可评估数、集合身份、覆盖率及两端比例。
2. `participation` 为当日 PIT 成员各自 `amount_ratio20` 的横截面中位数。每只证券用自身此前 20 个已验证实际交易 bar 的金额均值；已确认停牌可跨过，未知缺口、调整身份变化、非正分母均使该成员比率 UNKNOWN。输出可评估数、集合身份和覆盖率。
3. `stress_level` 仍按当日 PIT 成员有效涨跌停规则覆盖率与跌停比例；`stress_change` 在 t 与 t-1 PIT 共同成员且两端规则均有效的同一集合上比较跌停比例。两者原始比例分别保存。
4. 原有趋势生产者及规则不变。Native schema 增加可执行 `MARKET_REGIME_REV2_RAW`，覆盖成员变动、t/t-3 进出、个股金额中位数与部分 UNKNOWN、未知金额缺口、同成员压力变化；阈值向量继续保留。
5. R3 PIT 历史候选统一标记 `V4_03_PIT_STAGING_CANDIDATE`，同时保留 `CANDIDATE_NOT_STAGE_ACCEPTANCE` 与 `NOT_GRANTED`；不将 PIT 性质与验收/发布许可混用。
6. 确定性验证要求已有 baseline 与两次 replay 的 SHA-256 全相等。阶段处置在任一证据失败、原始量机器覆盖不成立或 PIT 标签不一致时保持 `MARKET_REGIME=BLOCKED`、`external_review_ready=FALSE`。

## 本地验收与下一阶段

本轮重新生成 786 日 Market path、786 日 Market Regime、5222 证券 47 字段候选、独立复算报告、机器合同向量回执及确定性回执；具体哈希与 PASS/FAIL 以同提交的 `reports/v4_03/V4_03_STAGE_DISPOSITION_R3.json` 和各 receipt 为准。Sector 仍为 capability-scoped BLOCKED，V4-03 final acceptance 仍为 `NOT_GRANTED`，V4-04 入口仍阻断。本地候选完成后提交并推送，外部独立验收由用户另行安排；本轮不自行发起云端审计。

最终本地结果：

- Market path 独立复算：786 行、0 mismatch，PASS。
- Market Regime 独立复算：786 行、0 mismatch，PASS；机器合同 4 项、25 向量、0 fail，PASS。
- 全字段独立复算：5222 行、47 字段、0 mismatch，PASS。
- `python -m pytest -q tests/v4_03 tests/v4_phase0/test_algorithm_contracts.py`：47 passed。
- 五类确定性产物均满足 `baseline_sha256 == replay1_sha256 == replay2_sha256`，PASS。
- 阶段处置：`CAPABILITY_SCOPED_PASS_CANDIDATE_NOT_FINAL_ACCEPTANCE`；`MARKET_REGIME=PASS_CANDIDATE`，`SECTOR_NATIVE=BLOCKED`，`external_review_ready=TRUE_WITH_CAPABILITY_SCOPE`，`v4_03_final_acceptance=NOT_GRANTED`。

主要产物 SHA-256：Market path `898a6554eaefae1206d5a228e2b99f78743ef2d749d40579862c9a5de1bdaedb`；Market Regime `89aae8484aa98837c3d6c685d48365edae2913ac506dd12916f8c56e92a9b139`；full-scope `9b6a1f16d90c2c5d08f1cc981edcceb737c29cab1792cad84bf25d62a7fd1e2e`。这些是本地候选证据，不代表外部独立验收已完成。

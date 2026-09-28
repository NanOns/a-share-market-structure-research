# V4-01 Source Fingerprint Blind Study｜外部验收 R1 处置

- 日期：2026-09-29
- 仓库：`NanOns/a-share-market-structure-research`
- 分支：`codex/v4-system-reform`
- 执行前 HEAD：`d1fe4e6e2b44457b9cc58104b7ecc7575fd3a2bf`
- 阶段：`V4-01-SOURCE-FINGERPRINT-CANDIDATE-STUDY`

## 适用合同与边界

- 最新适用 V4-01/02 修复状态：`docs/audits/V4_01_02_COMPLETE_REPAIR_STATUS_R2_20260925.md`，SHA-256 `b79f1d94ae6d18fdd9a3bb8dd35469fb5ba2a938cf4ae568c1c6ab8ea465fdba`。该收据记录 V4-01 仍为 `BLOCKED / R2_REPAIR_OPEN`。
- 本研究阶段合同：`V4_01_SOURCE_FINGERPRINT_CANDIDATE_V1 v1.0.0`，SHA-256 `d0891162e5290c42f84148b648f0a62c0052ae0ce49fef5d7c807f933988bd02`。
- 本次范围：修复诊断报告 F6 的语义残留；按外部意见补充离线 synthetic contract tests；归档外部验收原文。
- 阈值合同保持冻结，未改 detector v1.0、阈值、样本标签或盲测输入；未查询/写入 TDX 源；未修改生产身份、canonical identity、Historical Universe、V4-02/V4-03 产物或 accepted head。

## 外部验收原文

附件按字节原样归档于 `docs/evidence/V4_01_SOURCE_FINGERPRINT_BLIND_STUDY_EXTERNAL_ACCEPTANCE_R1_20260929.md`：9,615 bytes，SHA-256 `6db29d56cddce77ca1b5f33e2d75197208abb710aa8cbc19d247156c8fe9060a`。与用户提供的 `D:\Users\lps\Desktop\V4_01_SOURCE_FINGERPRINT_BLIND_STUDY_EXTERNAL_ACCEPTANCE_R1_20260929.md` 逐字节相同。

## 处置与证据

### P1 F6 语义残留：PASS

诊断脚本现在输出 `F6_no_substantive_dual_actual_trading = not substantive_dual_trade_days`，并继续分别列出完全相同的 provider alias bar 日期和实质不同的双边 bar 日期。相同 alias bar 不再令“无实质双边交易”信号为 false。旧字段 `F6_no_overlapping_dual_actual_trading` 已从执行代码移除。冻结的 R1 历史报告未被重写。

### Synthetic contract tests：PASS

执行命令：`python -m pytest tests/v4_01/test_source_fingerprint_candidate.py -q`

结果：`10 passed`。随后运行完整 `tests/v4_01` 目录：`62 passed`。新增用例覆盖：

- F6 对相同 alias bar 与实质冲突分别给出正确语义；
- v1.0 的 TDX volume `0.95` 和 BaoStock active exact `0.99` 阈值边界，以及边界下方拒绝；
- 停牌时 volume/amount 空值与数值零的限定归一；
- 实质不同的双边 actual bar 冲突 fail-closed；
- provider 返回代码不匹配、重复日期、不完整查询 fail-closed；
- 共享 IPO 元数据本身不会产生候选。

新增 synthetic 数据只用于离线合同测试，不充当市场样本或标签证据。

修改文件 SHA-256：

- `scripts/diagnose_v4_01_code_change_source_fingerprint.py`：`52e4470fbb21dab0ea443f160ba26ed00ef174bdb86238fc92b89b17fa0f9afa`
- `tests/v4_01/test_source_fingerprint_candidate.py`：`c5e38f845f7085bdd4bbdf3430c209ae5c6e1d12e151383e20a1609bdc0f5c83`

## 验收结论

```text
F6_SEMANTIC_CLEANUP = PASS
SYNTHETIC_CONTRACT_TESTS = PASS (10 passed)
FROZEN_V1_THRESHOLDS = UNCHANGED
BOUNDED_LABEL_SEPARATED_STUDY = PASS (TP=2, FN=0, FP=0, TN=2; original scope only)
BROADER_PAIRED_TDX_AND_CROSS_SCOPE_VALIDATION = OPEN
PRODUCTION_IDENTITY_MUTATION = PROHIBITED
V4_01_OWNER_GATE = BLOCKED
V4_01_FULL_PASS = NOT_GRANTED
```

本次处置未新增两个以上成对 old/new TDX 正样本、SH/STAR 样本或更困难负样本；既有标签证据仍限于原四案，未伪造或推定样本。阈值校准审计项 `AUDIT-V4-01-SOURCE-FINGERPRINT-CALIBRATION-20260929` 继续 `OPEN`。外部验收报告的基线 HEAD `d1fe4e6` 有 0 个 status checks、0 个 workflow runs；本次只记录本地测试结果，不把它表述成远端独立执行。

## 阶段记录

- 阶段合同：冻结的 candidate detector v1.0，仅输出研究候选，不授予 SAME_ENTITY 或 production mutation 权限。
- 证据：外部验收字节副本与 SHA-256；代码和测试变更；10 项本地测试结果；既有四案冻结盲测报告及标签摘要。
- 本次验收：`PASS_P1_CLEANUP_AND_SYNTHETIC_CONTRACT_TESTS; SAMPLE_EXPANSION_OPEN`。
- 下一阶段：保持 v1.0 与阈值不变，先纳入至少两个拥有 old/new TDX pair 的正式代码变更正样本及更困难 distinct/merger/provider-backfill 负样本；尽量覆盖 SH_MAIN/STAR；在揭盲前冻结逐案输出、FP/FN 和输入哈希，并取得独立标签复核。该工作与 V4-01 owner gate 的 official event index/completeness 审计保持独立。

# V4-01 通用源级指纹候选器｜标签盲测 R1

- 阶段合同：`V4_01_SOURCE_FINGERPRINT_CANDIDATE_V1 v1.0.0`
- 阶段验收：`PASS_BOUNDED_BLIND_VALIDATION`
- 样本：正样本 2，合并后继反例 2
- 候选检测：TP=2，FN=0，FP=0，TN=2
- 适用边界：本结果只验证冻结的小样本候选信号；不验证通用 SAME_ENTITY 规则，不清除 V4-01 Gate A。
- 生产 identity 变更授权：`false`

## 冻结的盲测结果

| Case | 代码对 | 有效日 | 新代码含旧史 | Bao 有效日严格一致率 | 完全相同的同日 bar | 检测输出 | 揭盲标签 |
|---|---|---|---|---:|---|---|---|
| BLIND-01 | `SZ.300114 → SZ.302132` | 2025-02-17 | old TDX=True; new TDX backfill=True; BaoStock backfill=True | 3419/3420 (99.97%) | ['2025-02-14'] | `STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE` | `PURE_CODE_RENUMBERING` (命中) |
| BLIND-02 | `SZ.000022 → SZ.001872` | 2018-12-26 | old TDX=False; new TDX backfill=True; BaoStock backfill=True | 5869/5885 (99.73%) | [] | `STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE` | `PURE_CODE_RENUMBERING` (命中) |
| BLIND-03 | `SZ.000024 → SZ.001979` | 2015-12-30 | old TDX=True; new TDX backfill=False; BaoStock backfill=False | N/A | [] | `NO_STRONG_ALIAS_FINGERPRINT_IN_SAMPLE` | `MERGER_SUCCESSOR_DISTINCT_ISSUER` (命中) |
| BLIND-04 | `SZ.000562 → SZ.000166` | 2015-01-26 | old TDX=True; new TDX backfill=False; BaoStock backfill=False | N/A | [] | `NO_STRONG_ALIAS_FINGERPRINT_IN_SAMPLE` | `MERGER_SUCCESSOR_DISTINCT_ISSUER` (命中) |

## 判别规则

- TDX 语义重叠比较 OHLC、amount、volume；`reserved` 和 raw 32-byte prefix 仅保留作描述，不能单独否定业务历史连续性。
- BaoStock 只在两边 `tradestatus=0` 时，将 volume/amount 的空值与数值零作为表示差异归一；真实交易日金额仍严格比较，不设置金额容差。
- 满足有效日之前的新代码回填、至少 20 个双边有效交易历史日且严格业务字段匹配率不低于 99%，并同时具备 TDX 历史信号及无实质冲突时，产生强候选。阈值仅为研究参数。
- 双代码同日返回逐字段相同的真实交易 bar 记作 provider alias duplicate；只有业务字段不同的双边真实 bar 才触发冲突。
- 输出永不自动合并 identity。正式 SAME_ENTITY 仍要求独立官方或经版本化接受的证据。
- 原始输入报告的旧 classifier 结果仅用于追溯；本轮 detector 不读取该字段，而是从冻结的原始 TDX/BaoStock 证据重新计算。

## 解释与限制

The four-case set contains two officially documented pure code-renumbering positives and two merger-successor negative controls. It is label-separated from detector execution but not independently blinded to an external reviewer. Only one positive has both local old/new TDX files for paired semantic overlap; the 0.95 TDX volume research threshold is therefore not calibrated. The result does not estimate market-wide false-positive/false-negative rates and does not establish a SAME_ENTITY confirmation rule.

## 证据摘要

- Contract SHA-256：`d0891162e5290c42f84148b648f0a62c0052ae0ce49fef5d7c807f933988bd02`
- 候选器模块 SHA-256：`307b5303667ae34a0130e3ecd1c766cfeed243c8cfdf864fa67eeecede13f77c`；评估器 SHA-256：`0dcffeca67ab27302a1a9626b6c5fd9238fe89808ace3fe6c846047ea636d4d6`。
- 样本清单 SHA-256：`aff7a8677fd69a947603617fcba582dc8bf8c2544f2a8f9ccbc480069c938cac`
- 揭盲标签 SHA-256：`2f97945dc9b2577a1f9af82077d542f253f2a333bb93f26a57bd0ed91dadf5f1`
- 最新 V4-01 owner receipt：`BLOCKED`；SHA-256 `e0c3f43831e418eca42eacea6a1d938fcf462797abf7187efd116d1d030ed15c`。
- 外部验收文件 SHA-256：`47588e946fee72611431a8743ec8615fee06da18482e75b0e27868f15bc9e1a1`。
- BaoStock request ledger SHA-256：`16f2f3a9610be91222d2f69246991d35fcdbffc6b5c3e39d0a636cabb279e54b`；2026-09-29 请求计数 60。
- 完整冻结 BaoStock 原始行位于压缩 JSON 输入；每个输入的压缩与解压后 SHA-256 见 JSON 收据。
- 下一阶段：`EXPAND_INDEPENDENT_BLIND_SET_WITH_MORE_PAIRED_TDX_CASES_AND_REASSESS_RESEARCH_THRESHOLDS; KEEP_PRODUCTION_IDENTITY_UNCHANGED`

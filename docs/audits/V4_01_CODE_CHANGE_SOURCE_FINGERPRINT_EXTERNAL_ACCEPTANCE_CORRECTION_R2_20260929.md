# V4-01 源级指纹诊断｜外部验收纠正处置 R2

- 日期：2026-09-29
- 复核输入 HEAD：`d18bdc13607fb1443509208863c8edc5135bc43c`
- 外部验收文件：`D:\Users\lps\Desktop\V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_EXTERNAL_ACCEPTANCE_20260929.md`
- 仓库冻结副本：`docs/evidence/V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_EXTERNAL_ACCEPTANCE_20260929.md`
- 外部验收文件 SHA-256：`47588e946fee72611431a8743ec8615fee06da18482e75b0e27868f15bc9e1a1`
- 外部验收处置：`ACCEPT_CLASSIFICATION_CORRECTION; RETAIN_CANDIDATE_ONLY_BOUNDARY`
- 对应盲测阶段：`reports/v4_01/V4_01_SOURCE_FINGERPRINT_CANDIDATE_BLIND_VALIDATION_R1.json`

## 处置结论

旧 R1 冻结报告的数据采集结果仍有效，但旧 classifier 的最终解释被本处置 supersede：

```text
PATTERN_D_UNRESOLVED_IDENTITY_RELATION
→ STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT
candidate_signal_strength = STRONG_GENERIC_IDENTITY_RELATION_CANDIDATE
```

这只是候选发现结论，不是 SAME_ENTITY 判定，也不授权修改生产 identity、dated alias、Historical Universe、V4-02/V4-03 或 V4-01 owner gate。

## 为什么纠正 Pattern D

300114→302132 的冻结数据表明：

- 3421 个 TDX 共同日期的 mismatch 仅涉及 `reserved` 445 条和 `volume` 54 条；OHLC 与 amount 在全部共同日期完全一致。raw 32-byte 前缀不完全相同不能否定业务字段连续性。
- BaoStock 有效日前共有 3509 个日期；两个查询均为实际交易的日期有 3420 天，3419 天的完整业务字段严格相同，另 1 天只差 amount `0.48` 元。严格检测保留该差异，不采用金额容差。
- 2025-02-14 两个代码的 BaoStock 实际 bar 逐字段相同，归类为 provider alias duplication 信号，不再作为“两只独立证券同时交易”的矛盾。
- BaoStock 停牌行的空值/零值差异按状态限定规则单列归一；原始值仍保存在冻结 JSON 中。

据此，外部验收对 alias migration fingerprint 的解释成立；原模式 D 把 raw bytes 差异、停牌表示差异和完全相同的 provider bar 过度解释成 unresolved contradiction。

## 通用候选器与盲测

新候选器使用版本合同 `V4_01_SOURCE_FINGERPRINT_CANDIDATE_V1 v1.0.0`。它使用通用 exchange/code/date 参数，无样本代码分支，并从冻结的 TDX/BaoStock 行重新计算；不读取原 R1 classifier 输出，也不读取盲测标签。

标签在所有四个样本完成推断后才由评估器加载。结果为：

| 组别 | 样本 | 结果 |
|---|---|---|
| 同实体代码更名正样本 | 300114→302132；000022→001872 | 2/2 生成强候选 |
| 吸收合并后继反例 | 000024→001979；000562→000166 | 2/2 未生成纯代码更名指纹候选 |
| 合计 | 4 | TP=2，FN=0，FP=0，TN=2 |

000022→001872 的旧 TDX `.day` 文件在当前本地快照中缺失，因此没有旧/新 TDX 成对 overlap；候选由新代码从共同 IPO 日回填的 TDX 历史、BaoStock 双代码历史连续性及连续生命周期元数据共同支持。该边界已明示，不计为 direct TDX pair validation。

## 研究阈值与限制

`20` 个共享有效交易日、BaoStock 活跃日严格匹配率 `99%`、TDX volume exact ratio `95%` 都属于候选研究阈值，不是 production acceptance threshold。当前仅一个正样本具备本地旧/新 TDX 成对文件，TDX volume 门槛仍未校准；本盲测也没有外部独立评审员参与。

因此阶段结果为 `PASS_BOUNDED_BLIND_VALIDATION`：支持继续研究通用 candidate detector，但不能估计全市场误报/漏报率，不能建立确认合同，也不清除官方代码变更索引覆盖门禁。

## 合同、证据与验收记录

- 候选合同：`config/v4_01_source_fingerprint_candidate_v1.json`
- 盲测输入清单：`config/v4_01_source_fingerprint_blind_cases_v1.json`
- 独立标签文件：`config/v4_01_source_fingerprint_blind_labels_v1.json`
- 离线评估器：`scripts/validate_v4_01_source_fingerprint_candidates.py`
- generic detector：`src/v4_01/source_fingerprint_candidate.py`
- 冻结输入压缩 JSON：`reports/v4_01/V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_*_R1.json.gz`
- 盲测收据：`reports/v4_01/V4_01_SOURCE_FINGERPRINT_CANDIDATE_BLIND_VALIDATION_R1.json`
- 可读结果：`docs/audits/V4_01_SOURCE_FINGERPRINT_CANDIDATE_BLIND_VALIDATION_R1.md`
- BaoStock request ledger 2026-09-29 计数：60；本组四案诊断请求增量：40；失败：0。
- 各冻结诊断报告记录 `tdx_sources_unchanged=true`；没有 TDX root 写入。
- 上游 `V4_01_OFFICIAL_CODE_CHANGE_EVENT_INDEX_R8_3` 仍为 `BLOCKED`；`AUDIT-V4-01-OFFICIAL-CODE-CHANGE-INDEX-COVERAGE-20260928` 保持独立开放。
- 当前 identity、alias 与 Historical Universe 生产产物未修改。

**阶段验收：`PASS_BOUNDED_BLIND_VALIDATION`**

**候选自动链接：`false`**

**生产 identity 修改授权：`false`**

**下一阶段：继续扩充跨板块正负样本，并重新评估研究阈值；不得据本阶段结论自动合并 identity。**

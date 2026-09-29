# V4-01 源级指纹阈值校准审计项 R1

- 审计项 ID：`AUDIT-V4-01-SOURCE-FINGERPRINT-CALIBRATION-20260929`
- 状态：`DEFERRED_NON_BLOCKING_RESEARCH`
- 日期：2026-09-29
- 所属阶段：`V4-01-SOURCE-FINGERPRINT-CANDIDATE-STUDY`
- 独立于：`V4-01 Gate A / official code-change event index coverage`

## 范围

评估 `V4_01_SOURCE_FINGERPRINT_CANDIDATE_V1` 的研究阈值能否在跨板块、跨样本 source 行为上稳定地产生候选，不赋予该候选 SAME_ENTITY 权限。

当前 R1 仅有：

- 两个同实体代码更名正样本，均来自深圳市场；
- 两个吸收合并后继负样本；
- 只有一个正样本同时有本地旧/新 TDX `.day` 文件可作成对历史字段比较；
- 四案结果为 TP=2、FN=0、FP=0、TN=2。

## 已知限制

1. TDX volume exact ratio `0.95` 仅由一个直接成对 TDX 正样本覆盖，尚未校准。
2. BaoStock 活跃历史匹配率 `0.99` 只在当前四案小样本上观察；不代表市场总体误报/漏报率。
3. 全部样本都来自 SZ，尚未验证 SH_MAIN、STAR 的 source 行为差异。
4. current TDX 对 000022 不含旧代码文件；其检测路径依赖 new-code backfill、BaoStock overlap 和 lifecycle metadata，不能代替 TDX 成对验证。
5. 本轮标签与 detector 分离，但没有外部独立评审员的盲审。

## 关闭条件

- 收集更多正式文件/公告绑定的代码更名正样本与 merger-successor/distinct 反例；
- 至少再获得两个具备旧/新 TDX 文件成对 overlap 的正样本；
- 覆盖 SZ 与 SH/STAR 等可获得的 Required Scope 市场，报告缺失样本的原因；
- detector 推断过程不加载 expected labels，标签证据由独立评审复核；
- 对 amount precision、volume agreement、停牌空值/零值归一分别报告严格值与候选值，不把未经校准的容差写成 accepted fact；
- 冻结 FP/FN 结果与候选合同版本，所有生产 identity mutation 继续由现有官方/独立接受证据政策单独确认。

## 当前处置

候选合同保持研究专用。此次 `PASS_BOUNDED_BLIND_VALIDATION` 仅代表四案数据采集完整、标签 hash 验证通过、四个输出符合冻结标签，以及 TDX 输入不变；本审计项继续开放，不阻断本候选研究报告，但也不改变 V4-01 Gate A。

**验收结果：`DEFERRED_NON_BLOCKING_RESEARCH`**

**production identity mutation：`PROHIBITED`**

## 2026-09-29 foundation closure task R2 disposition

本研究项不关闭，后续 paired-TDX、跨市场样本与阈值校准仍可继续；但按基础链 R2 任务，本研究不再是 V4-01 owner-gate blocker，也不授予生产确认权限。

- 当前状态：`DEFERRED_NON_BLOCKING_RESEARCH`
- `owner_stage_blocker = false`
- `production_confirmation_authority = false`
- 阈值合同：V1.0 原样冻结；本轮全 Required Scope scan 未调阈值。
- 阶段证据：`reports/v4_01/V4_01_FULL_SCOPE_SOURCE_FINGERPRINT_SCAN_R1.json` 与 `reports/v4_01/V4_01_IDENTITY_COMPLETENESS_GATE_V2_POSTCHECK_R1.json`。
- 下一阶段：独立外部验收后，后续研究仍可补充更多 paired TDX、SH/STAR 与困难负样本；研究通过也不能替代正式身份确认。

## 2026-09-29 外部验收 R1 后续处置

外部验收原文已按字节归档至 `docs/evidence/V4_01_SOURCE_FINGERPRINT_BLIND_STUDY_EXTERNAL_ACCEPTANCE_R1_20260929.md`，SHA-256：`6db29d56cddce77ca1b5f33e2d75197208abb710aa8cbc19d247156c8fe9060a`。处置与阶段合同、测试结果、接受边界、下一阶段记录见 `docs/audits/V4_01_SOURCE_FINGERPRINT_BLIND_STUDY_EXTERNAL_ACCEPTANCE_R1_DISPOSITION_20260929.md`。

- P1 F6 语义残留已修复：信号只依据实质不同的双代码 actual bars；完全相同的 provider alias bar 独立列示。
- 冻结的 candidate contract v1.0 和研究阈值未变。新增 synthetic contract tests 覆盖 0.95/0.99 边界、停牌空值/零值归一、实质冲突、provider code mismatch、重复日期、不完整查询及 metadata-only 不产候选；指定测试文件 `10 passed`。
- 扩样关闭条件尚未满足：至少两个额外 paired-TDX 正样本、跨市场及困难负样本仍开放。本审计项维持 `OPEN`；不据此改变 V4-01 Gate A 或生产身份。

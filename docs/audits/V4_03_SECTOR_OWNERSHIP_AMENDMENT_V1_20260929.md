# V4-03 Sector Ownership Amendment V1 — Candidate

- 日期：2026-09-29
- 合同：`V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1 v1.0.0-candidate`
- 状态：`AMENDMENT_CANDIDATE_PENDING_EXTERNAL_ACCEPTANCE`
- 适用阶段：V4-03 / V4-08

## 决策

本 amendment 调整依赖 accepted point-in-time (PIT) sector membership 的 materialization 所属阶段。它不删除 V4-03 的算法验收，也不降低质量门。V4-03 保留 membership-independent 的 Sector Native schema、machine contracts、field-local quality semantics、common-member semantics、native primitive formulas 与 synthetic/library vectors；这些内容的既有 machine-contract / producer-consistency / golden-vector receipts 继续绑定为 V4-03 evidence。

由于当前无 accepted historical PIT sector membership，V4-03 不生成 full-market sector rows。以下能力统一迁移至 V4-08 Sector / Rotation owner stage：

- PIT sector member snapshots 与 historical membership reconstruction；
- full-market Sector Native materialization；
- sector-native full-market rows；
- 任何消费历史 Sector/Rotation inputs 的生产路径。

`CURRENT_TDX_MEMBERSHIP` 仍为 diagnostic input，`pit_membership=false`，`historical_backtest_safe=false`。V4-08 必须先建立正式、可追溯的 membership source contract 与 baseline/PIT reconstruction，再产出、读取上述 materialization。此边界不授权将当前成员表回填到历史。

## Stage status and downstream permissions

Amendment 外部验收前，V4-03 为 `PASS_WITH_SECTOR_SCOPE_DEGRADED` candidate：Stock Core、Relative RPS、Market Reference、Market Regime 按各自现有 candidate receipts；Sector Native contract 保持 PASS，sector materialization 保持 `BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP`。当前 V4-03 accepted head 不变。

外部接受本 amendment 与 00-03 joint candidate 后，V4-03 可按修订范围申请 `FULL_PASS_AMENDED_SCOPE`。V4-04 Stock Core 仍须等待 joint external acceptance；V4-08 Sector/Rotation 仍 blocked，直到接受的 PIT membership baseline 和 full historical reconstruction 完成。Sector-dependent stock paths 继续 BLOCKED 或 SHADOW_ONLY。

## 不变项

- 没有伪造 historical PIT membership，也没有使用 `CURRENT_TDX_MEMBERSHIP` 回填历史。
- 没有修改 V4-01/V4-02 accepted input identities。
- 没有重建 V4-03 的 47 fields、market path 或 Market Regime。
- 没有生成 sector full-market rows、qualification、rotation 或 V4-08 production。
- 本 amendment 是 review candidate；未创建 V4-03 accepted head，也未授权 V4-04。

## 阶段记录

- Stage contract：V4-03 current capability contracts + V4-03 Sector Native boundary receipt + this versioned ownership amendment.
- Evidence：V4-03 R3 capability disposition、native machine-contract/producer/golden-vector PASS receipts、sector boundary `BLOCKED_ACCEPTED_SECTOR_MEMBERSHIP_INPUT_MISSING`。
- Acceptance：`AMENDMENT_CANDIDATE_PENDING_EXTERNAL_ACCEPTANCE`。
- Next stage：独立外部验收；之后才能按 accepted upstream/head policy 更新 sealed scope。

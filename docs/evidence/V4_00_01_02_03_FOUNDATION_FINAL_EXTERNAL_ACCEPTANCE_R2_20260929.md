# V4-00 ~ V4-03 Foundation Final External Acceptance R2

- 日期：2026-09-29
- 仓库：`NanOns/a-share-market-structure-research`
- 分支：`codex/v4-system-reform`
- 审计 HEAD：`8eb0bfeb0ec2eca7bfb3a3c5c2ca016160151b90`

## 最终裁决

```text
V4_00 = EXTERNAL_ACCEPTANCE_PASS

V4_01_IDENTITY_COMPLETENESS_GATE_V2 = EXTERNAL_ACCEPTANCE_PASS
V4_01_REQUIRED_SCOPE = EXTERNAL_ACCEPTANCE_PASS

V4_02_REQUIRED_SCOPE = EXTERNAL_ACCEPTANCE_PASS

V4_03 = EXTERNAL_ACCEPTANCE_PASS_AMENDED_SCOPE

V4_00_01_02_03_FOUNDATION_FULL_CHAIN = EXTERNAL_ACCEPTANCE_PASS

V4_04_ENTRY_AFTER_ACCEPTED_HEAD_PROMOTION = AUTHORIZED
```

当前只剩 `PROMOTE_ACCEPTED_HEADS_AND_GLOBAL_FOUNDATION_SEAL`，不再存在业务/算法修复。

## V4-01

完整扫描：
- 4,035,729 rows
- 786 sessions
- 5,351 source keys
- 330 entry boundaries
- 129 exit boundaries
- 917 R8.3 atomic boundaries
- 330/330 entry TDX files

Gate V2 已形成通用 candidate union：

```text
candidate_union =
  source_fingerprint_scan
  UNION r8_generic_relation
  UNION in_window_known_official_event
```

当前真实结果：

```text
candidate_union_count = 1
resolution_count = 1
missing_keys = []
extra_keys = []
duplicate_resolution_count = 0
invalid_state_count = 0
unresolved_count = 0
```

唯一 relation：

```text
SZ.300114 -> SZ.302132
effective_date = 2025-02-17
```

该 relation 同时得到：
- source-fingerprint discovery
- R8 generic discovery
- known official event
- independent TDX redecode
- accepted dated identity facts
- hash-verified SZSE official capture

正式 resolution：

```text
CONFIRMED_SAME_ENTITY_CODE_CHANGE
```

R7 canonical identity/universe hashes不变，因此无需重建。

## V4-02

上一轮 77/31 口径已修正：

```text
R6_PRICE_LIMIT_TOTAL_UNKNOWN_ROWS = 77
R6_UNKNOWN_SPECIAL_PHASE_ROWS = 31
R4_FAIL_CLOSED_EXCEPTION_SUBSET_ROWS = 31
UNDISPOSITIONED_ENGINEERING_EXCEPTIONS = 0
UNKNOWN_ROWS_CLAIMED_RESOLVED = 0
```

R6 external acceptance继续有效，V4-01 hashes未变化，所以无需 rebuild。

## V4-03

`V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1` 已接受。

V4-03 保留：
- Stock Core
- Relative RPS
- Market Reference
- Market Regime
- Sector Native schema/machine contracts/quality/common-member/native primitive formulas/vectors

迁移至 V4-08：
- PIT sector membership baseline
- historical membership reconstruction
- full-market Sector Native materialization
- Sector/Rotation production inputs

因此 promotion 后 V4-03 正式状态应为：

```text
FULL_PASS_AMENDED_SCOPE
```

V4-08 继续：

```text
BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION
```

## V4-00

Phase0 00A~00H 保持 FULL_PASS。

## Combined Regression

clean-code commit：

```text
8a446d6d8c3d6b05ea0ff3617288422685d68c53
```

命令：

```bash
python -m pytest -q -rs tests/v4_phase0 tests/v4_01 tests/v4_02 tests/v4_03
```

结果：

```text
275 passed
2 skipped
0 failed
0 error
```

两个 skip 都是 symlink creation unavailable 的平台限制，均标记为非 Required Scope。

## Commit binding

```text
tested_code_commit =
8a446d6d8c3d6b05ea0ff3617288422685d68c53

evidence_refresh_commit =
6f308dd9cd02ee02d7899beaf6523f34467e3b6f

candidate_seal_commit =
8eb0bfeb0ec2eca7bfb3a3c5c2ca016160151b90
```

`8a446 -> 6f308` 仅 evidence/candidate receipts。
`6f308 -> 8eb0` 仅新增 joint validation/final receipt。
测试后没有修改 src/scripts/config/tests/business logic。

GitHub 当前无 CI workflow/status check；本次外部验收依据源码、commit diff、hash-bound receipts 和 clean-worktree pytest receipt。

## 当前 formal head

`V4_STAGE_ACCEPTED_HEAD.json` 尚未 promotion，仍含历史：
- V4-01 PENDING
- V4-03 old degraded scope
- old V4-04 authorization wording

这是预期，因为此前任务明确要求外部终验前不得自行 promotion。

## Promotion 后正式状态

```text
V4_00 = FULL_PASS

V4_01 =
FULL_PASS_REQUIRED_SCOPE
EXTERNALLY_ACCEPTED

V4_02 =
FULL_PASS_REQUIRED_SCOPE
EXTERNALLY_ACCEPTED
BSE_OPTIONAL_DEGRADED

V4_03 =
FULL_PASS_AMENDED_SCOPE
EXTERNALLY_ACCEPTED

V4_00_01_02_03_FULL_CHAIN =
FOUNDATION_FULL_PASS

V4_04_ENTRY =
AUTHORIZED_FULL_CHAIN

V4_08_SECTOR =
BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION

INCREMENTAL_UPDATE =
DEFERRED_NON_BLOCKING

SOURCE_FINGERPRINT_CALIBRATION =
DEFERRED_NON_BLOCKING_RESEARCH
```

## 最终结论

```text
EXTERNAL_ACCEPTANCE = PASS
V4_00_01_02_03_FOUNDATION = PASS
BUSINESS_OR_ALGORITHM_REPAIR_REMAINING = NONE
FORMAL_PROMOTION_REMAINING = YES
V4_04 = AUTHORIZED_AFTER_PROMOTION_COMMIT
```

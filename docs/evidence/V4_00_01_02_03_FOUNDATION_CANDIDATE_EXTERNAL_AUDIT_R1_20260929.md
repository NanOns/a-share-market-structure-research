# V4-00~V4-03 Foundation Candidate 独立外部审计 R1
日期：2026-09-29
仓库：NanOns/a-share-market-structure-research
分支：codex/v4-system-reform
审计 HEAD：ecfcc3209404df5ccc7daaf6af905459cc075542

## 结论

```text
V4_00 = PASS

V4_01_IDENTITY_COMPLETENESS_GATE_V2_CONTRACT = EXTERNAL_ACCEPTANCE_PASS
V4_01_GATE_V2_IMPLEMENTATION = BLOCKED

V4_02_FUNCTIONAL = PASS
V4_02_CURRENT_TRUTH_RECONCILIATION = BLOCKED_METADATA_COUNT_FIX

V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1 = EXTERNAL_ACCEPTANCE_PASS
V4_03_STOCK_MARKET_CORE = PASS

V4_00_01_02_03_FULL_CHAIN = BLOCKED_FINAL_REPAIR
V4_04_ENTRY = NOT_AUTHORIZED_YET
```

当前不是大面积失败。真正剩余两个 P0：
1. V4-01 Gate V2 postcheck/resolution 仍硬编码 300114→302132，只处理 `resolution_items[:1]`，不能证明所有候选都会 fail-closed。
2. V4-02 把 R6 当前 Price-Limit 总 UNKNOWN=77 与 R4/UNKNOWN_SPECIAL_PHASE 子集 31 混为一谈。

另有两个 P1：
- 最终测试绑定的是 `50414582...`，最终 evidence HEAD 是 `ecfcc320...`，虽然两者之间只有 evidence JSON 变化，没有源代码/脚本/配置/测试变化，但最终 seal 应显式区分 tested code commit 与 final evidence commit。
- `267 passed, 2 skipped` 没记录 skip 原因；最终回归应使用 `-rs`。

## V4-01 Gate V2 合同

Gate V2 的设计方向接受：

```text
FULL ATOMIC BOUNDARY INVENTORY
+ GENERIC RELATION CANDIDATE DISCOVERY
+ SOURCE FINGERPRINT CANDIDATE DISCOVERY
+ KNOWN OFFICIAL EVENT CROSS-CHECK
+ FAIL-CLOSED RESOLUTION
+ INDEPENDENT POSTCHECK
```

旧 official event index 继续保留 `coverage_complete=false`，但不再作为唯一 exhaustive completeness gate。该 amendment 的工程收敛性和证据边界合理。

## V4-01 全量扫描

实际扫描：

```text
R7 Universe rows        = 4,035,729
sessions                = 786
source keys             = 5,351
entry boundaries        = 330
exit boundaries         = 129
R8.3 atomic boundaries  = 917
entry TDX files checked = 330
missing/invalid TDX     = 0
```

Required Scope 覆盖 SH_MAIN / SZ_MAIN / CHINEXT / STAR。

330 个 entry 中仅发现 1 个 `new TDX first_date < entry_date`：
`SZ.300114 → SZ.302132, effective 2025-02-17`。

独立 TDX 结果：
- shared pre-effective sessions = 3421
- OHLC/amount exact = 3421
- volume exact = 3420
- volume exact ratio ≈ 99.9708%

扫描输入使用 accepted `hsjday.zip`，本地 `D:\new_tdx` 仅只读观察。

## V4-01 P0：postcheck 非通用

`scripts/postcheck_v4_01_identity_completeness_gate_v2.py` 仍写死：

```python
candidate_pair = ("SZ.300114", "SZ.302132", "2025-02-17")
```

并写死 300114/302132 的 identity、official event、BaoStock 日期，最后多处使用：

```python
resolution_items[:1]
```

当前扫描恰好只有 1 个 candidate，所以本次数字结果正确；但 owner gate 不能靠当前单一案例成立。若未来全量重跑出现第二个 candidate，现实现可能只验证第一个并错误得到 unresolved=0。

修复后必须：

```text
candidate_union =
  source_fingerprint_scan_candidates
  UNION R8_3_generic_candidates
  UNION in-window known_official_candidates
```

以 `(old_code,new_code,effective_date)` 去重，并强制：

```text
resolution_keys == candidate_union_keys
resolution_count == candidate_union_count
unresolved_count == 0
```

任何候选没 resolution 都必须 BLOCKED。四个 blind cases 只能保留为 benchmark crosschecks，不能混入 Required Scope count。

## V4-02

R6 功能 acceptance 继续有效；旧 R1 OPEN 已正确改为 SUPERSEDED，R3 为 HISTORICAL_BLOCKED，R4=CLOSED，current_open_engineering_exception=0。

但当前生产事实是：

```text
V4_02_PRICE_LIMIT_BUILD_R6.unknown_rows = 77
UNKNOWN_SPECIAL_PHASE = 31
```

而 R4 的 `r3_fail_closed_dispositioned=31` 是 audit 子集。

新 reconciliation 和 joint receipt 把 `current_fail_closed_unknown_rows=31` 当成当前总 UNKNOWN，口径错误。

正确应至少拆为：

```text
r6_price_limit_total_unknown_rows = 77
r6_unknown_special_phase_rows = 31
r4_fail_closed_exception_subset_rows = 31
undispositioned_engineering_exceptions = 0
unknown_rows_claimed_resolved = 0
```

这是 evidence defect，不是 V4-02 algorithm defect。

## V4-03 Sector Ownership Amendment

本审计接受：

```text
V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1 = PASS
```

V4-03 保留：
- Sector Native schema
- machine contracts
- field-local quality
- common-member semantics
- primitive formulas
- synthetic/library vectors

迁移至 V4-08：
- accepted PIT sector membership baseline/reconstruction
- historical membership
- full-market Sector Native rows
- Sector/Rotation production inputs

`CURRENT_TDX_MEMBERSHIP` 继续 `pit_membership=false` / `historical_backtest_safe=false`，不得回填历史。

## V4-00

V4-00 current authority normalization 合格。00A~00H 不需重做。

## Combined Regression

当前：
`267 passed, 2 skipped, 0 failed`。

测试代码提交为 `50414582...`；最终 HEAD `ecfcc320...`。外部 compare 已确认两者之间只刷新 evidence/candidate JSON，没有修改 src/scripts/config/tests。因此测试对代码仍有效，但 final receipt 不应将 `50414582` 误称 current final commit。

最终应记录：

```text
tested_code_commit
final_evidence_commit
external_review_head
```

并校验二者 diff 只包含 evidence allowlist。

最终回归使用：

```bash
pytest -q -rs tests/v4_phase0 tests/v4_01 tests/v4_02 tests/v4_03
```

记录两个 skip 的测试名与原因。Required Scope gate 不允许无说明 skip。

## 最终状态

```text
V4_00 = FULL_PASS
V4_01 = FULL_PASS_CANDIDATE_BUT_GENERIC_RESOLVER_BLOCKED
V4_02 = FUNCTIONAL_FULL_PASS / EVIDENCE_FIX_REQUIRED
V4_03 = AMENDMENT_ACCEPTED / STOCK_MARKET_PASS
FULL_CHAIN = BLOCKED_FINAL_REPAIR
```

禁止继续扩 source-fingerprint 样本、调阈值、重算 V4-02 大数据、重算 V4-03 47 fields、做 Sector PIT、实现 incremental 或开始 V4-04。

完成两个 P0 与最终 evidence binding 后，如真实 candidate union 仍只有 300114→302132、unresolved=0、R7 hashes 不变，则下一轮可直接申请 00–03 FULL_PASS 和 V4-04 入场。

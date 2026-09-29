# V4-00~V4-03 Foundation FINAL REPAIR 任务卡 R3
日期：2026-09-29
基线 HEAD：ecfcc3209404df5ccc7daaf6af905459cc075542
性质：最后一轮小修，禁止扩大范围。

## 已外部接受

```text
V4_00 current authority = PASS
V4_01_IDENTITY_COMPLETENESS_GATE_V2 amendment semantics = ACCEPTED
V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1 = ACCEPTED
SOURCE_FINGERPRINT_CALIBRATION = DEFERRED_NON_BLOCKING_RESEARCH
```

## P0-A：V4-01 generic resolver/postcheck

Required Scope owner-gate 中删除所有 300114/302132/2025-02-17 特判和 `resolution_items[:1]`。

Blind benchmark 固定案例可以保留，但只能位于 `known_bounded_validation_crosschecks`。

构造：

```text
candidate_union =
  V4_01_FULL_SCOPE_SOURCE_FINGERPRINT_SCAN_R1.relation_candidates
  UNION R8_3 generic relation candidates
  UNION in-window known official relation candidates
```

canonical key：

```text
(old_source_security_key,new_source_security_key,effective_date)
```

逐 candidate 通用执行：
1. 独立重解码 TDX；
2. 重算 semantic overlap；
3. 读取对应 frozen BaoStock evidence（若有）；
4. 绑定 independent official / accepted identity evidence；
5. 输出四态之一：
   - CONFIRMED_SAME_ENTITY_CODE_CHANGE
   - CONFIRMED_DISTINCT_MERGER_SUCCESSOR
   - CONFIRMED_DISTINCT_CODE_REUSE
   - UNRESOLVED_IDENTITY_RELATION

必须强制：

```text
resolution_keys == candidate_union_keys
resolution_count == candidate_union_count
unresolved_count == 0
```

否则 V4-01 BLOCKED。

新增 synthetic tests：
- 2 candidates / 2 resolved => PASS
- 2 candidates / 1 unresolved => BLOCKED
- R8 generic 多一个 candidate => union 必须包含
- known official 多一个 in-window candidate => union/crosscheck 必须包含
- resolution 多出 union 外 key => BLOCKED

修复后重跑当前真实数据。如果 union 仍只有 300114→302132 且 R7 hashes 不变，不重建 V4-01/V4-02/V4-03 大数据。

## P0-B：V4-02 UNKNOWN 口径

正式 truth：

```text
R6_PRICE_LIMIT_TOTAL_UNKNOWN_ROWS = 77
R6_UNKNOWN_SPECIAL_PHASE_ROWS = 31
R4_FAIL_CLOSED_EXCEPTION_SUBSET_ROWS = 31
UNDISPOSITIONED_ENGINEERING_EXCEPTIONS = 0
UNKNOWN_ROWS_CLAIMED_RESOLVED = 0
```

删除或重命名含糊的 `current_fail_closed_unknown_rows`。

Full-chain validator 必须直接校验 R6 build `unknown_rows == 77`，同时单独校验 R4 subset=31。

## P1：最终测试与 evidence binding

修复代码/配置/测试后先 commit：

```text
TESTED_CODE_COMMIT=<SHA>
```

在 clean code commit 上运行：

```bash
python -m pytest -q -rs tests/v4_phase0 tests/v4_01 tests/v4_02 tests/v4_03
```

receipt 记录：
- passed/failed/skipped
- skip test names/reasons
- python/pytest version
- tested_code_commit
- git status

Required Scope 测试若 skip => BLOCKED；optional/platform skip 必须解释。

随后可生成 evidence-only seal commit：

```text
FINAL_EVIDENCE_COMMIT=<SHA>
```

validator 必须验证：
- tested_code_commit 是 final_evidence_commit 的祖先；
- 两者 diff 只允许 reports/**、candidate data JSON、docs/evidence/**、docs/audits/** 的证据文件；
- 不允许 final evidence commit 修改 src/**、scripts/**、config/**、tests/**、production/**；若有则必须重跑测试。

最终 receipt 使用：

```text
tested_code_commit
final_evidence_commit
external_review_head
```

不要再用含糊 `current_commit`。

## V4-03

本轮 amendment 已被外部接受，可在 candidate receipt 记录：

```text
external_amendment_acceptance = ACCEPTED_BY_EXTERNAL_AUDIT_20260929
```

但 joint FULL PASS 终验前仍不得 promotion global accepted head。

## 最终刷新

至少：
- `V4_01_IDENTITY_RELATION_RESOLUTION_R2.json`
- `V4_01_IDENTITY_COMPLETENESS_GATE_V2_POSTCHECK_R2.json`
- `V4_01_FINAL_STAGE_CANDIDATE_R10.json`
- `V4_01_ACCEPTED_HEAD_CANDIDATE.json`
- `V4_02_CURRENT_TRUTH_RECONCILIATION_R2.json`
- `V4_00_01_02_03_FULL_CHAIN_TEST_RECEIPT_R2.json`
- `V4_00_01_02_03_FULL_CHAIN_VALIDATION_R2.json`
- `V4_00_01_02_03_FULL_CHAIN_FINAL_RECEIPT_R2.json`

最终停在：

```text
V4_00_01_02_03_FULL_CHAIN = FULL_PASS_CANDIDATE
EXTERNAL_REVIEW_READY = TRUE
V4_04_ENTRY = PENDING_FINAL_EXTERNAL_ACCEPTANCE
```

禁止自行 promotion global accepted head。

## 禁止事项

不新增 source fingerprint 市场样本；不调 v1.0 threshold；不继续搜官方事件；不重建 V4-02；不重算 V4-03 47 fields；不做 Sector membership；不实现 incremental；不开始 V4-04/V4-05。

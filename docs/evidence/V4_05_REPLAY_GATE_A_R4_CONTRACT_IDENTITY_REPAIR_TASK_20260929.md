# V4-05 Replay Gate A R4
## Contract Identity / Period Semantics / Revision Ledger Final Repair Task

**项目：** 大A交易 / A-Share Market Structure Research  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**日期：** 2026-09-29  
**Starting HEAD：** `9864939068a633e650de232f2f285681592a6528`

---

# 0. R3 External Audit Result

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R3`

R3 已完成真实 replay 计算。

R4 **禁止重做已经通过的 source/adjustment 主链**。

仅关闭：

```text
B01 PERIOD_ASOF_VIEW_CONTRACT_DRIFT
B02 MARKET_REFERENCE_AND_REGIME_IDENTITY_DRIFT
B03 REVISION_IDEMPOTENCY_NOT_LEDGER_EXECUTED
B04 R3_LFS_REMOTE_RECOVERY_NOT_PROVEN
```

并增强 independent numeric postcheck。

---

# 1. Frozen Inputs — MUST NOT CHANGE

保持：

```text
Sep-28 official TDX package SHA
70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c

Sep-26 frozen GBBQ
sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e

target_trade_date
2026-09-28

formal_publication_at
2026-09-29T06:53:52+00:00
```

保持：

```text
historical_as_recorded_claim = false
coordinate_basis = T0_CURRENT_COORDINATE
```

保持 5222 target identities。

---

# 2. B01 Repair — Restore PERIOD_ASOF_V1 Semantics

当前错误：

```python
period_view = "BLOCKED" if quality_unknown else view
```

修复为：

```text
period_view is always temporal classification:
  CLOSED_ONLY
  AS_OF_PARTIAL

period_status carries data / adjustment block:
  BLOCKED_BY_ADJUSTMENT
  BLOCKED_BY_UNKNOWN_STATUS
  ...
```

QFQ unready：

```text
period_view = CLOSED_ONLY or AS_OF_PARTIAL
period_status = BLOCKED_BY_ADJUSTMENT
ohlc = null
adjusted_quality = UNKNOWN
```

禁止新增一个未被 accepted contract 定义的：

`period_view = BLOCKED`

除非另开正式 contract version；本任务禁止改 contract。

---

# 3. B01 Regression Test

必须新增：

## P01 Closed period + QFQ unavailable

Expected：

```text
period_view = CLOSED_ONLY
period_status = BLOCKED_BY_ADJUSTMENT
```

## P02 Active partial period + QFQ unavailable

Expected：

```text
period_view = AS_OF_PARTIAL
period_status = BLOCKED_BY_ADJUSTMENT
```

## P03 Consumer

V4-04 `closed_period_trend()`：

- temporal closed + unusable QFQ -> UNKNOWN because required input unavailable；
- 不是因为 invented `period_view=BLOCKED`。

重建 R4 period artifact。

---

# 4. B02 Repair — Exact V4-03 Universe Snapshot Identity

`MARKET_RELATIVE_REFERENCE_V1` 必须沿用 accepted V4-03 identity semantics。

不能再：

```python
digest(sorted(member_ids))
```

必须复用等价算法：

```text
snapshot_id =
SHA256(
  sorted(
    security_id,
    membership_basis,
    source_revision_id,
    eligibility_status
  )
)
```

对于 start sessions：

```text
T-1
T-3
T-5
```

必须从 accepted V4-01 historical universe 读取对应日期 provenance。

在 receipt 中记录：

```text
start_session
member_count
snapshot_id
snapshot_identity_algorithm_id
source_artifact_sha
```

---

# 5. Target Market Snapshot Identity

Market Regime 的：

`market_snapshot_id`

必须是：

`2026-09-28 target snapshot`

不能使用 horizon-1 的 Sep-24 start-universe snapshot id。

生成：

`V4_05_R4_TARGET_MARKET_SNAPSHOT.json`

至少绑定：

```text
target_trade_date
5222 identities
security_id
source_security_key
dated identity provenance
membership / eligibility semantics
source revision identity
snapshot digest
```

如果 go-forward target membership provenance 与 V4-01 historical row schema不同：

必须定义一个 versioned target snapshot identity contract，并证明不会把不同日期但同 member IDs 混成同 snapshot。

---

# 6. adjustment_basis_id Repair

禁止：

`adjustment_basis_id = "T0_CURRENT_COORDINATE"`

作为唯一 identity。

需要绑定实际 source identity。

推荐：

```text
per-security endpoint basis =
T0_CURRENT_COORDINATE
+
frozen GBBQ snapshot id
+
raw source package id

adjustment_basis_id =
SHA256(sorted(evaluable security_id + endpoint basis identity))
```

或复用 accepted V4-03 producer 的等价 basis-set identity 算法。

要求：

- 1/3/5 horizon 分别有 basis identity；
- independent postcheck 可重算；
- missing/unknown member 不可偷偷进入 evaluable set。

---

# 7. Rebuild Market Reference

重新构建：

`MARKET_RELATIVE_REFERENCE_V1`

1 / 3 / 5 session。

每个 horizon 必须绑定：

```text
market_calendar_id
start_session
end_session
start_universe_snapshot_id
evaluable_set_identity
adjustment_basis_id
input_source_digest
window_identity
max_source_trade_date
formal_publication_at
```

不要修改 reference formula。

保留 coverage / missing gate。

---

# 8. Market Reference Independent Recalculation

独立 verifier 不得调用 production receipt 的 PASS。

从：

```text
R4 daily history
accepted V4-01 start-universe rows
```

独立重算：

```text
1-session
3-session
5-session
```

至少比较：

```text
reference_return
universe_count
evaluable_count
missing_count
coverage
evaluable_set_identity
start_universe_snapshot_id
adjustment_basis_id
```

全部一致才 PASS。

---

# 9. Market Reference Path Continuation

当前 R3 直接：

```text
accepted path through Sep-24
+
target daily reference
```

但没有生成 contract-faithful Sep-28 path row。

R4 必须处理。

读取：

`V4_03_MARKET_REFERENCE_PATH_V1`

和其：

`rebase_policy = UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION`

明确决定并记录：

## Option A — Accepted-series continuation

如果合同允许：

生成 Sep-28 path row，绑定：

```text
series_version
prior_path_artifact_sha
prior_row_trade_date
prior_row_output_digest
target_market_return_1 output_digest
target start-universe snapshot id
target evaluable-set id
target adjustment-basis id
input_source_digest
path_level
output_digest
```

不得修改 2026-09-24 及更早 accepted path rows。

## Option B — New series version

如果 current-coordinate identity 导致旧 series 不能合法续接：

建立新 series version。

必须遵守 rebase policy。

## Option C — Fail closed

若 A/B 都无法在本任务证明：

```text
trend_axis = UNKNOWN
```

MARKET_REGIME 保持 DEGRADED_PASS。

禁止无证据地把 trend 标 OBSERVED。

---

# 10. Market Path Coordinate Diagnostic

无论选择 A/B/C，都运行一个 diagnostic：

使用 R4 T0-current-coordinate daily history独立重算最近至少 25 sessions 的 daily equal-weight reference/path。

比较：

```text
accepted historical path continuation
vs
T0-coordinate reconstructed path
```

记录：

```text
daily return differences
path level differences
MA20 difference
MA20(t-5) difference
trend-axis effect
```

此 diagnostic 不得 retroactively 改写 accepted V4-03 history。

它只用于判断 continuation semantics 是否安全。

---

# 11. Rebuild Market Regime Identity

Market Regime target identity 至少绑定：

```text
trade_date = 2026-09-28
market_calendar_id
target market_snapshot_id
market path / series identity
adjustment_basis_id
input_source_digest
parameter_set_id
```

现有 UNKNOWN 可以保留：

```text
breadth_axis
stress_level
stress_change
regime_ui
```

因为没有 accepted Sep-28 price-limit facts / prior comparable materialization。

不要为了 FULL_PASS 补造这些字段。

---

# 12. B03 — Real Revision Idempotency

当前 R3 的：

```text
hash(identity)
```

不是 G08 persistence replay。

项目已有 V4-00C publication/revision/namespace schema。

R4 必须在：

```text
temporary / isolated test schema
```

或合同等价的 isolated persistence harness 中执行。

禁止写生产表。

---

# 13. G08 Required Cases

## I01 identical replay

相同：

```text
target date
source package
GBBQ
calendar
contracts
parameters
formal publication identity
logical output
```

执行两次。

Expected：

```text
no second logical revision
no duplicate accepted publication
no head drift
same publication/revision identity
```

## I02 true source revision

只改变受控 source revision identity。

Expected：

```text
append new revision
old revision remains immutable
new revision points to correct predecessor / lineage
head moves only after accepted transition
```

## I03 same-day duplicate conflict

相同 revision identity + different payload：

hard fail.

## I04 rollback / transaction failure

中途失败：

```text
no dangling accepted head
no partial consumed-source binding
```

---

# 14. G08 Receipt Must Be Observed, Not Hardcoded

禁止直接写：

```text
duplicate_revision_count = 0
duplicate_publication_event_count = 0
```

除非这些值来自实际 isolated ledger query。

Receipt 至少包含：

```text
schema/migration identity
test namespace/schema id
before counts
after first replay counts
after second replay counts
changed-source counts
publication ids
lineage ids
revision numbers
head ids
rollback result
cleanup result
```

---

# 15. B04 — Remote LFS Restore

R3 有 5 个新 LFS objects。

R4 必须 fresh clone / isolated origin fetch：

```text
git clone
git lfs fetch
git lfs checkout
```

并恢复/哈希：

```text
V4_05_R3_T0_COORDINATE_DAILY_HISTORY
V4_05_R3_PERIOD_ASOF
V4_05_R3_PURE_CORE_FACTORS
V4_05_R3_FULL_SCOPE_FACTORS
V4_05_R3_FULL_MARKET_CORE_PROFILE
```

R4 修复后若产生新的 LFS artifact，也必须一起验证。

创建：

`V4_05_R4_REMOTE_LFS_RESTORE.json`

每个 artifact：

```text
pointer oid
expected bytes
restored bytes
expected SHA
restored SHA
status
```

任一失败：

`BLOCKED_REMOTE_LFS_OBJECT_UNAVAILABLE`

---

# 16. Independent Numeric Postcheck

R4 independent postcheck 不能只检查 hashes / PASS flags。

至少独立复算：

## Stocks

不少于 20 entities，覆盖：

```text
SH_MAIN
SZ_MAIN
CHINEXT
STAR

normal ready
no-T0-bar
adjustment-unknown
short history
code-change
boundary-like state
```

独立重算代表字段：

```text
ret1
ret5
ret20
ma20
ma60
atr20
amount_ratio20
rps5
rps20
rel_market_1
trend_state
position_state
compression_state
weekly trend
monthly trend
```

## Market

独立重算：

```text
reference 1/3/5
target snapshot identity
basis identity
target path row
trend_axis
participation_axis
```

不得直接调用 production builder 的最终函数作为“独立复核”。

可以复用底层数学 primitive，但输入选择、window、identity、聚合必须独立实现。

---

# 17. Core Profile Rebuild

B01/B02 修复后重建：

`V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz`

允许：

`PARTIAL_UNKNOWN = 5222`

只要 UNKNOWN 是合同允许且原因真实。

不要求变成 COMPLETE。

需要 R3→R4 diff：

```text
row set
business fields
state fields
period lineage
market identity
source digests
UNKNOWN reasons
```

任何预期之外的业务漂移必须解释。

---

# 18. Capability Matrix R4

至少：

```text
CURRENT_FORWARD_ADJUSTED_PRICE
WEEKLY_PERIOD
MONTHLY_PERIOD
PURE_CORE_FACTORS
MARKET_REFERENCE
MARKET_REGIME
CURRENT_FORWARD_STOCK_CORE
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
```

允许：

```text
FULL_PASS
DEGRADED_PASS
BLOCKED
```

不强迫：

`CURRENT_FORWARD_STOCK_CORE = FULL_PASS`

如果 prior-RPS delta / market axes 仍合法 UNKNOWN：

`DEGRADED_PASS`

可以是正确结果。

---

# 19. DATA_FACTOR_REPLAY_PASS Alias

只有在依赖身份修复后才允许：

```text
DATA_FACTOR_REPLAY_PASS
scope = CURRENT_FORWARD_STOCK_CORE
status = DEGRADED_PASS
```

不得 global PASS。

Historical AS_RECORDED 继续：

`BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

---

# 20. Tests

新增测试覆盖：

```text
period_view contract
snapshot identity algorithm
basis identity
target market snapshot
market path continuation
mixed-basis/path guard
real revision ledger idempotency
same-day conflict
rollback
remote-LFS receipt parser
independent numeric samples
```

运行：

```text
python -m pytest -q
  tests/v4_01
  tests/v4_02
  tests/v4_03
  tests/v4_04
  tests/v4_05
  tests/v4_joint
  tests/v4_phase0
```

正式 runtime receipt 必须绑定 implementation commit。

---

# 21. Required R4 Evidence

至少：

```text
reports/v4_05/V4_05_R4_STAGE_ENTRY.md
reports/v4_05/V4_05_R4_PERIOD_ASOF.json
reports/v4_05/V4_05_R4_MARKET_SNAPSHOT_IDENTITY.json
reports/v4_05/V4_05_R4_MARKET_REFERENCE.json
reports/v4_05/V4_05_R4_MARKET_REFERENCE_INDEPENDENT_RECALC.json
reports/v4_05/V4_05_R4_MARKET_PATH_CONTINUATION.json
reports/v4_05/V4_05_R4_MARKET_PATH_COORDINATE_DIAGNOSTIC.json
reports/v4_05/V4_05_R4_MARKET_REGIME.json
reports/v4_05/V4_05_R4_REVISION_LEDGER_IDEMPOTENCY.json
reports/v4_05/V4_05_R4_REMOTE_LFS_RESTORE.json
reports/v4_05/V4_05_R4_INDEPENDENT_NUMERIC_POSTCHECK.json
reports/v4_05/V4_05_R4_CORE_PROFILE_REPLAY.json
reports/v4_05/V4_05_R4_R3_DIFF.json
reports/v4_05/V4_05_R4_DETERMINISM.json
reports/v4_05/V4_05_R4_CAPABILITY_GATE.json
reports/v4_05/V4_05_R4_RUNTIME_TEST_RECEIPT.json
reports/v4_05/V4_05_R4_INDEPENDENT_POSTCHECK.json
reports/v4_05/V4_05_R4_STAGE_CANDIDATE_MANIFEST.json
reports/v4_05/V4_05_R4_CLOSURE.md
```

---

# 22. Accepted Heads

R4 仍然是 candidate repair。

禁止修改：

```text
data/v4/V4_05_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

除非 global head 只是被读取验证。

禁止提前授权 V4-06 / V4-07 / V4-08。

---

# 23. Stop Point

R4 完成上述修复后：

```text
external_acceptance = PENDING
```

停止。

等待独立外部验收。

只有外部验收通过后，下一张卡才允许：

```text
V4-05 Accepted Head Promotion
+
next-stage authorization
```

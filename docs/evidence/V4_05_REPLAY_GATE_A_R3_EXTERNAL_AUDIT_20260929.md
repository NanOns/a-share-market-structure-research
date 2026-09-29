# V4-05 Replay Gate A R3 独立外部验收审计
## Target-Date Replay / Capability-Scoped Data-Factor Gate

**项目：** 大A交易 / A-Share Market Structure Research  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计日期：** 2026-09-29  
**Reviewed HEAD：** `9864939068a633e650de232f2f285681592a6528`  
**R3 Implementation Commit：** `fc92ce7292794583ef4bd1bb0d7f33e5f10cccc1`  
**上一轮基线：** `7943596a800e9ac9234885b0dad77b06c87e1e25`

---

# 0. 唯一总状态

本轮外部验收结论：

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R3`

更精确的原因：

`BLOCKED_CONTRACT_IDENTITY_AND_REVISION_EVIDENCE`

注意：

这不是上一轮的“未执行”。

R3 已经真实完成：

```text
T0-coordinate daily history
Weekly / Monthly AS-OF
Pure-Core factors
current RPS / relative-market fields
Market Reference
Market Regime
Full-Market Core Profile
Determinism
Temporal negatives
Runtime tests
Independent postcheck
```

因此 R3 比 R2 前进了一大步。

但 R3 仍不能晋级 V4-05 Accepted Head，因为存在 4 个正式验收阻断：

```text
B01 PERIOD_ASOF contract drift
B02 Market Reference / Regime identity drift
B03 G08 revision idempotency is identity simulation, not ledger replay
B04 New R3 LFS artifacts lack remote-recovery proof
```

另外独立 postcheck 的数值复算深度不足，作为 R4 必修增强项。

---

# 1. R3 实际完成度

R3 构建了：

## Daily History

```text
entities = 5222
rows = 1,299,408
lookback = up to 251 actual bars

ADJUSTED_READY = 5195
NO_T0_RAW = 12
UNSUPPORTED / UNKNOWN = 15
```

R3 对所有 READY 实体的 lookback digest 与已接受 V4-02 go-forward candidate 一致。

**PASS**

---

# 2. Calendar Target Scope

R3 冻结了 2026-09-26 已采集的 SSE/SZSE 官方日历来源。

目标日期：

`2026-09-28`

R3 日历判断：

```text
2026-09-28 = session
2026-09-29 = session
2026-09-30 = session
2026-10-01 onward National Day closure
```

本轮外部审计另外核对了 SSE/SZSE 官方 2026 中秋/国庆休市公告：

- 9月25日至9月27日休市；
- 9月28日起照常开市；
- 10月1日至10月7日休市。

因此，对 **Sep-28 target 的 period completion 判断**，该 calendar source 可以接受。

这里接受的是：

`TARGET_SPECIFIC_GO_FORWARD_CALENDAR_SEMANTICS`

不是把整个 2024–2026 calendar retroactively 提升成 historical PIT publication。

**PASS for Sep-28 target scope**

---

# 3. G05 已真实执行

R3 Weekly / Monthly artifact：

`reports/v4_05/staging/V4_05_R3_PERIOD_ASOF.jsonl.gz`

SHA256：

`46225dc8bbac4e93e1b6e9d8eb07dda545828f02dc9f6ba44f48cffbdcf36d51`

rows：

`694,692`

R3 正确识别：

```text
target_week_closed_only = false
target_month_closed_only = false
future_price_rows_used = 0
```

即：

2026-09-28 是星期一，周/月后续 9/29、9/30 已由官方 schedule 知道存在，但不能读取它们的未来价格。

这一方向正确。

但见 B01。

---

# 4. G06 已真实执行

Pure-Core factor artifact：

`V4_05_R3_PURE_CORE_FACTORS.jsonl.gz`

Full-scope factor artifact：

`V4_05_R3_FULL_SCOPE_FACTORS.jsonl.gz`

5222 个 target identities 均保留。

R3 没有伪造第一天 forward 的 prior-RPS delta：

```text
rps5_delta1 = UNKNOWN
rps5_delta3 = UNKNOWN
rps20_delta3 = UNKNOWN

reason =
BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY
```

这是正确处理。

当前 cross-section 可合法计算的：

```text
rps5
rps20
rel_market_1
rel_market_3
rel_market_5
```

被单独计算。

**方向 PASS**

但 Market Reference identity 见 B02。

---

# 5. G07 Core Profile 已真实构建

Artifact：

`reports/v4_05/staging/V4_05_R3_FULL_MARKET_CORE_PROFILE.jsonl.gz`

SHA256：

`ec27446201b22e16364df617a1ce735e57029bf27f275ec9a8bb159acdc5b3be`

rows：

`5222`

board counts：

```text
SH_MAIN = 1702
SZ_MAIN = 1494
CHINEXT = 1408
STAR = 618
```

upstream adjusted unavailable：

`27`

这些实体没有被删除以制造“完整率”。

两次 replay：

```text
same row set = true
same logical digest = true
same output digest = true
same quality counts = true
```

**Determinism PASS**

目前：

`PARTIAL_UNKNOWN = 5222`

这本身不是错误。

原因主要包括：

- prior-RPS delta 尚无真实 forward history；
- Market Regime 部分 axis UNKNOWN；
- 27 个 adjustment-unavailable；
- 部分历史 gap / insufficient history。

在 §52B 下，字段级 UNKNOWN 可以支持 scoped DEGRADED_PASS，前提是上游身份和合同语义正确。

---

# 6. Temporal Suite

R3 执行 8 类 negative tests：

```text
A T+1 raw
B later week session
C future month-end
D future identity metadata
E later GBBQ revision
F provider after publication
G future factor source
H future market input
```

结果：

`10 passed`

正式 runtime：

```text
413 passed
0 failed
2 skipped
```

测试运行绑定 implementation commit：

`fc92ce7292794583ef4bd1bb0d7f33e5f10cccc1`

Seal commit 没有再修改业务实现。

**PASS as test evidence**

但测试没有覆盖下面三个合同漂移。

---

# 7. B01 — PERIOD_ASOF_V1 Contract Drift

这是明确阻断。

Accepted V4-02 period semantics：

```text
period_view =
CLOSED_ONLY
or
AS_OF_PARTIAL
```

数据质量问题由：

```text
period_status
adjusted_quality
```

表达。

原 accepted builder 在 QFQ 不可用时：

```text
period_view remains CLOSED_ONLY / AS_OF_PARTIAL
period_status = BLOCKED_BY_ADJUSTMENT
qfq OHLC = null
```

R3 新实现：

`scripts/build_v4_05_r3_periods.py`

写的是：

```python
"period_view": "BLOCKED" if quality_unknown else view
```

也就是说：

QFQ adjustment unavailable 时把：

```text
time-view dimension
```

从：

```text
CLOSED_ONLY / AS_OF_PARTIAL
```

改成了：

`BLOCKED`

这不是原 accepted PERIOD_ASOF 合同中的 period_view 值。

这会影响 V4-04 consumer：

`closed_period_trend()`

该 consumer 明确根据：

```text
period_view == CLOSED_ONLY
```

决定是否允许 closed-period trend。

虽然这批 affected rows 最终本来就应该 UNKNOWN，但不能通过改变 accepted enum/维度语义实现 UNKNOWN。

必须恢复：

```text
period_view = temporal view
period_status = quality/data gate
```

**B01 = FAIL / BLOCKING**

---

# 8. B02 — Market Reference Identity Drift

Accepted V4-03：

`MARKET_RELATIVE_REFERENCE_V1`

身份不是只看数值。

正式 identity 至少包含：

```text
market_calendar_id
start_session
end_session
start_universe_snapshot_id
evaluable_set_identity
adjustment_basis_id
input_source_digest
```

更重要的是：

## Accepted V4-03 snapshot identity algorithm

原 producer 使用：

```text
SHA256(
  sorted(
    security_id,
    membership_basis,
    source_revision_id,
    eligibility_status
  )
)
```

## R3 实现

`scripts/build_v4_05_r3_market_reference.py`

使用：

```python
digest(sorted(members[start]))
```

只哈希：

`security_id`

丢掉了：

```text
membership_basis
source_revision_id
eligibility_status
```

因此 R3 的：

`start_universe_snapshot_id`

与 accepted V4-03 producer identity semantics 不一致。

这不是单纯“hash 长得不一样”。

Replay Gate A 的目的之一就是证明 source/input identity 可复现。

弱化身份以后，未来即使 membership provenance 变化但 member IDs 没变，也会被错误认为同一个 snapshot。

---

# 9. B02b — adjustment_basis_id 被弱化

Accepted V4-03 producer 会对实际参与计算的 per-security adjustment basis 构造 identity digest。

R3 Market Reference 直接写：

`adjustment_basis_id = "T0_CURRENT_COORDINATE"`

这个字符串只描述坐标类型，没有绑定：

- frozen GBBQ snapshot；
- per-security basis；
- evaluable set 的 adjustment identity。

因此也不满足 accepted producer 的 identity 强度。

建议至少使用：

```text
hash(
  sorted(
    security_id,
    T0_CURRENT_COORDINATE,
    frozen_gbbq_snapshot_id
  )
)
```

并保持与 accepted V4-03 producer 的 basis-set identity 规则等价。

**B02 = FAIL / BLOCKING**

---

# 10. B02c — Market Regime target market_snapshot_id 错位

Accepted V4-03 regime producer：

```text
market_snapshot_id = snapshot_ids[target_trade_date]
```

即 target session 本身的 market snapshot identity。

R3：

`scripts/build_v4_05_r3_market_regime.py`

使用：

```python
market_snapshot_id =
target_reference["start_universe_snapshot_id"]
```

对于 horizon=1：

这是 **2026-09-24 start universe** 的 identity。

它不是 2026-09-28 target market snapshot identity。

即使 Sep-24 与 Sep-28 成员集合碰巧完全相同：

```text
target snapshot identity
!=
start snapshot identity
```

因为 identity 还应包含日期有效 provenance / source revision。

必须修复。

**BLOCKING**

---

# 11. Market Path Continuation — Current Result Not Yet Independently Acceptable

R3 Market Regime trend 这样构造：

```text
accepted V4-03 market path through 2026-09-24
+
Sep-28 newly computed 1-session market reference
```

然后计算 target level / MA20 / MA20(t-5)。

这个方向 **可能合法**，因为 accepted contract：

`V4_03_MARKET_REFERENCE_PATH_V1`

本身是版本化 chained research index，且有：

`rebase_policy = UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION`

所以外部审计不直接断言“数值一定错”。

但当前 R3 缺少正式 target path row / continuation receipt：

没有把以下身份完整绑定：

```text
series_version
prior accepted path SHA
prior path row output_digest
target market_return_1 identity
target start-universe snapshot identity
target adjustment-basis identity
target input_source_digest
target output_digest
```

与此同时 regime row 又错误地把：

`adjustment_basis_id = T0_CURRENT_COORDINATE`

直接放到一个同时消费旧 path 的 identity 上。

因此当前 trend_axis=`NEUTRAL` 不能作为已验收的 MARKET_REGIME observed field。

R4 有两个合法选择：

### Option A — Contract-faithful path continuation

真正生成 Sep-28 `MARKET_REFERENCE_PATH_V1` target row，继承 accepted series version，并完整绑定 prior-row identity。

### Option B — Fail closed

如果无法证明 series continuation 满足 accepted identity/rebase policy：

```text
trend_axis = UNKNOWN
MARKET_REGIME remains DEGRADED_PASS
```

禁止为了拿 PASS 修改 market-regime 算法。

---

# 12. B03 — G08 Revision Idempotency 目前只是哈希模拟

R3 receipt：

`V4_05_R3_REVISION_IDEMPOTENCY.json`

表面声称：

```text
duplicate_revision_count = 0
duplicate_publication_event_count = 0
output_drift = false
```

但实际代码：

`scripts/verify_v4_05_r3_determinism.py`

只是在内存中：

```text
hash(identity)
hash(same identity)
hash(changed identity)
```

然后直接写：

```text
duplicate_revision_count = 0
duplicate_publication_event_count = 0
```

没有真实执行：

- publication insert；
- revision append；
- accepted head；
- duplicate conflict；
- same-source rerun；
- changed-source revision。

项目已有 V4-00C versioned publication/revision/namespace schema 和 PostgreSQL migration tests。

Replay Gate A 的 G08 不能用：

`identity hash is deterministic`

代替：

`publication/revision behavior is idempotent`

R4 必须在：

```text
isolated / temporary V4 schema
```

或合同等价的独立 persistence harness 中真实执行。

不得写 production 数据库。

**B03 = FAIL / BLOCKING**

---

# 13. B04 — R3 新增 5 个 LFS 核心产物无远端恢复证明

本轮 5 个核心 staging artifact 均使用 Git LFS：

```text
V4_05_R3_T0_COORDINATE_DAILY_HISTORY
52,034,710 bytes

V4_05_R3_PERIOD_ASOF
60,108,555 bytes

V4_05_R3_PURE_CORE_FACTORS
26,822,192 bytes

V4_05_R3_FULL_SCOPE_FACTORS
30,265,965 bytes

V4_05_R3_FULL_MARKET_CORE_PROFILE
48,847,016 bytes
```

GitHub 当前能看到的只是 LFS pointer。

Pointer OID 与 manifest SHA 对得上。

但没有像上一轮官方 TDX 包那样证明：

```text
fresh clone
git lfs fetch
git lfs checkout
rehash restored bytes
```

因此当前只能证明开发机生成过这些 bytes，不能独立证明仓库远端可以恢复这些正式 replay 证据。

在正式 Accepted Head promotion 前必须补。

按此前同一项目标准，这一项作为 R4 promotion blocker。

**B04 = BLOCKING**

---

# 14. Independent Postcheck 深度不足

`postcheck_v4_05_r3.py`

确实独立扫描了：

- 1,299,408 daily rows；
- 694k period artifact；
- 5222 factor rows；
- 5222 profile rows；
- hash / row set / source-date / UNKNOWN propagation。

这比 R2 强很多。

但它仍主要验证：

```text
producer output internally consistent
```

没有独立数值复算：

- representative factor fields；
- market reference 1/3/5；
- market snapshot identity；
- adjustment basis identity；
- market trend；
- representative V4-04 state outputs。

所以它没有发现 B01/B02。

R4 必须增加真正独立的 sample recomputation。

建议至少：

```text
4 boards
normal ready
no-T0-bar
adjustment-unknown
short-history
code-change
high/low boundary cases
```

总样本不少于 20 个实体，且 market reference 1/3/5 全部独立复算。

这是 R4 必修，但可与 B01/B02 一次关闭。

---

# 15. 对 R3 Capability Matrix 的审计结论

R3 自报：

```text
CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS
WEEKLY_PERIOD = DEGRADED_PASS
MONTHLY_PERIOD = DEGRADED_PASS
PURE_CORE_FACTORS = DEGRADED_PASS
MARKET_REFERENCE = FULL_PASS
MARKET_REGIME = DEGRADED_PASS
CURRENT_FORWARD_STOCK_CORE = DEGRADED_PASS
HISTORICAL_AS_RECORDED = BLOCKED
```

外部审计调整为：

```text
CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS

WEEKLY_PERIOD =
BLOCKED_PENDING_PERIOD_CONTRACT_REPAIR

MONTHLY_PERIOD =
BLOCKED_PENDING_PERIOD_CONTRACT_REPAIR

PURE_CORE_FACTORS =
DEGRADED_PASS_CANDIDATE
(not promotable until dependent identity chain repaired)

MARKET_REFERENCE =
BLOCKED_INPUT_IDENTITY_DRIFT

MARKET_REGIME =
BLOCKED_INPUT_IDENTITY_AND_PATH_CONTINUATION

CURRENT_FORWARD_STOCK_CORE =
BLOCKED_PENDING_DEPENDENCY_REPAIR

HISTORICAL_AS_RECORDED_ADJUSTED_PRICE =
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

因此：

`DATA_FACTOR_REPLAY_PASS`

**本轮不得外部接受。**

---

# 16. 保留的正确设计

以下不要推倒重做：

- official Sep-28 source package；
- frozen Sep-26 GBBQ；
- T0-current-coordinate daily history；
- 251-bar lookback；
- 5222 identity set；
- 27 upstream UNKNOWN；
- prior-RPS delta bootstrap UNKNOWN；
- current rps5/rps20 cross-section；
- current relative-market return logic；
- official target calendar source；
- field-local UNKNOWN philosophy；
- Core Profile algorithm contracts；
- 413-test regression baseline；
- historical AS_RECORDED block；
- V4-08 sector block。

R4 是局部合同修复，不是重新设计 Replay A。

---

# 17. External Calendar Verification Note

本轮外部审计另行核验官方交易所公告：

- SSE 2026-09-17 中秋/国庆休市公告；
- SZSE 2026-09-17 中秋/国庆休市通知。

均确认：

```text
Sep 25–27 closed
Sep 28 resumes trading
Oct 1–7 closed
```

因此 Sep-28 / Sep-29 / Sep-30 的 target-week schedule 判断没有发现事实错误。

Calendar 本身不是本轮阻断源。

---

# 18. 最终结论

```text
V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R3
```

阻断：

```text
B01 PERIOD_ASOF_VIEW_CONTRACT_DRIFT
B02 MARKET_REFERENCE_AND_REGIME_IDENTITY_DRIFT
B03 REVISION_IDEMPOTENCY_NOT_LEDGER_EXECUTED
B04 R3_LFS_REMOTE_RECOVERY_NOT_PROVEN
```

下一阶段：

`V4_05_REPLAY_GATE_A_R4_CONTRACT_IDENTITY_REPAIR`

R4 只修这些问题，不重做已经正确的 source / adjustment / factor 主链。

R4 通过后再进行 V4-05 最终外部验收。

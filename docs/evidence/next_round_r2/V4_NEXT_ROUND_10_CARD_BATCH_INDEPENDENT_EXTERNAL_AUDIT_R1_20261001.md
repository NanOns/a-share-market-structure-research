# V4 下一轮10卡批次独立外部验收审计 R1｜2026-10-01

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计 HEAD：** `66ef2e342dd339cc9795c2d1fd774b8edec4c345`  
**前置基线：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`

## 1. 唯一总状态

```text
TEN_CARD_BATCH_EXTERNAL_ACCEPTANCE =
PARTIAL_PASS_WITH_V4_11_MAINLINE_BLOCKER

V4_11 =
BLOCKED_R2_AMR20_AMOUNT_A_SEMANTIC_CONFLATION

A02_PRIOR_RPS =
PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE
DOWNSTREAM_AMENDMENTS_NOT_ACCEPTED

A03_FORWARD_PIT =
PASS_BUILDER_SCOPE_ACCUMULATION_CONTINUES

A04_AMOUNT_A =
ENGINEERING_PASS_FORMAL_AUTHORITY_BLOCKED_R3

A05_LEGACY_VALID_MEMBER =
PASS_EXACT_CURRENT_SNAPSHOT_PRODUCER_SCOPE

A06_BAOSTOCK_TOLERANCE =
PASS_FAIL_CLOSED_NO_TOLERANCE_AUTHORIZED

A07_ADJUSTED_PRICE_LINEAGE =
PASS_LINEAGE_CAPTURE_SCOPE_WITH_PERMANENT_PRECAPTURE_BLOCK

OWNER_REGISTRY_BOOTSTRAP =
PASS_SCOPED_INACTIVE_CANDIDATE

HISTORICAL_READER_DI =
PASS_HISTORY_ONLY_DI_HARDENING

V4_DATA_ACCEPTED_HEAD = KEEP_2026_09_30
V4_STAGE_ACCEPTED_HEAD = KEEP_V4_00_TO_V4_10
V4_12 = NOT_AUTHORIZED_YET

PRODUCTION / SHADOW / FOCUS / GLOBAL_MANDATORY = FALSE
```

## 2. Batch governance｜PASS

本批未越权：Data Head 未动、Stage Head 未动、V4-12 未提前实现、Production/Shadow/Focus/Global mandatory 均 false。

最终 clean checkout：

```text
1692 passed
2 skipped
0 failures
0 errors
new_deselects = []
```

`current_v4_10_protected_gate=FAIL` 是当前 2026-09-30 movable Data Head 不等于 V4-10 历史接受时的 publication；history-only exact archive reader 已 PASS，因此不是本批新业务回归。

## 3. V4-11｜P0 语义串线，BLOCKED

V4-11 exact legacy extraction 对 LAUNCH_CONFIRM / STRONG_PULLBACK / RECOVERY_TURN / TREND_CONTINUE 的 AST、参数、输入单位和时间角色总体正确。

但 `src/v4/confirmation.py` 新增：

```text
AMOUNT_BRANCHES =
{LAUNCH_CONFIRM, RECOVERY_TURN, TREND_CONTINUE}
```

并无条件追加：

```text
AUD-AMOUNT-A-06:FORMAL_BRANCH_DISABLED
```

这是错误绑定。

旧 V3.3 实际输入是：

```text
amr20_mean_prior
unit = fraction
time_role = PRIOR_SESSION_WINDOW
```

阈值：

```text
LAUNCH        >= 1.20
RECOVERY_TURN >= 1.05
TREND_CONTINUE 0.80 <= x <= 2.50
```

最高合同明确区分：

```text
stock amount_ratio20 / AMOUNT_VOLUME_STATE_V1
```

与：

```text
sector amount_a_value / AUD-AMOUNT-A-06
```

A04 是板块 Amount A 独立审计，不是个股 `amount_ratio20` / `amr20_mean_prior`。

因此当前 V4-11 把不同字段族错误绑定，导致三个场景被人为 UNKNOWN。

外部裁决：

```text
V4_11_EXACT_AST_EXTRACTION = PASS
V4_11_EVENT_ENGINE = PASS_ENGINEERING
V4_11_PERSISTENCE = PASS_ENGINEERING
V4_11_REAL_INPUT_CAPABILITY = BLOCKED
V4_11_FORMAL_SCENARIO_GOVERNANCE = FAIL
V4_11_OVERALL = BLOCKED_R2
```

当前 2026-09-30 全市场 5224/5224 UNKNOWN 中，common-safety / episode accepted facts 缺失可以是合法 capability limitation；但 `AUD-AMOUNT-A-06` 造成的 UNKNOWN 必须删除并重新验证。

因此不得创建 V4_11_ACCEPTED_HEAD、不得推进 Stage Head、不得进入 V4-12。

## 4. V4-11 其他边界

以下方向正确并应保持：

- D0 不直接写 Final State；
- real D2 adoption 未接受前被拒绝；
- STATE_EVENT 使用 frozen prior-session state；
- same-day r1/r2/r3 不把 NEW_CONFIRMED 变 PERSISTENT；
- controlled publisher / append-only / retry / rollback；
- migration 026 由统一 allocator 分配并只在 disposable DB 验证；
- golden expected 不由 producer 自己生成；
- no-symbol 无未分类 runtime hardcode。

R2 只需定点修复，不需重写整个 V4-11。

## 5. A02 Prior-RPS｜PASS 输入生产者范围

A02 建立 2026-09-22、09-23、09-24、09-28、09-29、09-30 六个 immutable RPS publication。

边界：

```text
first computable = 2026-09-22
first delta1 = 2026-09-23
first delta3 = 2026-09-28
```

独立验证：

```text
250,680 endpoint/rank/delta values
mismatches = 0
```

Lineage：

```text
RECONSTRUCTED_CORRECTED
AS_RECORDED = false
```

因此 A02 输入生产者接受为：

```text
PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE
```

但下游变化巨大：

```text
V4-07 rows changed = 5222
old Base Seed: FALSE 2443 / UNKNOWN 2779
new Base Seed: FALSE 3755 / TRUE 976 / UNKNOWN 491

V4-09 business rows changed = 2811
```

所以 V4-05/V4-07/V4-09 amendment 不在本轮自动接受，必须版本化后再独立验收。

## 6. A03 Forward PIT｜PASS_BUILDER_SCOPE

已完成 immutable daily ledger、late/revision/gap/schema detector、duplicate guard、target date/calendar/identity guards、idempotent daily command，并有真实 current observation。

未来 observation 数不足不是工程 blocker。

外部裁决：

```text
A03_BUILDER = PASS
FORWARD_ACCUMULATION = CONTINUES_NATURALLY
HISTORICAL_AS_RECORDED_BACKFILL = PROHIBITED
```

## 7. A04 Amount A｜工程机制通过，formal authority 未闭环

A04 已完成 TDX raw amount exact source、CNY unit、20 prior sessions、common-member denominator、confirmed suspension zero、data-gap UNKNOWN、concentration、consumer inventory 与独立算术。

但当前：

```text
coverage_threshold = null
formal_amount_a = null
formal_consumer_enabled = false
```

且历史 H21 accepted PIT membership 不足。

因此：

```text
A04_ENGINEERING = PASS
A04_FORMAL_AUTHORITY = BLOCKED_R3
```

并再次强调：A04 是 `sector amount_a_value`，与 V4-11 stock `amr20_mean_prior` 无关。

## 8. A05 Legacy Valid Member｜PASS scoped

已恢复 exact producer：

```text
security_id fullmatch (SH|SZ|BJ).\d{6}
AND missing_state IS NOT NULL
AND missing_state NOT IN (FILE_MISSING, DELISTED_OR_INACTIVE)
```

真实验证：

```text
observations = 6188
legacy sectors = 541
mismatches = 0
```

接受范围：

```text
PASS_EXACT_CURRENT_SNAPSHOT_PRODUCER_SCOPE
```

不授予 historical PIT equivalence，也不自动开启 V4-08 B2 formal consumer。

## 9. A06 BaoStock tolerance｜PASS_FAIL_CLOSED

真实矩阵 matched rows = 15,634。官方资料不能证明 generation/rounding mechanism，因此候选正确保持：

```text
all tolerances = null
strict_binding_allowed = false
forbidden_empirical_percentage_tolerance = true
TDX core blocked = false
```

外部裁决：

```text
PASS_FAIL_CLOSED_NO_TOLERANCE_AUTHORIZED
```

## 10. A07 Adjusted Price Lineage｜PASS scoped

正确区分 AS_RECORDED / RECONSTRUCTED_CORRECTED / CURRENT_RECOMPUTED。

历史 pre-capture 无 first availability / revision / knowledge time / immutable capture receipt 时：

```text
PERMANENTLY_BLOCKED
```

外部裁决：

```text
PASS_LINEAGE_CAPTURE_SCOPE_WITH_PERMANENT_PRECAPTURE_BLOCK
```

不自动授予 adjusted-price consumer 权限。

## 11. Owner Registry Scoped Bootstrap｜PASS inactive scope

R4 candidate 对 OHLC、VOLUME、AMOUNT、QFQ、SECURITY_IDENTITY、SPECIAL_PHASE、SECTOR_MEMBERSHIP 逐字段建 owner，没有 bulk accept。

边界正确：

- Amount != Amount A；
- QFQ 仍由 GBBQ canonical；
- BaoStock factor supplemental only；
- Identity 保留历史 lifecycle limitation；
- membership 不用 current snapshot 回填 PIT；
- active_global_trust_root=false；
- global_mandatory_adoption=false。

接受：

```text
PASS_SCOPED_INACTIVE_CANDIDATE
```

## 12. Historical Publication Reader DI｜PASS

V2 reader 已从 module-global ROOT 切换为 per-call HistoricalBindingResolver / ProjectView / cloned validator namespace。

验证：

```text
module globals unchanged
sys.modules unchanged
wrong SHA fail
path traversal fail
3 concurrent readers exact
current Data Head remains 2026-09-30
business reacceptance=false
production=false
```

外部裁决：

```text
PASS_HISTORY_ONLY_DI_HARDENING
```

## 13. Batch最终结论

已通过/可正式化：

```text
A02 input producer
A03 builder
A05 exact producer current-snapshot scope
A06 fail-closed disposition
A07 lineage/capture
Owner scoped bootstrap candidate
Historical Reader DI
```

仍需修复：

```text
V4-11 P0 semantic conflation
A04 formal authority
```

需版本化 downstream amendment：

```text
A02 → V4-05 / V4-07 / V4-09
A05 → V4-08 B2 capability
```

因此 V4-12 本轮仍不得启动。

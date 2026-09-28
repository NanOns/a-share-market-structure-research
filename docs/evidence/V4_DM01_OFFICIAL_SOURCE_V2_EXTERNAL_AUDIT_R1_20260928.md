# 大A市场结构研究系统 V4｜DM-01 Official Daily Source v2 外部审计与 9/28 E2E 收尾任务

> 文档编号：DA-MSR-V4-DM01-OFFICIAL-SOURCE-V2-EXTERNAL-AUDIT-R1-20260928  
> 日期：2026-09-28  
> 仓库：`NanOns/a-share-market-structure-research`  
> 分支：`codex/v4-system-reform`  
> 当前 HEAD：`f158c95ea32c24e4dea609812d8f20dc9e539315`  
> 主线：V4-DM-01  
> V4-03：禁止启动  
> 历史代码变更 exhaustive completeness：DEFERRED，不占当前主线。

## 1. 外部审计结论

```text
TDX Official Daily Source            = IMPLEMENTED / PRE-LIVE
BaoStock DailyUpdates Adapter         = IMPLEMENTED / PRE-LIVE
TDX Snapshot Delta                    = IMPLEMENTED
Source Freeze V2                      = IMPLEMENTED
Daily Increment Framework             = IMPLEMENTED
Real Accepted Component Builders      = NOT WIRED
Real 2026-09-28 Source Freeze         = NOT RUN
Real 2026-09-28 Increment Build       = NOT RUN
Real Data Head Promotion              = NOT RUN

V4_DATA_ACCEPTED_HEAD                 = 2026-09-24
DM-01 Production Incremental          = BLOCKED_PENDING_REAL_WIRING_AND_E2E
```

## 2. 已确认正确的 TDX 官方源设计

正式主源已从本地 `D:/new_tdx/vipdoc` 尾部探测切换为 `https://www.tdx.com.cn/article/vipdata.html`：

```text
official page
→ _hsjdayinfo.js update date
→ exact target-date gate
→ official full package download
→ immutable content-addressed snapshot
```

本地 vipdoc 已降级为 `LOCAL_CLIENT_DIAGNOSTIC_ONLY`。方向接受。

## 3. TDX 下载安全实现基本合格

已包含：

```text
official host allowlist
HTTPS only
redirect host audit
bounded page/package size
zip path traversal guard
duplicate entry guard
entry-size limit
compression-ratio guard
total-uncompressed-size guard
CRC test
atomic temp download
SHA256
content-addressed immutable snapshot
no write to user TDX root
```

本项接受。

## 4. TDX Snapshot Delta 方向正确

`TDX_PACKAGE_DELTA_V1` 先比较 ZIP central directory，再只解析 changed/new daily entries，支持：

```text
APPEND_ONLY_TARGET_DATE
APPEND_WITH_HISTORICAL_CORRECTION
HISTORICAL_CORRECTION
NEW_ENTRY
REMOVED/TRUNCATION -> BLOCKED
```

避免每天全历史重跑。本项接受。

## 5. TDX Delta 仍需补一个严格边界

当前同长度 `.day` 文件发生 changed record 时，如果某个历史 record 的 `trade_date` 本身被改写，存在被归入 `HISTORICAL_CORRECTION` 的风险。

必须规定：

```text
historical correction
只能修改同 trade_date 的 OHLCV/Amount
```

任何 existing record date identity 改变或日期序列替换：

```text
BLOCKED_SOURCE_REVISION_ANOMALY_REWRITE
```

不得作为普通 vendor correction。

## 6. BaoStock DailyUpdates API 形态已核对

适配器使用：

```text
query_daily_history_k_AStock(date=...)
query_daily_adjust_factor(date=...)
```

并采用 date-level batch。Daily K 定位为 supplemental fingerprint/status facts；Adjustment Factor 定位为 `AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY`。TDX RAW authority 未被替代。本项接受。

## 7. BaoStock 当前有一个不应继续阻塞主线的旧治理问题

当前配置仍：

```text
baostock_production_network_enabled = false

baostock_activation_gate
= V4_00F_AUDIT_CLOSED_AND_WORKER_ENFORCES_ALL_BOUNDS
```

runner 实际传：

```text
baostock_capability_accepted = false
```

因此无论接口真实是否可用，DM-01 都会永久 `WAIT_BAOSTOCK_DAILY_UPDATE`。

这与当前用户确认的事实“BaoStock 接口可用正常”冲突。

正确处理：

```text
不要继续被旧 V4-00F 历史 gate 卡住。
```

但不能删除校验。应为 DM-01 建立独立：

```text
BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1
```

只验：

```text
installed SDK fingerprint
actual auth mode
query_daily_history_k_AStock(date)
query_daily_adjust_factor(date)
target-date response
provider date
field schema
request ledger
row bounds
immutable snapshot
```

LIVE smoke PASS 即可使 DM-01 DailyUpdates source accepted，不需要重开整个旧 00F 历史审计。

## 8. 0.9.3 / 0.9.4 pin 不应再按 auth mode 硬编码

当前代码：

```text
VIP_API_KEY -> expected 0.9.4
other auth -> expected 0.9.3
```

当前 workspace 为 0.9.4。正确做法是改成 `accepted_runtime_manifest`，绑定：

```text
package version
installed source digest
auth mode
exact supported DailyUpdates methods
live smoke receipt
```

后续升级版本必须重新 smoke + reseal，而不是写死版本号。

## 9. BaoStock Crosscheck 不能长期使用 float exact equality

当前 `close/volume/amount` 采用 float 精确相等，只能叫：

```text
RAW EXACT DIAGNOSTIC
```

不能成为正式冲突 Gate。

必须复用现有：

```text
BAOSTOCK_DAILY_FINGERPRINT_V1
field normalization
unit rules
source-specific tolerance / binding
```

在 tolerance 未冻结前，exact mismatch 只能是诊断，不能阻断 Data Head。

## 10. 当前最大 P0：真实 component builders 没有接线

`run_incremental_components(...)` 目前只是 generic orchestration shell。正式仓库尚未看到：

```text
RAW_DAILY -> accepted builder
IDENTITY_UNIVERSE -> accepted builder
TRADING_STATUS -> accepted builder
ISST -> accepted builder
ADJUSTED_DAILY -> accepted builder
PERIOD_RAW -> accepted builder
PERIOD_ADJUSTED -> accepted builder
SPECIAL_PHASE -> accepted builder
PRICE_LIMIT -> accepted builder
```

的生产映射。

测试里的 `_all_builders(...)` 全是 fake artifact builders。

因此：

```text
76 tests passed
```

只能证明框架 mechanics，不能证明 real production increment works。

## 11. run_v4_dm01_daily_increment.py 当前仍只是 readiness probe

当前只抓 TDX，然后传：

```text
baostock_capture = None
gbbq_snapshot = None
lifecycle_snapshot = None
special_phase_snapshot = None
```

因此即使 15:00 后 TDX 官网已发布 9/28 包，也不可能进入 `SOURCE_FREEZE_READY`。

## 12. run_v4_continuous_data_maintenance.py 也仍主动阻断生产

当前仍显式：

```text
baostock_capability_accepted = False
lifecycle = None
special_phase = None
component_builder_block = True
```

所以当前 production runner 在逻辑上不可能推进 9/28 Data Head。

## 13. GBBQ 9/28 可以复用当前已冻结 snapshot

已有 `V4_02_GBBQ_FORWARD_SNAPSHOT_FREEZE_20260926`：

```text
system_available_at = 2026-09-26
first_eligible_formal_trade_date = 2026-09-28
```

因此对 9/28，只要运行时未检测到新的 GBBQ source revision，该 immutable snapshot 可以作为合法 PIT_OBSERVED source。

不需要为了“每天一份”复制相同文件。正确模型应是：

```text
snapshot-by-revision
```

每天 Source Freeze 绑定当天实际有效的 latest accepted GBBQ snapshot。

## 14. GBBQ 后续维护

增加：

```text
GBBQ_SOURCE_REVISION_PROBE_V1
```

每天比较当前 gbbq/gbbq.map hash。

若相同：

```text
REUSE_ACCEPTED_GBBQ_SNAPSHOT
```

若变化：

```text
freeze new immutable revision
→ adjustment impact analysis
```

## 15. Identity/Lifecycle 不需要继续被历史换码 completeness 卡住

每日只需生成：

```text
CURRENT_LIFECYCLE_SNAPSHOT(T)
```

来源：

```text
parent accepted universe
+
target-date BaoStock/accepted roster
+
accepted dated identity facts
+
daily boundary detector
```

无 candidate：

```text
PASS_NO_IDENTITY_EVENT
```

有模糊 candidate：

```text
affected security = IDENTITY_UNKNOWN / REVIEW_REQUIRED
```

不阻断无关股票。

## 16. Special Phase 不需要每天等待新公告

当前 `special_phase = None` 导致永远 `WAIT_SPECIAL_PHASE_SNAPSHOT`，不合理。

应生成：

```text
SPECIAL_PHASE_SOURCE_MANIFEST(T)
```

绑定：

```text
accepted SPECIAL_PRICE_PHASE_EVENT_V1 store
+
listing/lifecycle facts
+
current policy revision
+
T cutoff
```

当天无新事件：

```text
NO_NEW_SPECIAL_PHASE_EVENT
```

仍是有效 manifest。

## 17. 9/28 真实 runner 必须改成完整 orchestrator

`run_v4_dm01_daily_increment --target-date 2026-09-28` 必须执行：

```text
1. official session check
2. TDX page capture
3. TDX package download if update_date=T
4. parent snapshot resolution
5. TDX package delta
6. BaoStock DailyUpdates capture
7. BaoStock runtime acceptance
8. GBBQ revision probe / bind accepted snapshot
9. lifecycle snapshot build
10. special-phase manifest build
11. Source Freeze V2
12. real component builders
13. independent postcheck
14. candidate manifest
15. atomic Data Head promotion
```

## 18. Parent TDX Snapshot 必须明确

首次 9/28：

```text
parent snapshot
= accepted 2026-09-24 official/full TDX archive
```

必须绑定 path / sha256 / cutoff / lineage，不能临时拿本地 vipdoc 当 parent。

## 19. Catch-up 多交易日需要拆 source delta 与 session view

未来如果：

```text
Data Head 停在 T0
current official package 已含 T1,T2,T3
```

不能要求分别下载历史 T1/T2/T3 包。

应设计：

```text
TDX_PACKAGE_DELTA_V1
= parent snapshot → current snapshot 的完整差异

TDX_SESSION_DELTA_VIEW_V1(T)
= 从 package delta 取某个 session 的 bar / revision impact
```

同一 current snapshot 可依次服务 T1/T2/T3，按 official session 顺序推进。

## 20. Real Accepted Builders 必须复用已有 01/02 runtime

映射至少：

```text
RAW_DAILY
→ accepted Canonical Raw builder

IDENTITY_UNIVERSE
→ accepted V4-01 identity/lifecycle + daily delta

TRADING_STATUS
→ accepted V4-02 status logic

ISST
→ accepted dated isST logic

ADJUSTED_DAILY
→ accepted adjustment runtime + GBBQ chain

PERIOD_RAW
→ accepted period builder

PERIOD_ADJUSTED
→ accepted adjusted period builder

SPECIAL_PHASE
→ accepted SPECIAL_PRICE_PHASE_EVENT_V1 consumer

PRICE_LIMIT
→ accepted generic V4-02 Price Limit runtime
```

禁止 second implementation。

## 21. 每个 builder 必须产生真实 artifact

不能只返回 `FULL_PASS`。必须包含：

```text
artifact path
artifact sha
input source revisions
parent artifact revision
row count
target date
unknown/degraded rows
elapsed time
```

## 22. Independent Postcheck 必须独立读取 staging artifacts

至少验：

```text
key-set consistency
duplicate stable-id/date
target-date cutoff
TDX source binding
BaoStock no raw substitution
status/bar relation
adjusted readiness
period cutoff
price-limit row key set
Stage/Dev Head hash unchanged
```

## 23. 9/28 收盘前当前 WAIT_MARKET_CLOSE 正确

当前 receipt：

```text
observed_at = 2026-09-28T03:50:07Z
= 11:50 Asia/Shanghai

status = WAIT_MARKET_CLOSE
```

正确。

15:00 只是允许开始检查，不代表 TDX 已发布。

## 24. 9/28 E2E 真正成功条件

必须拿到：

```text
TDX update_date = 2026-09-28
TDX full zip snapshot frozen
TDX package delta PASS

BaoStock 2026-09-28 DailyUpdates live snapshot accepted

GBBQ effective snapshot bound
Lifecycle snapshot READY
Special Phase manifest READY

Source Freeze V2 PASS

9 real component builder receipts
Independent Postcheck PASS
Data Head Promotion = PROMOTED
```

最终：

```text
V4_DATA_ACCEPTED_HEAD.accepted_trade_date
= 2026-09-28
```

同时 Stage/Dev Head hash 不变。

## 25. 本轮必须补的测试

至少：

```text
test_same_length_day_file_trade_date_rewrite_blocks

test_baostock_runtime_acceptance_uses_manifest_not_auth_hardcoded_version

test_baostock_live_dailyupdates_smoke_receipt_can_activate_dm01

test_exact_float_conflict_is_diagnostic_only_without_accepted_tolerance

test_gbbq_unchanged_revision_reuses_existing_snapshot

test_gbbq_changed_revision_freezes_new_snapshot

test_no_special_event_still_produces_valid_source_manifest

test_no_identity_event_still_produces_valid_lifecycle_snapshot

test_real_runner_invokes_all_nine_real_builders

test_fake_builder_not_allowed_in_production_runner

test_one_full_package_supports_multi_session_catchup

test_multi_session_catchup_promotes_strictly_sequentially

test_real_independent_postcheck_reads_artifacts

test_real_e2e_moves_only_data_head
```

## 26. 当前正式验收判断

```text
TDX official source implementation
= PASS_PRE_LIVE

TDX source authority / no local-vipdoc dependency
= PASS

TDX package security
= PASS

TDX delta architecture
= PASS_WITH_ONE_REWRITE_EDGE_FIX_REQUIRED

BaoStock DailyUpdates API adapter
= PASS_PRE_LIVE

BaoStock runtime activation
= BLOCKED_BY_STALE_PIN/GATE_DESIGN

BaoStock canonical authority boundary
= PASS

GBBQ go-forward 9/28 eligibility
= PASS

Lifecycle daily source
= NOT WIRED

Special Phase daily source manifest
= NOT WIRED

Real accepted 00/01/02 builders
= NOT WIRED

Real independent postcheck
= NOT WIRED

Real 9/28 E2E
= NOT RUN

DM-01 Production Incremental
= NOT PASS
```

## 27. 下一执行优先级

只做：

```text
P0-1  修 TDX date-identity rewrite edge
P0-2  建立 BaoStock DailyUpdates 独立 live runtime acceptance，去掉旧 gate/硬编码版本阻塞
P0-3  接 GBBQ current-revision probe
P0-4  接 daily lifecycle manifest
P0-5  接 daily special-phase manifest
P0-6  九个 capability 映射到真实 accepted builders
P0-7  接独立 artifact postcheck
P0-8  15:00后执行 2026-09-28 real E2E
```

禁止继续深挖历史换码 completeness、启动 V4-03、提前做 V4-04+。

## 28. 最终原则

```text
现在离“每天自动更新”已经不是设计问题，
而是生产接线问题。

源层基本完成；
真正剩下的是把已验收的 00/01/02 runtime
接到官方 TDX + BaoStock DailyUpdates 的 Source Freeze 后面。

9/28 首次真实 E2E 才是 DM-01 的正式验收点。
```

**文档结束**

# 大A市场结构研究系统 V4｜DM-01 9/28 收盘后继续验收 R2

> 文档编号：DA-MSR-V4-DM01-POSTCLOSE-EXTERNAL-AUDIT-R2-20260928  
> 日期：2026-09-28  
> 仓库：`NanOns/a-share-market-structure-research`  
> 分支：`codex/v4-system-reform`  
> 当前 HEAD：`644242dba8b29ebb2da42ee601cef95fd71b4190`  
> 上一审计基线：`f158c95ea32c24e4dea609812d8f20dc9e539315`  
> 主线：V4-DM-01  
> V4-03：继续禁止启动。

---

# 1. 外部验收结论

当前不能判：

```text
DM-01 Production Incremental = PASS
```

正式状态：

```text
TDX Official Source Capture        = PASS_PRE_LIVE
TDX Snapshot Delta                 = PASS
TDX Multi-Session Catch-up View    = PASS
BaoStock Runtime Acceptance Design = PASS_PRE_LIVE
GBBQ Revision Probe                = IMPLEMENTED
Lifecycle Daily Manifest           = IMPLEMENTED
Special Phase Daily Manifest       = IMPLEMENTED
Independent Postcheck              = IMPLEMENTED / MECHANICS_TESTED

Real Accepted 9-Component Builders = NOT WIRED
Real 2026-09-28 Source Freeze      = NOT READY
Real 2026-09-28 Increment Build    = NOT RUN
Real Data Head Promotion           = NOT RUN

V4_DATA_ACCEPTED_HEAD              = 2026-09-24
DM-01 Production Incremental       = BLOCKED
```

---

# 2. 最新仓库提交

当前 HEAD：

```text
644242dba8b29ebb2da42ee601cef95fd71b4190
```

相比上一审计：

```text
f158c95ea32c24e4dea609812d8f20dc9e539315
```

新增两笔提交：

```text
e29002b  Wire DM-01 official source audit gates
644242d  Record DM-01 post-close source gate
```

---

# 3. 9/28 收盘后真实 TDX Gate

仓库在：

```text
2026-09-28 15:00:29 Asia/Shanghai
```

执行了真实官方源检查。

结果：

```text
TDX official update_date = 2026-09-25
target_date              = 2026-09-28

status = WAIT_TDX_PUBLICATION
```

因此：

```text
9/28 包没有下载
BaoStock 没有继续调用
Source Freeze 没有生成
Component Builders 没运行
Data Head 没移动
```

这是正确行为。

不能因为已经 15:00：

```text
直接假定 9/28 包已发布。
```

必须等：

```text
TDX official update_date == 2026-09-28
```

---

# 4. TDX 历史 date-identity rewrite 边界已修

上一轮要求：

```text
历史 record 的 trade_date 被改写
不能算普通 HISTORICAL_CORRECTION
```

当前代码已增加：

```python
if old_records[index]["trade_date"]
   != new_records[index]["trade_date"]:
    raise SOURCE_REVISION_ANOMALY_REWRITE
```

因此：

```text
同日期 OHLCV 修订
→ HISTORICAL_CORRECTION

日期身份改写
→ SOURCE_REVISION_ANOMALY_REWRITE / BLOCKED
```

此项通过。

---

# 5. 多交易日 Catch-up 架构已补

当前新增：

```text
TDX_SESSION_DELTA_VIEW_V1
```

正式支持：

```text
parent snapshot
vs
current official full snapshot
↓
TDX_PACKAGE_DELTA_V1
↓
T1 session view
T2 session view
T3 session view
```

即一份最新完整包可以服务多个遗漏交易日，不需要为每个遗漏日寻找旧版官网完整包。

该架构方向通过。

---

# 6. BaoStock Runtime Acceptance 已从旧 gate 解耦

当前新增：

```text
BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1
```

绑定：

```text
package
version
installed_python_sources_sha256
auth_mode
supported_methods
live exact-date smoke
smoke receipt hash
```

DM-01 已不再要求整个旧 V4-00F 先关闭。

这是正确修复。

---

# 7. 但 BaoStock 仍未完成 9/28 live acceptance

截至当前 post-close receipt：

```text
baostock_runtime_smoke_or_capture_called = false
```

原因不是 BaoStock 自身失败，而是：

```text
TDX source gate 尚未 ready
```

runner 正确地没有继续向下执行。

因此当前只能说：

```text
BaoStock DailyUpdates runtime acceptance
= IMPLEMENTED / NOT YET LIVE-ACCEPTED FOR 2026-09-28
```

不能提前 PASS。

---

# 8. GBBQ Revision Probe 已实现，但当前本地 current source 不可用

真实 post-close receipt：

```text
status = WAIT_GBBQ_CURRENT_SOURCE_UNAVAILABLE
missing_source_files:
  - gbbq
  - gbbq.map
```

这说明代码没有虚假声称：

```text
当前本地 GBBQ 与 accepted snapshot 相同。
```

行为正确。

但是需要解决：

```text
daily runner 应该从哪里读取“current GBBQ source”
```

当前 accepted snapshot 本身：

```text
first_eligible_formal_trade_date = 2026-09-28
```

所以如果当天没有可访问的 current source revision，应明确：

```text
是否允许直接复用 accepted 2026-09-26 snapshot
```

还是：

```text
必须取得 current-source equivalence proof
```

这个权限必须在 DM-01 合同里冻结，不能由 runner 临时猜。

---

# 9. Lifecycle Daily Manifest 已实现

当前代码已经做到：

```text
parent accepted universe
+
target-date BaoStock roster
+
accepted identity records
+
daily identity detector
```

生成：

```text
CURRENT_LIFECYCLE_SNAPSHOT_V1
```

并正确坚持：

```text
BaoStock roster absence
!= delisting evidence
```

新/无法映射 source key：

```text
IDENTITY_UNKNOWN_REVIEW_REQUIRED
```

仅影响相关证券，不静默合并 identity。

此项方向通过。

---

# 10. Special Phase Daily Manifest 已实现

当前：

```text
SPECIAL_PHASE_SOURCE_MANIFEST_V1
```

复用：

```text
accepted V4-02 event store
accepted V4-02 policy
current lifecycle snapshot
```

当天没有新特殊事件：

```text
NO_NEW_SPECIAL_PHASE_EVENT
```

仍然是有效 manifest。

这修掉了上一轮：

```text
special_phase = None
→ 永远 WAIT
```

的问题。

此项通过。

---

# 11. Independent Postcheck 已实现，但还没经过真实 artifacts

新增：

```text
daily_increment_postcheck.py
```

已经具备真实 artifact 读取与检查逻辑，包括：

```text
source binding
key uniqueness
status/bar relation
target-date cutoff
TDX authority
BaoStock no raw substitution
Stage Head immutable
Dev Head immutable
```

测试还专门验证：

```text
fake artifact builders
不能通过 real independent postcheck
```

这一点很好。

但是：

```text
真实 9-component artifacts 还没生成
```

所以目前只能：

```text
POSTCHECK IMPLEMENTED / MECHANICS_TESTED
```

不能：

```text
REAL E2E POSTCHECK PASS
```

---

# 12. 当前最大 P0 仍未解决：真实 builders 没接线

仓库搜索不到正式：

```text
RAW_DAILY builder registry
IDENTITY_UNIVERSE builder registry
TRADING_STATUS builder registry
ISST builder registry
ADJUSTED_DAILY builder registry
PERIOD_RAW builder registry
PERIOD_ADJUSTED builder registry
PRICE_LIMIT builder registry
SPECIAL_PHASE builder registry
```

生产 runner 当前仍明确写：

```text
component_builder_block = True

incremental_component_builders
= NOT_WIRED_FAIL_CLOSED
```

因此：

```text
即使今晚 TDX + BaoStock + GBBQ
全部 source-ready，
当前 runner 仍会在 build 前主动阻断。
```

这是当前唯一真正的核心工程 blocker。

---

# 13. 76 / 89 tests 不能替代这个 blocker

当前测试数量增加到：

```text
89 passed
0 failed
```

这是好事。

但测试中 generic promotion 仍使用：

```text
_all_builders(...)
```

生成 fake artifacts。

虽然 real postcheck 已经能拒绝 fake artifact，但尚未证明：

```text
9 个 accepted V4-01/V4-02 runtime
已经能被 DM-01 production runner 调用。
```

所以：

```text
tests PASS
!=
production builders wired
```

---

# 14. Head 状态正确，没有提前污染

当前：

```text
V4_DATA_ACCEPTED_HEAD
accepted_trade_date = 2026-09-24
```

Stage Head：

```text
unchanged
```

Dev Baseline：

```text
accepted_data_cutoff = 2026-09-24
unchanged
```

说明这次 pre-live/post-close gate 没有提前写正式数据。

此项通过。

---

# 15. Stage Head 仍绑定旧 R8.1，属于治理债但不应卡当前 DM 主线

当前：

```text
V4_STAGE_ACCEPTED_HEAD
```

仍绑定：

```text
v4_01_final_stage_receipt_R8_1
```

而不是后续 R8.2/R8.3。

考虑用户已决定：

```text
历史换码 completeness 暂缓
不再占主线
```

当前不要求为了 DM-01 reopen 此处。

但必须记录为：

```text
KNOWN_STAGE_HEAD_GOVERNANCE_DEBT
```

未来正式 PRE-03 最终封口时统一处理。

不得在 DM-01 中偷偷修改 Stage Head。

---

# 16. 现在真正应该做的下一步

不再扩设计，不再深挖 identity。

只做：

```text
P0-1
实现 REAL_ACCEPTED_INCREMENTAL_BUILDER_REGISTRY_V1
```

把 9 个 capability 显式绑定到已有 accepted runtime。

---

# 17. Builder Registry 必须是显式、版本化的

建议：

```text
V4_DM01_ACCEPTED_BUILDER_REGISTRY_V1
```

字段至少：

```text
capability
builder callable/module
owner stage
accepted source receipt
accepted algorithm contract
incremental input contract
output contract
version
```

禁止：

```text
动态发现任意函数
fake builder
test builder
fallback builder
```

进入 production registry。

---

# 18. 九个真实映射

至少：

```text
RAW_DAILY
→ accepted TDX Canonical Raw runtime

IDENTITY_UNIVERSE
→ accepted identity/universe runtime + CURRENT_LIFECYCLE_SNAPSHOT_V1

TRADING_STATUS
→ accepted trading-status runtime

ISST
→ accepted dated isST runtime

ADJUSTED_DAILY
→ accepted GBBQ/QFQ runtime

PERIOD_RAW
→ accepted raw period aggregator

PERIOD_ADJUSTED
→ accepted adjusted period aggregator

SPECIAL_PHASE
→ accepted SpecialPhaseEventStore / policy runtime

PRICE_LIMIT
→ accepted generic V4-02 Price Limit runtime
```

---

# 19. 不允许为了“增量”写九套简化算法

DM-01 只能新增：

```text
scope selection
parent revision resolution
staging
receipt
atomic publication
```

算法本身必须来自：

```text
accepted V4-01/V4-02 runtime
```

否则等于重新实现 01/02。

---

# 20. GBBQ 权限需要定死

建议当前 DM-01 明确：

如果：

```text
accepted go-forward snapshot
first_eligible_formal_trade_date <= T
```

且：

```text
没有证据证明 source 已产生新 revision
```

是否允许：

```text
REUSE_ACCEPTED_GBBQ_SNAPSHOT_WITHOUT_CURRENT_SOURCE_PROBE
```

当前仓库选择的是：

```text
必须取得 current source equivalence
否则 WAIT_GBBQ_CURRENT_SOURCE_UNAVAILABLE
```

这是更保守的策略。

如果保持最高标准，可以继续维持：

```text
current source unavailable
→ WAIT
```

但必须确保实际生产机能取得 gbbq/gbbq.map 当前源，否则 Daily Lane 会永久卡住。

---

# 21. 9/28 再次运行时的正确预期

TDX 页面当前仓库证据显示：

```text
15:00:29
update_date = 2026-09-25
```

官网页面明确说明包含当日的数据应等更新日期变为当日后再下载。

因此下一次运行：

如果仍：

```text
update_date = 2026-09-25
```

继续：

```text
WAIT_TDX_PUBLICATION
```

如果变成：

```text
update_date = 2026-09-28
```

才进入：

```text
download
→ delta
→ BaoStock live smoke
→ BaoStock capture
→ GBBQ
→ lifecycle
→ special phase
→ source freeze
→ real builders
→ postcheck
→ promotion
```

---

# 22. 最终 FULL_PASS 标准保持不变

只有真实看到：

```text
TDX official package = 2026-09-28
BaoStock exact-date snapshot accepted
GBBQ source gate PASS
Lifecycle snapshot PASS/accepted degraded
Special Phase manifest PASS

Source Freeze V2 = PASS

9 real builder receipts
Independent Postcheck = PASS

V4_DATA_ACCEPTED_HEAD
2026-09-24 → 2026-09-28

V4_STAGE_ACCEPTED_HEAD unchanged
V4_DEV_BASELINE_HEAD unchanged
```

才能：

```text
DM-01 Production Incremental = FULL_PASS
```

---

# 23. 本轮最终判断

```text
Previous source-layer design problems
= MOSTLY CLOSED

TDX date rewrite edge
= CLOSED

Multi-session catch-up architecture
= CLOSED

BaoStock runtime manifest design
= CLOSED_PRE_LIVE

Lifecycle daily manifest
= CLOSED_PRE_LIVE

Special Phase daily manifest
= CLOSED_PRE_LIVE

Independent artifact postcheck
= CLOSED_PRE_LIVE

TDX 9/28 publication
= WAITING_FOR_OFFICIAL_SOURCE

GBBQ current-source proof
= WAITING_FOR_SOURCE

Real accepted builder registry
= OPEN P0

Real 9/28 E2E
= NOT RUN

DM-01
= NOT PASS
```

---

# 24. 一句话结论

```text
这次更新已经把“官方源怎么来、怎么冻结、怎么发现修订、
怎么处理多日catch-up、怎么做生命周期和特殊阶段manifest、
怎么独立postcheck”基本补齐。

现在剩下的最大问题非常集中：
9个 accepted 00/01/02 component builders
还没有真正接进 production runner。

在它们接通前，
即使 TDX 今晚发布9/28包，
系统也只能做到 Source Freeze，
不能合法推进 Data Head。

下一步只做真实 builder registry + wiring，
然后等官方 TDX 9/28 包发布后跑真实 E2E。
```

**文档结束**

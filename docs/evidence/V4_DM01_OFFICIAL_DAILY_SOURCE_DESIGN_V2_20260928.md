# 大A市场结构研究系统 V4｜DM-01 每日盘后增量数据维护正式设计 v2

> 文档编号：DA-MSR-V4-DM01-OFFICIAL-DAILY-SOURCE-DESIGN-V2-20260928  
> 日期：2026-09-28  
> 当前主线：V4-DM-01 / Daily Incremental Data Maintenance  
> V4-03：禁止启动  
> 历史代码变更 exhaustive completeness：暂缓，不占当前主线  
> Required Scope：SH_MAIN / SZ_MAIN / CHINEXT / STAR  
> Optional Scope：BSE 独立 degraded

---

# 0. 本版纠正

此前 DM-01 把：

```text
D:/new_tdx/vipdoc/.../*.day
```

理解成“每天会由通达信客户端自行更新”的实时 source readiness。

这与用户实际工作方式不一致。

正式改为：

```text
TDX 官方个人行情数据页
https://www.tdx.com.cn/article/vipdata.html
↓
盘后检测官网更新日期
↓
下载当日日线完整包
↓
保存为新的 immutable source snapshot
↓
从新旧 snapshot 之间只抽取增量/修订
```

通达信官方页面说明：

```text
适用于个人版PC端盘后数据下载
包含沪深京日线完整包
如需包含当日，等待网页“更新日期”变为当日后再下载
```

因此：

```text
TDX官网完整包
= 每日 Canonical Raw 主源 snapshot
```

而不是：

```text
监控客户端本地 vipdoc 是否自己更新
```

---

# 1. BaoStock 正式定位

BaoStock 官方 DailyUpdates 能力：

```text
按指定日期获取 A股 / ETF 日K
按指定日期获取复权因子
```

DM-01 正式使用：

```text
BaoStock DailyUpdates
= 每日增量补充 + cross-check + 状态事实源
```

继续遵守既有合同：

```text
TDX OHLCV/Amount
= Canonical authority

BaoStock OHLCV/Amount
= supplemental fingerprint / cross-check

BaoStock tradestatus/isST
= dated supplemental status facts

BaoStock adjustment factor
= freeze + audit evidence
!= 自动取代 TDX accepted QFQ chain
```

---

# 2. 正式双源架构

每日盘后：

```text
                ┌──────────────────────┐
                │ Official Session T   │
                └──────────┬───────────┘
                           ↓
           ┌───────────────┴───────────────┐
           ↓                               ↓
┌─────────────────────┐          ┌─────────────────────┐
│ TDX vipdata official│          │ BaoStock DailyUpdates│
│ full daily package  │          │ date-level increment │
└──────────┬──────────┘          └──────────┬──────────┘
           ↓                               ↓
 TDX immutable snapshot            BaoStock immutable snapshot
           ↓                               ↓
 TDX delta / revision set          status/factor/fingerprint facts
           └───────────────┬───────────────┘
                           ↓
                   Source Freeze T
                           ↓
                 00/01/02 Increment
                           ↓
                Independent Postcheck
                           ↓
              V4_DATA_ACCEPTED_HEAD
```

---

# 3. Source Authority Matrix

| Capability | Primary Authority | Secondary / Audit | Fallback |
|---|---|---|---|
| Raw OHLC | TDX official daily full-package snapshot | BaoStock daily K | NONE |
| Volume | TDX | BaoStock fingerprint | NONE |
| Amount | TDX | BaoStock fingerprint | NONE |
| Security identity | accepted security master / dated lifecycle | BaoStock roster + official event facts | UNKNOWN |
| Trading status | accepted TDX/calendar/status rules | BaoStock tradestatus | UNKNOWN |
| isST | accepted dated identity/isST chain | BaoStock isST | UNKNOWN |
| Adjustment/QFQ | accepted TDX/GBBQ adjustment chain | BaoStock daily adjustment factor for audit | NONE |
| Weekly/Monthly | derived from accepted Canonical Daily | — | NONE |
| Price Limit | accepted V4-02 generic runtime | — | UNKNOWN |
| Turnover | V4-06 only | BaoStock later | NOT IN DM-01 |

---

# 4. TDX_SOURCE_ACQUISITION_V2

新增正式组件：

```text
TDX_OFFICIAL_DAILY_PACKAGE_SOURCE_V1
```

职责：

```text
访问 vipdata.html
读取页面当前“更新日期”
解析当前完整包下载入口
冻结页面 HTML / metadata
下载完整 zip
校验 zip
保存 immutable source snapshot
```

---

# 5. 不允许硬编码“每天16:00一定有数据”

正式 readiness 不能：

```text
now > 16:00
→ assume TDX ready
```

必须：

```text
official_session = T
AND vipdata_page.update_date == T
AND download succeeds
AND zip validates
```

才：

```text
TDX_PACKAGE_READY(T)
```

否则：

```text
WAIT_TDX_PUBLICATION
```

---

# 6. TDX 页面自身也属于证据

每次检测到：

```text
update_date = T
```

必须保存：

```text
page_url
page_capture/html or normalized metadata
observed_at
update_date
resolved_download_url
HTTP response metadata
page sha256
```

下载包必须保存：

```text
final_url
downloaded_at
bytes
sha256
content disposition
zip entry count
zip integrity result
```

这样未来可证明：

```text
当日系统什么时候看见了哪一版官方 TDX 包。
```

---

# 7. TDX 包禁止直接覆盖用户通达信目录

官网说明个人使用可以解压覆盖 vipdoc。

但本研究系统正式运行禁止：

```text
download
→ unzip into D:/new_tdx/vipdoc
```

研究系统必须：

```text
download
→ data/v4/source_snapshots/tdx/YYYYMMDD/<snapshot_id>/
```

只读解析。

原因：

```text
不污染用户客户端
可审计
可回滚
可重放
可保留 source revision
```

---

# 8. TDX 完整包是 Full Snapshot，系统只做 Incremental Consume

源本身每天下载：

```text
完整包
```

但 Canonical pipeline 不做：

```text
每天重新构建全部历史。
```

而是：

```text
TDX_FULL_SNAPSHOT(T)
vs
TDX_ACCEPTED_SNAPSHOT(parent)
↓
TDX_PACKAGE_DELTA_V1
```

---

# 9. TDX_PACKAGE_DELTA_V1

先利用 zip central directory：

```text
entry path
CRC
uncompressed size
compressed size
```

和上一 accepted package 对比。

分类：

```text
UNCHANGED_ENTRY
CHANGED_ENTRY
NEW_ENTRY
REMOVED_ENTRY
```

只对：

```text
CHANGED / NEW / REMOVED
```

进一步解压、hash、解析。

避免每天对所有历史 `.day` 全量重复解析。

---

# 10. Changed .day 不能默认等于“只追加今天”

对于 changed entry：

```text
old .day
vs
new .day
```

必须区分：

```text
APPEND_ONLY_TARGET_DATE

HISTORICAL_CORRECTION

TRUNCATION_OR_REWRITE

INVALID_FILE
```

---

# 11. APPEND_ONLY_TARGET_DATE

正常盘后：

```text
old records
+
T one new row
```

生成：

```text
TDX_DAILY_INCREMENT(T)
```

只进入 T 日 Raw Canonical 构建。

---

# 12. HISTORICAL_CORRECTION

如果新官网完整包修改：

```text
T 之前的历史 bar
```

不得静默覆盖旧 canonical。

生成：

```text
TDX_HISTORICAL_SOURCE_REVISION_EVENT
```

保存：

```text
security key
affected dates
old values/hash
new values/hash
source snapshot old/new
reason = VENDOR_SOURCE_REVISION
```

再走：

```text
affected-scope recalculation
```

禁止：

```text
直接 overwrite old Raw fact
```

---

# 13. REMOVED / TRUNCATED Entry

如果新包出现：

```text
历史记录减少
文件截断
entry 消失
```

必须：

```text
SOURCE_REVISION_ANOMALY
```

默认 BLOCKED，不得自动删除 canonical history。

---

# 14. TDX Session Readiness 新定义

删除此前：

```text
latest local .day tail date
```

作为主 readiness。

正式：

```text
TDX_SESSION_READINESS_V2
```

只认：

```text
vipdata page update date == T
official zip downloaded
zip integrity PASS
required market directories/entries present
target-date delta parsed
```

---

# 15. 包发布成功后仍要做 coverage QA

因为：

```text
完整包 ready
```

不等于：

```text
每个 active stock 一定有 bar。
```

停牌本来就可能没有当日 bar。

对 Required Scope：

```text
Universe(T)
↓
TDX target-date bars
+
BaoStock tradestatus
+
lifecycle
```

分类：

```text
ACTUAL_TRADED
LEGITIMATE_SUSPENSION
IDENTITY/LIFECYCLE_NOT_ACTIVE
SOURCE_MISSING_UNKNOWN
```

只有最后一个是真正数据缺口。

---

# 16. BaoStock DailyUpdates 正式适配层

新增：

```text
BAOSTOCK_DAILY_UPDATE_SOURCE_V1
```

实现前必须从：

```text
当前安装 BaoStock SDK
+
官方 DailyUpdates 文档
```

确认：

```text
精确 API/function 名称
参数
返回字段
分页
日期语义
复权因子接口
错误码
更新时间/可用时间
```

禁止根据印象发明 API 名称。

---

# 17. BaoStock 日级调用目标

对于目标交易日 T，优先使用官方“按日期每日更新”的批量能力：

```text
DAILY_K(T)
ADJUSTMENT_FACTOR(T)
```

另结合现有已验证接口：

```text
query_all_stock(T)
query_trade_dates(...)
```

生成 T 的：

```text
security set
daily row
tradestatus
isST
adjustment-factor fact
```

如果 DailyUpdates API 已直接返回这些字段，则优先一次性获取，避免 security × date 逐只查询。

---

# 18. 现有 query_history_k_data_plus 不作为首选 daily fetch

仓库已有：

```text
query_history_k_data_plus(...)
```

适合历史/定点补充。

DM-01 每日更新应优先：

```text
官方 DailyUpdates 日期级接口
```

原因：

```text
更符合每日增量语义
减少请求次数
更容易 freeze 当日 provider revision
```

只有官方 DailyUpdates 无法提供某个必要字段时，才调用现有已验收 supplemental API 补字段。

---

# 19. BaoStock raw snapshot 必须冻结

每个 T 保存：

```text
provider api version
SDK version
query operation
request params
provider date
response rows
response digest
observed_at
received_at
source revision id
```

文件例如：

```text
data/v4/source_snapshots/baostock/YYYYMMDD/<snapshot_id>/
```

---

# 20. BaoStock OHLC 不得填 TDX 缺口

即使 BaoStock：

```text
DAILY_K(T)
```

已 ready，

如果 TDX 官网完整包：

```text
还没有 update_date=T
```

则：

```text
RAW_DAILY(T)
= NOT_READY
```

禁止：

```text
BaoStock OHLC
→ Canonical Raw substitute
```

---

# 21. BaoStock Daily K 的主要作用

对 TDX actual rows 做：

```text
identity/date exact match
close fingerprint
volume fingerprint
amount fingerprint
```

发现冲突：

```text
TDX remains authority

emit:
TDX_BAOSTOCK_DAILY_CONFLICT_RECEIPT
```

不能自动改 TDX。

---

# 22. BaoStock tradestatus/isST

正式用于：

```text
无 TDX bar 的证券
```

区分：

```text
provider tradestatus=0
→ suspension supporting evidence

provider tradestatus=1
但 TDX 无 bar
→ SOURCE_MISSING / conflict
```

仍遵守：

```text
BaoStock missing
!= suspension
```

---

# 23. BaoStock Adjustment Factor

DailyUpdates 的指定日期复权因子必须保存。

但当前角色：

```text
ADJUSTMENT_FACTOR_AUDIT_FACT
```

不是：

```text
QFQ_CANONICAL_AUTHORITY
```

用途：

```text
检测公司行为变化
辅助触发 adjustment-impact review
与 TDX/GBBQ chain cross-check
未来 source comparison
```

禁止：

```text
BaoStock factor
→ 自动生成 Canonical QFQ
```

除非以后修改并重新验收 V4-02 adjustment contract。

---

# 24. GBBQ 仍然是独立 source family

TDX vipdata 官方页面说明的是：

```text
日线完整包
```

不能假定：

```text
其中自动包含并更新 GBBQ corporate-action source。
```

因此保留：

```text
GBBQ_DAILY_SNAPSHOT_V1
```

来源按照现有 V4-02 go-forward contract 执行。

在 Adjusted build 前冻结：

```text
gbbq
gbbq.map
hash
observed_at
system_available_at
```

---

# 25. 每日 Source Readiness State Machine

目标 T：

```text
WAIT_MARKET_CLOSE
↓
WAIT_TDX_PAGE_UPDATE
↓
TDX_PACKAGE_DOWNLOADED
↓
TDX_PACKAGE_VALIDATED
↓
WAIT_BAOSTOCK_DAILY_UPDATE
↓
BAOSTOCK_DAILY_SNAPSHOT_READY
↓
WAIT_GBBQ_SNAPSHOT_IF_REQUIRED
↓
SOURCE_FREEZE_READY
↓
BUILD
```

---

# 26. TDX 和 BaoStock 不要求同一时刻发布

例如：

```text
TDX 16:10 ready
BaoStock 17:00 ready
```

可以：

```text
先冻结 TDX snapshot
```

但不 promote Data Head。

等 Required Source Set 全部 ready 后：

```text
freeze composite source manifest
→ build
```

---

# 27. 日常运行建议：轮询而不是固定一次

盘后从：

```text
15:00 Asia/Shanghai
```

开始允许检查。

建议 configurable：

```text
poll interval = 10~30 min
stop deadline = 23:30
```

但：

```text
发布时间不是合同事实
```

真正触发条件永远是：

```text
TDX page update_date == T
BaoStock T data available
```

---

# 28. TDX 下载避免重复

同一天如果官网：

```text
update_date=T
```

且：

```text
download URL / ETag / Last-Modified / bytes / sha
```

与已冻结 snapshot 完全一致：

```text
NOOP_SOURCE_ALREADY_FROZEN
```

如果同日官方重新发布不同包：

```text
new SHA
→ TDX_SOURCE_REVISION(T, revision+1)
```

不得覆盖 revision 1。

---

# 29. BaoStock 同日重新发布

同理：

```text
same query identity + same digest
→ NOOP

different digest
→ APPEND PROVIDER REVISION
```

然后判断：

```text
是否影响 status/factor/cross-check
```

---

# 30. 正式 Daily Source Freeze

每个 T：

```text
V4_DAILY_SOURCE_FREEZE_V2
```

至少绑定：

```text
TDX_PAGE_CAPTURE
TDX_FULL_PACKAGE
TDX_PACKAGE_DELTA
OFFICIAL_CALENDAR
BAOSTOCK_DAILY_UPDATE
BAOSTOCK_ADJUSTMENT_FACTOR
GBBQ
IDENTITY_LIFECYCLE
SPECIAL_PRICE_PHASE
```

---

# 31. Canonical 增量构建

Source Freeze 完成后：

```text
TDX Target-Date Delta
↓
RAW_DAILY(T)
↓
Universe / Identity(T)
↓
Trading Status(T)
↓
isST(T)
↓
Adjusted(T + affected history only)
↓
Weekly/Monthly affected periods
↓
Special Phase(T)
↓
Price Limit(T)
↓
Postcheck
↓
Data Head promotion
```

---

# 32. Historical Correction Impact Propagation

TDX 完整包每天都可能带 provider 修订。

如果发现 T 之前：

```text
Raw correction
```

必须生成：

```text
RAW_REVISION_IMPACT_SET
```

再决定受影响：

```text
Adjusted
Weekly/Monthly
later previous-close chain
Price Limit
future Factors（以后03接入后）
```

DM-01 当前只处理 00/01/02 范围。

---

# 33. 9/28 首次 E2E 正确流程

今天 2026-09-28 收盘后：

```text
1. 检测 vipdata.html
2. 如果 update_date != 2026-09-28
   → WAIT_TDX_PAGE_UPDATE

3. update_date == 2026-09-28
   → 下载新完整包
   → archive + hash + validate

4. 对比 parent TDX snapshot
   → target-date delta
   → historical corrections

5. 调 BaoStock DailyUpdates(2026-09-28)
   → daily K
   → adjustment factor
   → status/isST related facts

6. freeze GBBQ/source facts

7. Composite Source Freeze

8. Build 9/28 increment

9. Independent postcheck

10. Promote:
    V4_DATA_ACCEPTED_HEAD
    2026-09-24 → 2026-09-28
```

---

# 34. 如果 TDX 当晚迟迟未更新

正确：

```text
WAIT_TDX_PUBLICATION
```

不是：

```text
SOURCE_ERROR
```

也不是：

```text
用 BaoStock 顶替。
```

次日再次检查官网。

---

# 35. 如果 BaoStock 暂未更新

TDX 可以先 freeze。

但需要 BaoStock 的 Required Supplemental Facts 尚未 ready 时：

```text
WAIT_BAOSTOCK_DAILY_UPDATE
```

不 promote atomic Data Head。

如果未来我们决定：

```text
BaoStock只是optional cross-check
```

需要单独修改 capability permission contract，不在本任务擅自降低要求。

---

# 36. 如果两源冲突

例如：

```text
TDX bar exists
BaoStock tradestatus=0
```

或者：

```text
TDX close != BaoStock close
```

正式：

```text
TDX canonical remains
+
CONFLICT_RECEIPT
+
evaluate whether dependent status capability becomes UNKNOWN
```

不能：

```text
多数投票
```

也不能：

```text
BaoStock覆盖TDX。
```

---

# 37. 下载安全

TDX downloader 必须：

```text
bounded URL host allowlist
https only
redirect final host audit
download size upper bound
zip bomb protection
entry path traversal protection
CRC validation
sha256
temporary file + atomic rename
```

禁止：

```text
直接解压进项目根
直接覆盖 vipdoc
```

---

# 38. BaoStock 请求治理

复用：

```text
existing request ledger
soft/hard limits
runtime pin
login validation
```

DailyUpdates 应尽量：

```text
date-level batch
```

避免：

```text
5000 stocks × individual daily query
```

---

# 39. 新组件建议

```text
src/workbench_analysis/
tdx_official_daily_source.py
baostock_daily_update_source.py
daily_source_orchestrator.py
tdx_snapshot_delta.py
daily_increment_builder.py
```

scripts：

```text
capture_tdx_official_daily_package.py
capture_baostock_daily_update.py
run_v4_dm01_daily_increment.py
independent_v4_dm01_real_e2e_postcheck.py
```

---

# 40. 当前旧代码需要废弃/改写的假设

删除：

```text
discover_local_tdx_coverage()
作为 primary source readiness
```

可以保留它作为：

```text
LOCAL_CLIENT_DIAGNOSTIC_ONLY
```

但不能决定 Data Head 是否 ready。

删除：

```text
TDX_ROOT = D:/new_tdx
作为每日增量输入主源
```

改为：

```text
project immutable TDX source snapshots
```

---

# 41. Stage/Dev/Data Head 继续保持

不改变：

```text
V4_STAGE_ACCEPTED_HEAD
V4_DEV_BASELINE_HEAD
V4_DATA_ACCEPTED_HEAD
```

Daily Source 改造只允许：

```text
最终移动 Data Head
```

---

# 42. 关键测试：TDX 官网源

至少：

```text
test_tdx_page_update_date_before_target_waits
test_tdx_page_update_date_target_enables_download
test_tdx_download_url_is_discovered_not_hardcoded
test_tdx_package_sha_is_frozen
test_same_package_is_noop
test_same_day_republished_package_creates_revision
test_zip_crc_failure_blocks
test_zip_path_traversal_blocks
test_new_package_append_only_delta
test_historical_correction_is_detected
test_truncation_blocks
test_package_never_writes_client_vipdoc
```

---

# 43. 关键测试：BaoStock DailyUpdates

至少：

```text
test_dailyupdates_exact_trade_date
test_dailyupdates_provider_date_matches_target
test_dailyupdates_batch_semantics
test_dailyupdates_adjustment_factor_frozen
test_baostock_ohlc_never_substitutes_tdx
test_baostock_tradestatus_crosscheck
test_baostock_isst_crosscheck
test_baostock_revision_append_only
test_baostock_not_ready_waits
test_request_budget_enforced
```

---

# 44. 集成测试

至少：

```text
test_tdx_ready_baostock_not_ready_does_not_promote
test_baostock_ready_tdx_not_ready_does_not_promote
test_both_ready_builds_target_session
test_tdx_baostock_price_conflict_keeps_tdx_authority
test_suspended_stock_without_tdx_bar_is_valid_with_status_evidence
test_missing_trading_stock_tdx_bar_is_source_gap
test_source_revision_rebuilds_affected_scope_only
test_stage_and_dev_heads_never_move
test_atomic_failure_keeps_old_data_head
```

---

# 45. 首次真实 E2E 验收材料

9/28 实盘增量必须输出：

```text
tdx_page_capture_receipt
tdx_package_download_receipt
tdx_package_delta_receipt

baostock_daily_update_receipt
baostock_adjustment_factor_receipt

gbbq_snapshot_receipt

source_freeze_v2_receipt

raw_increment_receipt
identity_universe_increment_receipt
trading_status_increment_receipt
isst_increment_receipt
adjusted_increment_receipt
period_increment_receipt
special_phase_increment_receipt
price_limit_increment_receipt

independent_postcheck
data_head_promotion_receipt
```

---

# 46. 首次 E2E 的成功标准

```text
TDX official page update_date = 2026-09-28
TDX zip integrity = PASS
TDX delta = valid
BaoStock 2026-09-28 update = READY
Required Source Freeze = PASS

all required 00/01/02 components
= PASS or contract-accepted explicit per-security degraded

independent postcheck = PASS

V4_STAGE_ACCEPTED_HEAD = unchanged
V4_DEV_BASELINE_HEAD = unchanged

V4_DATA_ACCEPTED_HEAD.accepted_trade_date
= 2026-09-28
```

---

# 47. 这才是真正的“每日增量更新”

注意：

```text
源层：
每天重新下载 TDX 完整 snapshot

处理层：
只解析/重建 delta

发布层：
只发布 T + affected revisions
```

所以：

```text
FULL SOURCE SNAPSHOT
!=
FULL SYSTEM REBUILD
```

这是本设计最核心的区别。

---

# 48. 当前下一步

```text
停止旧 DM-01 local vipdoc readiness 方案

实现：
TDX_OFFICIAL_DAILY_PACKAGE_SOURCE_V1
+
BAOSTOCK_DAILY_UPDATE_SOURCE_V1
+
TDX_PACKAGE_DELTA_V1
+
V4_DAILY_SOURCE_FREEZE_V2
+
REAL_INCREMENT_BUILDER

然后直接以 2026-09-28
作为第一次真实 E2E。
```

V4-03 继续禁止启动。

**文档结束**

# 大A V4｜动态日更、任意交易日断档补齐、后端默认自动调度与页面触发｜完整设计与执行合同 V1.1

- 版本：`V4-DYNAMIC-DAILY-R1.1`；日期：2026-10-09（北京时间）；类别：正式设计＋Codex 工程任务卡；无图，Markdown。
- 前版：`V4-DYNAMIC-DAILY-R1.0`；本版为用户范围纠偏后的**完整替代执行合同**，前版保留在 Drive 作为历史，不再作为执行依据。主要变化：任意缺口（旧 9/30→10/08、10/09 只是一例）；**本轮无分钟 K**；周/月 K 复用现有日 K 聚合；**后端运行自动更新默认 ON，无需页面打开和再次手动启用**。
- 仓库依据：`NanOns/a-share-market-structure-research`，`codex/v4-fp14-r2-repair`，审阅时远端 HEAD `6f0cf3c5a983eab481283d0436e050d70b77fe29`。执行前重新核对最新 HEAD、`AGENTS.md` 和 Drive 当前 FP02/FP11/FP14/DRIVER。
- 设计基线：R4.3 已上线的 `data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json` 当前截止 `2026-10-08`，SHA `e751fb6ebee81baa3fd213515800e220135738d485118828bc6c81fe9dd853c8`；`data/v4/V4_DATA_ACCEPTED_HEAD.json` 的严格历史 PIT 9/30 完全隔离。
- 本合同属于 FP02（主）、FP03（Job API/BFF）、FP04/FP11（工作台/操作入口与诊断）、FP13（E2E）、FP14（原子发布/运维）的跨阶段先行工作。核心 FP 页面可并行，不需要等未来 20 天统计成熟。工作流**只读研究数据**，不涉及股票下单、自动交易或解除历史 PIT 权限。

## 0. 设计结论与不可谈判目标

在工作台的“数据与诊断 → 日更中心”和首页顶部建立可用的 `检查更新`、`立即补齐`、`自动更新设置` 入口。后端不仅检查，还能真正执行交易日历计算、源采集、断档重建、逐日 QA、历史依赖重算、候选生成、同 token 读回、CAS 发布与失败回滚。后台服务存活时调度器**默认开启**，在北京时间 `18:35` 首次尝试当日完整日线/复权源校验；数据不齐则重试，不允许卡点误认源已入库。页面不开也照常运行；服务启动/重启必须 catch-up。**不纳入分钟 K，不新增财务报表抓取，不调用 BaoStock 周 K/月 K**；周/月 K 使用仓库现有接受的日 K 派生链。

严格区分：

1. **时间门 `TIME_ELIGIBLE`**：只表示可能完成，不意味着数据完成；
2. **源门 `SOURCE_READY`**：采集并校验目标日期的数据实际可用；
3. **研究门 `DERIVED_READY`**：当日及受影响历史数值重算 QA 通过；
4. **发布门 `PUBLISHED`**：权限与 CAS 真实成功，API 和 UI 用新 context token 回读；
5. **独立验收 `EXTERNAL_ACCEPTANCE`**：与工程运行状态分列，不能自动用任务成功代替。

必须保留最后一次正式有效 Head；重试、人工点击、重启、节假日、断网均不得导致页面全部 UNKNOWN。

## 1. 数据源节奏（北京时间 Asia/Shanghai）

以下 BaoStock 时间**按用户提供的实际入库节奏作为调度基线**；不把其当服务 SLA，始终要求日期/行数/复权/校验实际验证。通达信官网一般在 17:30 前后可取得，但也仅为经验，不设为硬事实。所有时间可通过配置版本化调整，统一记录 provider 响应时刻和处理时刻。

| 数据系列 | 参考节奏 | 自动执行原则 | 是否属于当前基础日更 | 权威、就绪与责任 |
|---|---|---|---|---|
| 通达信原生日 K／官方行情包 | 通常 17:30 后具备最新包（经验，不是 SLA） | 可在 17:45 预检；18:35 主检查；缺失时继续重试 | **是，OHLCV 主权威** | 来源包实际日期、完整覆盖、真实目标交易日 Bar、不可变快照 SHA、上市停牌身份一致 |
| BaoStock 目标交易日日 K | 用户提供入库节奏：当交易日 17:30 | 主校验 18:35（可以在更早时轻量预检，但不得宣称完整） | **是，日期级来源及交叉核验** | `provider_date`/行集/停牌与 TDX 差异；不覆盖 TDX OHLCV |
| BaoStock 目标交易日复权因子 | 用户提供入库节奏：当交易日 18:00 | **18:35 才开始完整验收，至少留 30 分钟缓冲** | **是，既有事件/复权源核验** | 回执、适用日期、合法无变更、受影响证券 QA；不改变 QFQ 既有 GBBQ/计算权威 |
| **系统自身计算的周 K、月 K** | 随每日被接受的日 K 增量 | 日线 QA 后通过既有 `PERIOD_RAW/PERIOD_ADJUSTED` 更新 | **是，属于现有计算产物** | `WEEKLY/MONTHLY` 从已接受日 K 按交易日历聚合，RAW/QFQ 基准隔离、未完周期与正式收盘状态区分 |

**明确排除**：本轮不设计、采集、调度或验收分钟 K；不新增 BaoStock 周 K／月 K 下载、周六／月初等待门；不把次日财务报表入库纳入新增日更流水线。若既有产品其他独立模块需要财务数据，必须以其原阶段合同为依据，不能借本方案扩张。
推荐首次主任务的具体动作：
- `17:45` **轻量预检** TDX（可选，不对 BaoStock 的日/因子做提前就绪断言）；不得自动把预检视为成功。
- `18:35` 主日更：检查 `TDX + BaoStock 日线 + 因子 + 证券身份/生命周期/GBBQ + 完整性`，通过后立即生产增量。
- 若等待：`19:05`、`19:35`、`20:05`、`20:35`、`21:05`、`22:05` 进行有上限的重试，次日 `07:35` 追加一次；调度间隔与次数可配置。重试需要先读 provider 状态/快照摘要，**不要每次重下大包/全市场查询**。
- 如果跨越午夜或者节假日才补上，仍按原 `trade_date` 写入，`observed_at/published_at` 使用真实采集/发布时刻；历史补采绝不可改成“当日首次可得 PIT”。
- **默认模式：AUTO=ON**。只要 V4 后端服务进程运行，独立调度 worker 就持续工作；网页关掉、浏览器退出不影响。Windows Task Scheduler／Windows Service 可用于确保**后台服务开机启动**，但不作为“网页启动定时任务”的替代。若后端进程本身关闭，不谎称仍在更新；重启后根据最后有效 Head 自动补齐所有成熟的遗漏交易日。
- 运行策略保留版本化配置与操作审计：服务启动默认启用只读研究数据日更；管理员可在页面暂停／恢复；关闭自动模式只停止未来新任务，不破坏已有已接受数据。


### 1.1 默认自动运行的启动及恢复语义（独立于 UI）

- 服务由 `run_workbench_service.py` 正常启动时，scheduler 默认启用，启动时读取持久策略与 accepted operational head，**先进行遗漏任务恢复和所有已成熟交易日断档补齐**；如果今天还未达到 18:35，只处理此前已成熟交易日，并给今天登记下一次触发时间。
- 主调度必须实现服务启动 catch-up + 18:35 正常触发 + 等待数据时有上限重试 + 下次重试持久化，时区固定 `Asia/Shanghai`；不能只在 18:35 分这一分钟上线才执行，不能要求网页打开或人工刷新。
- 如 18:35 时后端断电／停机、22:10 才恢复，恢复时立即核查当前已经成熟的缺口；如服务连续停数周，基于最后成功 Head 一次枚举**所有**缺失交易日并按序推进，绝不只处理“上一个交易日”或“今日”。
- **默认开启**是用户已明确确认的只读运营数据日更产品规则；必须由版本化配置、实际启动日志和身份/权限边界记录支撑，而不是以定时任务自动获准修改算法或历史 PIT。用户可以自行暂停，暂停时页面必须显示 `AUTO_PAUSED_BY_USER` 和最后有效数据；重启后按最新持久设置恢复。
- 手动按钮由后台同一 Job Queue 执行；同日期的重复点击/时间触发去重，不会出现双重 CAS、重复下载或过量 BaoStock 请求。

## 2. 任意数量的交易日断档识别：不可按自然日加一天

用已接受 SSE+SZSE 官方交易日历 `session_dates`，先计算缺口：

```text
last_good = accepted operational head.trade_date
eligible_target = min(用户目标日期, 当前时点允许的最新已收盘交易日)
missing_sessions = [d for d in accepted_calendar.session_dates if last_good < d <= eligible_target]
```

**示例 A（非日期特化规则）**：生产仅到 `2026-09-30`，现在 `2026-10-09 18:40`，节假日不计入：`missing_sessions=[2026-10-08, 2026-10-09]`；按 8 日、9 日严格前后依赖进行构建与 QA。主源可共用**一份最新已经校验的 TDX 包**，独立提取两天真实 `.day` 日线，BaoStock 按每一日分别查询，不能强求 TDX 官网 `update_date == 每一个旧目标日`。把整份 TDX 包的 `source_available_at` 记为 10/09 实际观察时刻；8 日是事后回补，不冒充 10/08 即时取得。

例 B：10 月 9 日下午 16:00 手动执行，8 日已满足就绪时间，9 日尚未满足 BaoStock 发布门。允许**先把 8 日原子发布**，把 9 日保留在 `WAIT_BAOSTOCK_FACTOR` / `SCHEDULED`，到 18:35 再继续；或者用户选择“只预检并等待全部”，但默认不得让一个未就绪新日阻塞前一已完成日。

例 C：系统关机两周或两个月后重启；从 last_good 扫描**所有已收盘且符合时间就绪门的交易日**，不限制仅今天、昨天或固定两天；可为 1、2、5、10、20 或更多交易日，以批量复用捕获物、逐日发布或 staged batch 单 CAS 的策略补齐。每个交易日均有独立 `DAY_RECEIPT`，跳过交易日必须有市场正式休市凭据，不能凭 `data.size=0` 当作非交易日。

例 D：存在先前失败的源捕获；优先复用 SHA 校验过的不可变缓存/检查点，只补缺环节；支持 `RETRY_FAILED_ONLY`，不重复拉 2 年历史。若 source revision 变更，则新建版本并保留旧输入。

## 3. 必须解决的两个现存代码硬阻塞

### 3.1 通达信历史包补齐语义

现 `src/workbench_analysis/tdx_official_daily_source.py::capture_tdx_official_daily_package()` 只有 `update_date == target_date` 才下载包；当 10/09 下载页已经更新为 10/09，回补 10/08 调旧入口会返回 `WAIT_TDX_PUBLICATION`，**即使当前最新包实际包含 10/08 的原生日线**。

增加 `capture_latest_tdx_package()` 一次读取官网最新 metadata＋ZIP；独立 `extract_target_session_bars(latest_package_ref, trade_date)` 对任意 `trade_date <= package_content_max_trade_date` 提取真实条目并冻结。若 ZIP 不含历史 8 日数据，则允许从已校验 `D:/new_tdx` 本地 `.day` 读取目标日期，并附官方新包不含该日的证据＋BaoStock 对照；**仅因最新包标注 10/09 不能推断其必然包含 10/08**，必须检查内部数据。仅访问本机 TDX 时不改写 TDX 根；快照写在项目独立数据源目录。输出 `provider_package_date`、`target_session`、`bars_date_coverage`、`frozen_at`、`source_sha256`、`reconstruction_from_later_snapshot=true`。不能伪造 10/08 旧下载页/旧网页时间。

现有严格当日捕获模式保留供兼容；引入“latest package＋历史抽取”新模式，不在同一 `target_date` 字段中混淆 provider 发布日。

### 3.2 R4.3 冻结四日的 `DATES` 和硬编码 `2026-10-08`

现 `src/workbench_analysis/r43_operational_sources.py::DATES`、`src/workbench_analysis/r43_operational_publication.py::validate`、`CandidateReadV2.context/read/dispatch` 把日期固定在 `[09-28,09-29,09-30,10-08]`，默认接受日硬编码 10/08。**不允许直接把这个原有冻结合同改成“任意日期”后覆盖已验收历史。**

新增版本化继承型候选，例如 `V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1` 和 reader `OperationalSuccessorReaderV1`：
- `accepted_trade_date=max(published_sessions)` 由 head 得出，不能写死；
- `published_sessions` 是准确递增的接受交易日清单，可引用历史日 Owner；要求交易日连续，不允许跳过；
- `source_registry[day]`、`owners[day][domain]` 每日 SHA/size/行数/计算口径绑定；
- 旧 R4.3 four-session Head 作为前驱版本不可变；仅新 `V4_OPERATIONAL_RESEARCH_HEAD.json` 在 CAS 中变更；严格 PIT 9/30 Head 不动；
- 在候选中记录 `data_cutoff_date` 与 `observed_at`、`snapshot_membership_asof`，禁止把新的成员 S 回投成历史 as-recorded；
- `CandidateReadV2` 保留原版，后继使用 `OperationalSuccessorReaderV1`；service 按 `contract_id` 分派 reader，保证回滚能读旧版；
- 旧 context_token 请求在新 Head 上拒绝并提示刷新（或旧版显式历史路由），不得默默使用新 token 混旧 HTML；
- 编辑/编译任何 producer/算法代码必须走算法版本接受与数据回算影响分析；不能把数据日更当作自动算法权限升级。

### 3.3 已核实的周 K／月 K 既有聚合机制（原样复用，不增加行情源）

仓库已验证代码和合同：

- `config/v4_02_formal_period_contract_v1.json`：`open=first valid actual daily open`、`high=max(daily high)`、`low=min(daily low)`、`close=last valid daily close`、`volume/amount=sum`；针对真实停牌、数据缺口、复权未知明确区分；`CLOSED_ONLY` / `AS_OF_PARTIAL` 分开，不凭未来收盘重建过去。
- `scripts/build_v4_02_formal_periods.py`：`period_key()` 生成 `WEEKLY`/`MONTHLY` 交易日期分组，程序从已有日 K 生成 RAW/QFQ 正式周期数据；不是向 BaoStock 请求周期数据。
- `src/workbench_analysis/dm01_incremental_component_builders_r3_3.py::_build_period`：既有 `PERIOD_RAW`、`PERIOD_ADJUSTED` 增量构建器消费日线和上一正式聚合状态，维护周/月的 `AS_OF_PARTIAL` 与 `CLOSED_ONLY`，支持周或月尚未结束时的当前可见周期 K。

**日更正确调用顺序**：日 K QA → 既有复权日 K（原权威与事件）→ `PERIOD_RAW` / `PERIOD_ADJUSTED` → 下游依赖（Core、Profile、RPS、板块等，准确依赖图按原合同）→ 新运营 Head。日线连续补两日时周/月聚合必须连续执行两次，保证当周/当月开高低收、累计成交量额、周期状态及 SHA 正确；周五等最后有效交易日才确认相应周 K 的完整结束状态。**不得单独等待 BaoStock 周六 17:30、每月 1 日 17:30**。

当缺失前一天停牌或行情缺口时必须维持 `DATA_GAP/UNKNOWN` 而非造价；发生复权事件则重算受影响的周期与滚动窗口，不允许把 RAW 偷当 QFQ。

## 4. 后端流水线与事务顺序

```text
UI / Scheduler
  └── POST /api/v4/operations/daily-update/jobs
       └── persistent job queue (SQLite or existing durable job DB; NOT in-memory)
            ├── 01 CALENDAR_GAP_PLAN (last_good, latest eligible, target, missing_sessions)
            ├── 02 SOURCE_PREFLIGHT  (TDX latest version, BaoStock date readiness; snapshots)
            ├── 03 CAPTURE_TYPED_SOURCE (reuse frozen bytes; quota; retries)
            ├── 04 IDENTITY_LIFECYCLE_GBBQ (target-dated source evidence)
            ├── 05 DAILY_BAR_RECONCILE (actual bar / suspension / delist / identity unknown)
            ├── 06 ADJUSTMENT_AND_AFFECTED_HISTORY (QFQ event; rolling windows)
            ├── 06B DERIVE_EXISTING_WEEK_MONTH_K (PERIOD_RAW / PERIOD_ADJUSTED, no BaoStock W/M)
            ├── 07 PRODUCE_FULL_MARKET_DAILY_OWNERS (market / sector / stock / focus / forward)
            ├── 08 QA_AND_CANDIDATE (source SHA, completeness, numeric oracle, schema)
            ├── 09 AUTHORIZED_PROMOTION_CAS (expected previous head digest)
            ├── 10 HTTP_READBACK_AND_UI_REFRESH (same token, date, 4+ domains)
            └── 11 RECEIPT_ARCHIVE (checkpoint; logs; optional Drive sync)
```

按交易日顺序处理，每日可单独发布（默认），当日正式 CAS 失败保留此前成功已发布的最近交易日；失败日期之后不得越序发布。若改用“整批一次 CAS”须明确失败语义与展示差异，不允许部分不可见又称全部成功。交易日版本链 `D-1 -> D` 必须可重算。

**源层**：TDX 原始日线主权威，BaoStock DailyUpdates 日K＋因子用于日期就绪/交叉验证；现既有 `baostock_daily_update_source.py` 把因子定义为 `AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY`，不能在日更设计中偷偷改成 QFQ 计算权威。GBBQ 与最新行动作仍按现接受合同处理，变化时记录 `ACTION_QA_REQUIRED`；跨事件时需要重算受影响历史价格和滚动特征，而非只 append 今日一行。无因子变化的合法空结果需有来源证明，不能一律判“缺失”；无实际数据的空日 K 必须判 WAIT/ERROR。

**Owner 层**：市场四轴、个股 Core/Profile/RPS、板块 Native/LOO/Rotation、Focus/Forward 随新日数据各自产出；对不具备正当源的域精确 `SOURCE_INCOMPLETE` 并保留 `last_good`，核心日 K、复权和真正必需的市场/板块/个股 Owners 缺失不得全局 PUBLISHED。类似历史 Snapshot S 最新成员回算应继续标明 `AS_RECORDED=false`, `PIT_ELIGIBLE=false`, `survivorship_bias_risk=true`。新成员版变更需冻结独立 S 快照，不可静默改旧 daily Owner。

**数值验收**：市场分母 / 真实 Bar 与停牌守恒、证券身份/代码变更、ST/涨跌停异常、关键 Close/Volume/Amount 交叉核对、时间窗口所有证券 RPS、滚动量价、跨日 Focus 状态更新，保证同比口径正确。Rotation 在未完成独立状态机验证时仍具名 `VALIDATION_ONGOING`，不因此阻断非依赖域。

**发布权限**：本轮用户已明确要求“后端运行时自动日更默认开启”，因此新版本化 `READ_ONLY_OPERATIONAL_DAILY_RELEASE_POLICY_V1_1` **默认 AUTO=ON，无须用户进入页面再次点击开启**。不过必须将当前用户指令及范围绑定为正式可审计的策略配置，策略只能覆盖**同一已接受算法／研究域**的后继交易日数据、来源完整性 QA 和 CAS，且严格保持只读研究权限、独立审计记录与合法来源；绝不将 10/09 那次“一次性候选切换”证明复制成后续无限签名，也绝不宣称算法新版本自动获得准入。首次部署策略由工程门验证这份用户明确要求，后续用户可以从页面暂停／恢复；需要升级算法、改变成员时间知识性质、扩张交易或 PIT 权限时仍须新增授权/验收。

## 5. BaoStock 时间与成功准则细则

时间可开始并不等于数据齐全。每个目标交易日必须：
- `provider_date == target_trade_date`（日报和日因子日期级来源，或有可审计的零更新说明）；
- 实际 K 行数与完整市场身份/停牌/退市状态对账，覆盖率不得只用固定阈值掩盖结构断层；
- 日/因子源响应 SHA、查询方法、返回状态与请求时间留证；重要行情源差异有逐证券处理，不要“接近就算相等”；
- 同一目标日期满足两类数据的入库缓冲条件；因子跨日回修触发依赖重算；
- BaoStock 预算沿用代码现有 40,000 软、45,000 硬停止；由 **北京时间实际发出 API 请求日**计数，断档合并读取和缓存复用减少浪费，不因点手动按钮重置账本；
- BaoStock SDK / DailyUpdates 真实能力必须先运行 live smoke、实际认证和版本绑定，再调用。现 `capture_baostock_daily_update.py` **要求同目标日期 runtime acceptance manifest**，新增日期必须有真实 runtime 接受流程，不能只复制上个交易日 manifest 改日期。

**批量反复核验策略**：对相同 `target_date`＋方法＋同 snapshot SHA，缓存 `READY` 结果；重试先读 provider “就绪证明”或小样本，必要时才全量，若发生修订另开版本并启动受影响窗口重算。**本轮只使用当前合同规定的日 K、复权因子及既有动作/身份来源；周月是本地计算产物，不存在新增 BaoStock 周月请求队列。**

## 6. 页面入口与交互定义（FP04＋FP11）

入口一：首页右上角“数据更新”——显式状态图标、截止日、下一待补日、最后成功时间，点击进入日更中心。

入口二：一级 `数据与诊断` -> **`数据更新中心`**。页面至少显示：

```text
V4 数据更新中心                                      [检查数据源] [立即补齐] [自动更新设置]
正式运营截止：2026-09-30         最新已收盘交易日：2026-10-09
应补：2026-10-08、2026-10-09（2 个交易日）
BaoStock：日K 已到 / 因子 等待(18:35 后检查)；TDX：官网已到 / 原生包已冻结
模式：基础日更（TDX日线+BaoStock日线/因子+研究Owners）
进度：10/08 [已校验 / 已发布]  10/09 [等待复权因子 / 下次尝试 19:05]
任务 #.... 状态 WAIT_PROVIDER   运行时长 --  重试次数 --   [查看详细日志] [重试失败日]
自动更新：开 / 关  | 首次 18:35 | 失约重试 | 最后有效 Head SHA ...
周/月 K：由日 K 自动派生，RAW/QFQ 分开，显示本周/月部分周期或已结束周期；不下载 BaoStock 周月 K
历史版本与回滚：当前 release → 旧 release；需单独有权限的操作按钮
```

按钮定义：
- **检查数据源**：只执行 source probe 和缺口推导，不请求正式数据写入，不移动 Head；可在任意时刻。
- **立即补齐**：发起真实有持久 Job ID 的任务；默认追到“当前有资格被验收的最新交易日”，未来未到入库门的交易日自动进入等待队列；支持选择结束目标日期。不是单纯打开日志，也不是前端 setTimeout。
- **重试失败日**：只对失败/等待的日期和缺失步骤重做，不重抓已验收旧日数据。
- **自动更新设置**：服务运行时默认 `ON`；显示 18:35 首次正式验证、上次调度、下次重试、当前任务和服务是否存活；允许管理员主动暂停/恢复及调整已授权的重试策略。暂停只阻止后续新任务，不取消已开始 CAS 的原子性。**首次使用不需要打开页面或显式点 ON**。
- **查看日志**：展示交易日→阶段→来源→字段→错误/下次动作，允许复制脱敏运行摘要；不得泄漏凭据、个人路径隐私。
- **取消**：仅采集/分析/候选尚未 CAS 时可请求取消；CAS 阶段不可任意半终止，完成后通过独立 rollback 行为处理。

**必须展示的分组状态**：`UP_TO_DATE`、`SOURCE_CHECKING`、`WAIT_MARKET_CLOSE`、`WAIT_TDX`、`WAIT_BAOSTOCK_DAILY`、`WAIT_BAOSTOCK_FACTOR`、`QA_BLOCKED`、`CALCULATING`、`STAGED`、`PUBLISHING`、`PUBLISHED_PARTIAL`、`PUBLISHED_FULL`、`FAILED_RETRYABLE`、`FAILED_TERMINAL`、`ROLLBACK_RESTORED`；不要一个 UNKNOWN 覆盖全部。

**前端交互质量**：可保留上一次数据、刷新/重开网页后取持久任务状态；HTTP 202 返回 job_id，页面轮询或 SSE，连接断开不取消任务；分交易日进度、点击详情、状态和错误码明确；禁止阻塞网页服务器的请求线程。

## 7. API / 存储 / 并发合同（建议）

| Method | Route | 功能 |
|---|---|---|
| GET | `/api/v4/operations/daily-update/status` | 当前运营截止、官方日历、目标日、TDX/BaoStock readiness、下一调度、上次 job、当前 token |
| POST | `/api/v4/operations/daily-update/probe` | 实际探测来源就绪，**no publish**，返回 202 job_id |
| POST | `/api/v4/operations/daily-update/jobs` | body `{mode:"CATCH_UP",through_date:"YYYY-MM-DD"}`；真实多日补齐，接受后 202 job_id；非幂等动作带 Idempotency-Key |
| GET | `/api/v4/operations/daily-update/jobs/{job_id}` | 状态机 / 分日明细 / blocked_reason / CAS 结果 |
| GET | `/api/v4/operations/daily-update/jobs/{job_id}/events` | 分页事件、真实 source digests、速率/时间安排，SSE 可选 |
| POST | `/api/v4/operations/daily-update/jobs/{job_id}/retry` | 只重做失败域，拒绝当前 CAS 进行中互相覆盖 |
| GET/PUT | `/api/v4/operations/daily-update/settings` | 服务运行时自动更新默认 ON、暂停/恢复、日 K 18:35／重试计划、允许的只读域、持久版本与审计；不包含分钟、财务、BaoStock 周月时点 |
| GET | `/api/v4/operations/daily-update/releases` | 发布版本链、前驱、source/owner QA、回滚资格，严格权限分离 |

持久模型至少 `update_jobs(job_id, trigger, owner, target_session, through_date, status, started_at, finished_at, head_before, head_after, idempotency_key, error)`、`update_job_days(job_id, trade_date, state, source_checks, owner_ref, attempt_count, next_retry_at)`、`update_events(job_id, timestamp, stage, event_code, safe_detail)`、`source_revisions(trade_date, provider, artifact, sha, available_at, captured_at, verified_at)`、`operational_release_chain(...)`、`scheduler_policy(...)`。可用 SQLite WAL（仅 Job 元数据；不重返已经退役的市场数据 DuckDB）或现有可靠 PostgreSQL，必须单实例/多进程锁正确、崩溃恢复可重播；保留 append-only 原始凭据。

鉴权与安全：localhost 默认只供本机，LAN 开放必须登录；有能力权限的编辑动作 + CSRF/origin protection、allowlisted target 日期、请求体大小限制、rate-limit、敏感信息脱敏；读 API 与执行 API 独立权限。单全局 publisher 锁＋每个目标交易日 source job 锁，防止手动与定时重复运行；跨进程严格 compare-and-swap。HTTP 端口仍用现有工作台，页面不允许任意 shell 命令调用。

## 8. 任意断档与交易日时间示例及期望结果

| 场景/北京时间 | 缺口 | 允许做的事 | 结果 |
|---|---|---|---|
| 10/09 16:01；上次接受 09/30 | 10/08,10/09 | 10/08 若真实数据就绪先补；10/09 仅探测/预约 | 不把 10/09 标记 READY |
| 10/09 18:35，全部当日源正常 | 10/08,10/09 | 优先复用最新同一官方包提取双日，独立 BaoStock 每日证据，按序数值重算 | 成功发布 10/08 再 10/09；截至 10/09 |
| 10/09 18:35，因子尚未可用 | 10/09 | 不发布 10/09，19:05 再探测 | 旧有效 Head 继续可见，状态 WAIT_BAOSTOCK_FACTOR |
| 10/09 19:35 因子可用 | 10/09 | 重试缺项，QA 后 CAS + HTTP | 截至 10/09、显式新 token |
| 休市日/节后补跑 | 任意连续缺失交易日 | 官方日历生成准确序列，缓存复用；断档 1、2、10、20 日均按序处理 | 不把周末节假日当作失败交易日 |
| 后端服务启动但未打开网页 | 已成熟缺口 | 调度器启动即 catch-up，或按时在 18:35 自动执行，不必人工打开自动设置 | 自动运行并保存 Job 及每日期状态 |
| 周内任一新日、当月未结束 | 日 K 已通过 | 现有程序生成 `AS_OF_PARTIAL` 周/月 K，后续交易日继续累积 | 不等待周六/月初外部 K 源 |
| 补至 10/09 期间 10/08 某一证券缺少原生 Bar | 10/08,10/09 | 根据停牌/身份/退市证明判断 | 若未知不得跳 10/08，保留上次正式 Head |
| 任务执行进程在 CAS 之前崩溃 | 任意 | 重新加载 Job checkpoint 检查输入 SHA | 发布 Head 未改变，允许精准恢复 |
| CAS 成功，HTTP 失败 | 任意 | 检查发布锁和 expected head，原子回滚到前驱 | 页面维持旧 last-good，留错误回执 |
| TDX/BaoStock 历史数据在新交易日更正 | 受影响窗口 | 新 SHA 修订记录，重算受影响证券/窗口/板块，比较差异 | 不覆写历史旧输入，不静默沿用旧数值 |
| 目标日是 10/09 但当前已自动更新 10/09 | 无 | 只读复核 | `NOOP_ALREADY_CURRENT`，不重复拉所有数据 |

## 9. 完整验收门（以下 24 项均适用；另加任意断档和默认开启负测，不许仅单测通过）

1. 官方交易日历能处理任意连续交易日缺口，09/30→10/09 正确生成 `[10/08,10/09]` 只是一个样本；另测 1 日、5 日、10 日、跨周跨月和停机恢复，排除休市日。
2. 10/09 最新官方包能够真实提取 10/08，且不会被 `update_date != target_date` 错误阻断；若官方包并不含旧日，清晰回退到可校验来源/明确缺失。
3. 10/09 16:00 手动只发布已具备条件的 10/08，不伪称 10/09 已就绪。
4. 10/09 18:34 自动模式严格不给 10/09 full-daily ready；18:35 之后才允许检验。
5. 18:35 BaoStock 日线 READY/因子 WAIT，任务正确等待；19:05 变 READY 后自动恢复。
6. 校验实际 API 日期，避免 BaoStock 返回 10/08 却写成 10/09。
7. BaoStock 空合法因子变化不会假失败；无来源证明时继续 WAIT。
8. 通达信网页日期、包日期、包内行情日期/窗口分开记录，不能用包发布日期伪造旧日 PIT。
9. 真实停牌无 K / 缺失未知 / 尚未上市与退市分别对账，不造 0 Bar。
10. 股票代码变更/证券身份追溯不中断，两日上市池可以不同。
11. 采用相同冻结原始字节重跑两次得到相同 SHA；新增修订新版本而非覆盖。
12. 复权因子事件更新引发受影响历史价格坐标及相关 rolling 指标的重新计算与比较。
13. 同一主线板块 S 有新版就冻结新快照并挂 `reconstructed` lineage；不提升成历史 PIT。
14. 10/08 先 CAS PASS，10/09 FAIL 时最后接受日仍是 10/08；不跳过 10/09。
15. 失败重试幂等、避免同一日期重复全包/全市场 BaoStock 请求；预算软/硬限制生效。
16. 手动与定时同时触发，只允许一个实际 Publisher；另一个被拒绝或复用相同 Job ID。
17. 重启浏览器后 Job ID、已完成日、错误原因与恢复位置持久；关掉浏览器期间后端仍按计划执行。
18. **服务运行后 AUTO 默认 ON**，不打开网页也能在 18:35 自动触发；重启 Windows/服务进程后调度恢复，错过18:35可 catch-up；服务进程未启动时不得报告任务正在执行。
19. 没网络、来源 API 异常、下载 HTML 验 ZIP、TLS 验证失败时 fail-closed 且旧页面持续可用。
20. 新运营 Head 与旧严格 PIT Head 的发布权限、数据口径、token 严格隔离。
21. 每次真实生产 CAS 完成后 `/api/v4/context`、`/api/operations/status`、stocks/sectors/market/focus 同 token、日期，前端 1366/1920 可读。
22. 成功发布后 Forward/Rotation 仍保留各自未验数值/权限状态；不越权说全部独立 PASS。
23. **周/月由已接受日 K 自行派生**，本周/月未结束时正确为 `AS_OF_PARTIAL`；结束后改 `CLOSED_ONLY`；RAW/QFQ、累计量额及跨周月边界正确，不访问 BaoStock 周/月或分钟接口。
24. 外部审计可从 Google Drive/GitHub 及部署日志追溯 Job、每个交易日输入、源 SHA、数值 QA、CAS 和回滚；正式交付 Markdown 自动归档并回读。

## 10. 推荐分包执行顺序（Codex）

### DD-01｜动态交易日历与断档计划／只读盘后就绪门（P0）
保留原冻结类不动，创建 `operational_daily_calendar_v2.py` 和 `source_readiness_v2.py`；根据现在时刻与 last-good 枚举全部缺口；加入配置 18:35 和 30 分钟缓冲；日期级 WAIT/READY 和官方休市日。单测含多日跨节、8/9、16:00、18:34、18:35、断网。

### DD-02｜TDX 最新包与历史目标提取＋ BaoStock 双系列正确采集（P0）
改造“官网包发布日期”和“目标 K 线日期”解耦；支持最新一次 ZIP 对多日覆盖的真实提取/本地可信历史 fallback；BaoStock per-day runtime live smoke、K/因子双响应、SHA、异常与预算，保留现旧契约。校验同一源 SHA，不做整包反复下载。

### DD-03｜动态 Owner successor 与多日数值计算链（P0）
新版本候选与 reader，日期数组按真实日历扩展；真实生命周期/GBBQ/QFQ/RPS/Core/Profile/Native/LOO/Market/Focus/Forward 继承再运算，受影响历史滚动窗口重算，明确未知域；每完成一日可以发布，禁止跨日跳号。

### DD-04｜持久 Job、**后端默认 ON** 调度器、权限与发布 CAS（P0）
Job/Day/Event 持久表；后端启动注册持久 worker，默认 AUTO=ON；18:35 自动入队，退避重试；服务启动时 catch-up；页面关闭不影响任务。Windows 自启动由系统服务/Task Scheduler 托管进程，不能依赖浏览器。绑定本次用户明确指令的受限只读日更策略、审计状态与 CAS，故障回滚和恢复；允许从页面暂停/恢复，不得复制旧一次性 Head 签收。手动与自动复用单一任务队列、去重与锁。

### DD-05｜工作台可触发入口、状态与日志（P0）
在现 `/v4/research/diagnostics` 增加**真实可点击**的按钮和独立 `/v4/research/data-update` 页面；前后端状态闭环，使用实际 API，显示 gap 日期/来源 readiness/任务执行结果、阶段 SHA、下次尝试，支持手动多日、重试失败日、自动开关；不存在“演示点击”。避免因局部无源清空整个页面。

### DD-06｜**既有周/月 K 增量聚合复用与 QA**（P0，随 DD-03 开发）
绑定原 `PERIOD_RAW`/`PERIOD_ADJUSTED`、`V4_02_FORMAL_RAW_QFQ_PERIODS_V1`，真实日 K 增量驱动 `WEEKLY/MONTHLY`，验证跨周/月边界、节后恢复、`AS_OF_PARTIAL → CLOSED_ONLY`、RAW/QFQ、停牌与缺口传播、复权事件的受影响窗口；**禁止新建 BaoStock 周/月采集器或分钟 K 任务**。完成后为 DD-03 日更数值验收提供证据，不另设外部发布时钟。

### DD-07｜独立 E2E 验收与归档（P0 发布门）
冻结输入 T0：至少覆盖 **1 日、2 日、跨节假日、5～10 日、多周跨月**等不同断档长度；09/30→10/08→10/09 只作其中一个典型样本。Mock 控制时间快照，真实/模拟源分别标识；每个目标交易日完整 Owner、RAW/QFQ 周月派生、新 Head 与任务状态、CAS 后重启、负向回滚和 Chrome/Edge 1366/1920 都必须验证；**自动调度无页面、服务重启 catch-up、默认 ON**加入硬测。产出 `DYNAMIC_DAILY_EXTERNAL_AUDIT.md`、分日收据 JSON、job/event 证据、真浏览器图、Git SHA 与 Drive 回读。工程绿不等于正式独立外审签发。

**切入原则**：DD01＋DD02＋DD04 的 Job/UI 契约可并行，DD03/ DD06 依赖真实DD02，DD05 可先实现稳定接口而不冒充后台已就绪；DD07 最后。允许 FP03/FP04/FP09/FP10 等其他前端开发不受其等待堵塞。不要一次性把所有包塞为一轮不可审计的巨大 commit。

## 11. Codex 最短启动指令

> 以当前 Drive 最新 FP02/FP11/FP14 合同和精确 Git HEAD 为基准执行 `V4-DYNAMIC-DAILY-R1.1`，**V1.0 已被本版替代**。做 DD01–DD06 日 K 和既有周月派生、DD07 独立 E2E；页面手动触发与后端服务存活默认 AUTO=ON 同时交付。断档按所有缺失交易日连续补齐，9/30→10/08→10/09 只是验收例之一；BaoStock 18:00 因子延迟到18:35再验证、TDX 最新官网下载日与历史行情目标日解耦、动态 successor 日期版和CAS完整串通。**完全禁止分钟 K、新财务链、BaoStock 周月 K 下载**。不动 R4.3 旧冻结四日 Owner 和9/30 PIT Head；禁止使用固定日期/伪造PIT和伪造外审。逐包执行→真实测试与页面→提交推送→Google Drive正式归档；失败保留 last-good 并报告真实阻断原因，不准只交只读预检。

---

**代码核验依据**：
- `config/v4_02_formal_period_contract_v1.json`（既有 WEEKLY/MONTHLY 聚合公式与质量边界）；
- `scripts/build_v4_02_formal_periods.py`（已有正式历史周/月 K 程序自绘计算）；
- `src/workbench_analysis/dm01_incremental_component_builders_r3_3.py::_build_period`（现有每日继承的周/月增量算法）；
- `scripts/capture_tdx_official_daily_package.py`、`src/workbench_analysis/tdx_official_daily_source.py`（旧当日官网日期严格比较）；
- `scripts/capture_baostock_daily_update.py`、`src/workbench_analysis/baostock_daily_update_source.py`（日 K 与因子日期级快照；原有 QFQ 权威不变）。

**版次治理 / V1.0→V1.1**：删除分钟 K / 新财务抓取 / BaoStock 周月下载/独立周月时钟；明确周/月从日 K 派生；补齐不限断档长度、默认 AUTO=ON 和后台服务恢复语义；其它源/时间门、SHA、数值 QA、CAS、回滚、权限隔离与 Drive 归档要求继续有效。具体 BaoStock 计划入库时间来自用户提供的运营说明，实际数据始终现场核对，不作为 SLA。

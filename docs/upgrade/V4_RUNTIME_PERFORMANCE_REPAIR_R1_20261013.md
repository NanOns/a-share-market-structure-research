# 大A V4｜生产卡顿、真增量日更、新股/换代码、进度可视化与轻量测试整改总方案 R1

> 文档类型：供本地 Codex 直接执行的工程修复总卡 / 单一方案，不是重新进行 V4 全量验收。  
> 版本日期：2026-10-13；版本 R1；优先级 P0。  
> 仓库：`NanOns/a-share-market-structure-research`；实际审阅分支：`codex/v4-full-closeout-20261012`；冻结审阅 SHA：`5f322baaca3f7acc2b8fe3179f2fcb5ace8753cc`（北京时间 2026-10-13 19:55:39 的提交）。  
> 本文依据该提交的 GitHub 已提交代码、验收资料，以及用户提供的 20:11—20:25 本机 Codex 实测说明编写；**未远程连接用户 Windows 本机、未复现在线压测、未验证 20:25 之后日更最终发布状态**。  
> 用户要求：**个人本地项目优先简单、实用、高效；保留真正重要的数据正确性边界，取消无意义的商业级交付排场与重复全量测试。**

---

## 0. 唯一总目标及不可妥协的底线

最终让一台用户电脑在每天收盘后，**获取当天新数据 → 只计算必要的新交易日/受影响对象 → 更新股票画像/市场/板块/Focus/Forward/日周月 → 用 PG 原子发布 → 页面能流畅读上一版及新版 → 页面/托盘能看到真实进度**。

不要趁本轮扩大 V4 功能、重写已有算法或设计企业级分布式平台。

**保留 6 条必要边界：**

1. 本地通达信 `D:/new_tdx` 等目录始终只读；临时及工作文件放 `G:/codex_tmp` 或 `G:/codex work`。不要删除或覆盖正式数据、历史原始输入或已接受 Head。
2. PG 继续是正式现役业务数据、任务状态及读模型的唯一数据库；不引入 DuckDB/SQLite/Redis/新基础设施。现有历史兼容代码不在本轮清理范围。
3. 已发布 T0 数据只读，后台产生候选；候选数值和关键关系检查通过后才切当前 Head。失败保留上一版，不发布“成功”。
4. 同一交易日不得两个生产者同时写入；保留 PG advisory lock / 幂等日更键；读服务始终能提供上次发布数据。
5. **新证券没有历史就显示数据不足**；不能伪造 MA、收益率、前收盘或周月已完成状态；新代码不等于能够无证据把旧代码历史拼接到新代码。
6. 现有 Core 精确复权、画像、板块、Focus/Forward、阶段证据和数值合同不降级。性能优化只改变**重算范围、存储与服务方式**，不偷偷改变因子意义。

不需要：每个小改动全量跑 7,288 项测试、每次重建 EXE、每次重切 28765、每次扫旧 V1/V2 功能、每个阶段做完整外部审计、性能与回滚商业交付演练、反复打印数万条对照记录或反复生成多个大型 ZIP。

## 1. 最新提交已确认的事实：不是从零开始

### 1.1 代码现状与明确瓶颈

| 范围 | 仓库文件 | 已确认的代码现状/缺口 |
|---|---|---|
| HTTP 串行等待 | `src/workbench_service/core_product_server_r1.py` | `make_product_handler()` 声明 `threading.RLock()`；大部分 `/api/v4/*` 的缓存校验、PG 身份校验、BFF 查询及构造处于 `with lock:` 内；慢请求能堵住其他业务请求。 |
| 全量装载伪分页 | `src/workbench_service/core_product_bff_r1.py` | `page()` 先调用 `self.project(domain,day)`，完成全量 `deepcopy`、各数据源映射、字段补充，再在 Python 筛选/排序，`paged()` 最后才执行 `items[offset:offset+limit]`，默认 limit=30。 |
| 额外请求 | `src/workbench_service/static/core-product-r1/app.js` | 板块重叠组件进入详情时，从首 200 项继续循环请求所有页面；这不是按需加载。 |
| 计算服务共进程 | `src/workbench_desktop/engine.py` | 在同一桌面进程中启动 HTTP `ThreadingHTTPServer` 与 `ManagedDailyJobs`；`src/workbench_analysis/operational_daily_jobs_v1.py` 中 worker 同步执行 `self.executor(...)`。 |
| 反复历史计算 | `src/workbench_analysis/operational_daily_owner_v1.py` | `dates=parent.get('published_sessions',parent['dates'])+[day]`，再把依赖窗口加入 `required`；`src/workbench_analysis/operational_daily_ready_owner_v2.py` 继续调用 `owner.replay(..., context['dates'],...)`。`operational_owner_adapter_v1.py` 逐段 materialize Core/Profile/Sector/Market/Focus。 |
| 可观测性 | `operational_daily_jobs_v1.py`、`operational_daily_jobs_pg_r1.py` | 当前已有 `update_jobs/update_job_days/update_events` 和阶段 `checkpoint(day,stage,detail)`，但没有统一的证券级已完成/总数、每步时长、心跳和可供两端复用的具体进度合同。**应扩展现有 PG 表和日志，不另造任务框架。** |
| 托盘 | `src/workbench_desktop/tray.py` | “查看运行状态与最近错误”是状态对话框，不是持续日更进度；没有“查看日更进度”的直达入口。 |
| 原生 PG Owner | `src/workbench_db/v4_operational_owner_pg_closeout.py` | 以 `kind+fact_key` 读取整份 PG JSON 载荷再做 Python 投影，说明 PG-only 不等于已经具备逐股票 SQL 查询索引。 |

**用户提供的本机实测（不是本文重新实测）**：普通 HTML 0.07 秒、状态 API 0.18 秒、PG 简单连接查询约 0.15 秒，但 `context/stocks/home` 均超过 20 秒超时；同一 Python 进程内日更运行，内存约 6.6GB；业务接口共享锁。暂时有力指向**代码请求路径、全量投影和计算共进程**，不足以认定 PG 本身是主要瓶颈。仍需各段计时，避免把所有慢都归咎于锁。

### 1.2 新股修复已经做了什么；什么仍然没有做

最新 10 月 13 日提交链：`6d1a55d` → `de2e64e` → `3713f64` → `5f322ba`。涉及：

- `src/workbench_analysis/operational_new_listing_r1.py`（新）；`src/workbench_desktop/source_adapter.py`；`config/v4_operational_new_listing_r1.json`；`docs/upgrade/V4_CURRENT_OPERATIONAL_NEW_LISTING_R1_20261013.md`。
- 代码能对已冻结的**当日两源行情中新增、此前身份池没有的代码**调用 BaoStock 单证券 `query_stock_basic`；**只有当 `ipoDate == day`、type=1、status=1、无 outDate 时**才追加新身份；一次最多 20 条新股。
- 新版本通过私有数据映射将新身份接入当日生成，未覆盖旧身份及 Head。提交证据显示 `SZ.301660`（证据标注“粤芯半导体”）于 10 月 13 日当日接入，身份数由 5,224 增为 5,225；新股首根 K 和当期部分周月指标边界已专项核验，8 个相关负例测试通过。
- **重要状态边界**：`docs/audits/v4_new_listing_daily_20261013_r1/RESULT.json` 明确为 `PASS_CURRENT_IPO_IDENTITY_AND_REAL_DERIVATION_ENTRY`，`daily_acceptance=IN_PROGRESS_NOT_YET_PUBLISHED`；**不能把新股接入通过等同于 13 号全市场已经发布**。
- 当前代码的 `admitted_identity()` 遇到 `deps['missing_codes']` 直接异常；遇到 IPO 日期不等于当天的新增行情代码也拒绝。**真正的换代码、跨期新出现代码以及旧代码从当日名单消失，仍可能让整个日更阻断**。

参考：[新股实现](https://github.com/NanOns/a-share-market-structure-research/blob/5f322baaca3f7acc2b8fe3179f2fcb5ace8753cc/src/workbench_analysis/operational_new_listing_r1.py)、[核心服务](https://github.com/NanOns/a-share-market-structure-research/blob/5f322baaca3f7acc2b8fe3179f2fcb5ace8753cc/src/workbench_service/core_product_server_r1.py)、[BFF](https://github.com/NanOns/a-share-market-structure-research/blob/5f322baaca3f7acc2b8fe3179f2fcb5ace8753cc/src/workbench_service/core_product_bff_r1.py)。

---

## 2. 新股及换代码：按“新增行情对象”处理，而不是每天做证券身份研究

### 2.1 用户认可的主规则（本轮明确执行）

**以规范化行情代码为日常更新中的主操作键。** 比较上一个有效的已发布证券集合与当日有效行情代码集合：

- `new_codes = target_valid_codes - accepted_valid_codes`。
- `still_codes = target_valid_codes & accepted_valid_codes`。
- `absent_codes = accepted_valid_codes - target_valid_codes`。

`new_codes` **只要有当日可信、唯一、非矛盾的真实 A 股行情，就应新增为研究对象**。无需证明它一定是“真正 IPO”，也无需先证明与哪个旧股票是同一家企业。即使是旧代码变成新代码，用户接受以**新独立行情对象**处理。

**“新行情对象”不等于“已确认 IPO”。** 界面应使用 `NEW_CODE_OBSERVED` / “新出现代码”；有上市首日来源事实才标 `CONFIRMED_IPO`。没有足够证据时标 `NEW_CODE_UNLINKED` / “代码变化关系未核实”，而不是以假定 IPO 去写 10 月 13 日的历史上市日期。

### 2.2 极简允许准入，不强制三方元信息一致

每个新增代码只需要满足：

1. 属于 V4 现有受支持 A 股交易所与板块；代码符合规范并在**当日真实的通达信和 BaoStock 交易代码/行情集合**中能唯一定位；至少一个可信完整的当日成交 K、另一源的 OHLCV 对应核对在现有精度容差内。**不一致时仅将该代码放入异常清单，绝不伪造数据**。
2. 当日业务数据确实属于目标交易日，关键 OHLC、成交量、证券代码不自相矛盾；停牌新标的允许按已确认证券池加 `SUSPENDED/NO_BAR`，不能要求一定有成交条目。
3. 以 `(exchange, normalized_new_code, first_seen_date)` 生成稳定新 `security_id`，重复运行得到同一 ID；当日读入只添加一条，不重复追加。
4. `query_stock_basic` 用来**辅助判定 IPO / 中文名 / 上市日**，不能成为新行情代码存在性证明的唯一通道；`ipoDate != target` **不应阻塞**真实存在的新行情对象。元数据缺失标 `METADATA_PENDING`，后台下一轮有界补齐。
5. 无需猜它是否由旧代码继承。历史数据默认从这个新代码可证明的首个有效行情日起积累；能证明有更早同代码行情时可将可验证历史作为该代码历史导入，但禁止用猜测跨代码拼接。

*若当天两源只有一个有该证券*：先区分数据源更新时间差/停牌/新上市未同步。**阻断该证券的“可用行情入库”，可以将其列入待补录；不应仅因单只新证券的来源差异阻断其余 5,000 多只证券的整日结果。** 对外必须明确本日身份覆盖未完整，不能把部分纳入说成全量齐备；按现有产品字段的完整性要求确定是 `PARTIAL_READY`（有明确异常清单）还是仍需等源，不能静默忽略。

### 2.3 `absent_codes` 不能直接等于退市，也不能阻断整日

昨日有、今日没有，**这只是名单差异，不是退市证据**。对这类对象：

- 保留稳定 ID 与所有已发布历史；不删除对象，不反写历史。
- 如当日完整证券池可证明暂停上市/退市，标相应可核实事实；若仅数据源缺失，标 `SOURCE_MISSING/NOT_OBSERVED`，不造一根停牌零成交 K。
- 当日对象“是否活跃/有行情”与“是否存在为研究实体”分开处理。不同日 `active_universe` 数量允许变化；不会因为某只消失而整体拒绝发布。
- 如果此前旧代码与今日新代码其实对应同一企业，先各自保留独立 ID、独立时序。未来只有公告、官方身份映射或可复核的数据链支持时才**可选**增添 `ALIAS/SUCCESSOR` 关系；不自动拼接、不以名字相似合并、不修改老序列。用户当前明确允许这种简化。

> 例：昨日 `X.000001` 存在、今天缺失且出现 `X.000002`，两者都应被记录为“代码状态变化”，但没有证据就不宣布同一证券。对于真实历史股票代码切换样本，可在离线专项测试验证结果，不能作为日常阻断条件。

### 2.4 与历史不足、统计分母和板块关系的接口

- 只有首日 K：MA5、MA20、MA60 等完整窗口因子 `value=null`，`quality=DATA_INSUFFICIENT`，最好附 `actual_count/required_count`；`ret1` 不得使用臆造的昨收。
- 第 2 日开始以真实可用交易日逐步计算。停牌与交易日计数按现有算法合同，不因优化私自更改 MA/收益口径。
- 首周/首月可以有截至 T0 的 `AS_OF_PARTIAL` OHLCV；**不要标记“完整周线/月线”**。
- 板块成员关系仍以通达信成员源为准，新代码没有归属关系就 `UNKNOWN/UNMAPPED`；不能因为名称相近擅自归入行业/概念。
- 市场宽度、板块分母、Focus 资格：按**当日可验证有效池**计算，并披露 source missing / unmapped 数量；不得由于老 Universe 固定数量而硬写 5224。

### 2.5 建议直接改动

| 文件 | 动作 |
|---|---|
| `operational_new_listing_r1.py` | 将 `validate_basic` 拆为 **行情准入**、**元数据增强** 两步；允许 `NEW_CODE_UNLINKED`；新增 `absent_codes` 非退市处理；移除把 `ipoDate==day` 用作所有新代码唯一准入条件；保留当前 IPO 快速路径。 |
| `source_readiness_v2.py`、`operational_daily_executor_v1.py` 相关接线 | 用显式 `new_codes/absent_codes/invalid_codes` 和域级质量状态，不再把“与昨日代码集合不完全相同”当作全系统硬错误。 |
| `operational_daily_owner_v1.py` / `operational_daily_ready_owner_v2.py` | 当前日期构造对象池时允许新增、保留旧身份，切分有行情/停牌/缺源状态；新股早期窗口正确不足。 |
| `config/v4_operational_new_listing_r1.json` | 改成版本化“每日新增代码接入规则”；原严格 IPO 规则仍可作为 metadata 标记，**不应成为唯一业务总闸**。 |
| 读接口 / 前端 | 标注“首次观测日期、确认的 IPO 日期（可空）、历史不足、关联未核实”，用户看到新证券而不是系统阻断。 |

**止损式约束**：真实 OHLCV 核对、稳定 ID、T0 截断、重复代码、跨市场代码规范和原子发布不可删；多层“身份是否独立承认”的文书式关卡可以删。任何碰到少数代码异常的场景，都应尽量单对象降级并给出明细，严禁把“合格 5,000 多只全市场”一并卡死。

---

## 3. API 卡顿：短锁 + PG 真分页 + 轻量读模型，先救前端

### 3.1 真正的根因修复顺序

1. **为 `/api/v4/context`、`/api/v4/stocks`、`/api/v4/sectors`、`/api/v4/home` 加分段耗时记录**：Head/权限检查、PG connect、查询、解码、投影、筛选、序列化、锁等待、响应字节。连续 20 次本地请求，空闲与 DERIVING 中分别测。别先靠猜。
2. **`core_product_server_r1.py`：把 BFF 读、PG 查询、字段组装、JSON 编码及发送移出共享大锁**。只在缓存版本指针创建/更换时加小锁（毫秒级）；`head_token` 的只读缓存对象必须不可变，切换时原子替换引用，不要清空正在被其他读请求使用的对象。并发首个 miss 可用单飞构建，同版本只构建一次；失败不将未验证对象上线。
3. `context` 使用 Head 和轻量统计及已缓存的授权标识，不允许每次触发完整 `project('stocks')`、历史权威清单深度扫描；授权/PG 身份检查通过有界 TTL 或版本化连接池复用，避免**每个请求**新建 PG 连接、重算身份。（仍要在发布/重启/身份变化时严查。）
4. `core_product_bff_r1.py` 的 list/page/read 模式**不能先跑完整 `self.project(...)`**。正式 PG 中新增当前版本的轻量只读索引/物化投影：例如 `v4_read_index(head_token,trade_date,domain,entity_id,symbol,display_name,state,sector_type,sort_keys...,list_quality)`；列表仅查询必要列 `WHERE + ORDER BY ... NULLS LAST + LIMIT/OFFSET`，`COUNT(*)` 可单独求值或版本内缓存。支持已有过滤、排序和同页稳定 tie-break by entity_id。
5. 数据详情/来源字段不用混进 30 条列表。详情在点击时按 `(head_token,day,domain,entity_id)` 取一次完整字段；证据抽屉再按字段/来源取。主页面仅字段摘要；不要把巨大的 source/evidence JSON 逐页反复复制。
6. PG 正式读索引在**发布前**由生产者建立并验证，或由一次性、只读旧 Head 的本地迁移作业创建。HTTP 请求**绝不现场运行大型映射/创建索引**。索引键和字段类型采用已存在合同，不能悄悄改变数值、排序语义或 NULL 处理。利用现有 PG 表结构，避免为了改分页新增专用数据库。
7. 先切 `stocks/sectors/focus` 这几个最慢列表和 `context/home`，其他轻量接口按实测选择性改；历史日期按需索引，不需要一次性重建多年全部读模型。

### 3.2 前端改动

- `app.js` 板块重叠详情不再用 `for(offset...)` 自动抓取全部；首次只显示 20—30 条，点击“加载更多”才取下一页。历史 timeline/关联明细同理。
- 详情页图表、因子、来源、Focus 时间线、成员等改为“用户展开后再取”或首屏后低优先级加载。非当前 Tab 不请求。
- 搜索框 250—350ms debounce、取消失效的旧请求、请求版本切换检查。页面跳转不重复抓同一 T0 下相同的 `context`/静态元信息；保持原有日期参数及筛选。
- 防止大列表几千 DOM 节点；默认只渲染当前页。CSV 导出是**用户主动点击的独立批处理**，可以流式取全部页，不允许页面首开触发。
- 对大响应日志只记**字节数、耗时、错误码**，不在每次页面请求中输出几千证券完整内容。

### 3.3 建议性能验收阈值（个人本地项目，可根据首轮基线修正）

| 场景 | 初版验收目标 |
|---|---|
| 本地 `context` | 稳态 P95 ≤ 0.5 秒 |
| `stocks/sectors/focus` 第 1 页 30 条 | 空闲 P95 ≤ 1 秒；后台日更运行 P95 ≤ 2 秒 |
| `home` | 空闲 P95 ≤ 1 秒；日更运行 P95 ≤ 2 秒 |
| 同时 3—5 个业务请求 | 不出现串行排队造成的 20 秒超时 |
| 版本切换 | 一次请求只绑定一个 Head/T0/token；不混合两版数据 |

**阈值是整改目标，不是当前测试成绩**。测本机 loopback、20—30 次请求，记录 median/P95/最大值与 payload 大小；不要求复杂压测平台。重请求个别接口若超过目标，继续细化计时而非把整个系统卡住。

---

## 4. 日更重构：真正新增 T0，不要每次重算全历史

### 4.1 把“计算日期”和“可用历史日期”彻底分开

当前 `operational_daily_owner_v1.py` 的 `dates` 把历史已发布日期+当天一起交给 replay；`required` 为正确计算窗口补依赖数据是合理的，**但不能据此对 required 的每个历史日重新 materialize 全链**。

改成两个显式变量：

```python
# 示意，不代表当前库中已经存在这些函数
new_session = target_day
history_dependencies = accepted_history_window(new_session, algorithms)   # 只读，不重算
compute_sessions = {new_session}  # 普通日更唯一 T0
if source_revisions or algorithm_revisions:
    compute_sessions |= impact_planner(source_revisions, algorithm_revisions)
```

旧数值计算核心可以不动；把外部驱动改成**目标日生产 + 读取历史已发布状态/滚动窗口**。对于现存 Owner 要求全日 `CORE_REPLAY.json` 的接口，新增小型适配器合成“旧日指向已验收不变 Owner 绑定、新日指向新增 Owner”的引用集合，不能重新跑旧 Owner，也不能重写旧日成果来凑成一份文件。

### 4.2 每日应当确实完成的计算

| 模块 | 正常新增日处理（需要） | 不应该做的事情 |
|---|---|---|
| 来源与行情 | 获取当日 TDX/BaoStock、复权/公司行动变化、可交易代码集合、官方日历；验日期、数量和冲突 | 每天重复抓所有旧日期及重算旧日价格 |
| Core 与 MA | 当日每股 RAW/QFQ、MA5/20/60、量比/均量/涨跌幅/ATR/所需精确字段；历史只读窗口 | 把历史每个已发布日期重新计算全部 Core |
| Profile/结构 | 当日结构状态、价格位置、有效/失效、标签；读取昨日状态和足够历史 | 每天重算此前每个日子的完整结构 |
| Sector/市场 | 依据当日成员关系和当日个股结果计算行业概念、宽度、资金参与、相对强弱等，保留来源质量 | 全量重放所有旧板块日期；将最新成员关系说成历史 PIT |
| Focus/Forward | 昨日未完 Episode 今天继续观察、状态转换、今天到期的后继结算、当日新信号 | 重新遍历过去每个已结算日期并重复产出旧日所有 Episode |
| 周线/月线 | 从当日 K 增量更新当前周/月 as-of 部分棒和正式已完成周期，保留正确 RAW/QFQ 坐标 | 逐日重建所有历史周/月数据 |
| PG 发布 | 只写今天新增/必要修订；候选全链校验；CAS 切 Head；读回 7 入口同版 | 旧日无变化时批量覆盖旧结果；页面自己参与派生 |

*算法细节必须沿用现有合同*：如某因子需要之前 N 个**有效观察**而不只是 N 个日历日，必须从真实历史窗口读取；若公司行动引起复权坐标变化，不能拿旧坐标滚动 MA 冒充一致。

### 4.3 非正常情形：影响范围调度，而不是默认全量

建立简单的 `impact_plan`（JSON/PG 一行即可），记录 `reason/source_revision/affected_codes/affected_dates/affected_fields/affected_downstream`：

- **普通收盘新增日**：目标日期今天；影响当天所有有效股票、当天板块、市场、进行中的 Focus/到期 Forward、当前周月。
- **新股**：只补该新代码可验证历史/当天窗口 + 当天市场和相关板块分母；其他证券 Core 历史不动。
- **单个证券历史复权因子更新**：重算该证券从受影响原始日期起、按算法依赖传播到当前的必要日期/字段；对应日期的板块、市场、Focus/Forward 若确实依赖要一并重算；不能只改今天而留下历史坐标矛盾。
- **源行情单股历史纠错**：同上；先认定受影响输入键，再逆/顺依赖确定最小范围。
- **板块成员变更**：影响有证明的成员日期/受影响板块，不改所有证券 Core 历史。
- **算法版本变更**：仅该因子及依赖链历史重算；若影响全市场重要字段且确实无增量复用途径，才人工触发受控大批次回建。
- **Head/来源损坏、缺乏可靠老窗口**：只对受影响的对象或首个未完整缓存窗口回填；不可凭缺失声称历史已验证。必要时手动全量模式，而不是悄悄进入“日更”。

严格把 `RANGE_REPAIR/FULL_REBUILD` 显示为**非正常日更工作量**，避免用户看到“日更3小时”却不知道在全历史重算。

### 4.4 实现接口与工作清单

涉及 `operational_daily_owner_v1.py`、`operational_daily_ready_owner_v2.py`、`operational_owner_adapter_v1.py`、`operational_daily_executor_v1.py`、`operational_daily_periods_v1.py`、`operational_daily_jobs_pg_r1.py`、当前 PG Owner 和 period/focus 发布器。

建议新建最多 **2—3 个很小的模块**，例如：

- `operational_increment_plan_v1.py`：读 Head / 源修订事实，决定 `APPEND_DAY/RANGE_REPAIR/FULL_REBUILD`、计算对象、日期、来源/算法指纹、需要读取的历史窗口。
- `operational_increment_runner_v1.py`：调用**同一现有算法内核**生成当前 T0 的 Core→Profile→Sector/Market→Focus/Forward→Period；必要时引用旧日不可变 Owner；以 PG 候选结果输出。
- `operational_increment_parity_v1.py`（可以只放 tests）：对固定最近日期验证增量结果与旧全量结果在参与字段上的值、NULL、质量、前后引用、Digest、周期边界一致；差异必须报告，不能“肉眼看起来差不多”就算过。

**不要**额外建立一套 V5 因子框架、通用 DAG 引擎、外部任务平台或把计算结果写进新的数据库。优先把重复循环和数据流拆开，复用已验证数值内核。

### 4.5 性能目标的正确口径

分别报告 `source_wait`、`source_capture`、`derive_core`、`derive_profile`、`derive_sector_market`、`derive_focus_forward`、`derive_period`、`pg_publish`、`http_readback`。

- 优先目标：**数据源可用后常规单交易日派生+发布≤15分钟**，争取 5—10 分钟；这是优化目标、不是未经测量的承诺。
- 如果第一次测量尚达不到，至少证明计算日期数从 N 个旧日变为**仅新日**，并列出真正剩余热点。
- 来源方延时不计入算法耗时，不要用 3 小时的网络等待掩盖算法耗时；复权修订/全量重建单列工作量，不与常规日更混为一谈。

---

## 5. 计算与 HTTP 隔离：本机只需两个进程，不是微服务

最终进程安排：

```text
DaAV4.exe / Desktop + Tray
   ├── HTTP Reader 127.0.0.1:28765  ── SELECT ──┐
   │    - 启动后只绑定已发布 Head               │
   │    - 轻量只读 PG 索引、按需详情             │ PostgreSQL（同现有实例）
   │    - 进度/健康只读                          │  - 已发布正式数据/索引
   └── 本地 Daily Worker 子进程 ── UPDATE ──────┘  - 日更任务/进度/候选
        - 原已配置 BaoStock/TDX 源
        - 单写者 advisory lock
        - 生成候选，不挤占网页进程的 Python GIL
        - 经过数值检查和 CAS 发布
```

- Windows 可采用 `subprocess.Popen` 启动同一 EXE 的专用 `--daily-worker` 子命令（打包版本）或开发模式 `python -m ...`；**不用新安装服务、容器、消息队列、额外守护进程**。
- 子进程不再创建托盘、不绑定 28765、不重启 HTTP；进度通过 PG 表传递，管理端只作调度、显示及有限控制。
- 原有 PG advisory 单写者锁仍生效；子进程退出、崩溃、Windows 退出后状态/未发布候选可恢复；`job_id+target_day+mode+source_revision` 幂等。不得发生跨两个进程都认为自己已获得 writer 锁的竞态。
- 保留正常的“安全停止/取消发布前任务”语义；用户关闭应用时不要无提示强杀正在提交 Head 的发布动作。
- 计算侧使用独立 PG producer 角色，HTTP 使用只读 reader 角色；不要给前端 API 写表权限。

**快速交付建议**：先上线锁与真分页（解救当前卡顿），再整合 Worker；不要为了等 Worker 的所有细节导致页面继续 20 秒超时。开发阶段用源码进程测试，不需要每改一个文件打包。

---

## 6. 统一日更进度：复用 PG，前端和托盘一个口径

### 6.1 只加一个小进度模型

`update_jobs` 和 `update_job_days/update_events` 已存在；建议在现有 jobs schema 加 `update_job_progress`（或给 `update_job_days` 添加少数字段），不要起第二套“工作流管理平台”。示例：

```json
{
  "job_id":"...",
  "mode":"APPEND_DAY",
  "target_trade_date":"2026-10-13",
  "last_published_trade_date":"2026-10-12",
  "stage":"CORE",
  "stage_state":"RUNNING",
  "processed":2350,
  "total":5225,
  "unit":"securities",
  "started_at":"...",
  "stage_started_at":"...",
  "last_progress_at":"...",
  "elapsed_seconds":null,
  "stage_elapsed_seconds":null,
  "eta_seconds":null,
  "recent_message":"正在计算当日 Core",
  "error_code":null,
  "error_detail":null,
  "head_unchanged":true
}
```

Elapsed 允许由 API 用数据库时间戳实时计算；未知 ETA 为 null，**禁止伪造预计完成时间**。每完成 100/200/500 个对象或每 1—3 秒刷新一次持久化进度即可，不要每只股票 commit 一次。长时间无进展显示心跳/可能卡住。

端点：`GET /api/v4/operations/daily-update/progress`（现有 API 前缀和权限规则复用），`GET /api/v4/operations/daily-update/status` 仍保持兼容。进度查询不得争用业务全局锁；单次读一行 PG 记录，不需解码整个 Owner 产物。

### 6.2 页面与托盘

- `/v4` 首页右上角一个“日更状态”入口：上次发布日、当前目标日、当前阶段、进度条/真实计数、耗时、最近更新时间、错误。点击可看各阶段历史耗时及已完成日期。
- 详情页 `诊断→日更` 显示：采集 → Core → Profile → 板块/市场 → Focus/Forward → 周/月 → QA → PG 发布 → HTTP 读回，失败停在具体位置。
- 托盘新增“查看日更进度”菜单项，直接打开 `/v4/research/diagnostics?tab=jobs` 或轻量状态窗口，**从同一进度端点读数据**；托盘标题可以显示“日更 Core 45%”，但后台真实无 total 时只显示阶段，不要假进度。
- 正常计算不持续打扰用户；只在发布成功、真实失败或需要人工处理时显示系统通知。
- 页面查看历史时，必须显式告诉用户“目前正在生成 13 号，页面仍显示已发布 12 号”，避免误以为卡死。

---

## 7. 高效修复实施顺序：少分支、少包、少验收

**所有修复统一在最新 V4 工作分支继续，不要再复制出多个互相偏离的仓库或重复跑旧 22 阶段。** 单次总体合并、一个核心任务卡，Codex 内部按下表顺序提交即可。

| 次序 | 工程包 | 必改要点 | 出口检查 | 是否需要 EXE 打包 |
|---|---|---|---|---|
| **A** | `HOTFIX-API` | 计时、业务请求移出 RLock；context 快速化；小列表 DB 查询/延迟重对象 | 3—5 并发 API 无排队；现有 T0/Token 不变 | 否，源码调试；生产安装最终统一一次 |
| **B** | `NEW-CODE` | IPO/新代码统一接入；`absent_codes` 非退市；代码变更当新行情对象，缺历史标不足 | 1 新股 + 1 模拟换代码 + 1 消失代码 + 1 来源冲突；不整日失败 | 否 |
| **C** | `APPEND-ONLY` | 仅计算新增 T0，复用昨日已发布窗口/Owner；按影响范围重算 | 近期 2—3 个交易日增量/全量核心数值、状态、周月、PG 绑定一致；未改旧日 | 否 |
| **D** | `WORKER+PROGRESS` | 日更计算独立进程；复用 PG 任务表；进度页面+托盘 | 计算期间浏览不卡；故障不损已发布 Head；进度能直接观察 | 否 |
| **E** | `ONE-RELEASE` | 合并专项测试、打包一次、切换原 28765、实测新增日完整发布和页面使用 | 用户实测通过；交付简洁报告 | **是，仅此一次** |

说明：A 与 B 可并行编码，C/D 可分开设计，但**整体只进行一次最终 Windows 生产打包**。若发现会污染 Head/误发布的 P0 错误，则先修再切，不为追求速度破坏唯一真实数据。

### 7.1 当前 10 月 13 日日更正在计算：不要先打断它

用户提供 20:21 后续对话称 Core 重放执行到 10 月 9 日、预计耗时较长。最新 GitHub 审计仅证明此前 `DERIVING` 已开始，**当前是否完成须以本地 PG job/Head 为准**。

- 不要求立即停掉正在执行的合法日更；允许 13 号旧路径最终完成，保留其真实耗时作为慢基线。
- 修复先在 G 盘隔离工作区做源码运行，不去抢生产 28765、覆盖正在写的 source freeze 或强制重启。
- 发布/停机/重启安排在安全边界，只用一个最终安装包切换。
- 旧路径若错误退出，允许仅从未完成 checkpoint 恢复，严禁为“重新测试”无意义重放 9 月所有日期。

---

## 8. 超轻量测试规范：尽可能 1 次完整试跑 + 1 次打包

### 8.1 三档门禁，不搞商业式逐阶段冻结

**T1（每次修改，目标几十秒）——纯单元/小构造：**

- Python import/compile + 变更模块定向 pytest；典型为新增代码判别、`missing_codes`、重复代码、空历史 MA、分页 SQL null-last/稳定排序、锁范围、增量影响计划。
- 不连外网、不跑真实全市场、不启动桌面、不生成 EXE。不要求跑全库 7,288 项。

**T2（每个工程包合并，目标数分钟，按证据可延长）——小型真实数据回放：**

- 使用一份 G 盘**固定 13 号已冻结真实输入**（不要每个用例重新抓 BaoStock/TDX），在独立 PG schema/测试目录验证；新股用 `SZ.301660`，代码变更/消失用可控合成差分；再取 30—100 个含异常样本的证券验证 Core、结构状态及依赖链。
- 真实当前 PG 只读；测试 schema 与生产 schema 分离。限制本地日志大小和重复证据。SQL 分页至少验证搜索、不同排序、过滤、NULL、末页、日期参数、token 稳定。
- 增量计算对最近 2—3 日做一次独立全量参考值**只在测试环境、只产一次**；把 reference 持久化到 G，后续代码小改只重跑受影响模块并对比缓存的参考结果。**只要算法版本/输入变化就重新生成相关参考，不可拿陈旧 reference 充数。**

**T3（最终一次打包前/后，目标一次验证）——本机真实闭环：**

1. 在源码/隔离副本完成**一轮**完整新增交易日的：Core→Profile→板块/市场→Focus/Forward→周月→PG 候选→QA；确认所用输入真实且未跨 T0。和 T2 参考比对。
2. 仅当 A—D 通过之后，**一次** PyInstaller/Windows 构建，确认必要模块和资源会随包进入；禁止在每个小改动后自动重新生成 1GB+ 包/多套测试目录。
3. 原进程到达安全边界再替换；原 28765 启动后测 6 大导航页面、业务 5 个核心接口、查询分页、一个新股详情、日更进度、托盘入口。
4. 在**计算同时运行**时采样接口 20—30 次，看 P95、超时、CPU/内存、PG 慢查询；确认旧 Head 在发布前保持不变，新 Head 发布后所有关键接口相同 `T0/token`。
5. 若问题只在前端样式/文字，不再重打所有 Python 包；若问题是运行时代码，打包前源码端先修完并定向验证，必要时额外一次补丁包（注明原因），禁止进入“测试→打包→失败→重复全量”死循环。

### 8.2 “保留/取消”一览

| 保留且必须通过 | 可以取消或延后 |
|---|---|
| 原始行情真实性、日期/代码/复权校验；核心数值一致性；完整性状态；上市前无伪历史 | 每个小改动反复拉取同一天所有数据 |
| 原生 PG 一致性、单 writer、Head 原子性、业务 HTTP 同版、失败保留 last-good | 每个局部小修重复 7,288 项历史全量回归 |
| 本地实际“新增日一次”运行 + 计算期间页面实测 | 每个阶段重复做新安装包与 Windows 重启 |
| 修改范围覆盖的定向 pytest、一次全链数值基线对照 | 多份高度重复的证据 JSON、全套大型 ZIP、逐文件机械 SHA 表 |
| 小而清楚的修复前后耗时表、变更文件清单、唯一错误列表 | 非现役旧 V1/V2 功能验收、商业压测平台、外部多轮独审 |

### 8.3 最少必须覆盖的功能测试（十个用例即可形成第一轮闸门）

1. 当天确有新股（真实 `SZ.301660`）：出现一条独立稳定对象，首日无 MA5/20/60，周月为部分周期。
2. 昨天无、今天有，但 metadata 上市日期早于今天：作为 `NEW_CODE_UNLINKED` 接入，不因不是 IPO 阻断，历史不乱接。
3. 昨天有、今天缺失：保留历史，标观察缺失/可证的停牌，不造退市，不阻断全体。
4. 同一交易日重复代码/两来源 OHLCV 不一致：只报该证券异常，不接受伪造 bar；发布质量有明示。
5. 新股第二日、第五日、第二十日、第六十日：窗口依赖按算法合同逐步可用，不凭日历猜有效样本量。
6. 普通 1 日增量：Core/Profile/Sector/Focus/周月的当日值与已存独立全量参考完全按合同一致；旧日 digest/Owner 不变。
7. 复权/行情修订：仅受影响代码日期及下游重算；不会泄漏旧复权坐标，不会“全市场每日重建”。
8. `stocks/sectors/focus` 30 条 SQL 分页：过滤排序正确、`total` 正确、NULL 末尾、稳定排序，不触发全量 `project()`。
9. 日更 Worker 占用 CPU 时：3—5 并发 business API 无原先 20 秒堵塞，页面依旧显示 last-good。
10. 任务中断/PG 错误/重启：展示具体进度和错误，Head 不意外改变，重试不生成重复 ID 或双 writer。

## 9. 测试、版本、打包的“减负规则”——Codex 必须遵守

1. **不允许把旧全系统回归作为每次进入下一修复阶段的必要门禁。** 仅变更所涉及的现役模块与其必要依赖，先跑 T1/T2；最终仅一次 T3。
2. **不允许每个模块执行后都要求用户等待打包。** 开发运行用现有 Python 解释器、隔离副本和 PG 测试 schema；四包合并后统一正式 EXE。
3. 对不可控 BaoStock 网络，先采集一次冻结输入供重复测试。外网失败与算法失败分列；失败的测试应尽快定位到实际阶段，不重复前序所有工作。
4. 源码修改过程每次记录一行 commit/文件变化/针对性测试结果即可；无需生成大量同内容 `R1/R2/R3` 重复报告。证据只保存**输入版本、核心数值 diff、关键错误、性能分位、正式 Head 发布记录**。
5. 不许将 2026-10-13 的“旧算法跑完但耗时很长”说成真增量已通过；不许把 `DERIVING` 说成 `PUBLISHED`。
6. 前端/托盘不必每个按钮都做浏览器截图验收；最终一次人工点开六入口 + 真实 3—5 个业务点验证就够了。截图只对异常保留。
7. 每次正式发布只做“代码版本/旧 Head 备份/新包运行/当前业务同版”的轻量必需保护。用户不要求大型回滚演练，**但不可删除原包和 last-good 数据**。
8. 只处理 V4 现役代码；历史兼容/旧阶段可留，但不为清理它们阻断当前日更整改。范围外产品预测、严格历史 PIT、交易下单不在本次任务。
9. 单份主 MD 总结全部任务进度；仅当出现真实重大错误或用户改方向才增加版本，不要无意义地每天出十几份任务卡。
10. 所有生产代码和证据依据 `AGENTS.md` 要求提交、推送到当前分支。**Git push 不等于本地安装完成**：最终报告需列出源码 SHA、EXE 包版本、真实端口/进程、最近正式 T0、普通日更耗时、API 性能结果。

---

## 10. Codex 执行命令（可以整段交给本地 Codex）

> 读取并执行本文。当前最高任务不是补 V4 功能，也不是继续新股身份审批，而是解决 **生产页面慢、伪分页、全局大锁、共进程、伪增量日更、IPO/换代码阻断和进度不可见**。  
> 基线 `codex/v4-full-closeout-20261012 @ 5f322baaca3f7acc2b8fe3179f2fcb5ace8753cc`；执行前读取最新远端 HEAD，若前进先合并并标明基线变更。不要用默认 `main` 或旧 `codex/v4-system-reform`。  
> 遵守本方案 0—9 章、`AGENTS.md` 与 G 盘工作约束。先检查 13 号生产日更是否仍运行，**不强行停止、抢锁或重发同日旧 Head**。  
> 优先落地 A（锁/分页/缓存）和 B（新行情代码入库），然后 C（当日增量）与 D（worker+进度），最后 E 一次性打包部署。支持并行研发，但避免并行抢同一生产数据。  
> 数值内核、PG、既有 Core/画像/板块/Focus/Forward、日期边界、原子发布不降级；保留正式输入及 last-good。  
> 每包只跑受影响的快速测试和固定数据专项验证；**不要重复全部旧阶段测试，也不要四包各自打包一次**。最后执行一次真实新增日端到端和 Windows 打包/部署。  
> 输出唯一主报告：本轮修复 SHA、修改的文件、10 项用例状态、增量与全量实际比较、日更各阶段耗时、空闲/计算期间 API median/P95、实际发布日期及未完成点。  
> 不能通过的事项明确报 BLOCKED 和最小复现；不要为通过而擅自减少数据、掩盖错值、改写历史或关闭功能。

## 11. 用户最终验收：只看 6 件事

1. 今天有新股、新代码：正常出现在研究对象列表，历史不足正确显示；没有莫名其妙“身份待审批”把全日堵死。
2. 每日只计算新交易日：普通日更日志清楚显示 `APPEND_DAY: 1 trading day`，不会出现“重新计算 9 月 28 日至今全部已发布日”。
3. 日更正在计算时：打开首页、股票、板块和 Focus，操作仍流畅，无十几/几十秒转圈。
4. 进度能直接看到：阶段、已完成/总证券、耗时、当前 T0、错误和最近进展，页面与托盘口径一致。
5. 算法与数据没缩水：MA5/20/60、画像、市场、板块、Focus、周月和所需字段还在，和全量参考结果一致。
6. 开发过程高效：局部测试快、完整测试只在整合时做一次，**正式 EXE 最后统一打包一次**；结果确实能从本机 28765 看到。

**一句话最终定位：V4 已切换并具备既定功能，但现在要把“多日重放式研究程序”改成“真正每天可高效使用的个人本地研究工作台”。不要商业化工程过度设计；保留数据真实性、算法数值、PG 单一主仓和原子发布四条硬底线，其余流程以最小有效验证收敛。**

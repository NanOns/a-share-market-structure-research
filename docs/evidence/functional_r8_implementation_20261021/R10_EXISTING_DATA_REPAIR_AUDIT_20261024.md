# R10 V4 存量数据修复专项审计（2026-10-24）

## 阶段合同与结论

**状态：`PARTIAL_REPAIR_NOT_ACCEPTED`。** 本报告只接受源码级消费者隔离与可复核的存量清点结果；不接受新增日期、外部补采、正式 Head 变更或以 UNKNOWN/跳过代替数值修复。工作分支 `codex/v4-unified-development` 的审计起点为远端 HEAD `2b08972c3727f6cd9358ad9833794f66f351cc8f`。本次先读取 Google Drive R10 任务卡（ID `1SqPW4Y64s85EzSJwY7wwoptnQKe_YVbL`）、远端分支最新 `R10_V4_REAL_FUNCTIONAL_CLOSEOUT_REPORT.md` 与配套 Evidence，并查阅适用的 V4 R8 修复规范、运行性能修复规范、R2 综合修复计划及项目规范。

本轮停止了新增采集、SourceIngress 写入、新交易日 Owner/Core 生成及自动日更。未访问外部行情源，未改变正式 Head，未物理删除数据或证据，也未启动、停止或重启服务。为修复三日存量消费者读投影，按现有开发授权对 PG 仅执行同 token/date ReadIndex 追加式重建；原有 schema/version 均保留，并在 G 盘留存切换前 authority 精确字节备份。扫描器阶段 0 沿用 R10 已记录的 `FULL_PASS` 回执；本轮未运行扫描器。

## 可证实的问题与修复

### 1. 13 份旧 Market 候选及消费者隔离

R10 机器证据逐项列出 13 份 `market_owner_candidate_v2.json` 及 SHA-256：10/19 三份记录 `breadth_common_count=5223`，10/20 三份与 10/21 七份记录 5224。绑定的历史 universe 文件对对应比较日 10/14、10/15、10/16 的四板块范围均无成员；当期 Core 虽有约 5,225 行，但未与该历史成员集合逐项证明相同，不能替代其分母。上一轮独立 A/B 复算的 10/19 旧 Core 分母结果为 5,225 个身份、5,223 个当前交集、5,208 个可计算样本；正收益指示器均值 0.2465437788，SIGN 均值 0.5057603687。历史 universe 可用身份数为 0，因此这些数值是**旧候选诊断值**，不是可接受的正确历史结果；本轮不伪造替代数值。

确认的消费者链为：PG ReadIndex `/api/v4/home` 快照包含 Market `row/raw/regime/sources` → BFF R2 预建响应路径只追加 `candidate_trend_review`，未核验或清除其他旧轴 → Home 页面将四轴和 Evidence Drawer 直接渲染。`/api/v4/radar/priority?view=candidate` 另行暴露候选 Market 风险对象；其候选 API 保持非接受标记。六入口研究 UI 与兼容 UI 均消费 Home Market 轴。

本轮在 BFF 增加同日 Market 衍生检查：必须为 `READY`、日期吻合、有 Core 与限价 Owner、非空分母/可计算数、来源 digest 完整，并且响应四轴值与独立衍生值一致。任一条件不满足，或复算异常时，API 将四轴、压力方向、原始数值及综合状态全部标成 `SOURCE_INCOMPLETE/UNKNOWN`，保留 `sources` 供追溯并明确标记 `QUARANTINED_PENDING_DATED_SOURCE_AND_RECOMPUTE`。R2 ReadIndex 路径与 BFF 现场构造回退路径都执行该门禁；风险族结果不会在后续覆盖隔离状态。旧 PG 原始快照不覆写；通过新 sealed ReadIndex 版本承载修复后的消费者投影，保留旧版本及其历史证据。

以现存 10/21 候选根和同一只读 PG 连接，在新 Python 进程内运行修复后 BFF `/api/v4/home` 读回 10/19、10/20、10/21，三日均返回 HTTP 200、所有 Market 轴及轴质量均为 `UNKNOWN/SOURCE_INCOMPLETE`，并给出 `R10_MARKET_HISTORICAL_UNIVERSE_DATE_SCOPE_EMPTY:2026-10-14`。冷首请求 30.234 秒，随后同一进程的 10/20 为 4.156 秒、10/21 为 1.107 秒；后两次命中同一进程的派生缓存，不能当作冷启动延迟预算。发现轴隔离后 `field_quality` 仍保留旧 `OBSERVED` 的元数据矛盾，已在同一修复中改为 `SOURCE_INCOMPLETE`，并加入回归断言。

为让未重启的 28766 也读取隔离结果，在候选 workspace `G:/codex_tmp/v4_daily_candidate_chain_20261020` 对 10/19、10/20、10/21 追加三个 R2 ReadIndex 版本，使用同一 token `14ee0cf87a46f810b52295a8d42c4bbda391fd0fe49f4cb3457a1620067ad378`。新 schema 分别为 `v4_c94ffc1071e8bf4c7d526524de1a1ac1eee38912c76a3e55c5ae2853`、`v4_2d9e9ce6c601c0d196a2f80a395300a3ff1d61d40934420652ba7aeb`、`v4_36b669df3ca8764b591d83d06cc6ce53482f35eff3cb1e87ee86092c`；新行分别为 9,615、6,910、10,012 `read_items`，各含 3 条 `read_responses` 与 1 条 `read_versions`。PG 先封存新版本并逐行回读通过，随后原子更新 R2 authority 指针。切换前 authority SHA-256 为 `38c8f9e79c2239513dffdc8c94f73d26acacaa695061e794d3ad8f52ac8b20e2`；原字节备份位于 `G:/codex_tmp/R10_READINDEX_AUTHORITY_R2_PREWRITE_20261024.json`，SHA 相同；切换后 authority SHA-256 为 `b3d4528d8eb737f66cca5b00969cf246db282e24f64ce2a85a8a7f492ca1ae4b`。10/20、10/21 旧版本仍在 revision history；10/19 在当前 token 下原本没有 R2 绑定。回滚只需把 authority 精确恢复到备份字节；新 sealed schema 保留为不可达证据，不删除。

Home 页面实际加载的 `/v4/assets/app.js` 返回 HTTP 200，源码按 `d.market.row[k]` 显示四轴；当前 API 又返回 `SOURCE_INCOMPLETE` 和 `UNKNOWN`，所以页面投影读取的是隔离值。初稿未完成浏览器视觉验收；本次追记已改用 Codex 内置浏览器（IAB）在 28766 打开 10/20 页面，截图与无障碍树均显示股票 5,224、板块 400、雷达 607，市场四轴均为“来源不足”。未使用本机浏览器。

**修复前 → 修复后**：无同日复算证据时，旧 28766 返回 10/21 `READY / FACT_AXES_OBSERVED_COMPOSITE_UNACCEPTED`，轴值为 `DETERIORATING / THIN / LOW`，没有隔离标记 → 新 sealed ReadIndex 的 10/19、10/20、10/21 都返回四轴 `UNKNOWN`、轴质量和综合状态 `SOURCE_INCOMPLETE`，并带隔离标记和精确缺失日期。随后对原 28766 只读读回三日均获同样结果，不需重启。旧 PG 版本和来源证据仍保留；线上进程仍运行旧代码，但读取新的只读投影。

正确重算条件是获得可验证、日期匹配且覆盖既定四板块的历史身份集；以该集合与当日/比较日行情和涨跌停 Owner 逐身份交集复算；合同参数、阈值与公式版本一致；记录输入绑定、覆盖分母、缺失/未知分类、时间角色和输出 digest，并由独立数值对账确认。当前历史集合为空、10/22–23 同日身份/成员 Owner 缺失、10/23 日线及因子缺失，故这些候选只可隔离，不能重算为已接受值。

### 2. 全库和日期盘点（只读）

通过 `127.0.0.1:5432/market_research` 的只读事务，对写入前 108 个 `v4*` schema、472 张表完成 `COUNT(*)` 与可识别交易日列分布，合计 4,858,619 行，无查询错误。关键基线分布：

| 区域 | 对象数 | 行数 | 解释 |
|---|---:|---:|---|
| canonical `v4` | 125 表 | 3,494,748 | 包含 History、Forward、Owner、ReadIndex、作业和迁移记录 |
| research 快照 | 23 schema / 138 表 | 516,134 | 多版本候选快照，不等同正式发布 |
| ReadIndex 及读响应 | 42 个候选命名空间，另含 canonical 表 | 394,237 | 存在多代/多 token 读投影；保留，不做清理 |
| SourceIngress | 2 表 | 38,981 | 38,974 日线、7 个收据，日期为 10/15、16、19、20、21、22、23 |
| History/Forward 附加 schema | 4 表 | 21,859 | 多种迁移/候选归档 |
| 其他候选/运维记录 | 其余表 | 392,660 | 包含 31 个 Owner 版本、18 个 Owner payload、13 组 Owner 行及迁移证据 |

服务上下文中的已发布/可读日期为 2026-09-28、09-29、09-30、10-08、09、12、13、14、15、16、19、20、21；SourceIngress 还含 10/22、10/23，但这两日没有获准继续生成 Owner/Core。canonical V4 的历史版本记录覆盖 9/28、9/29、9/30、10/08、09、12、13、14、15；Priority、Risk 与 Sector Lifecycle canonical Owner 当前覆盖 10/13–15。10/20、10/21 已存在的开发候选 Priority/Lifecycle Owner 曾由 R10 做过 digest/行数只读核验，但不能据此推断所有日期和所有业务域已复算通过。

canonical `market_universe_snapshots`、`market_universe_snapshot_rows`、`publications`、`publication_heads` 均为 0 行；当前没有 canonical 市场发布行可安全回写。PG 存在多个 token/hash 命名空间下的 Owner 与 ReadIndex 候选，未将其合并为正式 Head，也未清理或删除。

ReadIndex 追加后再次只读精确计数：111 个 `v4*` schema、481 张表、4,885,168 行。净增仅 3 个内容寻址 ReadIndex schema、26,549 行；canonical `v4` 数据及所有 Owner、Publication 和原始来源计数未变。

### 3. 原因分类及尚未闭合范围

| 现象 | 分类 | 证据/处理 |
|---|---|---|
| 10/14–16 历史四板块比较 universe 无成员；10/22–23 同日 Identity/Member、10/23 行情/因子缺失 | **来源缺失/来源覆盖不足** | 保留原始文件与 SHA；不外部补采、不用 Core 替代、不生成新日期 Owner |
| 13 份 Market 候选的 5223/5224 分母与合法历史 universe 不符；ReadIndex 仍传给消费者 | **可证实计算/流程缺陷** | 修正比较日与四板块集合校验逻辑已在 HEAD；本轮补齐 BFF 全轴失败关闭及回归测试；旧 PG 快照只读保留 |
| D0 cutoff/seal、D2 冻结失效锚、Focus Priority 排序、Market 趋势引用/复合环境、LIVE Forward cohort 等无授权/完整版本合同 | **业务合同缺失** | 不生成数值，不以 UNKNOWN 或通过门禁替代合同；分别保持未发布/未授权 |
| 10/22–23 未生成 Core/Profile/Sector/Priority/Focus/Forward/ReadIndex；历史日期跨域数值逐行对账未完成 | **本轮范围未验收** | 未把缺数据描述为计算错误；亦未声称全日期业务链正确 |

跨源 Amount 差异和 139 个供应方生成关系样本仍按既有审计记录保持未证实状态；TDX 原始金额仍是当前权威，未用外部值覆盖。S02 正收益指示器与 SIGN 的业务裁定依任务卡保持独立；不把候选公式对账升格为正式接受。

### 4. API、页面与事务/恢复

只读核验：28766 `/api/v4/context` 返回 T0=2026-10-21 和 13 个可读日期。重建前线上 Home 10/21 返回错误市场轴；10/19、10/20 现场计算读取曾分别等待超过 30 秒。重建后三日线上 `/api/v4/home` 均返回 HTTP 200、隔离值及精确原因；一次批量读回约 3.8 秒总耗时，不作为独立 P95 样本。`/v4` 页面与 `/v4/assets/app.js` 均返回 HTTP 200，前端源码读取 `market.row` 四轴；未取得浏览器截图。PG 在 5432，28766 为 Python PID 52916；28765 无监听。`Codex-V4-OperationalDaily-28765` 任务已停用（`Settings.Enabled=false`、`NextRunTime=null`）；未启动或重启服务。

PG 写事务范围为三个新 ReadIndex schema：在事务内写入唯一版本、逐域条目、三条 API 响应并封存，事务提交后逐行回读；所有校验通过后，再原子更新候选 workspace R2 authority。权威文件已在写入前做精确 SHA 备份，可恢复指针；旧 PG schema 未覆盖、未删除。尚未实施故障注入或重复执行，因此事务中断和幂等重试仍需专门验收。未对 canonical Owner、Publication 或业务结果表做写入。

## 本轮续修：全日期 Owner 对账、10/20 ReadIndex 二次修复与事务恢复

起始 remote HEAD 更正为本轮 fetch 后确认的 `2b08972c3727f6cd9358ad9833794f66f351cc8f`；第一版证据文件记录的 `283a264...` 是过期值，现同步更正。候选 Head token 为 `14ee0cf87a46f810b52295a8d42c4bbda391fd0fe49f4cb3457a1620067ad378`，候选 Head 文件 SHA 与各 Owner 文件 SHA 均在新增 [全日期独立对账证据](R10_ALL_DATES_RECONCILIATION_EVIDENCE_20261024.json) 中逐项记录。以下是 13 个已发布候选日从原始 Owner 字节独立流式解析的结果：

| 日期 | Lifecycle/Core/Profile 行数 | Sector/Rotation 行数且身份集相等 | D0 TRUE/FALSE/UNKNOWN | D2 行数/重复 | Forward episode | Event | 当前 token R2 | Home 页面 stocks/sectors/focus/radar |
|---|---:|---|---|---:|---:|---:|---|---|
| 2026-09-28 | 5222/5222/5222 | 400/400 相等 | 114/0/5108 | 5222/0 | 2477 | 182 | 有 | 5222/400/1178/1045 |
| 2026-09-29 | 5223/5223/5223 | 400/400 相等 | 190/0/5033 | 5223/0 | 2477 | 393 | 有 | 5223/400/1717/556 |
| 2026-09-30 | 5224/5224/5224 | 400/400 相等 | 175/0/5049 | 5224/0 | 2477 | 393 | 有 | 5224/400/2152/442 |
| 2026-10-08 | 5224/5224/5224 | 400/400 相等 | 150/0/5074 | 5224/0 | 2477 | 409 | 有 | 5224/400/2477/393 |
| 2026-10-09 | 5224/5224/5224 | 400/400 相等 | 274/0/4950 | 5224/0 | 2805 | 913 | 有 | 5224/400/2805/365 |
| 2026-10-12 | 5224/5224/5224 | 400/400 相等 | 164/0/5060 | 5224/0 | 3025 | 340 | 有 | 5224/400/3025/311 |
| 2026-10-13 | 5225/5225/5225 | 400/400 相等 | 180/0/5045 | 5225/0 | 3151 | 560 | 有 | 5225/400/3151/163 |
| 2026-10-14 | 5225/5225/5225 | 400/400 相等 | 145/0/5080 | 5225/0 | 3247 | 278 | 有 | 5225/400/3247/177 |
| 2026-10-15 | 5226/5226/5226 | 400/400 相等 | 64/5111/51 | 5226/0 | 404 | 203 | 有 | 5226/400/404/367 |
| 2026-10-16 | 5226/5226/5226 | 400/400 相等 | 90/5084/52 | 5226/0 | 3823 | 236 | 有 | 5226/400/3575/416 |
| 2026-10-19 | 5224/5224/5224 | 400/400 相等 | 152/5018/54 | 5224/0 | 4134 | 506 | 有 | 5224/400/3673/318 |
| 2026-10-20 | 5224/5226/5224 | 400/400 相等 | 141/5033/52 | 5226/0 | 679 | 514 | 有 | 5224/400/679/607 |
| 2026-10-21 | 5224/5224/5224 | 400/400 相等 | 99/0/5125 | 5224/0 | 4965 | 265 | 有 | 5224/400/3975/413 |

逐日结果：Core/Profile/Lifecycle 精确身份集一致 12/13 日，均无重复；唯一差异是 10/20 Core 有 5,226 行，较 Lifecycle/Profile 的 5,224 多 2 个身份。该异常已通过两个层次处理：候选发布校验在 Owner 进入后继链前拒绝身份集合不守恒；BFF 在消费者边界按同日 Lifecycle 过滤过宽 Owner，原始 Owner bytes 保留。Sector/Rotation 在 13/13 日均为 400 行且身份集相等。D2 在 13/13 日均与 Lifecycle 数量相符、身份唯一，但全部 `PIT_ELIGIBLE=false` 且 `accepted=false`。D0 数据行存在，状态值跨日包含 TRUE/FALSE/UNKNOWN；缺少 cutoff/source-seal 合同，不能把这些结果视为已接受业务输出。Forward episode 与 Event 均存在，但所有 Forward episode 均 `PIT_ELIGIBLE=false`，LIVE cohort 未授权。以上是身份/完整性复算，不代表所有数值公式已完成逐字段重算。

### 10/20 已有数据的可逆修复

10/20 已发布生命周期范围为 5,224 个证券身份，Core 5,226、Profile 5,224；Consumer 输出过滤掉 Core 的 2 个多余身份，不改 Core 文件。调整后 ReadIndex 股票数保持 5,224；原调整后收盘 Owner 有 5,217 行，缺少 7 个范围内身份。初始投影曾将缺行呈现为 `<MISSING>` Close；新源码将 7 行显式呈现为 `SOURCE_INCOMPLETE / DATED_ADJUSTED_SECURITY_ROW_MISSING`，值为 null，不从 Core/Profile 借值。修复前同样为 5,224 股票，修复后仍为 5,224；字段质量从含糊的 MISSING 改为可追因的 SOURCE_INCOMPLETE，7 个真实缺源缺口完整保留。

同 token/date 新 R2 binding 的最终 digest 为 `0fe56436b670a9c8ee868e89d43fcdcc8ee6b1e9f606f64e470466ab4d1c31f8`，schema 为 `v4_4d792b71062e1cd883c20208ad4d1467a7bab76ecb87c88bb831dfa3`；此前中间修复 digest `9e98a746...` 和更早旧版本均仍保留在 revision history。最终 authority SHA-256 为 `812f4451890f438e12aef3fdbffc4432bb0abe6a9a74f52863444f85ca3ab04e`。写入前另有精确 authority 备份 `G:/codex_tmp/R10_READINDEX_AUTHORITY_R2_PRE_ADJUSTED_GAP_FIX_20261024.json`（SHA 对应中间 authority `b715e5e986d354f42a2b4d31069b8eeea7b30ef3e66917ba35424f16ee4de12c`）；第一次修复前备份仍记录旧 authority。最终读回：10/20 `focus/radar/sectors/stocks=679/607/400/5224`，Close 质量 `KNOWN=5217, SOURCE_INCOMPLETE=7`。所有原版本和失败中间版本作为不可变证据保留，没有删除。

### Core 数值独立复算范围

按同日 OHLC 从原始 raw Owner 独立重算 `clv=(close-low)/(high-low)`，13 个日期共 67,698 行可计算样本全部精确匹配 Core（0 mismatch）；逐日行数及 Owner SHA 见 [Core 数值复算证据](R10_CORE_NUMERIC_RECONCILIATION_20261024.json)。对 10/21 另运行既有独立精确数值 Oracle：`ret1` 5,216 个对照、8 个未知；breadth 分母 5,224、raw 实际报价 5,216、amount 精确和 5716687389023/4；指数 OHLC/amount/volume 3,600 个比较；限价 Owner 5,224 行，其中 5,198 行完成价格与极值规则验证（25,990 项）；总差异 0，状态 `SCOPED_NUMERIC_PASS`，证据在 [R10_CORE_MARKET_ORACLE_20261021.json](R10_CORE_MARKET_ORACLE_20261021.json)。该日仍不构成 PIT 或发布许可。

其余日期 `ret1`、`tr` 和滚动字段的跨日重算需要 Core 声明的 QFQ 历史价格坐标与对应历史价源；该来源绑定未在每个日期的 raw Owner 中提供。直接把原始 close 当作相同 QFQ 坐标会产生不可比较差异，故分类为**来源/价格基准证据缺失**，不冒报算法错，也不修改数值。其余 12 日的完整 Core 数值公式复算仍未通过验收。

### Priority、Market 与 ReadIndex 覆盖

PG canonical Priority Owner 仅有 10/13、10/14、10/15 三个 sealed 版本，契约为 `V4_DAILY_RESEARCH_PRIORITY_R1`，PIT=false，Market 权限为 `FACT_ONLY_NO_FORMAL_PERMISSION`；10/14、10/15 的 Priority payload sector 列表为空。当前候选链另有 10/20、10/21 的 loader 结果，但无法作为其余日期的 canonical Owner。Priority 历史查询会被 API 明确拒绝，原因 `CANDIDATE_PRIORITY_CURRENT_TOKEN_DATE_REQUIRED`。候选 Market 风险对象现经 Priority BFF 同样执行同日候选验证；失败时置空 stress 数值、移除可消费候选方向并打上 `QUARANTINED_PENDING_DATED_SOURCE_AND_RECOMPUTE`，不修改保留的原始 Owner。

当前 token 的 R2 binding 已覆盖 13/13 个候选日期，日期集合与候选 Head 完全相等；每个日期均有一个 sealed version、三条预建 Home responses，PG ReadIndex counts 与 Codex 内置浏览器逐日 Home 页面显示的 stocks/sectors/focus/radar 数完全相等。全部日期的 Home API 都返回四轴 UNKNOWN、SOURCE_INCOMPLETE 和隔离处置标记。13 份 Market 异常候选仍因 10/14–16 比较 universe 缺失而不能合法重算。缺口归因继续分为：来源/覆盖缺失（历史 universe、调整行或 Owner 缺失）、可证实流程/计算缺陷（未验证分母的 Market 候选进入消费者、10/20 Core 超范围、缺失调整行未明确分类）、业务合同缺失（D0、D2、Focus Priority 次序、Market 复合环境许可、LIVE Forward cohort）。

### 事务失败、幂等与恢复演练

在同一 `market_research` 开发 PG 内运行合成测试，不写业务 Owner、Head 或 SourceIngress：故意让带有预插版本行的 R2 prepare 在缺 `symbol` 时失败，PostgreSQL 事务回滚后检查内容寻址 schema 不存在；随后用同一合成 T0 的修正数据 prepare 成功，再重复完全相同调用，binding digest 相同、`stocks=1`、版本 sealed，最终只删除本次测试建立的合成 schema。结果为 `failure rollback=PASS; corrected retry=PASS; identical retry=PASS; test schema cleaned=PASS`。真实 10/20 authority 更新采用“先 sealed PG 写入、逐项回读、再原子替换 authority 文件”的顺序；旧 binding/备份仍在，可按精确字节恢复 authority 指针。该演练验证了事务失败和幂等路径，不等于所有操作系统掉电/文件系统损坏故障模式都经过测试。

Forward 页面运行验收进一步暴露一个可修复的读取性能缺陷：HTTP handler 为每次请求新建 BFF，因此原 `_forward_candidate_late_preview_cache` 只保存在短生命周期实例内，重复请求仍会重放整套当前/前一日 Owner 并重建 Late Forward 样本。源码已改为使用 Reader 共享 cache，以 candidate token、T0 和全部当前/前序 raw/core/sector/lifecycle/freeze binding SHA 组成 key；缓存命中前逐个校验 Owner bytes。跨 request-local shallow Reader copy 与 binding SHA 变更回归测试通过。当前已运行的 28766 仍是旧进程，Forward 页面在内置浏览器仍停留读取态；受本任务“不重启 28766”的约束，不能加载源码修复，故运行时 Forward 页面不宣称通过。内置浏览器已验证 10/20 stocks、sectors、focus、market、diagnostics 页面均加载；Priority 历史查询返回 `CANDIDATE_PRIORITY_CURRENT_TOKEN_DATE_REQUIRED`，按当前 token 日期合同拒绝。

PG 写后只读清点按时间顺序为：初始三日投影后 111 schemas/481 tables/4,885,168 rows；10/20 二次投影后 115/493/4,914,745；本次 13 日全覆盖后 125/523/4,998,994（ReadIndex `read_items` 534,364）。最后一步追加 10 个日期 schema、30 张表、84,249 行（其中 read_items 净增 84,209 行）。两次 10/20 历史修订及先前中断准备产生的不可达 schema 都保留；未经对象级确认的 schema 未删除。数据库连接身份为 `127.0.0.1:5432/market_research`；28766 未重启，28765 未启动；自动日更保持停用。

## 验收证据

- 11 组针对性回归测试：`128 passed`，覆盖 BFF、Home ReadIndex、市场派生、旧候选隔离、缓存身份、Operational Owner 身份守恒与缺失复权行；`git diff --check` 通过。
- R10 原市场数值 A/B 证据仍标记 `NON_PIT_CANDIDATE_REPLAY`，对历史无集合日期不作正确值宣称。
- 新增代码没有证券代码、板块代码或固定交易日业务分支；新增测试使用合成日期 `test-day`。简体中文提示直接用于消费者响应。
- 对 13 个 R2 schema 做了第二次只读 PG 逐表核验：日期与候选 Head 一一对应，version digest/contract/sealed、各域精确行数、三条响应及 response SHA 均通过。
- PG 新版本写入范围为现存 13 个日期的候选 ReadIndex；Owner、Core、正式 Head、SourceIngress、旧 ReadIndex、历史来源及所有既存工作区未跟踪文件均保留。
- 后续继续审计 Priority 候选 Market 出口时发现，先前隔离逻辑虽清空 `market_stress`，但未清掉同对象 `trend_reference` 的指数收盘/均线数值。现改为只返回合同、来源绑定和失败诊断，`market_stress` 与 `trend_reference` 均置空；回归加入趋势数值不可泄漏断言。相关三组测试 `51 passed`。该修复不改原始 Owner 或 PG 候选数据。
- Market 历史行情按 10/19、10/20、10/21 三份现存 gzip Owner 作流式输入复核，证券行数均 5,224，公式需要的四个交易日条目数分别 20,855、20,859、20,864；重复证券与重复证券日期均为 0。读取路径不再完整物化所有历史 bars，遇到重复输入会明确拒绝，不再由字典最后写入值覆盖。SHA 与 10/19、10/20 绑定匹配；10/21 实测 SHA `de3b85d2ad1cca69598713c19453cc105cc460488fddb87fa2df873c0d7e0221`。详情见 R10 Closeout Evidence `market_history_streaming_fix`。

## 下一阶段与恢复门槛

R2 13 日 PG→Home API→首页计数和市场隔离已逐日对齐，10/20 五个业务页面已实际加载；仍未验收的工作是 Core 已有 13 日 CLV 与 10/21 scoped oracle 证据之外的数值字段：其余日期 Core QFQ rolling/ret1/tr 及 Sector、D0/D2、Priority、Forward 逐字段独立复算仍未完成；Forward 页面源码修复的运行时读回、Priority 生产/历史访问合同，以及所有页面的逐域逐日 PG→API→页面数据行对账。28766 本轮不重启，运行态继续标 `UI_RUNTIME_NOT_RELOADED`；若要验收新进程，需另行安排允许的开发服务运行窗口。Priority/Market/D0/D2/Forward 缺失业务合同和 10/14–16 historical universe 来源缺口保持明确分类。来源缺失期间不生成虚假数值、不新增采集。所有输出继续标为开发候选。

只有在全存量日期逐项数值对账通过、错误候选无可达消费者、API 与页面读回一致、事务失败/恢复闭环有证据、未授权合同保持阻断并由独立验收签收后，才能讨论恢复数据更新。**本报告不构成该验收，自动日更继续停用。**

## 2026-10-24 后续续修：增量完成语义与 RPS 复核口径

### 为什么过去的“增量完成”与交易日业务链缺口同时存在

已追到当前 R8 SourceIngress 入口 `scripts/r8_batch04_ingest_tdx_source.py::ingest`：它的实际终点是把原始 TDX 日线与 receipt 写入开发 PG，并对 receipt、OHLCV、来源 SHA 和证据类别逐项读回；它明确不生成 Core、Profile、Sector、Market、D0、D2、Priority、Focus、Forward、ReadIndex，也不更新任何 Head。10/22 与 10/23 的 `SOURCE_INGRESS_READBACK_PASS` 因此只证明该入口自己的来源入库步骤完成，不能证明“交易日增量完成”。先前把该结果向用户概括成“增量跑完”是错误报告，业务日期链确实没有闭合。

入口回执现在增加机器可读字段：`completion_scope=SOURCE_INGRESS_ONLY`、`business_chain_status=NOT_RUN`、`business_chain_complete=false`，并列出后续需完成的域与 API/页面读回范围；原 `SOURCE_INGRESS_READBACK_PASS` 保留为兼容字段。回归测试防止以后把来源入库误读为整日业务链完成。未追加来源、未创建 10/22 或 10/23 的 Core/Owner、未改 Head。

### 本次独立数值复核修正

先前审计把相邻日期各自在自身价格坐标中的 Core RPS 直接相减，作为跨日期 delta oracle；这个算法错误，因为复权坐标跨日不同。改用 10/20 当日 Owner 的 `prior_core_target_coordinate.jsonl.gz`，该文件保存 10/19 在 10/20 当前坐标内的 return 输入，再分别按精确 Lifecycle 成员做独立 midrank 重排：

| 10/20 字段 | 有效观察 | 独立复算 | 不一致 |
|---|---:|---:|---:|
| `rps5_delta1` | 5,205 | 5,205 | 0 |

10/20 lag1 的逐源 SHA、行数和复算方法记录在 [RPS5 delta1 独立对账证据](R10_RPS5_DELTA1_INDEPENDENT_ORACLE_R1_20261024.json)。对全部 13 个日期做相同 lag1 重排后，完整结果见 [13 日 RPS5 delta1 对账](R10_RPS5_DELTA1_INDEPENDENT_ORACLE_R2_20261024.json)：65,266 个已观察值中，60,061 个可对账，56,197 匹配、3,864 不匹配；09/28 的 5,205 行缺前一交易日 Lifecycle 精确成员，不能独立验证。10/16 为主要异常日：2,825 个 delta 已观察行全部只有 1 行匹配，其余 2,824 行与 10/15 精确 Lifecycle 端点排序不一致。该批结果是对现存 Owner 的反证，不能据此把 Owner 宣称通过。

10/20 lag3 的历史端点分数必须在 10/20 坐标下由同一日历史输入重算；本轮没有把不在同一坐标的历史 Core 分数用作替代，也不把尚未重算的 lag3 宣称为通过。lag1 多日异常首先需结合生产时实际 `dated_identity` 来源绑定，逐日确认是成员来源错配还是上游 return 输入问题；随后按精确日成员重算受影响的候选 Core 和消费者投影。该修复及重建尚未完成，专项仍失败。

### 本次验证与页面回读

- `tests/v4_joint/test_r9_source_ingress.py`：10 passed。
- Market / Home cache 与候选 Priority 缓存回归：21 passed。
- 前端候选标签回归：9 passed。
- 仅通过 Codex 内置浏览器查看 `127.0.0.1:28766`。刷新后页面明确显示“当前候选数据日期 2026-10-21”与“候选快照记录时间 2026/10/23 08:40:33”；业务日期和文件/快照记录时间不再混为一项。28766 未重启；28765 未使用。

### 专项结论仍为未验收

上述语义修正不补齐数据。现有 10/22、10/23 仍只有 SourceIngress 原始来源，没有 Core/Owner 和后继业务链；本轮原冻结要求暂停这两个日期的 Core/Owner 生成，因此它们没有被推进。13 个候选日的 Core 同日公式复算（2,733,787 项、0 数值差异）和横截面 RPS5/RPS20 检查也不能替代跨日期与跨域闭环：RPS delta1 已发现 3,864 个差异，lag3 尚未完成；10/16 `rel_market_1` 的存储基准是 2,834/2,828 行，10/15 精确 Lifecycle 基准是 5,226/5,215 行。由每条已观察 `ret1-rel_market_1` 反推的旧基准为 0.0051775465706488，精确 Lifecycle 复算为 0.0044730070704939，差 0.0007045395001549。逐源 SHA 和值已在 [10/16 Market 相对基准复算证据](R10_MARKET_RELATIVE_START_UNIVERSE_DIAGNOSTIC_R1_20261024.json) 固定。其余日期 Sector/D0/D2/Priority/Focus/Forward 数值独立复算及每域逐行 API/页面对账仍未完成或合同/来源不充分。不得将此状态描述为全存量修复通过；自动日更继续关闭。

## 2026-10-24 用户反馈后的续修：增量完成语义与板块消费者隔离

用户指出历史交易日仍显示缺数据，要求解释先前增量运行报告与当前缺口的矛盾。原因已从入口源码追到 `scripts/r8_batch04_ingest_tdx_source.py::ingest`：此入口的成功边界是 SourceIngress 原始行和 receipt 的持久化与逐项回读，既不生成 Core/Owner，也不构建后继业务域或 ReadIndex。先前将 SourceIngress 成功口头表述为“交易日增量完成”，把入口局部成功误报成了业务日闭环。该口径错误由我承担。

入口现在把完成范围固定为 `SOURCE_INGRESS_ONLY`，并返回 `business_chain_status=NOT_RUN`、`business_chain_complete=false` 及全部后续域名称。兼容的 `SOURCE_INGRESS_READBACK_PASS` 只代表原始来源已入库并读回，不再表示全日完成。冻结日期 10/22、10/23 没有生成 Core/Owner，本轮没有采集或追加来源。

第二个可见缺陷是 Sector/Home 消费不一致：10/13 的 ReadIndex `/api/v4/home` 板块计数为 0，而独立 `/api/v4/sectors-meta` 已返回按日来源缺失；当时 28766 页面仍显示 400 个板块与“0/400”板块生态风险。页面头部同时披露该成员源实际来自 10/09，且 `PIT_ELIGIBLE=false`，所以该 400 分母不能作为 10/13 历史板块证据。直接在 Core Product BFF 修复：Home 对齐日期源门禁，计数、轮动、板块变化及板块风险改为来源不完整；列表页空 ReadIndex 响应继续携带精确 gap。`core-product-r1` 与研究页面都加了同样提示，避免拿空列表展示成“没有变化”。

该修复已通过 84 项目标 pytest、`git diff --check`、两个前端文件 Node 语法检查。新增机器证据见 [R10_EXISTING_DAY_CHAIN_CONSUMER_REPAIR_R1_20261024.json](../v4_existing_data_closure_20261024/R10_EXISTING_DAY_CHAIN_CONSUMER_REPAIR_R1_20261024.json)。仅使用 Codex 内置浏览器做可见验收；浏览器现场仍由未重启的 28766 进程提供旧响应，刷新后仍可见 400/0-of-400，因此 UI 运行态尚不能验收通过。没有重启 28766 来规避冻结要求。

本续修未把专项状态改为通过。10/09 与 10/12—10/21 共九个日期仍缺精确日期行业关系来源；TDX 现有成员快照止于 10/09，不足以证明其后 PIT 成员。13 日 RPS5 delta 独立 oracle 仍有 3,864 个可比较差异，正确候选 Core 及下游消费者重算尚未完成。此外，各域逐字段对账、完整 API/页面行对账及事务故障恢复演练仍有未完成项。详见 R10 续修证据的 `remaining_blockers`。自动日更和新交易日更新保持冻结。

## 2026-10-24 用户最新要求后的续修：13 日板块映射与 ReadIndex 消费闭环

本续修按用户最新指令，对已存在日期缺少精确历史板块映射的情况，统一使用候选 Owner 内已存在、且经来源校验的最新通达信映射。该回退用于候选研究展示，明确标记 `PIT_ELIGIBLE=false`、`AS_RECORDED=false`，保留快照 ID、观察时间和成员生效时间，不声称历史当日成员关系。10/22、10/23 仍冻结；没有采集、SourceIngress 追加或 Core/Owner 生成。

**修复前 → 修复后**：13 个已有日期的 Home/板块列表因严格历史成员源缺失而整体清空或状态不一致 → 新增版本化 `V4_SECTOR_MEMBERSHIP_FALLBACK_R1` 元数据读取及 Home 绑定，并对每日 Core 身份与 Sector Owner 成员对逐一校验，使 Home、板块列表 API 与首页使用同一映射依据。快照绑定/摘要、映射行、Owner 绑定或成员对不一致时继续失败关闭。该处理未修改原始 Owner、历史来源或候选 Head。

13 日 ReadIndex 均追加至不可变新 schema，封存后逐日核对 version digest、域行数、三条响应正文 SHA 和 Home/板块状态，再原子替换候选 R2 authority。authority SHA-256 从 `96a6e5f045526e3e31f69b2d634b737a0c270b622ec0431238981301030f2b2a` 变为 `ddf369a6ba7b5e9509abffd003961b337b572d94e4c829eaaae424ea27a92d71`；切换前 authority 的原始字节备份留在 G 盘临时证据目录。逐日 PG 回读及响应 SHA 见 [R10 13 日 PG/API 对账证据](../v4_existing_data_closure_20261024/R10_TDX_LATEST_MEMBERSHIP_READINDEX_PG_API_RECONCILIATION_R1_20261024.json)。候选 Head 文件 SHA `14ee0cf87a46f810b52295a8d42c4bbda391fd0fe49f4cb3457a1620067ad378` 未变化；正式 Head、Production Head、SourceIngress 均未写入。

| 交易日 | 股票行数 | 板块数 | 与该日 Core 交集的映射关系 | 映射快照成员时间 |
|---|---:|---:|---:|---|
| 2026-09-28 | 5,222 | 400 | 52,900 | 2026-10-09 09:44:01 +08:00 |
| 2026-09-29 | 5,223 | 400 | 52,905 | 2026-10-09 09:44:01 +08:00 |
| 2026-09-30 | 5,224 | 400 | 52,912 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-08 | 5,224 | 400 | 52,912 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-09 | 5,224 | 400 | 52,912 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-12 | 5,224 | 400 | 52,912 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-13 | 5,225 | 400 | 52,912 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-14 | 5,225 | 400 | 52,912 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-15 | 5,226 | 400 | 52,912 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-16 | 5,226 | 400 | 52,912 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-19 | 5,224 | 400 | 52,910 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-20 | 5,224 | 400 | 52,910 | 2026-10-09 09:44:01 +08:00 |
| 2026-10-21 | 5,224 | 400 | 52,910 | 2026-10-09 09:44:01 +08:00 |

内置浏览器在未重启的 28766 对 10/20、10/21 Home 做可见读回：交易日切换正确；10/21 首页显示股票 5,224、板块 400、雷达 413。板块映射标明 10/09 时间和“非历史 PIT”，轮动信息也明确 `PIT_ELIGIBLE=false`；市场四轴均显示来源不足并隔离候选。因用户要求仅用内置浏览器，本轮未使用本机浏览器。

**仍未完成的修复**：RPS5 `delta1` 跨日独立对账曾发现 3,864 个差异；其余 Core 跨日字段、Sector/D0/D2/Priority/Focus/Forward 数值与 API/UI 逐域对账，以及缺失合同的设计仍待完成。13 份 Market 候选已在 Home 全轴隔离，但历史四板块分母来源仍不完整，不能伪造正确市场数值。因此本节仅验收板块映射及其 ReadIndex→API→页面消费，不将专项改为总体通过，也不恢复数据更新。

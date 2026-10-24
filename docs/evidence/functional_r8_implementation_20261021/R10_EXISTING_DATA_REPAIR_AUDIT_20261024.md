# R10 V4 存量数据修复专项审计（2026-10-24）

## 阶段合同与结论

**状态：`PARTIAL_REPAIR_NOT_ACCEPTED`。** 本报告只接受源码级消费者隔离与可复核的存量清点结果；不接受新增日期、外部补采、正式 Head 变更或以 UNKNOWN/跳过代替数值修复。工作分支 `codex/v4-unified-development` 的审计起点为远端 HEAD `283a26414609d47004adbec318eb5b4846b6d7c7`。本次先读取 Google Drive R10 任务卡（ID `1SqPW4Y64s85EzSJwY7wwoptnQKe_YVbL`）、远端分支最新 `R10_V4_REAL_FUNCTIONAL_CLOSEOUT_REPORT.md` 与配套 Evidence，并查阅适用的 V4 R8 修复规范、运行性能修复规范、R2 综合修复计划及项目规范。

本轮停止了新增采集、SourceIngress 写入、新交易日 Owner/Core 生成及自动日更。未访问外部行情源，未改变正式 Head，未物理删除数据或证据，也未启动、停止或重启服务。为修复三日存量消费者读投影，按现有开发授权对 PG 仅执行同 token/date ReadIndex 追加式重建；原有 schema/version 均保留，并在 G 盘留存切换前 authority 精确字节备份。扫描器阶段 0 沿用 R10 已记录的 `FULL_PASS` 回执；本轮未运行扫描器。

## 可证实的问题与修复

### 1. 13 份旧 Market 候选及消费者隔离

R10 机器证据逐项列出 13 份 `market_owner_candidate_v2.json` 及 SHA-256：10/19 三份记录 `breadth_common_count=5223`，10/20 三份与 10/21 七份记录 5224。绑定的历史 universe 文件对对应比较日 10/14、10/15、10/16 的四板块范围均无成员；当期 Core 虽有约 5,225 行，但未与该历史成员集合逐项证明相同，不能替代其分母。上一轮独立 A/B 复算的 10/19 旧 Core 分母结果为 5,225 个身份、5,223 个当前交集、5,208 个可计算样本；正收益指示器均值 0.2465437788，SIGN 均值 0.5057603687。历史 universe 可用身份数为 0，因此这些数值是**旧候选诊断值**，不是可接受的正确历史结果；本轮不伪造替代数值。

确认的消费者链为：PG ReadIndex `/api/v4/home` 快照包含 Market `row/raw/regime/sources` → BFF R2 预建响应路径只追加 `candidate_trend_review`，未核验或清除其他旧轴 → Home 页面将四轴和 Evidence Drawer 直接渲染。`/api/v4/radar/priority?view=candidate` 另行暴露候选 Market 风险对象；其候选 API 保持非接受标记。六入口研究 UI 与兼容 UI 均消费 Home Market 轴。

本轮在 BFF 增加同日 Market 衍生检查：必须为 `READY`、日期吻合、有 Core 与限价 Owner、非空分母/可计算数、来源 digest 完整，并且响应四轴值与独立衍生值一致。任一条件不满足，或复算异常时，API 将四轴、压力方向、原始数值及综合状态全部标成 `SOURCE_INCOMPLETE/UNKNOWN`，保留 `sources` 供追溯并明确标记 `QUARANTINED_PENDING_DATED_SOURCE_AND_RECOMPUTE`。R2 ReadIndex 路径与 BFF 现场构造回退路径都执行该门禁；风险族结果不会在后续覆盖隔离状态。旧 PG 原始快照不覆写；通过新 sealed ReadIndex 版本承载修复后的消费者投影，保留旧版本及其历史证据。

以现存 10/21 候选根和同一只读 PG 连接，在新 Python 进程内运行修复后 BFF `/api/v4/home` 读回 10/19、10/20、10/21，三日均返回 HTTP 200、所有 Market 轴及轴质量均为 `UNKNOWN/SOURCE_INCOMPLETE`，并给出 `R10_MARKET_HISTORICAL_UNIVERSE_DATE_SCOPE_EMPTY:2026-10-14`。冷首请求 30.234 秒，随后同一进程的 10/20 为 4.156 秒、10/21 为 1.107 秒；后两次命中同一进程的派生缓存，不能当作冷启动延迟预算。发现轴隔离后 `field_quality` 仍保留旧 `OBSERVED` 的元数据矛盾，已在同一修复中改为 `SOURCE_INCOMPLETE`，并加入回归断言。

为让未重启的 28766 也读取隔离结果，在候选 workspace `G:/codex_tmp/v4_daily_candidate_chain_20261020` 对 10/19、10/20、10/21 追加三个 R2 ReadIndex 版本，使用同一 token `14ee0cf87a46f810b52295a8d42c4bbda391fd0fe49f4cb3457a1620067ad378`。新 schema 分别为 `v4_c94ffc1071e8bf4c7d526524de1a1ac1eee38912c76a3e55c5ae2853`、`v4_2d9e9ce6c601c0d196a2f80a395300a3ff1d61d40934420652ba7aeb`、`v4_36b669df3ca8764b591d83d06cc6ce53482f35eff3cb1e87ee86092c`；新行分别为 9,615、6,910、10,012 `read_items`，各含 3 条 `read_responses` 与 1 条 `read_versions`。PG 先封存新版本并逐行回读通过，随后原子更新 R2 authority 指针。切换前 authority SHA-256 为 `38c8f9e79c2239513dffdc8c94f73d26acacaa695061e794d3ad8f52ac8b20e2`；原字节备份位于 `G:/codex_tmp/R10_READINDEX_AUTHORITY_R2_PREWRITE_20261024.json`，SHA 相同；切换后 authority SHA-256 为 `b3d4528d8eb737f66cca5b00969cf246db282e24f64ce2a85a8a7f492ca1ae4b`。10/20、10/21 旧版本仍在 revision history；10/19 在当前 token 下原本没有 R2 绑定。回滚只需把 authority 精确恢复到备份字节；新 sealed schema 保留为不可达证据，不删除。

Home 页面实际加载的 `/v4/assets/app.js` 返回 HTTP 200，源码按 `d.market.row[k]` 显示四轴；当前 API 又返回 `SOURCE_INCOMPLETE` 和 `UNKNOWN`，所以页面投影读取的是隔离值。Computer Use 未能确认 Chrome 当前 URL，未进行画面操作；因此没有声称截图级浏览器验收通过。

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

## 验收证据

- 6 组针对性回归测试：`94 passed`，覆盖 BFF、Home ReadIndex、市场派生、旧候选隔离及缓存身份；`git diff --check` 通过。
- R10 原市场数值 A/B 证据仍标记 `NON_PIT_CANDIDATE_REPLAY`，对历史无集合日期不作正确值宣称。
- 新增代码没有证券代码、板块代码或固定交易日业务分支；新增测试使用合成日期 `test-day`。简体中文提示直接用于消费者响应。
- PG 新版本写入范围限定为 10/19、10/20、10/21 ReadIndex；Owner、Core、正式 Head、SourceIngress、旧 ReadIndex、历史来源及所有既存工作区未跟踪文件均保留。

## 下一阶段与恢复门槛

下一阶段继续限于存量数据：为每个已存在日期逐域列出 Owner/输入合同/行数/SHA 和 PG→API→页面调用链；独立重算 Core/Profile/Sector、D0/D2、Priority/Focus、Market、Forward 与 ReadIndex，分别标记来源缺失、算法不一致、合同缺失和运行故障；补足事务失败、幂等重试与可恢复演练的明确范围及证据。对缺失来源只记录缺口，不进行采集。所有输出继续标为开发候选。

只有在全存量日期逐项数值对账通过、错误候选无可达消费者、API 与页面读回一致、事务失败/恢复闭环有证据、未授权合同保持阻断并由独立验收签收后，才能讨论恢复数据更新。**本报告不构成该验收，自动日更继续停用。**

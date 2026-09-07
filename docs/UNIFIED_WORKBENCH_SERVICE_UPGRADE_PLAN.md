# 统一工作台与通达信盘后数据自动化升级方案

> 此文件保留为 V1 历史方案。后续实施以 [统一工作台升级方案 V2](UNIFIED_WORKBENCH_SERVICE_UPGRADE_PLAN_V2.md) 为准；两者冲突时采用 V2。

## 1. 目标

将当前“下载通达信数据、运行 CMD、打开静态 HTML”的日常流程升级为一个仅监听本机的统一工作台：

- 后台主服务随 Windows 登录启动并持续运行；代码升级或服务异常时才重启。
- 工作台显示通达信官方完整包的发布日期、下载状态、输入就绪状态和分析状态。
- 使用者点击“生成今日数据”后，系统自动完成检查、下载、校验、解压、发布输入、运行分析和打开当日报告。
- 工作台可以切换所有已成功发布的交易日。
- 市场、板块、股票、候选池、V2 队列、Forward 观察、结果和审计身份统一写入 DuckDB。
- 板块页显示当日单日涨跌、上一交易日单日涨跌、两日变化、今日与昨日排名及排名变化。

该升级不改变现有模型规则、阈值、候选定义和 Forward 口径。

## 2. 官方数据源边界

官方页面：<https://www.tdx.com.cn/article/vipdata.html>

页面说明该文件是个人版 PC 客户端使用的沪深京日线完整包，覆盖 A/B 股、交易所指数、板块指数、回购、可交易基金、可转债等；如需当日数据，应等待页面更新日期变为当日后再下载；官方使用方式是在客户端 `vipdoc` 下覆盖解压。

实施时不得猜测或永久写死下载地址。下载适配器应从官方页面解析：

- 页面声明的更新日期；
- 实际下载地址；
- HTTP ETag、Last-Modified、Content-Length（若服务器提供）；
- 下载时间、文件长度和本地 SHA256。

该页面只明确承诺日线完整包，没有明确承诺包含 `T0002/hq_cache` 中的复权、证券名称和板块成员配置。因此数据源分为两类：

1. 每日价格输入：由官方完整包自动更新。
2. 元数据输入：`gbbq`、`shs.tnf`、`szs.tnf`、`bjs.tnf`、`tdxhy.cfg`、`tdxzs.cfg`、`infoharbor_block.dat` 等继续独立记录来源日期和 SHA256。

在确认官方存在可自动取得的同口径元数据包之前，工作台必须显示元数据新鲜度。超过合同允许期限时阻断正式发布，不能静默使用旧数据。

### 2.1 通达信终端作为元数据更新器

通达信终端保持登录并开启后台盘后数据更新时，可继续负责刷新 `T0002/hq_cache` 元数据。统一服务不模拟交易操作、不读取账号凭据，也不调用交易功能；它只监控本地元数据文件是否形成一个稳定的新快照。

推荐运行方式：

- Windows 登录后将通达信终端最小化启动，并启用软件自身支持的后台盘后数据更新。
- 统一服务独立下载官方日线完整包，不与通达信终端同时覆盖同一个 `vipdoc`。
- 对 `hq_cache` 所需文件连续读取两次，只有文件长度、修改时间和 SHA256 在稳定窗口内均不变化时才复制到项目管理的只读快照。
- 如发现通达信仍在写入、文件组合不完整或部分文件新旧混合，状态保持 `METADATA_UPDATING`，不得启动正式分析。
- 每个元数据快照记录观察时间、文件修改时间、文件长度、SHA256、通达信进程状态和上一个快照身份。

这使通达信终端可以持续联网更新元数据，但分析进程永远只读取已经封存的稳定副本。

### 2.2 新股、新概念和成员关系动态更新

新增版本化合同 `tdx-dynamic-universe-v1.0`，每天比较最新稳定元数据快照与上一快照：

- 新股：从 `shs.tnf`、`szs.tnf`、`bjs.tnf` 发现新证券代码和名称；只有存在有效日线、市场归属有效并通过现有 NORMAL_UNIVERSE 合同时才进入计算。
- 新概念板块：从 `tdxzs.cfg` 和 `infoharbor_block.dat` 发现新 `sector_id`、名称、类型和成员集合，首次观察日写入数据库。
- 新成员关系：记录板块新增成员和移除成员，不用当前关系回填到过去交易日。
- 板块改名：稳定代码不变时新增名称版本；代码变化时视为新板块并保留旧板块终止记录。
- 退市、暂停维护或消失的证券/板块：标记 `inactive` 和最后观察日，不物理删除历史记录。
- 同名不同代码、同代码名称变化、空板块、成员骤变和解析失败必须产生审计事件。

采用观察时点版本表：

| 表 | 关键字段 | 用途 |
|---|---|---|
| `security_master_versions` | `security_id,valid_from,valid_to,metadata_identity` | 新股、名称和状态版本 |
| `sector_master_versions` | `sector_id,valid_from,valid_to,metadata_identity` | 新概念、改名和停用版本 |
| `sector_membership_versions` | `sector_id,security_id,valid_from,valid_to,metadata_identity` | 成员加入与移除 |
| `metadata_snapshots` | `metadata_identity,observed_at,source_hashes` | 稳定元数据快照 |
| `metadata_change_events` | `metadata_identity,event_type,entity_id,details` | 可解释变更记录 |

`valid_from` 表示项目首次观察到该关系的交易日，不等同于交易所正式生效日，因此只支持从首次观察日开始的时点查询，不做历史推断。

## 3. 输入目录设计

自动化不直接在 `D:/new_tdx` 中边下载边覆盖。该目录继续作为只读的已知良好元数据源和人工回退源。

新增项目管理的输入区：

```text
runtime/downloads/<date>/<download_id>/package.zip
runtime/extracting/<date>/<download_id>/vipdoc/...
data/source_snapshots/tdx_daily/<date>/<source_identity>/vipdoc/...
```

发布顺序：

1. 将 ZIP 下载到 `.part` 临时文件。
2. 下载完成后计算 SHA256，再原子改名为 `package.zip`。
3. 在独立临时目录解压，拒绝绝对路径、`..`、符号链接和越界文件。
4. 执行 ZIP CRC、文件数量、扩展名、`.day` 长度为 32 字节倍数、尾记录日期、沪深主要指数日期、三市场覆盖率检查。
5. 检查页面更新日、包内最新日、系统交易日三者一致。
6. 生成输入 manifest 和 SHA256 后，将完整目录原子发布为不可变快照。
7. 分析进程只读取已经发布的快照，从不读取下载中或解压中的目录。

如未来确实需要让通达信客户端也使用这些文件，应另建显式的“同步到客户端”功能，要求客户端进程已关闭、先备份、逐文件原子替换并可回滚。它不属于每日分析的必要路径。

## 4. DuckDB 存储

DuckDB 是嵌入 Python 进程的本地分析数据库，不需要单独安装数据库服务器、创建账号或运行 Windows 数据库服务。数据库是一个项目文件，例如：

```text
data/database/market_research.duckdb
```

当前机器的 `E:/python/python.exe` 环境已经包含 DuckDB 1.5.5，模块位置为 `E:/python/Lib/site-packages/duckdb`。它可能由此前环境或依赖安装加入，并非独立安装的软件界面。

### 4.1 DuckDB 与本机 MySQL 的选择

预计一年约两百万行对两者都很小。当前场景选择 DuckDB，原因是：

- 单机、单用户、一个后台写任务，符合 DuckDB 的嵌入式单写者模型。
- 工作台以按日期、板块、队列做聚合和排序为主，DuckDB 的列式分析执行更合适。
- 无需维护数据库服务、端口、用户、密码和 Windows 服务。
- 可直接批量读写 Pandas、Arrow 和现有 Parquet，历史迁移路径短。
- 整库备份和恢复可以围绕一个数据库文件和 manifest 完成。

MySQL 更适合多个用户通过局域网访问、多个进程高并发写入、需要独立数据库权限体系或未来部署到服务器的情况。仅仅因为本机已经安装 MySQL，不足以抵消当前项目中额外的服务运维和行式分析开销。

数据访问层必须通过 repository 接口隔离 SQL。若未来出现以下任一条件，再迁移 MySQL：

- 需要其他电脑访问；
- 同时存在多个写入任务；
- 需要多用户权限和长期在线数据库服务；
- 数据库必须脱离当前工作站独立运行。

两百万行无需因此提前采用 MySQL；DuckDB 足以留出明显余量。

采用单写者事务：后台任务拥有写连接，页面请求使用只读连接。每日发布在一个事务中完成，失败则整体回滚。

核心表：

| 表 | 主键 | 用途 |
|---|---|---|
| `schema_migrations` | `version` | 数据库结构版本 |
| `source_packages` | `source_identity` | 官方页面、下载、ZIP 与解压证据 |
| `source_files` | `source_identity,path` | 输入文件长度、SHA256、最新日期 |
| `metadata_snapshots` | `metadata_identity` | 终端稳定元数据快照 |
| `security_master_versions` | `security_id,valid_from` | 新股、名称与状态版本 |
| `sector_master_versions` | `sector_id,valid_from` | 新概念和名称版本 |
| `sector_membership_versions` | `sector_id,security_id,valid_from` | 动态成员关系版本 |
| `daily_runs` | `run_id` | 任务状态、阶段、错误与日志摘要 |
| `daily_publications` | `trade_date,revision` | 每日不可变发布及当前版本 |
| `market_daily` | `trade_date,revision` | 市场概览 |
| `sector_daily` | `trade_date,revision,sector_id` | 板块指标、结构和排名 |
| `stock_daily` | `trade_date,revision,security_id` | 全市场股票指标 |
| `candidate_daily` | `trade_date,revision,security_id` | 候选池与研究优先级 |
| `v2_queue_daily` | `trade_date,revision,queue_name,security_id` | 五类 V2 队列 |
| `sector_membership_daily` | `trade_date,revision,sector_id,security_id` | 板块个股关系 |
| `forward_observations` | `observation_id` | Forward 封存观察 |
| `forward_outcomes` | `observation_id,horizon` | 到期结果 |
| `audit_receipts` | `trade_date,revision,receipt_type` | 收据、身份和 SHA256 |
| `job_events` | `job_id,sequence` | 页面进度和诊断事件 |

数据库本身是主查询入口；不可变 manifest 和数据库备份仍需保留，用于灾难恢复和外部审计。

## 5. 板块单日对比口径

新增版本化合同 `sector-daily-comparison-v1.0`：

- 个股 `RET1 = 当日有效收盘价 / 上一主交易日有效收盘价 - 1`。
- 板块当日涨跌幅为有效成员 `RET1` 的中位数。
- 上一日涨跌幅从数据库上一成功发布交易日读取，不能用自然日减一。
- 变化值为当日板块涨跌幅减上一交易日板块涨跌幅，单位为百分点。
- 排名只在 INDUSTRY、THEME、STYLE 各自类型内计算。
- 当前或上一日有效覆盖不足时显示“数据不足”，不填零。
- 使用当前成员快照，不宣称历史 PIT 成员关系。

板块页面新增字段：

```text
板块 | 类型 | 当日涨跌 | 上一日涨跌 | 较前日变化 |
今日同类排名 | 上一日同类排名 | 排名变化 | 5/20/60日强度 | 覆盖率
```

## 6. 本地后台服务

服务仅绑定 `127.0.0.1`，不接受局域网和公网连接。第一版可使用 Python 标准库 HTTP 服务或补充固定版本的 Web 框架；不依赖外部云服务。

建议接口：

| 方法与路径 | 用途 |
|---|---|
| `GET /api/status` | 服务、数据库、当前发布和输入状态 |
| `GET /api/source/latest` | 官方页面日期及下载状态 |
| `POST /api/jobs/daily` | 创建“生成今日数据”任务 |
| `GET /api/jobs/{id}` | 查询阶段、进度、结果或阻断原因 |
| `GET /api/trading-days` | 可切换的成功发布日期 |
| `GET /api/dashboard?date=` | 市场概览 |
| `GET /api/sectors?date=` | 板块排行及前日比较 |
| `GET /api/stocks?date=` | 股票排行与查询 |
| `GET /api/queues?date=&queue=` | V2 队列 |
| `GET /api/linkage?date=&sector_id=` | 板块成员 |
| `GET /api/linkage?date=&security_id=` | 股票所属板块 |
| `GET /api/forward?date=` | Forward 状态与样本积累 |

任务状态机：

```text
IDLE
 -> CHECK_OFFICIAL_DATE
 -> DOWNLOAD
 -> VERIFY_PACKAGE
 -> EXTRACT_STAGING
 -> VERIFY_TDX_SNAPSHOT
 -> WAIT_STABLE_METADATA
 -> DIFF_DYNAMIC_UNIVERSE
 -> PUBLISH_SOURCE_SNAPSHOT
 -> RUN_PHASE0
 -> RUN_V1_V2
 -> WRITE_DATABASE_TRANSACTION
 -> VERIFY_RECEIPTS
 -> PUBLISHED
```

任何阶段失败进入 `BLOCKED`，保留上一成功发布版本。数据库和工作台不得将失败任务显示成当日已完成。

同一官方包、同一输入身份和同一模型身份重复点击时返回已有发布，不重复下载、计算或写入 Forward 观察。

## 7. 统一工作台

工作台顶部固定显示：

- 当前选择交易日；
- 最新成功发布交易日；
- 官方页面更新日期；
- 日线包状态；
- 元数据日期和新鲜度；
- 通达信终端是否在线、元数据是否仍在写入；
- 新股、新板块、成员新增/移除数量及异常变更；
- 模型身份；
- “检查最新数据”和“生成今日数据”按钮；
- 当前任务阶段、进度和阻断原因。

页面：

1. 今日总览：领先板块与优先研究个股。
2. 板块排行：当日/上一交易日涨跌和排名变化。
3. 个股排行：候选池与全市场查询。
4. 五类结构队列：V2 独立队列和证据。
5. 板块个股联动：双向查询。
6. Forward：封存日期、到期结果和样本充分性。
7. 运行与审计：阶段日志、收据和 SHA256。

切换交易日只查询已发布数据库快照，不重新计算。

## 8. 后台驻留和启动

提供一个入口：

```text
START_MARKET_WORKBENCH.cmd
```

入口行为：

1. 检查后台服务端口和 PID 文件。
2. 服务已运行则直接打开浏览器。
3. 服务未运行则后台启动，等待健康检查通过后打开浏览器。
4. 服务崩溃时写日志并由 Windows 计划任务重新拉起。

Windows 计划任务设置为用户登录时启动，不需要管理员权限。代码或数据库 schema 升级时，服务先完成迁移检查，再切换版本；迁移失败继续使用旧版本。

## 9. 配置中心、目录管理与热重启

所有可变路径和保留策略进入版本化配置文件，例如：

```text
config/workbench.toml
```

工作台“系统设置”页面允许查看、修改、验证和恢复配置。核心配置项：

| 配置 | 默认值 | 说明 |
|---|---|---|
| `tdx.metadata_root` | `D:/new_tdx` | 通达信终端主目录，只读 |
| `source.daily_snapshot_root` | `data/source_snapshots/tdx_daily` | 日线只读快照目录 |
| `source.metadata_snapshot_root` | `data/source_snapshots/tdx_metadata` | 元数据只读快照目录 |
| `runtime.download_root` | `runtime/downloads` | ZIP 下载临时区 |
| `runtime.extract_root` | `runtime/extracting` | 解压临时区 |
| `database.path` | `data/database/market_research.duckdb` | 正式数据库 |
| `backup.root` | `data/backups` | 数据库备份目录 |
| `logs.root` | `logs/service` | 服务日志目录 |
| `retention.source_trading_days` | `3` | 日线与元数据快照最多保留交易日数 |
| `retention.download_packages` | `1` | 成功 ZIP 最多保留份数 |
| `retention.failed_download_days` | `3` | 失败下载隔离保留天数 |
| `retention.logs_days` | `30` | 普通日志保留天数 |
| `retention.job_events_days` | `30` | 详细任务事件保留天数 |
| `retention.database_backups` | `3` | 数据库备份份数 |
| `limits.runtime_cache_gb` | 可配置 | 运行缓存空间上限 |

目录重新配置流程：

1. 页面编辑产生候选配置，不立即覆盖当前配置。
2. 后台验证绝对路径、目录权限、剩余空间、路径是否重叠、数据库可打开性和通达信必需文件。
3. 对通达信目录执行只读验证；程序不得用写入测试探测该目录。
4. 对项目托管目录执行临时文件写入、原子改名和删除测试。
5. 页面展示旧值、新值、需要迁移的数据和是否需要重启。
6. 使用者应用后，配置以临时文件加原子改名方式发布，并记录 `config_revision` 和审计事件。
7. 新配置启动失败时自动恢复上一版本。

路径安全规则：

- 通达信主目录与下载、解压、数据库、备份目录不得相互包含。
- 快照目录不得位于通达信主目录下。
- 清理器只能删除配置中明确标记为项目托管且通过工作区边界校验的目录。
- 数据库、当前使用快照、正在下载/解压目录和运行锁目标永远不能被清理。
- 目录移动采用复制、校验、切换指针、延迟删除旧目录的流程，不能直接搬动正在使用的数据。

配置分两类生效：

- 即时生效：页面偏好、日志级别、保留数量、磁盘告警阈值。
- 受控热重启：通达信目录、快照目录、数据库、备份目录、服务端口和 Python 运行环境。

受控热重启流程：

```text
STOP_ACCEPTING_NEW_JOBS
 -> WAIT_CURRENT_JOB_SAFE_POINT
 -> FLUSH_DATABASE_AND_LOGS
 -> WRITE_RESTART_HANDOFF
 -> START_REPLACEMENT_PROCESS
 -> VERIFY_HEALTH_AND_CONFIG_REVISION
 -> SWITCH_BROWSER_CONNECTION
 -> STOP_OLD_PROCESS
```

若每日发布事务正在执行，工作台显示“等待安全点”，不强制终止写入。浏览器保持打开并自动轮询重连；新进程健康检查失败时旧进程继续服务。

## 10. 自动清理与容量管理

成功数据已经写入 DuckDB 后，原始日线和元数据快照只保留最近三个成功交易日。交易日集合从 `daily_publications` 读取，不能按自然日或文件修改时间计算。

默认清理策略：

| 对象 | 默认策略 |
|---|---|
| 解压临时目录 | 成功发布后立即删除 |
| `.part` 下载文件 | 成功或确认失败后清理；失败样本最多隔离 3 天 |
| 成功 ZIP | 仅保留最新 1 份，可配置为 0 |
| 日线快照 | 最近 3 个成功交易日 |
| 元数据快照 | 最近 3 个成功交易日；相同身份只保存一份 |
| V1/V2 中间计算缓存 | 发布并校验入库后按最近 3 个交易日和容量上限轮转 |
| 动态 HTML | 改为数据库驱动后不再按日复制整页 |
| 普通日志 | 30 天 |
| 审计摘要、SHA256、配置变更记录 | 长期保存在数据库，体积很小 |
| 数据库备份 | 最近 3 份 |

清理任务在每次成功发布后运行，也可由工作台手动执行。安全步骤：

1. 从数据库读取当前发布、运行租约和最近三个交易日。
2. 生成清理预览，列出路径、类别、日期、大小和原因。
3. 再次解析每个绝对路径，确认位于配置的项目托管根目录。
4. 将目标原子改名到同卷 `.trash/<cleanup_id>`，避免查询读到部分目录。
5. 提交清理日志后删除 trash；失败可在提交前恢复。
6. 清理后复查数据库当前发布、工作台查询和三个保留交易日。

工作台“存储与清理”页面提供：

- 各目录已用空间和剩余空间；
- 按数据类型统计占用；
- 下一次自动清理内容；
- “预览清理”和“立即清理”按钮；
- 最近清理记录、释放空间和失败原因；
- 修改保留交易日、日志天数、ZIP 份数、备份份数和缓存上限；
- 一键清理失败任务缓存，但不删除成功数据库发布。

磁盘空间低于配置阈值时先清理可回收缓存；仍不足则阻断下载和分析，保留当前数据库和已发布结果。

## 11. 迁移步骤

### M1：数据库基础与历史导入

- 建 schema、迁移器、单写者锁和事务发布器。
- 导入 20260904、20260907 的现有封存数据。
- 逐表比较行数、主键、关键字段和来源 SHA256。
- 文件仍为当前生产主入口，数据库先以影子模式运行。

验收：数据库查询与现有发布逐行一致，重复导入幂等。

### M2：官方完整包下载器

- 实现官方页面日期与链接解析适配器。
- 实现断点/临时下载、SHA256、ZIP 安全检查和 staging 解压。
- 建立日线快照和输入 manifest。
- 完成异常包、半包、旧包、未来日期、指数不同步和部分市场更新测试。

验收：不启动通达信终端即可生成与手工下载同日期、同记录内容的只读日线快照。

### M2.5：终端元数据监控和动态证券板块

- 监控通达信终端进程及 `hq_cache` 稳定窗口，不读取未稳定文件。
- 建立元数据不可变快照、身份和变更事件。
- 实现新股、新概念板块、改名、停用、成员加入和移除的版本化差异。
- 增加成员骤变、同名冲突、代码复用、文件截断和终端写入中断测试。
- 工作台显示变更摘要，并可查看每项变更的来源文件和 SHA256。

验收：在合成元数据和真实终端更新样本中，新证券、新概念及成员变化能进入下一次正式发布，历史交易日查询保持不变。

### M3：数据库正式发布与板块比较

- 日常流水线改为事务写库。
- 增加板块 RET1、上一交易日比较和同类型排名变化合同。
- 数据库成为工作台主查询源；保留审计导出和备份。

验收：失败注入后数据库无半成品；当日与前日对比可独立复算。

### M4：后台服务与统一工作台

- 实现本机 API、任务队列、单实例锁和实时进度。
- 实现日期切换、“检查最新数据”和“生成今日数据”。
- 合并市场、板块、个股、V2、联动、Forward 和审计页面。
- 增加 `START_MARKET_WORKBENCH.cmd` 与登录启动任务。

验收：通达信终端可在后台持续更新元数据；从浏览器完成日线下载、稳定快照、分析、切日和结果查询，无需人工操作终端界面。

### M5：切换与独立复审

- 连续至少两个真实交易日双轨运行，比较原文件链和数据库链。
- 校验当前 V1 身份、五个 V2 表、统一研究板、集成身份、Forward 防护和数据库事务。
- 演练断网、下载中断、ZIP 损坏、磁盘不足、重复点击、服务重启和数据库备份恢复。
- 通过复审后停用旧的两个日常 CMD，保留只读回退工具。

验收状态只能是 `EXTERNAL_AUDIT_PASS` 或带明确阻断项的 `BLOCKED`。

## 12. 备份与恢复

- 每次成功发布后执行 DuckDB checkpoint。
- 每日生成数据库一致性摘要和 SHA256。
- 保留最近若干数据库备份及全部不可变日线源 manifest。
- 恢复时先在临时数据库执行完整性与行数检查，再原子替换正式数据库。
- 不将下载 ZIP、数据库、备份和运行日志提交 Git。

## 13. 预计改动规模

这是一个版本升级，不是单页字段修改。主要新增模块包括下载适配器、安全解压器、输入快照发布器、DuckDB schema 与迁移器、事务写入器、本地 API、任务状态机、动态工作台和 Windows 驻留启动器。

建议按 M1、M2、M2.5、M3、M4、M5 分阶段交付，每阶段独立测试和验收。最关键的前置验证是确认官方 ZIP 的稳定下载协议，以及实测通达信终端后台更新 `gbbq`、证券表、板块定义和成员文件的时序；在这些证据完成前，不宣称完全替代通达信终端。

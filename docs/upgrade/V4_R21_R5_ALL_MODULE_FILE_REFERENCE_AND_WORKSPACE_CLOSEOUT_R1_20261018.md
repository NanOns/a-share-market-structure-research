# V4_R21_R5 全模块文件引用与 Workspace 集中实修收尾报告

- 执行分支：`codex/v4-workspace-cleanup`（基础 `4a69c4cd0841c9fbb83e730c2e4f9a910d8628d2`）
- 状态：`CODE_SCOPE_PARTIAL; BROWSER_PARTIAL; LIVE_PG_VERIFIED; FORMAL_HEAD_CLOSURE_PENDING`
- 本次范围：现役 V4 的 PG 读取链、Owner/Membership、合同 Registry、股票历史、回放、研究 BFF/UI、开发候选服务及 Workspace 引用。

## 实际代码修复

相对本轮起点 `4a69c4cd0841c9fbb83e730c2e4f9a910d8628d2`，本分支累计修改 **37 个现役 V4 运行时代码文件**、2 个 PostgreSQL 迁移及 7 个聚焦测试文件。R5 基线报告早先的 `26/1/4` 计数不完整，以此处按 Git 差异重新核对的 `37/2/7` 为准。按功能链计，实际替换/收紧 10 组：

1. V4 原生连接使用现有 `WORKBENCH_PG_DSN` 连接同一数据库；保留显式 V4 覆盖项，不再要求额外 Reader DSN。
2. 开发候选服务直接绑定 PG snapshot schema，`/api/v4/*` 经 PG reader/BFF 读取；该分支不构造文件型 accepted-Head reader，不读取 UI authority 文件来选入口，也不启动日更 worker。
3. 候选 reader 校验 PG snapshot identity、descriptor 和数据 manifest；股票、板块、Focus/Forward、市场、诊断和操作状态从 PG 投影读取。
4. Owner 与 Membership 运行路径移除本地快照回退；Membership schema 从 Head-bound binding 读取。
5. Product BFF 移除 R1 read-index、FEP `MODEL_CATALOG.json` 及单位注册表文件回退；缺少 PG 投影时显式降级。
6. Product 启动缓存减少对本地 authority、manifest 和 Owner/source 文件签名的二次依赖，改校验 Head-bound PG Catalog 与数据库身份。
7. 股票历史图在候选模式下按 T0、Head token 和 source digest 唯一匹配 PG history version；不再从 workspace 路径或本地指针选历史表，来源不唯一时明确返回缺口。
8. 回放/比较新增候选快照路径：正确标注事后重建、严格 PIT 证明不足时不显示为 PIT；后续观察保持独立区。
9. `/api/operations/status` 和诊断 Jobs 页面展示 PG snapshot 的 T0、记录数及“无日更 worker/无作业进度”真实状态。
10. 新增合同版本与审批事件 PG Registry 迁移，落实 append-only 约束及 Accepted publication 的合同绑定校验。

本轮增量实修：日更 Owner/生命周期、Membership、Sector、Calendar、Predecessor 读取统一走 PG 绑定；在线 operational Head 缺失时停止读取冻结文件回退；read-index R2 authority 改为 candidate/Head 内嵌的 PG binding；Core BFF 与服务缓存不再用 workspace Head 文件或 R2 JSON 选择运行入口；source capture 的 calendar 由 PG publication Head/contract binding 提供；日更路径与 TDX source/cache roots 复用中央路径解析器；更新日更候选绑定后的 transport 再进入 CAS；修复 PG 板块名查询以同时匹配 canonical `display_name`。这些改动覆盖真实读链，但不等同于稳定 ID 正式核销。

续作增量实修：`v4_operational_owner_authority_v2.prepare_successor()` 现在先通过专用 predecessor PG ingress 固化一次候选 predecessor，再从 PG 读取用于 Owner 复用；相同来源绑定的 Owner 复用路径仅检查 PG fact 和摘要，不再要求旧 payload 文件仍存在。新日期/新来源仍只在明确 ingress 分支读取原始 payload 后写入 PG。`operational_daily_owner_v1.py` 与 `r43_operational_sources.py` 的 TDX root、BaoStock request-ledger 改为 `config/paths.yaml` 中央解析器。`research_bff.py` 新增 `/api/v4/candidates/cohort` 的 PG snapshot 只读路由，复用同一个 Forward projection，明确关闭生产接受、正式入组和 PIT 资格。

2026-10-18 继续实修：新增 `V4_HISTORICAL_SOURCE_INGRESS_PG_R1`，将确切路径和字节摘要绑定的历史业务输入固化到同一个 `market_research` PostgreSQL 的 append-only Forward fact store，并提供 PG-only 后续读取及 G 盘临时物化。已从现有 V4 绑定图导入并读回 **643 条**来源事实（Forward facts 表约 **38.3 MB**）；没有导入或切换 Accepted publication/Head。稳定来源 ID 使用规范相对路径 SHA-256，运行消费者不再内嵌 evidence/report 路径。

续作增量实修：Operational Owner 对旧 Head 直接绑定的 source payload 增加 `PG ingress → 精确字节解析 → 新 Head-bound PG Owner fact` 迁移路径；历史 Owner authority 文件缺失时，以旧 Head 的日期/Owner 精确 binding 作为一次性 source selector，不再要求该 authority JSON 存在。`v4_operational_owner_pg_closeout.py` predecessor 入口也改为从 PG ingress 读，不再另开本地读取口。DM-01 stage-state 复用既有历史 ingress Forward facts schema，避免新增未预置的 workspace schema；对应已有共享表增加路径+摘要与 source ID 索引。两索引在 `market_research` 实例 `v4_forward_213e535c50ad7135` 创建并读回；Stage authority 的 12 项 PG 绑定读取由约 29 秒降至约 2.9 秒。现存 `data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json`、其 predecessor archive 和已删除的 Owner authority 文件路径尚无历史 ingress 行；当前代码会在合法 source ingress 时固化前两者，缺失文件不被伪造。

本次真实代码改动覆盖 5 个运行时模块及 2 个 PG ingress/CLI 模块：`r43_owner_replay.py` 与 `v4_current_stage_authority.py` 的现行/冻结 Head、来源绑定、采集合同及历史 owner 输入改为 PG ingress 读；R43 replay 输出 workspace 移至 `data/v4/workspaces/r43_owner_replay_v1`，TDX root 经中央解析器；日更 Owner 与 R4.3 来源重建通过 PG 来源事实读取 acquisition、phase-0、V4.02 acceptance、stage manifest、事件、策略和分日 typed-delta；Lifecycle 产物改追加到 DM-01 stage-state PG 并由其 descriptor 绑定进入 special-phase manifest。正式 Head 未移动。

本次最小实际验收：`CurrentStageAuthority` 从 PG ingress 重建当前 V4-15 authority view，返回 T0 `2026-09-30`、8 个不可变 Owner 绑定；真实 V4.02 acceptance/stage、22 条特殊阶段事件和策略从 PG 组装 special-phase manifest，返回 `READY`；6 个修改 Python 模块及一个 CLI 脚本 `py_compile` 通过，暂存区 repository policy 通过，`git diff --cached --check` 通过。未执行大测试套件。

本轮新增最小验证：9 个变更 Python 模块及 CLI `py_compile` 通过；`CurrentStageAuthority` 当前 PG ingress 读回 12 个绑定（约 2.856 秒）；旧 Operational Head 绑定下 `diagnostic` Owner 实际通过 PG SourceIngress 解析为 10 行；未运行全量测试。

## PostgreSQL 实例操作

直接使用现有 `127.0.0.1:5432/market_research`，没有创建 Reader DSN 或新实例。已应用 `043_v4_contract_registry_approval_events_r1.sql`，登记迁移校验值，并写入及读回校验 7 个源文件合同版本为 **DRAFT**（逐字节摘要、版本及源修订一致）。审批事件、Accepted publication、正式 publication Head 仍均为 0；没有改动正式 Head。

续作代码修复：`configured_reader_dsn()` 不再识别或要求单独的 `V4_NATIVE_PG_READER_DSN`，而是复用 `configured_dsn()` 所选定的同一实例身份；每个读事务仍由 PostgreSQL 强制 `READ ONLY`。移除了“高权限账号必须再设置 `V4_NATIVE_ALLOW_PRIVILEGED_READ_ROLE=1`”的重复准入门槛；读取前仍校验目标 schema 存在及事务只读状态。源码编译通过；本次 PowerShell 子进程未继承连接环境变量，故没有另行运行命令行直连，既有候选服务浏览器读链结果见下节。

候选快照为现有 PG snapshot，T0 `2026-09-30`：股票 5,213、板块 378、Focus/Forward 各 117、事件 33。它仍是候选快照，不构成 Accepted authority。

## 28766 内置浏览器验收

通过 Codex 内置浏览器在 `127.0.0.1:28766` 实际操作；候选服务使用真实 PostgreSQL 数据：

- 总览：5213 股票、378 板块、117 雷达及 117 Forward 显示；市场四轴与 33 条变化事件可读。
- 板块：检索“煤炭开采”返回真实 PG 结果；详情成员及字段可读。
- 个股：检索 `600675` 显示“中华企业”；详情、行情值可读。历史图在 Head/source 不匹配时显式停止拼接。
- Focus/Forward：显示 Focus 469 条锚点、Forward 117 个样本、585 条期限计划、5 条已发布结果及 0 个成熟样本；未宣称胜率或收益分布。
- Focus 真实搜索 `600675` 后返回 1 条中华企业（SH.600675）；市场页展开上证指数真实历史图，页面显示指数收盘 3842.19、原始成交量单位待核实。
- 市场：2344 涨、2712 跌、155 平、13 未知，市场分母 5224、实际行情 5213；指数、涨跌停和事件区域显示。
- 诊断：health 4 项真实记录；Jobs 页显示 `PG_CANDIDATE_SNAPSHOT`、T0 和计数，并明确没有启动日更 worker。
- 回放：真实操作选择中华企业和“事后重建对照”，显示实际收盘 2.520、成交额 323885760、成交量 135013893；页面明确声明这不是 PIT。严格 PIT 可用日为 0，且未伪造 PIT 结果。
- 比较：真实操作运行“股票 vs 市场”，中华企业收益来源标为不完整；同窗 Universe 基准显示 -0.136%，并标注共同起止日。
- 本轮重启后再次在内置浏览器打开“煤炭开采”详情：实际 URL `/v4/research/sectors/INDUSTRY%3AT010101`，读取 25 个成员、当前宽度/相对强度及成员详情。缺少前序 PIT 成分股的历史轮动值显示“来源能力不足”，页面明确未用当前成员回填。
- 同一现场再次确认首页仍显示 PG 候选快照、T0 `2026-09-30`；Compare 严格 PIT 可用日期 0。Shadow 路由显示 `NO_REAL_SHADOW_DATA`、真实样本 0，故浏览器验收为部分通过，不能报告全模块 PASS。
- 本轮代码更新后重启的 28766 服务再次在 Focus 页面实际搜索 `600675`，呈现中华企业 1 条 Focus 结果、Forward 117 样本及 585 期限计划；数据为同一 PG 候选快照。修复前该快照模式的独立 `/api/v4/candidates/cohort` 返回 `ROUTE_NOT_FOUND`；修复后浏览器真实 HTTP 读回 200、`domain=forward`、117 项总数、2026-09-30、数据库身份 `market_research/646711`，并含 `contract_id=V4_PG_CANDIDATE_COHORT_READ_R1`、`production_accepted=false`、`cohort_enrollment_enabled=false`、`PIT_ELIGIBLE=false`。

以上为候选 UI 功能验收，不是生产验收。开发服务端口为 28766，未触碰 28765。

## 验证与准入

- 聚焦验证先前执行结果：29 passed；3 项被仓库测试隔离插件以 `DISPOSABLE_PG_CLUSTER_REQUIRED` 拒绝连接共享实例。未绕过隔离器；真实数据库行为已通过本任务授权的迁移/读写读回和浏览器链路核验。
- `git diff --check`：通过（已统一相关源码换行）。提交前仍执行暂存区仓库准入策略。
- 未运行 GitHub CLI 流程测试、重复全仓基线扫描、大型 pytest 或 GitHub Actions。

## 未完成项与单独授权边界

- 任务卡原始稳定 ID 总数 **266**，正式关闭数仍为 **0/266**。冻结矩阵原始计数为 PG-only code pending **54**、ingress adapter open **9**、OPEN **203**、未映射引用边 **22**；冻结摘要出现 53/10/203 的一项分类差异，本轮未改分母。只按原矩阵与本分支源码路径做 delta，发现 **66 个稳定 ID 的主 source_file 落在本分支已改路径**（冻结状态分布：40 PG-only pending、6 ingress open、20 OPEN）；“路径被改”不代表这 66 项都迁移或关闭，未逐 ID 精确核销者仍全部保持未关闭。活跃残留包括 `v4_operational_owner_authority_v2.py` / `v4_operational_owner_pg_closeout.py` 中历史 Head/authority 初次导入边界、`operational_successor_release_v1.py` 对 Operational Research Head 的文件 CAS/恢复、`v4_current_stage_authority.py` 的冻结 Stage/Head 读取，以及 Owner/Head/Publication 缺正式 PG accepted row 导致的下游阻断。非 V4 引用只登记。
- 7 份导入合同均为 DRAFT，没有批准事件；publication/head 表仍为空。不得将其称为正式接受或 Head 切换。
- 仍需单独授权：正式 Head CAS/切换、生产 28765 部署、物理删除及 Git 强推/历史重写。正常提交和推送不包含上述操作。
- GitHub Issue/PR 状态更新连接器此前返回 HTTP 403，本轮不通过 GitHub CLI 绕过。

稳定 ID 对照说明：现有冻结 inventory 中 **85 条**记录的 `source_file` 出现在从 `4a69c4c` 到当前 HEAD 的改动路径中；此数字不是修复数或关闭数。实际代码修复按上列 10 组和本报告具体改动描述统计，稳定 ID 正式关闭仍为 0/266；未逐条完成语义证据核销的记录均保持未关闭。

本报告如实区分代码层修复、真实 PG 候选验收与正式 authority closure；提交/推送不代表生产发布。

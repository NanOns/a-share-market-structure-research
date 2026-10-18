# V4 R21-R6 开发全权限连续实修进度 R2

- 状态：`DEGRADED_PASS`，继续实修；尚未达到全模块验收。
- 授权：2026-10-18 Drive 任务卡与长期开发授权 SOT R2。开发期 PostgreSQL DDL/DML、迁移、SourceIngress、Owner、合同和候选 Head 写读均已授权；生产切换和最终打包仍后置。
- 运行边界：开发分支 `codex/v4-workspace-cleanup`；唯一 PG `127.0.0.1:5432/market_research`（OID `646711`）；开发服务 `127.0.0.1:28766`。现场监听只有 PG 5432 与开发 28766；28765 未监听、未触碰。

## 已完成的代码与 PG 实修

- `src/workbench_db/v4_native.py`、Owner workspace mapping 与迁移 046/047：加入稳定 workspace logical ID/PG alias、保持只读读路径，并让已授权共享 PG 配置可用于开发写入。两项迁移在唯一 PG 应用并读回；4 个 ACTIVE alias 解析到原有 schema。搬动模拟确认 logical ID、history/publication namespace 与 Owner mapping 稳定。
- TDX 官方 2026-10-16 包：ZIP 校验通过，12,205 个条目，549,184,442 字节，SHA-256 `c0ea0dff…3248219`；抽取 5,567 根目标日 bars。包首见时间在 10-18，故只作诊断候选，未宣称 PIT 或 accepted。
- 将精确 TDX 目标行集作为 1,502,467 字节 SourceIngress 原始绑定写入 PG，并完成字节读回；创建 5,567 行 `core` Owner、Owner authority manifest 和 `development_head_candidate`，均从 PG 精确读回。
- 修复 `dm01_corrected_source_capture_v2.py`：临时 smoke 收据可绑定在配置的 G 盘 ingest temp root；绝对临时路径只用于内存中的 staging-only manifest，Durable runtime loader 仍只接受仓内收据。6 项路径/归一化定向测试通过。
- BaoStock 2026-10-16 同日快照实际捕获完成，幂等重跑为 `NOOP_SOURCE_ALREADY_FROZEN`：5,226 条日线、48 条归一因子；另保留 48 条 SDK 原生 `adjustFacto` 因子响应。2,599,570 字节 BaoStock 快照和 9,404 字节原生因子响应以精确绑定写入 PG SourceIngress 并读回。
- 扩展开发 Owner 候选 v1.1 到 4 域：TDX `core` 5,567 行、BaoStock 日线 5,226 行、归一因子 48 行、原生因子 48 行；Owner authority 和 `development_head_candidate` 均做 PG 全量读回。所有候选均 `DIAGNOSTIC_ONLY`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`，没有更新现行 accepted Head 或 publication。BaoStock 请求预算 ledger 记录本轮 11 次公共账本操作，修正捕获另外使用 G 临时区预算账本。
- 交叉核对：5,216 个共同证券中，close 与 volume 一致；4,883 个 amount 严格不等（最大绝对差 508.46 元、最大相对差约 `1.29e-7`）；集合差 361，其中 TDX-only 351 个全为北交所，BaoStock-only 10 个。严格合同不设容差，原值和差异均保留，未提升为业务源。
- 两项 `DRAFT_DEVELOPMENT_DIAGNOSTIC_ONLY` 合同已按精确字节 SHA 登记 PG，无审批事件。Owner 候选合同扩至 v1.1.0；PG `contract_versions` 19 条、审批事件 16 条。
- 修复 `_existing_downloader_package` 把 TDX 收据路径固定到旧目录的问题，现按配置 snapshot root 校验；定向回归测试 1 项通过。该代码修复已提交并推送：`f467f2ad6`。

## PG、28766 和功能验证

- PG 事实：`v4.contract_versions` 19 条、审批事件 16 条；`dm01_data_accepted_heads` 1 条。现有 `publications`、`publication_heads`、`operational_research_heads` 与 accepted 市场日历为空。BaoStock `query_trade_dates` 实查 10-16 为交易日，并存为 PG 诊断日历候选；补齐身份/namespace 后正式市场日历读取仍明确返回 `NO_ACCEPTED_PUBLICATION_HEAD`，不伪造 accepted 日历或源接受。
- 28766 仍服务 PG 候选 T0 `2026-09-30`：股票 5,213、板块 378、Focus 469、Forward 117、事件 33；只读、生产权限关闭、日更 worker 未启动。
- 对 28766 做了 41 个 API 请求（context、列表/详情、股票图表、Market、Events、Focus、Forward、Sources、Diagnostics、Replay/Compare）及 6 个产品页 HTTP 请求。有效数据路由为 200 且上下文 token 一致；明确返回 `SOURCE_INCOMPLETE` 的域保留该状态；Replay/Compare 因无首可用时间证明返回 `PIT_NOT_AVAILABLE`。服务返回的 8 个页面/静态资源与本仓 `static/research` 文件 SHA 全部一致。
- 28766 页面交互已有 R5 同日真实浏览器矩阵覆盖（板块、股票详情、Focus/Forward、Market、Diagnostics、Compare、Replay、数据更新页）；该矩阵标明 candidate context 和 PIT 限制。R6 本次续行再次调用 Windows UI 自动化时，工具无法可靠判定 Chrome 当前 URL，故未绕过，也未声称新增浏览器验收。
- 在当前有效 `V4_CURRENT_ACCEPTED_READ_CONTRACT_V1` 绑定下，实际依次读取 summary、radar、entity、sector、cohort、settlement、health 七个产品模块，并将精确合同、PG context、七模块结果摘要追加为 `VALIDATED_CANDIDATE_PENDING_PUBLICATION` 事实，再从同一 PG descriptor 读回验证。候选 T0 为 2026-09-30；`accepted_head_changed=false`、`workspace_authority_changed=false`。这是七模块 PG 读链执行证据，不代表 publication/Head 被接受。
- 28766 续行 API 探针：context、home、sectors、stocks、focus、forward、market、diagnostics health/jobs、cohort candidate 共 10 个路由均 HTTP 200，PG context token 一致；Jobs 按预期返回 `SOURCE_INCOMPLETE`，市场事实事件保留 `SOURCE_UNAVAILABLE`。开发服务仍只监听 28766，PostgreSQL 为单一 5432 PID `8640`；28765 无监听。
- 实跑 `scripts/run_v4_dm01_daily_increment.py --target-date 2026-10-16 --typed-scope-v2`，准确返回 `BLOCKED_MISSING_INTERMEDIATE_SESSION:2026-10-08`，BaoStock 数据源请求 0 次，accepted data Head 未动。随后以 10-08 作为最早缺口执行 G 临时目录下的诊断候选模式；官方 TDX 页面与更新元数据各有界读取一次，实际最新发布日为 10-16，因此状态 `WAIT_TDX_PUBLICATION`。页面/更新回执仅落 `G:\\codex_tmp`，对应 `source_readiness` PG 阶段事实已读回；未下载日线 ZIP、未请求 BaoStock、未建数据候选或提升 Head。连续日更的真实阻断现已定位为历史中间日官方 TDX 包不可用，不能以 10-16 包倒填 10-08 或伪造 PIT。
- 将该 gate 的原始官方页面证据追加到 PG SourceIngress 并精确读回：HTML 25,379 字节 / SHA-256 `d1fc6a295bc618e741fd552b9e6bc60c71846aa1e4053c0212c5e03b58404130`；更新元数据 120 字节 / SHA-256 `88289590fcfa5906ec058021999e623111396dbcf27340a5c1f71219510edf8a`。来源记录均标记 `TDX_OFFICIAL_DAILY_PAGE_CAPTURE`；保留 G 临时回执作过程证据。

## 验证、清理与未完成项

- 已通过：此前 22 项 PG/namespace/Owner 定向测试；本轮 TDX 收据路径回归 1 项；`git diff --check`、暂存策略及提交推送正常。
- 已清理 G 盘可重建 pytest/pyc/pip 缓存 2,674,361,197 字节。大型 `G:/codex_tmp/r7_active_baseline_20261015` 含改动源码及独有材料，尚未逐项归属，保留；未动 TDX 只读源或无关文件。
- 后续继续项：恢复可用的开发 PG publication/calendar/Head 输入链，再运行正式目标日期运行接受、完整 DM-01 日更冻结与 Core/全模块业务 Head 联调；继续现役 V4 业务文件读取收口和 Focus/Forward/Market/Cohort 接线；按任务授权逐项清理已确认无消费者的开发衍生物；补完 28766 浏览器交互矩阵。
- 证据仍不支持全模块验收。生产切换和最终生产打包保持关闭，必须等全功能验收通过并由用户另行明确启动。

## 用户再次确认开发 PG 全权限后的续行实修（2026-10-18）

- 将 `focus_daily_stage` 自动执行门禁由本地 JSON 文件读取改为精确绑定的 PG SourceIngress 字节读取。代码固定合同路径、SHA-256 与 180 字节长度；PG 不可用、事实缺失或身份错误时 fail-closed，不回退读取工作区文件。当前门禁继续保持关闭，原因来自 PG 读回的原合同值：等待真实次日接受及多日 Forward/到期结果接受。
- 在唯一 `market_research` PG 中一次性登记 `config/focus_daily_pipeline_gate_v1.json` 原始字节：SHA-256 `8d398694d8df852d2f623d74538afc4e77358a5de394ee2364c43a5fba7daaa2`、180 字节；同路径/摘要精确读回，并从运行函数默认路径实测得到 `(False, REAL_NEXT_DAY_ACCEPTED; MULTI_DAY_FORWARD_AND_DUE_OUTCOME_ACCEPTANCE_PENDING)`。
- `tests/upgrade_v3/test_focus_07a_post_sync_stage.py` 定向验证 9 项通过，覆盖 PG 字节入口、不可用时关闭、既有 Focus preflight/apply 顺序和同步身份检查。`git diff --check` 通过。该修复关闭一个仍由 V4 运行时直接读取业务配置文件的调用点。
- 28766 当前 HTTP/API 服务仍为 PG 候选上下文；本次 UI 自动化工具在无法确认 Chrome 当前 URL 时拒绝继续，未绕过。既有 R5 浏览器页面操作矩阵仍是最近一次真实浏览器验收证据；本次未运行日更/采集、创建正式 publication 或切换 Head。

## 本轮续行实修与核验（2026-10-18）

- 修复候选构建中两个迭代器被消费的问题：`corrected_structure_replay` 和 `corrected_sector_replay` 先物化同一日期输入后再供下游复用。重建 2026-09-28、09-29、09-30、10-08 四日 Owner 候选；Profile/Structure 均有完整运行行，Sector 每日分别得到 5,222、5,222、5,222、5,224 条成员和 83 个行业，行业相对强弱已知 5,135、5,137、5,135、5,129 条。其依据仍为日期有效重建分类，不是 PIT/accepted。
- 修复 Focus/Forward 输入适配：精确登记所需配置、日历、状态与序列描述符到 PG SourceIngress，并从 PG 字节读回；时间序列描述符由 PG 读取、行情行通过专用不可变序列表读取。当前四日合计 505 个 Focus episodes、1,307 个 events；Forward outcomes 为 OBSERVED 518、PENDING 2,007，未将待观察状态伪装为已接受结果。
- 修复历史 Owner 和压缩 Focus 历史输入的 PG 字节读回路径，支持 32 MiB 分块 SourceIngress 与流式 gzip 解压。本轮把 67,226,640 字节 Owner 历史包按精确绑定写入 PG 并读回；此前已登记的 551,726,664 字节 TDX 包仍在 PG。当前 Owner SourceIngress 汇总 78 条、494,213,060 字节；此数为事实行合计，不含另列的 TDX 大包。
- 修复 `stock_prewatch.load_package` 的 PG 字节包装对象身份比较；修复 FP05 市场历史绑定校验对已移除 `production_v4.reference` 符号的依赖，改为仓库根目录约束下分块 SHA-256 校验。
- 完成 Sector/Market Rotation 实际重跑。Market Rotation 四日输出均为 `UNKNOWN` 83 个行业；10-08 的 B0 为 TRUE 21、FALSE 32、UNKNOWN 30。该输出是有效的阻断证据，不能解释为模块业务验收完成。完整候选链状态为 `CORRECTED_OWNER_CANDIDATE_READY_PENDING_RELEASE_QA`，`production_admission=false`、`data_head_moved=false`、本轮 SourceIngress 自动请求数为 0。
- 本轮在 28766 对 context、home、sectors、stocks、focus、forward、market、diagnostics/health 八个 API 端点重新请求，均为 HTTP 200；现场仍只有开发 28766 和唯一 PG 5432 监听，生产 28765 未监听。真实页面交互最近一次有效证据仍是 R5 浏览器矩阵；本轮未新增浏览器验收。
- 回归：针对 Owner replay、Stock Prewatch、DM01 诊断日历的只读 PG 定向套件为 187 passed、1 deselected（6.72 秒）。被排除用例 `production_and_v4_09_acceptance_stay_disabled` 属历史冻结治理 profile，执行时将仓库根映射为历史临时快照，并尝试读取该历史根对应、当前不存在的 PG schema；它不构成当前 PG 候选的失败证据。此前未带只读 PG 定向开关的尝试在收集期被安全隔离插件拒绝，未产生写入。
- 尚未完成全目标：所有现役 V4 业务文件读取迁移、工作空间消费者盘点/清理、完整模块业务 Head 连通、日更真实接受链、浏览器交互复验仍有缺口。现存显式数据阻断包括 2026-10-08 官方 TDX 日包暂不可用（不得以 10-16 倒填）、Market Rotation 核心输入未知、无 accepted calendar/publication Head，以及 Focus/Forward 多日结果待真实接受。当前只到开发候选与 API 验证，不是全模块验收。

## FP05 与历史 Owner 收据的 PG 读链收口

- 根据暂存准入策略发现并改正两处现役代码仍直接读取历史报告的路径。`scripts/build_fp05_market.py` 现通过 `ingress_path`/`load_bytes_binding_pg` 读取执行上下文、历史日报收据、历史行业指数、市场阶段序列、历史市场分类、合同和价格影响配置；压缩流与 GBBQ 均从 PG 读回字节解析。Owner pipeline 的当前 TDX source-capture 收据和其绑定收据也改为 PG SourceIngress JSON 读回。
- 实际将 FP05 三个历史文件和 Owner 收据/绑定按精确路径、SHA 与字节数登记/读回 PG；例如两个 gzip 输入分别为 234,720 字节（`898a6554…1bdaedb`）与 356,287 字节（`89aae848…a9b139`），Owner capture receipt 为 3,019 字节。`tools/git_repository_policy.py --staged` 在这一修正后通过 16 个变更 blob 的准入检查。
- 新命名空间 FP05 实跑到历史行情绑定处后 fail-closed：日报收据指向的历史坐标行情包 SHA 为 `7d67a7d4…79ff8c7`；仓内同路径只有 133 字节且 SHA 为 `aebc94d8…c9cbbdc`，PG 精确 source 和 package 也都不存在。未用占位文件替代，未生成 FP05 市场产物。符合 R2 新运行路径机制的空 ENTRY 记录已移出仓库并保存在 `G:\\codex_tmp\\r6_fp05_blocked_start\\fp05`。继续完成 FP05 需要恢复这一精确历史输入或基于已接受源重建并重新绑定其历史合同。

## 最新连续实修补充（2026-10-18）

- 更正上节 FP05 阻断结论：已从仓库 `.git/lfs/objects` 找回收据指定的 52,034,710 字节 LFS 原始包（SHA `7d67a7d4…79ff8c7`），通过分块 SourceIngress 写入/读回 PG；未改动 133 字节跟踪指针。FP05 实际产出 `MATERIALIZED`：9/30 `WEAK / IMPROVING / THIN / LOW / DECLINING`，5224 个历史证券。
- FP06、FP07、FP08、FP09 均以 PG SourceIngress/序列输入完成候选运行：Sector 5224 行/378 板块；Stock 1,309,832 根日线/5224 证券；Focus 469 episodes/766 events；Market Center 完成 5 个指数、5224 个对象规则与 5213 条实际行情的独立计算。所有产物留在 R2 候选命名空间，未更新 accepted Head。
- FP10 将市场/股票 authority、日历、历史 T0 冻结和日线价格输入改为 PG 精确绑定；新增共享只读 PG 序列校验作用域，避免每个样本重复验证 1,309,832 行快照。当前重跑尚在计算，尚未生成最终 Forward authority/结算收据；不得计为完成。
- FP12 已在候选 namespace 构建 9/28–9/30 三日回放目录；严格 PIT 日期为 0。FP13 在 28766 上完成独立行情/板块/Focus/Forward/Market 数值核对，写出 110 行字段矩阵；复查发现并移除残留 SQLite 路径，所有候选快照查询改走 PG。
- 28766 浏览器实测首页、板块、个股、Focus、市场事件、诊断、回放和比较页面可加载。当前可见候选值与历史 T0 数据一致；Replay API 为 `PIT_NOT_AVAILABLE`、0 条日期，Focus 路径字段仍有缺口，Sector Rotation 资格仍为来源不足，不能视作全模块验收。`/api/v4/diagnostics/health` 与 jobs 路由可用；旧式 `/api/v4/health` 不是有效路由。
- 变更脚本编译通过；相关定向回归本轮 36 项通过。4 个 FP05 PG 写库用例因要求隔离 PG 实例而被仓库安全插件拒绝，未在共享业务库上绕过隔离；两份冻结历史测试在收集期因导入已删除的 `production_v4.reference` 失败。此限制不影响已完成的真实候选运行及 28766 验证。
- 工作空间收口：本轮 FP05–FP09、FP12/FP13 的 ENTRY/原始回读/矩阵均移至 `G:\\codex_tmp\\r6_daily_evidence`，仓内对应生成目录已清空；阶段保护检查改为基于 Git 跟踪的代码、合同配置和 V4 data Head，抽查 2,959 项全部未变，避免对 60,134 个仓库文件做全盘哈希。
- FP10 运行剖析显示重复读取同一 T0 冻结快照造成大量重复 PG 索引往返；ForwardStore 已加入不可变事实读缓存，并消除初始化阶段重复读取冻结记录。先前中断前已写入的 facts 保持追加幂等，将在优化后的新运行中复用。

## FP10 候选 Forward 投影完成（2026-10-18）

- 缓存版 `scripts/build_fp10_forward_v2.py` 成功完成，PG 候选 authority 已落在 `data/v4/r2_daily_candidates/20261018_r6/v4_forward_operational_authority_v1.json`；发布内容按 SHA 绑定于 `data/v4/fp10_forward/`。候选数据规模：117 enrollments、585 plans、585 outcomes、117 T0 freezes。
- 本日 `2026-09-30` 没有真实到期计划：`settlement_gate=NO_REAL_DUE`、due_count 0、actual_price_reads 0。585 个 horizon 当前均为 PENDING，mature eligible 为 0，胜率/收益分位不计算；历史权限未变，严格 PIT 未授予。此为真实生命周期推进结果，不是业务验收通过。
- 所有本轮 R2 过程回执（含成功的 FP10 readback 和前次中断/重跑入口）均已移至 `G:\\codex_tmp\\r6_daily_evidence`，不提交原始证据或过程输出。
- FP10 缓存改动回归复验 `tests/test_r2_forward_daily.py` 与 `tests/test_v4_21_forward_observation_contract.py`：32 passed（0.20 秒）。此前首次复验中发现的 `__new__` 测试工厂兼容问题已修复。

## 联合发布校验器适配 PG R2 descriptor（2026-10-18 续行）

- 修复 `src/workbench_service/joint_release.py`：联合候选现可直接校验 `V4_PG_RESEARCH_SNAPSHOT_R2` descriptor，先经 PG snapshot `read()` 校验不可变表内容与数据库身份，再从 descriptor 内嵌 metadata 校验 SourceIngress 来源与 Owner 绑定；旧文件 manifest 仍走原路径。
- 新增 snapshot context-token 解析，PG descriptor 使用其 `logical_digest` 对应的 `research-v4-pg-candidate-…` token；旧 authority 继续使用 manifest SHA token。全产品 QA 与连续日更候选门禁统一调用该解析器，避免把 PG 候选误判成不同 snapshot。
- 新增 `tests/test_v4_joint_pg_descriptor_binding.py` 隔离回归：descriptor 联合候选校验和缺失/错误 digest 关闭路径共 2 项通过（0.09 秒）。此处没有执行 release CAS、没有改写 Joint authority、没有移动业务 Head，也未访问生产端口。
- 实际 28766 当前 context token 与其服务 PG schema 的 snapshot logical digest 一致（`research-v4-pg-candidate-7461…9e6a`）。服务仍是 2026-09-30 的候选预览，operational scope 未绑定；这次修复解决校验格式差异，不把候选 preview 提升为发布验收。完整验证与 Head/namespace 联调继续进行。
- 对 28766 真实运行 44 条 HTTP 功能矩阵，所有请求 HTTP 200，覆盖六入口、来源/诊断、Forward、Replay/Compare、个股图表六种 D/W/M×RAW/QFQ 组合，以及个股/板块/Focus 详情。发现 8 个仍准确标为缺源或候选状态的能力：FEP 当前日 inference Owner、媒体/官方事实事件源、日更 worker receipts、严格 PIT 与 Compare 证明、个股结构 timeline 字段、Sector 历史成员轨迹、Focus 到期 outcomes。原始矩阵在 `G:\codex_tmp\v4_28766_function_matrix_20261018.json`，仅过程证据不入 Git。

## Structure Owner 时间线与完整候选重建（2026-10-18 续行）

- 新增 `scripts/build_v4_stock_structure_candidate.py` 与 `build_snapshot` 的候选 Owner 投影：七个日更模块 authority 与 Owner runtime manifest 首次按原字节进入 SourceIngress 并精确 PG 读回；构建时继续从 PG 解压/读取候选 Structure runtime rows，校验 manifest、日期、Head、每行 lineage 与 event 候选标记。
- Structure Owner 输入为 `V4_12_R13_RUNTIME_CANDIDATE_MANIFEST`，manifest 7,758 字节（SHA-256 `55ad2c6d…ba2afc82`）；`runtime_security.jsonl.gz` 36,899,143 字节（SHA-256 `b46386ae…650243bf`）。读取 5,224 行，其中 5,213 条绑定当前证券 Universe，11 条明确计为非当前 Universe；输出保留 `RECONSTRUCTED_CORRECTED`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`。
- 生成完整不可变 PG 候选 schema `v4_research_7f5f6c66a4681999ca5420f5`，logical digest `91b4066e…2ec116935`；包含 stocks 5,213、sectors 378、focus 469、forward 117、settlement 585、events 33、market 1，以及 stocks/sectors/market/focus/forward/replay/Structure 共 8 个 PG domain features。未移动 Data Head、Joint authority 或 accepted Head。
- 仅将开发端口 28766 重启并绑定该 schema（PID 33460）。实际 46 条 API 功能矩阵 0 个 HTTP 失败；股票日/周/月×RAW/QFQ 六种图表全部 `READY`。有 Structure 事件样本返回 2 个事件+1 个锚点、`READY`；已知无事件样本返回 `EMPTY_VALID`，不再误报缺源。12 个前端页面/脚本资源 HTTP 200。过程矩阵保存在 `G:\codex_tmp\v4_28766_function_matrix_20261018_r2.json`。
- 清理本轮失败试跑产生且未被任何 authority/alias/服务引用的候选 schema `v4_research_a2c230b897102db46262f9e0`；活动 28766 schema 保留。端口复核仍只有 PG 5432 与开发 28766，28765 未监听、未访问。
- 剩余 7 项业务态保持准确关闭：FEP 没有当前日模型推断 Owner；无已批准官方/媒体事实事件数据集；候选不含日更 worker receipts；严格 PIT/Compare 首次可知证明未授予；Sector 历史成员篮子未发布；Focus outcomes 尚无到期发布。当前 UI 是完整开发候选，不是全模块验收或生产切换。

## 日更准入与补充业务读链（2026-10-18 续行）

- `continuous_daily_release.promote` 与 `activate_r2_daily_successor` 现在按 Joint Head 中的 admission 路径/SHA 读取精确 PG SourceIngress 字节；配置、证据和实现 binding 不再由该调用点直接打开工作区文件。SourceIngress helper 支持既有 authority 只提供 path+SHA 的紧凑 binding；PG readback SHA 与 Head 一致。此次读取将当前 admission 及其证据/实现事实写入唯一开发 PG，所有记录均按原始 SHA 定位，没有提升外部签发或生产接受状态。
- `joint_release.validate` 对快照 manifest、数据源、UI 资源、Owner publications 和 PG descriptor 改为按精确 binding 从 PG 校验/读回。发现并修复了一处实际 workspace drift：`reports/v4_13_runtime_r16/real/2026-09-30/r6/profile_advanced.jsonl.gz` 的仓内副本与 Head SHA 不同；PG 保有 Head 指定的 37,627,535 字节原版本。全候选 PG-bound validation 最终读验了 50 个 manifest source，T0=`2026-09-30`、七个 domain feature 完整，`full_product_release=false`、`trading=false`。
- 尝试把同一 admission 刷新进 Joint control authority 并使用 28766 做 CAS 健康读回时，健康门发现候选 manifest token 与正在服务的 PG candidate schema token 不同而拒绝；Joint CAS 按契约恢复了原 authority，admission 文件也恢复到提交版本。具体现状：authority 指向 manifest digest `d9d052…e72f3`，28766 提供 token `research-v4-pg-candidate-7461…9e6a`。因此没有报告开发 Head 刷新成功；该处仍是实际的 28766 Head/namespace 集成缺口。28765 未访问。
- 修复 `corrected_owner_replay.materialize_core`、`r43_owner_replay.materialize_core` 对 accepted-chain `IDENTITY_UNIVERSE`/`TRADING_STATUS` artifact 的直接文件读取，改为按链内 artifact SHA 读取 PG bytes。R43 GBBQ 下游由 PG 精确 bytes 直接解析，取消原本的仓内临时镜像和二次文件读取。实测当前链 3 个日期、6 份 artifact 共 31,338 行，两生产器读到完全相同 payload；R43 GBBQ 5,613,070 字节解码 193,554 条事件，摘要与 PG binding 一致。
- 本续行新增验证：Forward/Joint 定向测试 13 passed；Forward 子集 5 passed；上述 Head-bound PG validation 通过。28766 的全候选健康 CAS 未通过，原因是服务注入 schema 与联合 authority manifest 不一致，已按 CAS 机制回滚而非强行改写。

## 28766 浏览器交互续验

- 在已运行的 `127.0.0.1:28766` 实际浏览器页进入“数据与诊断 → 日更与失败状态”，页面与 API 均返回同一候选上下文：T0=`2026-09-30`，事件33、Focus469、Forward117、Market1、Sector378、结算5、来源4、股票5213。展开“查看快照缺口与日更状态”后证实 `SOURCE_INCOMPLETE`、`worker_started=false`、`source_requests=0`，原因 `PG_CANDIDATE_DOES_NOT_CONTAIN_DAILY_WORKER_RECEIPTS`，策略 `NO_WORKSPACE_RECEIPT_FALLBACK`。
- 市场页实测显示盘后截面、宽度分母5,224/实际行情5,213、上涨2,344/下跌2,712/平盘155/未知13及成交额14,378.36亿元；点击展开上证指数后真实走势图可见，收盘3,842.19，并明确显示指数成交量原始单位待核实。页面继续标注 `PG 候选快照·不代表正式 Head`。
- 这补齐了日更诊断抽屉与市场图表两个实际交互点；它们仍是候选态功能核验。没有启动日更写入进程，没有改动 Joint authority，也没有触碰28765。
- 另从实际 DM-01 运行入口调用 `current_parent()` 做只读全链核验：PG 返回 accepted trade date `2026-09-30`、Head SHA `38e7c9b6…bae08`、9项组件；accepted chain、机器接受记录、组件权限、9个组件产物与回执均校验通过，状态 `DM01_PG_PARENT_READ=PASS`。这证明现行DM-01接受Head读链在PG端实际可用，不等于本次下一交易日已接受；目标增量仍受中间交易日官方源包缺失门禁约束。

## 首次观察冻结改为 PG SourceIngress

- `src/workbench_service/pit_observation.py` 不再把当前源复制到工作区作为 PIT 冻结档案；5类 manifest 源按精确 path/SHA 从 PG SourceIngress 读取，观察收据也以内容绑定写入/读回 PG。历史本地收据只在 PG 缺失时按原字节做一次导入；已有 18 个本地归档文件保留，实测前后文件集合、大小和时间戳均未变化。
- 用28766正在服务的同一 PG 候选 schema 实跑冻结两次：T0=`2026-09-30`、5个源、同一 receipt 与 source identity，`idempotent=true`；随后对5个 path/SHA 再经 PG SourceIngress/package binding 精确读回，共75,180,686字节。PG 收据为1,569字节、SHA `6de3d849…42a828`，合同 `R2_FIRST_OBSERVED_FREEZE_V1`。按合同仍返回 `strict_t0_pit_ready=false`、`AS_RECORDED=false`。
- 定向验证 `tests/test_r2_csv_pit.py`：3 passed。该改动只消除了首次观察模块对业务源文件的重复回读和新档案落盘，没有授予历史 PIT、改变任何 Head 或发布范围。

## DM-01 日更接受数据继续收口到 PG

- 修正 `scripts/run_v4_dm01_daily_increment.py` 对 PG 日更合同读取器的旧式参数调用。该入口现在按已登记的 `BAOSTOCK_SUPPLEMENTAL_SOURCE_V1@1.1.0` 读取合同，不再把废弃的本地合同文件参数传给只支持 PG registry 的运行时。
- BaoStock 日线首次 SourceIngress 后保留原 path/SHA/bytes PG binding 并传给后续步骤；当前进程捕获的 TDX 收据、从 PG 接受事实加载的 BaoStock runtime manifest 分别用内容寻址方式登记 SourceIngress。`project_source_freeze` 下游继续通过 `dm01_runtime_r4.read()` 精确从 PG 读这三类输入，避免回开工作区副本。投影键含捕获内容摘要，重复捕获不会覆盖不同 receipt。
- 将 BaoStock runtime acceptance fact store 在唯一开发 PG 中完成空库 DDL 初始化及稳定 workspace alias 注册：namespace `v4_forward_ca206ffd216e90b4`，alias `ACTIVE`，原路径目录不存在、原始文件迁移数为 0、当前事实数为 0；没有写入接受记录或移动 Head。对真实 PG 读路径核验后，缺事实按 `BAOSTOCK_PG_RUNTIME_ACCEPTANCE_NOT_FOUND` 返回，不再触发未初始化表的 SQL 异常。
- 定向单测 7 passed；首次观察 PIT 套件 3 passed；修改模块 `py_compile` 通过。较宽的冻结 DM-01 系统套件由仓库隔离插件拒绝访问非 disposable 的共享 PG，未关闭或绕过该隔离。当前日更仍受 2026-10-08 官方 TDX 中间交易日源包缺失阻断；本修正尚未使日更或接受 Head 通过。

## DM-01 冻结消费者继续移除工作区回读

- 冻结脚本现在以精确 PG SourceIngress binding 读取 TDX capture receipt、delta receipt/delta、BaoStock daily update、GBBQ accepted manifest/member；对每份 JSON 校验 path、SHA、字节数与业务日期/快照身份。Delta 收据/JSON 从 snapshot ID 与日期形成确定性 PG logical path，并核对收据路径声明；官方日历继续由 PG-bound runtime reader选择，冻结清单直接引用其 binding；不再把本地副本重新算哈希后当作来源记录。
- 日更编排在启动冻结前把本次 TDX capture receipt 写入 SourceIngress 并将 binding 传给冻结脚本。GBBQ 首次边界现在对 manifest 声明的源成员校验原始 SHA/长度，逐件写入并从 PG 精确读回；冻结消费者只按 manifest 的 path/SHA 读 PG。TDX 原 ZIP 仍由上游受控捕获/差分构建负责读取；冻结阶段仅检查其捕获路径仍存在并引用已验证 receipt 中的 SHA，不在下游重复散列 ZIP。
- 新增或更新定向回归覆盖 BaoStock 精确绑定、错误日期拒绝、通用 JSON binding SHA/长度拒绝以及冻结脚本无工作区 `read_text/read_bytes`；8 项通过，两个脚本 `py_compile` 和 `git diff --check` 通过。完整实际日更仍由 2026-10-08 中间交易日 TDX 源包缺失阻断，尚未据此宣称端到端接受 Head 通过。

## TDX 页面捕获与 28766 现场续验

- 真实跑 `2026-10-16` DM-01 时，编排在来源请求前因连续交易日缺口 `2026-10-08` 返回 `BLOCKED_MISSING_INTERMEDIATE_SESSION`，`source_requests=0`、Data Head 未移动。随后真实跑 `2026-10-08`，官方 TDX 页面与 update-info 两次捕获均报告最新发布日为 `2026-10-16`，状态 `WAIT_TDX_PUBLICATION`；未下载 ZIP、未请求 BaoStock、未移动 Head。页面原件 25,379 字节、JS 120 字节、receipt 1,604 字节已分别 SourceIngress 并按 SHA/长度 PG 原字节读回。
- `scripts/capture_tdx_official_daily_package.py` 现在在捕获命令边界校验并写入 page HTML、update-info JS、capture receipt 的 PG binding；捕获元数据仍受 4 MiB/256 KiB 字节上限。真实 CLI 回执返回三个 binding；新增正反例纳入后 10 项定向测试通过。当前交易日缺口仍是真实供应方发布时间事实，不做倒填/倒签。
- 实查 `127.0.0.1:5432/market_research` 的现有连接角色为 `postgres`，`rolsuper=true`、库级 CREATE 与当前 schema USAGE/CREATE 均为 true，事务非只读；这是实际连接能力，不是权限申请或凭据名义阻断。没有创建平行实例。
- 28766 API 已按有效 context token 读验同一 PG candidate/T0=`2026-09-30`。首页、市场、板块 378 项、股票 5,213 项、Focus 469 项、Forward plans 585 项、settlement 5 项均返回 READY；样本股票日/周/月图分别返回 253/54/13 个有效聚合区间，周 QFQ 图返回 20 条并绑定 history version、Head 与 source digest。板块成员样本 25 项。FEP 返回 `SOURCE_INCOMPLETE / NO_CURRENT_DAY_MODEL_INFERENCE_OWNER`；日更状态仍 `PREVIEW_ONLY`、jobs disabled、worker `NOT_STARTED`。数据更新页及脚本、主/组件/API 静态资源 HTTP 200；这一轮是 HTTP/API 验证，没有把它扩称为新一轮浏览器交互验收。
- 补验市场四轴 API：指数 5 项、涨跌停 5,224 项、梯队 56 项均 READY，breadth 汇总 READY；`market/facts-events` 明确 `SOURCE_UNAVAILABLE / NO_APPROVED_BOUND_OFFICIAL_OR_MEDIA_EVENT_DATASET`。事件列表 33 项、Focus events 469 项、Forward risk 5,213 项可读，诊断 health 返回 5 个模块。该事件源缺口保留为数据集/Owner 缺失，不用价格波动推断媒体事实。

## 唯一工作区与衍生目录现场分类

- `git worktree list` 仅登记唯一主仓 `G:\codex work\大A交易`，当前分支仍为 `codex/v4-workspace-cleanup`。监听核对仅见 PG `5432` 与开发 `28766`；未见 `28765` listener。28766 使用本主仓进程，且此前 PG identity 与 `market_research` 一致。
- `G:\codex_tmp\v4_r6_tdx_20261016` 为 568,127,024 字节/39 文件的 TDX 原始源快照，`KEEP_SOURCE`；`r6_daily_evidence` 为 3,066,205 字节/22 文件，`KEEP_EVIDENCE`。`test_temp` 共 468,656,932 字节/20,492 文件，均为旧测试与本轮定向 pytest disposable basetemp 候选；当前无 pytest 进程，PostgreSQL 仅监听 5432，未见 disposable PG listener，列为 `DELETE_REBUILDABLE`。清理请求被执行器策略拒绝，未绕过该限制。
- `data/v4/dynamic_daily_sources/tdx/20261008` 下两份页面捕获目录的 6 文件共 54,192 字节全部已 PG 精确读回、无现役消费者引用，分类为 `MIGRATE_TO_PG / DELETE_REBUILDABLE`；目录递归删除同样被执行器自动策略拒绝，文件副本保留并登记待清理，不影响 SourceIngress 运行路径。
- `G:\codex_tmp\r7_active_baseline_20261015` 实测为未登记 worktree 的旧 Git clone：2,252,363,310 字节/2,726 文件、分支 `master`、23 条未提交路径，当前运行代码未发现其路径引用。因该副本带有未归属的源码/数据更改，分类 `UNKNOWN / PRESERVE`，未清理。`v4_repository_governance_r3_20261016` 为 4,675,814,273 字节/82 文件且无 `.git` 的恢复快照容器，分类 `KEEP_EVIDENCE/UNKNOWN`。当前主仓 5 个未跟踪路径（本地 hook、R75 报告、3 个审计脚本）同样保留，未覆盖或暂存。

## 浏览器实页与结构时间线联验（2026-10-18 续行）

- 用 in-app browser 打开 28766 当前 PG 候选的首页、个股详情、板块详情、Focus、Market、Diagnostics/Jobs 实页；导航、详情表、筛选控件、图表控件和各域表格均完成加载。所有页面头部 context 均显示同一 T0 `2026-09-30` 与 `PG 候选快照 · 不代表正式 Head`。
- 个股 `SEC-0051683845B17D59641B7D1DC261FE2A` 实页显示 253 根日线实际成交图、个股画像与“结构锚点与事件”入口（2 项结构事件）。同一 context-token 的 API 回归 15 个路由全部 HTTP 200：stocks 5,213、sectors 378、focus 469、forward 117、settlement 585、板块成员 25、结构时间线 3 条。板块历史时间线准确返回 `SOURCE_INCOMPLETE / FIRST_ACCEPTED_PIT_MEMBERSHIP_NO_PRIOR_DATED_NATIVE_HISTORY`；Diagnostics/Jobs 准确返回 worker receipts 缺失，没有启动 worker。
- 对同一 PG candidate reader/BFF 做只读 Python audit-hook 运行时审计，跨产品共调用 45 次（44 个不同路由，另含重复的 Diagnostics/Jobs 复核）；所有返回 HTTP 200，审计期间 `data/`、`config/`、`reports/`、`runtime/` 本地业务文件打开计数为 0。源码证据包位于 `G:\codex_tmp\v4_r6_runtime_business_file_audit_20261018.json` 与 `G:\codex_tmp\v4_r6_runtime_business_file_audit_extended_20261018.json`；调用分别覆盖股票/板块/图表/时间线、Focus/Forward、市场四轴/事实事件、Sources、cohort、Replay/Compare 与诊断。业务内容由相同 immutable PG candidate 读取；SOURCE_INCOMPLETE/PIT_NOT_AVAILABLE 按原 Owner 和权限事实返回。
- 本轮测试一度给页面 URL 加了临时 `uiqa` 参数，页面按合同将未知筛选项拒绝；改用无参数正式 URL 复测后 Focus 469 行、Forward 117 行、待结算 585 行均正常呈现，属于测试参数错误，不是产品缺陷。
- 对 `data/v4/dynamic_daily_sources/tdx/20261008` 与 `G:\codex_tmp\test_temp` 的边界、文件数/大小及无活跃 pytest 进程已复核。PowerShell 执行器对这两个删除请求均自动拒绝；文件仍在，未尝试改用其他执行路径绕过。TDX 捕获副本已迁 PG 且无消费者，pytest basetemp 为可重建项，仍列待清理。

## Focus/Forward 四日真实运行续验（2026-10-18）

- `r43_focus_replay` 的研究配置合同标注为 `JSON_COMPATIBLE_YAML`，而当前运行 Python 没有 PyYAML；修正为与其他现役消费者一致的标准库 `json.loads`，入口仍先从 PG Historical SourceIngress 读取精确配置字节。新增定向测试验证 PG-only 配置路径、缺源 fail-closed 与 Owner 输入读取。
- 使用已接受 Data Head 日历与 R4 日历扩展的诊断候选上下文实跑 Focus/Forward，保持 `production_admission=false`。四日分别处理 5,222、5,223、5,224、5,224 个证券行；D0 TRUE 为 114、190、175、150，其余状态保持 UNKNOWN；PREWATCH TRUE 为 1,106、1,190、1,120、910；D2 fresh 为 114、169、122、100。结果形成 2,477 个 Focus episodes、7,524 个 events；Forward outcomes 为 OBSERVED 3,418、PENDING 9,742，未将未到期结果改写为接受状态。
- 首次完整计算发现 PG immutable Series 已写入，但供 Focus adapter 消费的 descriptor 没有进入 Historical SourceIngress。已在 Series builder 后新增精确 descriptor ingress/readback，再用新候选命名空间完整复跑；最终 Series descriptor、4日各 D2/calculation/fact/status 文件及压缩 Focus/Forward 产物合计 18 项均按实际 SHA、长度及原字节从 PG 精确读回。最终 Focus/Forward SHA-256 为 `48e77f32…e709a0`（5,319,773 字节）。
- 独立候选读回用合同 `validate_candidate_output` 逐行复验四日 20,893 条 D2；每日期的 D2、D0 calculations、input facts、Focus status 都是相同证券行数且日期/行身份一致。PG immutable Series 再读得 20,843 bars。Focus projection 的 episode scope、事件数、Forward 状态以及 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`production_admission=false` 一致，候选级验证为 `PASS_CORRECTED_CANDIDATE_SCOPE`；这不是外部独立验收或正式准入。
- 验证结果：`tests/test_v4_r6_pg_only_owner_source_reads.py` 3 passed；本轮修改模块及回归文件 `py_compile`、`git diff --check` 通过。28766 context/home/focus 在 PG 写入后仍以同一 context token 返回 HTTP 200。该实跑不创建 publication/Head，不改变 production admission；全模块外部 QA、最新浏览器交互复验和未获执行器准许的衍生文件清理仍未全部通过/完成，见本报告未完成项。

## R4.12 冻结合同消费者改为 PG-only（2026-10-18）

- 定向读链扫描发现 `FrozenContracts` 在 Structure/Health/Breakout 每次运行时仍直接读取冻结入口及合同文件。入口、16 份 frozen contracts 与外部 freeze acceptance 共 18 份源均为当前 clean Git revision；逐项核对合同声明 SHA/bytes 后，以 `git:<revision>:<path>` provenance 登记到唯一开发 PG，并逐字节读回。未修改合同文本或审批状态。
- `FrozenContracts` 改为按稳定 SourceIngress ID 读取入口，其他冻结合同与 acceptance 按声明 path/SHA/bytes 从 PG 读取并复验摘要；不再从工作区回退。实际 loader 初始化返回 16 个冻结合同、冻结 digest `9c0556af…193602`、counter contract `V4_12_SESSION_COUNTER_V2`。新增 PG-only mock regression；R6/R4.12 合并定向套件 4 passed，py_compile 和 `git diff --check` 通过。该改动切断 18 个运行期合同/验收文件读取点，不改变业务模型、Head 或 production admission。

## Corrected Owner 旧支线的 PG 读写边界续修（2026-10-18）

- Structure/Sector/Focus/Market Rotation 旧 Corrected 支线继续把 replay manifests、研究配置、算法参数、策略合同从 PG 精确绑定读取；阶段回执、逐日数据文件、D2 与 Focus/Rotation 成品在生成后写入 SourceIngress，后续消费者不再依赖其本地副本。Focus 研究配置同样改为 JSON-compatible YAML 的标准库解析。
- R4.04 该支线的 `output_schema`、`field_window_mapping` 和 dated-membership policy 三份精确合同此前未在 PG；核对 clean Git revision SHA/bytes 后完成 SourceIngress，原字节读回一致。代码变更后的 5 项 Structure contract / R6 PG-only 定向测试全部通过，相关模块 `py_compile` 和 `git diff --check` 通过。
- 该旧支线的 PG Owner Core/Profile manifest 当前不存在，因此这里只完成读取/写回边界修正，未宣称它已真实四日运行；已完成真实四日业务运行的是上节 R43 Focus/Forward 候选。后续该支线可在其 Core/Profile Owner 从 PG 登记完成后继续联调。
- Corrected Owner stage orchestrator 和 Health projection 也已改为从 PG 读取续跑 receipt/manifests、输出投影写回 SourceIngress；若旧目录有文件但 PG 无对应绑定，按 `UNINGRESSED_WORKSPACE_CANDIDATE_NOT_CONSUMABLE` 拒绝使用。更新后 Structure/Health/Sector/Focus/Rotation/Owner 编排器组合定向套件 6 passed，py_compile、`git diff --check` 通过；该边界修正不补造缺失 Core/Profile Owner 输入。
- 在上述 SourceIngress 写入后再次探测 28766 的 context/home/focus/forward/market/diagnostics-health 六路：全部 HTTP 200、同一 `research-v4-pg-candidate-91b4066e…2ec116935` context token。Focus 明确保留 `SOURCE_INCOMPLETE`，原因 `AUTOMATIC_WRITE_PATH_ADAPTER_AND_LEGACY_HISTORY_MIGRATION_NOT_ADMITTED`；没有把可读候选状态描述成 Focus 写入/续算已准入。监听仍仅 PG 5432 PID 8640 与开发 28766 PID 33460，无 28765。

## 28766 Focus 与证券详情实页复验续行（2026-10-18）

- 使用本机 in-app browser 直接打开 `http://127.0.0.1:28766/v4/research/focus`，实页加载同一 PG 候选 context token/T0=`2026-09-30`；Focus 清单显示 469 条，Forward 显示 117 个独立样本，期限结算 585 条。页眉明确标注“PG 候选快照 · 不代表正式 Head”，成熟样本为 0 时未展示收益胜率。
- 通过真实页面查询参数 `q=002771` 验证检索闭环，结果从 469 条收敛到 1 条 `SZ.002771`，分页按钮与筛选输入状态一致；Forward 和结算分区保持独立，查询不改变数据。
- 从 Focus 命中的证券身份打开详情页 `SEC-00E228DA7EBF038EA528EF36B65B4C97`：详情表、来源证据按钮、所属行业/关联概念、事实/研究状态/假设分区、关注时间线与结构事件区均完成渲染。图表选择器显示日线/周线/月线与原生前复权/不复权选项；日线实页为 T0 截止 253 根、默认展示 120 根，成交量股/成交额元。
- 缺失 Owner 继续以“来源能力不足/字段未接入/待补证据”展示；该实页验证不把候选提升为 accepted Head，也不表示 Focus 自动写入或全模块验收完成。

## Market/日更诊断实页与 10-08 本地行情复核（2026-10-18）

- 真实打开 28766 Market 页：宽度 5,224 个分母中有 5,213 个实际行情（上涨 2,344、下跌 2,712、平盘 155、未知 13），成交额 14,378.36 亿元；5 个指数、涨跌停统计和 56 个涨停梯队正常呈现。页面说明这是截至 9-30 的盘后历史截面；分钟级炸板与批准的媒体/官方消息事实源仍未绑定，状态没有被推断填充。
- 真实打开 Diagnostics/Jobs 页：环境为 `PG_CANDIDATE_SNAPSHOT`、T0 9-30，显示 events 33、Focus 469、Forward 117、Market 1、Radar 117、Sectors 378、Settlement 585、Sources 4、Stocks 5,213；明确标注本次没有启动日更 worker、快照不含作业回执、source requests=0，原因 `PG_CANDIDATE_DOES_NOT_CONTAIN_DAILY_WORKER_RECEIPTS`。
- 对配置为只读输入的 `D:/new_tdx` 只检查三个沪/深/北证 `.day` 文件边界及 2026-10-08 记录：均无目标日记录，最新分别到 2026-09-10、09-11、09-10。该本地终端快照不能补出 10-08；未从之后的数据包倒填，也未更改 TDX 源目录。
- 官方[通达信个人行情数据页](https://www.tdx.com.cn/article/vipdata.html)列出沪深京完整日线包，并说明下载包要在更新日期到达后才包含当日数据；该公开页没有 2026-10-08 的独立历史日包链接。此前 PG SourceIngress 捕获的官方更新元数据把最新可用包标在 10-16，因此连续正式日更链仍卡在 10-08 中间日；本地旧快照和 10-16 回溯内容均不被当作 PIT/accepted 输入。

## 证券图表交互控件实页复验续行（2026-10-18）

- 在 28766 的 Focus 命中证券详情实页上，真实操作“行情周期”从日线切换为周线，选择器状态为周线，图表由日线 253 根汇总为 54 根周线；末端标注仍不超过 T0=`2026-09-30`。
- 再将“价格口径”切换为“不复权”，页面刷新后的状态摘要明确显示“不复权”，周线样本数仍为 54；图表标注包含按周聚合的开高低收与成交量。此项验证覆盖实际交互与数据刷新，不只核对静态控件选项。
- 本次浏览器验证使用 PG 候选快照，不写业务数据、不改变 Head 或准入状态；全部功能验收仍未完成。

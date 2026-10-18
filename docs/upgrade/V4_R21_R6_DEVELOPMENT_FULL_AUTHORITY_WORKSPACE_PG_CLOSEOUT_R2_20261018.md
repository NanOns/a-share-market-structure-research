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

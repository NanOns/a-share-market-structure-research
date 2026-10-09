# 大A V4｜DD R2.2 数据优先：生产加载、真实交易日日更与关键板块复验任务卡


- 编号：V4-DD-R2.2-DATA-FIRST
- 发布时间：2026-10-10（Asia/Shanghai）
- 性质：独立审计 R1 派生的正式 Codex 执行合同（未执行、未验收）
- 来源审计：V4_DD_R2_1_DATA_FIRST_INDEPENDENT_AUDIT_R1_20261010.md
- 基准仓库：NanOns/a-share-market-structure-research
- 目标工作分支：codex/v4-fp14-r2-repair
- 编写时远端 HEAD：302a40113576b38bb4b7e0b01192c415e320d67c；执行前必须重新 fetch 记录真实 BASE_SHA，禁止把旧 SHA 假装最新
- 工作空间：G:/codex work/大A交易；所有新增临时文件和测试缓存：G:/codex_tmp（优先遵守仓库 AGENTS.md 最新规定）
- 当前裁决：EXTERNAL_ACCEPTANCE_BLOCKED；已通过的独立数值抽样为 DATA_NUMERIC_SAMPLE_EXTERNAL_PASS，不需要重做
- 核心目标：**让可靠数据先运行起来，再谈辅助维护；不为缺少整机重启、托盘或全量历史审计而阻塞数据开发。**


## 0. 直接交给 Codex 的执行摘要


本轮只执行三个工作包：


**P0-A：生产数据代码加载身份核验。** 检查正在运行的工作台是否真正加载已提交的最新 source gate、daily executor、V2 Owner adapter；仅在用户已明确允许的机制下正常重载工作台服务。若权限策略阻止进程重载，则不强关、不绕过审批，在报告中精确给出人工重载步骤，并将此项保留 PROD_RELOAD_REQUIRED，不得假装生产已切换。无需 Windows 整机重启。


**P0-B：真实后继交易日完整数据链端到端。** 2026-10-10 是周六，预计下一个交易日是 2026-10-12；先以已接受的正式交易日历复核。现在能做的先完成；实际 10/12 的官方数据未发布时保持 READY_FOR_REAL_SESSION，不得用 mock、10/09 数据或事后重放伪造 10/12 新交易日发布。10/12 源到齐后执行既有 AUTO 主链，并逐域核验 TDX、BaoStock 日线/因子、身份/GBBQ、RAW/QFQ、周/月、Core/RPS/板块/Market/Focus、Owner QA、CAS/六接口。遇到真实失败只定点修数据断点。


**P1-C：两个有代表性的通达信板块数值抽样。** 从已冻结的 10/09 真实板块及成员数据中选择一个成员较多的通达信 INDUSTRY、一个通达信 CONCEPT（优先真正的热门/主线概念，如无法以已冻结数据定义主线则只按可复现规则选择，不编造热度）。独立复算 Native/LOO 必要字段。该项可以在 10/12 数据出现前完成，不能阻塞 P0 数据日更。


**严禁**：上传或补传之前 3–4 GB 数值 Owner、551MB TDX 原始 ZIP、任何整库备份；大规模系统维护、Windows 机器重启、托盘/开机项、全面性能压测、前端重做、算法重构、新数据提供方、新证券身份强行准入、调整 Amount 主权威。新增 Drive 文件整体建议 < 5 MiB，硬上限 10 MiB；单个 ≤ 5 MiB。大卷只留本机，引用路径（可脱敏）/size/SHA 即可。执行本任务无需问用户是否还想上传大卷。


## 1. 事实与权限基线


### 1.1 当前可认可的历史事实


- 已认可 10/09 运营 Head 的 canonical SHA：55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e。
- 严格历史 PIT Head SHA：38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40。
- 前轮源码已增加 execute_sources→verify_source_gate 与 derive_ready_sources 再次复核、单独的 operational_daily_ready_owner_v2.py；代码层已有审核证据。
- R2.1 Drive 小包 3,052,805 字节通过独立 ZIP/CRC/SHA 与离线公式抽样复算：45,559 项原 oracle 检查及 21,032 项另行数值检查均无差异；这不代表完整全市场 Owner 已获外审全量通过。
- R2.1 的实时 HTTP 回读证明 10/09 旧 Head 可以读，**不证明旧进程已经载入最后的源门和 V2 适配代码**。Drive 最终结果仍把生产装载列为阻断。
- 2026-10-10 是休市日；不应生成不存在的“今天新行情”。


### 1.2 仓库约束


先读取最新 AGENTS.md、本文件、上述 R1 审计、现有每日更新合同 V1.1、当前 HEAD 及其待合并工作；保留不相关改动。TDX 根 D:/new_tdx **只读**；本轮不修改、删除、重命名或写入 TDX 目录。产生的临时文件仅落 G:。严守 Source/PIT/Owner 绑定和事务安全，不使用未来数据来冒充历史观测。


### 1.3 任务执行不跨越现实时间


本任务卡是在 10/10 编制，不预言 10/12 TDX、BaoStock 必然有数据。Codex 当前执行环境如果还没有目标日真实数据，只执行 P0-A（权限许可范围）、P0-B 预检与隔离回归、P1-C；把下一交易日 E2E 标为 WAIT_REAL_SESSION，留可重复的操作命令与真实触发条件。不得为了使报告看起来“全 PASS”自行编造时间、价格、状态、截图或请求回执。


## 2. P0-A｜生产数据代码版本实际加载核验


### A01：只读勘察


- git fetch origin；记录分支、精确 HEAD、工作树和必要未提交更改，不覆盖用户修改。
- 定位工作台实际启动命令、Python exe/venv、服务或托盘启动入口、运行 PID、工作目录、绑定端口、实际 Python 模块路径；核查运行代码与仓库文件身份是否一致。
- 定点列出至少以下源文件当前 SHA256、文件 mtime、Git blob/ref 和运行进程可证实的模块路径：operational_daily_executor_v1.py、source_readiness_v2.py、operational_daily_ready_owner_v2.py、operational_daily_owner_v1.py、operational_daily_jobs_v1.py、operational_daily_periods_v1.py。静态磁盘 SHA 不能替代已加载的进程版本证明。
- 查询 10/09 运营 Head、严格 PIT Head、AUTO flag、worker state、读回 API，不触发正式新发布。
- 验证“服务当前仍是旧模块”是否仍然属实；如果已有进程重载，必须以真实启动时间和进程证据纠正旧报告，而不是照抄旧结论。


### A02：安全、最小的服务重载


- **只允许用户明确授权且当前系统权限允许的正常服务停止/启动操作**；遵守此前 stop/reload 被策略拒绝的事实。禁止 taskkill /F、终止不相关进程、修改 Windows 服务 ACL、绕过安全策略、注册自启、Windows 整机重启。
- 如果当前能正常重载：在不启动新数据采集的前提下，确认新 PID 的进程实际从该工作树加载相应模块，记录模块源 hash / import 路径 / start_time；核查原 10/09 运营 Head SHA、严格 PIT SHA 未变、AUTO 状态符合用户原设置、六个读接口同 token，旧 token 按合同返回 409。
- 如果执行权不足：生成 4–8 行清晰的人工作台正常退出/启动指导（具体命令必须从仓库启动配置推导，不凭空写 Windows 服务名）；停止进一步生产重启尝试。其他数据预检/样本复验可继续。状态必须是 PROD_RELOAD_REQUIRED。


### A03：验收和禁止


- A-PASS = 正确实际加载新模块 + 10/09 原 last-good 不变 + 六端点数据同源 + 无越权。
- A-BLOCKED = 本机进程未更新且安全流程不能执行；在报告中具体写出 blocked by policy，以及必须由用户执行的一个最短正常动作；**不要把此项推广成 Windows 运维大工程**。
- 服务不可控时不要进入新的生产发布操作；后续只做离线准备，等用户真实完成正常服务重载再跑 B 包。
- 保留 P0-A 单次读回的最小 JSON（进程身份/6 API 摘要/Head SHA），禁止导出整个数据库。


## 3. P0-B｜真实新交易日日更全链核验（数据主任务）


### B00：截止日期与执行条件


- 独立从系统**已接受的日历**计算 10/09 后第一个交易日（预期 10/12），不能以固定周一代替日历算法。
- 准备好代码和接入检查可以先做，但若 10/12 尚未收盘或三源未发布，必须只输出 SOURCE_WAIT/WAIT_REAL_SESSION；不模拟成功、不硬编码 10/12 行数。
- 尊重既有时间门与后端 AUTO（原系统首查 18:35 Asia/Shanghai、后续有界重试）；不要为了赶结果早于官方可用时间强行抓取或以旧包填新日期；如果当天源确实迟到，由系统保留 last-good 并继续正常重试。
- 只有 A-PASS 且新日期三源真实合格，才允许接入真实新日 Owner / CAS。已接受 10/09 不重新发布、不改成所谓 PIT 合格的历史 as-recorded。


### B01：三源及身份完整性（数据入门硬门）


核验并生成极小的每源摘要表：


1. **TDX Native**：官方来源/包 SHA、抓取时间、包标识、目标日（10/12）Bar 真正存在、提取后的 Bar 数/日期集合、源可用时刻；若发生本地 fallback 则单独说明真实来源和观测时刻、适用权限，绝不能把本地更新观测时间回填为历史 PIT；不下载或上传第二遍相同大 ZIP。
2. **BaoStock 日线**：目标日期、API 响应及规范化摘要、证券集合、交易/停牌分层、行数、覆盖异常。对正常交易证券与 TDX Native 的 OPEN/HIGH/LOW/CLOSE/VOLUME 比较；对停牌禁止伪造零 Bar；不同数据源成交额差异只记单独开放项 DD-A05，不拿其替换 Native。
3. **BaoStock 复权因子**：真实查询日期、response SHA、变更个数；若当天合法零变更，必须有原始查询成功且目标日匹配的零变更证明，不能以“没拿到数据”当零因子。
4. **身份与 GBBQ**：已接受 dated identity pool 的新增/退市/停牌/未知身份计数；GBBQ 原始字节 SHA、应用事件和失败数量；当日成员版本 as-of，不把 10/12 最新成员关系虚写为 10/08 历史 PIT。
5. **共同 SOURCE_READY**：三源 proof 全 VERIFIED 且日期/包 SHA/观察时间及 identity、GBBQ 依赖一致，最终 gate 与冻结 source revision 一一绑定；单项缺失就明确 WAIT_*，**禁止启动派生或 CAS**。


不能把 10/09 的旧数值 5224、5210、14 或 5559 用作 10/12 固定预期；不同范围的日线数量必须说清是原始覆盖、A股接受池还是有效交易 Bar。


### B02：派生数据及算法核验（真实 P0）


只有 B01 PASS 才继续：
- 日 K RAW/QFQ：单证券/抽样横跨普通、停牌、复权、缺口；验证结构键、日期、价格/量/额、前收及 GBBQ 作用的复权窗口，发现无法观测事件即按合同 unknown/fail-closed，不能伪造。
- 周 K/月 K：严格使用截止 T0 可得的真实日 K 增量自算；当周/当月未结束的 PARTIAL 语义、周/月边界、跨节假日、停牌不生成假 Bar；RAW 和 QFQ 两种来源分开验。**不得直接用 BaoStock 周/月 K 替代**。
- CORE/PROFILE：确认全已接受证券的行数/唯一性/必需字段类型和窗口质量，MA20/ATR20、成交量/金额比例、ret5/ret20 与 RPS 有明确前置 T0 截止，抽 20–30 股做小样本复算。严禁只凭总行数 OK 宣称数值 OK。
- 板块：权威仍用通达信 INDUSTRY + CONCEPT 及其成员快照，验证聚合与成员集合、停牌/身份过滤、相对强弱及 LOO，不能悄悄退回证监会行业分类替代；多个证券属于同板块时避免双重计算。
- Market：全市场统计明确 denominator/eligible/excluded、实际贡献；关键轴至少做参与度与一个其它轴的数据质量抽查，不能只检查数字存在。
- Focus/Forward/Rotation：验证合法字段、对象关联、结构与旧 Head 同源；运行成熟结果未到期只记录 OPEN，不在本轮补齐所有预测/轮动算法研究。
- 已在 R2.1 明确通过的旧两日样本不重跑 4GB Owner，仅检查新真实日期的必要增量和正式 QA。


### B03：安全发布事务（真实 P0）


- 正式 Owner 必须完成所有原合同发布硬 QA（生命周期守恒、核心数值、周期、板块、市场、依赖 SHA）且 build/resolve 期间原 parent 未变，才允许 candidate→CAS；不能为了页面有数据跳过 QA。
- 发布前冻结 old Head 的路径/字节/SHA，CAS 使用 expected predecessor；任何失败保留旧 10/09 last-good 和合法候选证据，不能进行半发行。
- 发布成功后读取新交易日 accepted_trade_date、data_cutoff_date、predecessor、day receipt、各 Owner binding/source revision/SHA；旧严格 PIT Head 必须不变。
- 用真实服务重新调用 context、operations/status、stocks、sectors、market、focus 六读端点：相同日期和新 context token、可读取真实对象与数量；旧 token 按既有合同返回 409。若接口不通，区分数据已正式发布但 BFF 未读回的危险状态，按既有回滚协议处理，不写成全成功。
- 数据未来观察不得被标记 as-recorded 的旧日 PIT。合法 10/12 正式新 Head 的 SHA 应是新有效 SHA，不能继续宣称 10/09 SHA 是新 Head。


### B04：异常与止损


发生如下任一情况马上停止发布、定位真正首个失败环节，而不是“优化所有系统”：
- 交易日未成熟、TDX 实际日 K 不存在、BaoStock 日线/因子目标日不符或缺证明；
- 身份/GBBQ/成员 revision 冲突，RAW/QFQ/Owner 行守恒不成立；
- 核心因子或周期 QA FAIL，RPS cohort 不一致，CAS 前驱变化或 HTTP readback 失败。


只产出：第一失败节点、真实来源收据、对应异常证券/板块的 5–20 条 compact 样本、修复建议和影响范围。**不得为通过验收修改算法口径、删除 QA、改写历史 Head 或强制发布**。


### B05：实际验收状态


- B-PASS：现实 10/12（或实际下一接受交易日）真实源全部就绪 + 全链派生完整 + 原合同 QA 通过 + 事务发布及六端点读回 + 保留前驱和 PIT。若真实日期变更则以接受日历更新条件。
- B-WAIT：现实时间/来源不满足；输出 READY_FOR_REAL_SESSION 和阻塞列表，不属于功能失败，更不能标 PASS。
- B-FAIL：来源具备条件但真实算法/数据/发布失败；完整记录 first failure、last-good、仅定点修复后复验。
- 如果 A 受策略阻断，B 只能做到只读预检或隔离回归，必须为 PROD_DEPLOYMENT_BLOCKED，不能用隔离模拟伪装实盘数据验收。


## 4. P1-C｜通达信大行业与概念板块的轻量独立复算


R2.1 原板块样本生成按成员数从小到大排序取前三个，均是仅 7 名成员的 INDUSTRY 样本，没有 CONCEPT；虽公式通过，但不足以支持现实主线板块判断。按下面收敛补强：


- 用 2026-10-09 **冻结的、已绑定 as-of 的通达信成员快照**，按可重复排序选一个成员较多（避免同名复制、身份未知）的 INDUSTRY 和一个 CONCEPT。无 CONCEPT 合格对象时写 NOT_VERIFIABLE，不允许编造。
- 每个板块只输出一套紧凑的完整成员贡献向量（当日证券 ID、成员归属、停牌状态、ret1/ret5 或原合同实际字段、权重/有效分母、核心输入 SHA/版本）。
- 脚本独立实现 Native 聚合与至少 1 个实际 LOO“剔除目标自身贡献”的计算，保留 expected、actual、delta、容差；如当前数据只够验证 sector_rs1 与 breadth_ret1，其他指标必须标未验证。
- 对照单独的 source membership authority，说明是 TDX INDUSTRY/CONCEPT，而不是 CSRC 行业。若用今天最新快照反证旧 10/09 成员，那只是重建判断，不能冒充 10/09 PIT。
- 使用 R2.1 老轻量包即可增量补强，不重建原 3MB 包，不再采全市场历史。产物建议 ≤1MB。C-PASS 只证明选中两板块的对应数值，不是全体板块/LOO 完整外审。
- C 项可以与 A/B 预检并行，**不得阻断正式新日数据功能**；如遇环境依赖不完整，只归档 OPEN_AFTER_DATA_SUCCESS。


## 5. 任务顺序、最小代码改动和一次执行策略


推荐依赖：
- 立即执行 A01（只读进程与 repo 校验）＋ B00（日期/来源可用性预检）。
- A02 能合法操作就做一次最小工作台服务重载并完成 A03；否则停止服务修改工作、提供用户明确的正常重载步骤。
- 10/12 真实来源未具备前，做 B01/B02 在**已有冻结 10/09 证据上的隔离只读预检**、复用现有 R2.1 通过证据，并行做 C；报告 B-WAIT，不要在本周末运行生产“10/12 成功”的假流程。
- 真实下一交易日数据到齐后，由 Codex 重新运行这张卡的 B01-B05（可重复执行，幂等读取与合法重试）；失败只修首个数据障碍，不开启辅助维护项目。
- 同一轮不得循环重启服务和重刷巨型 Owner 来证明“一切正常”。


只有发现真实数据 bug 才改生产代码。每个改动记录 bug 输入、影响字段/模块、以前失败→以后通过的对照、小回归、Git 精确提交。不能为做任务而改无关代码。


## 6. 完成交付与数据验收门（按实际证据判定）


| Gate | 验证对象 | PASS 事实 | 失败/未成熟时 |
|---|---|---|---|
| A01 | 生产已加载源码 | PID/启动时间/真实模块路径与目标 SHA 可核实 | PROD_RELOAD_REQUIRED |
| A02 | last-good / PIT 权限 | 10/09 旧 Head 与 PIT SHA 保留，读回无脏发行 | BLOCKED（禁止擅自回滚） |
| B01 | 三源实际日期与内容 | 目标日实际 TDX Bar、BaoStock 日线、因子三证据全 VERIFIED | WAIT_SOURCE |
| B02 | 身份与价量复权 | 接受池/停牌/GBBQ、RAW/QFQ 按目标 T0 和 QA 可追踪 | QA_BLOCKED |
| B03 | 周/月与 Core/RPS | 周月正确部分周期、滚动窗口、RPS cohort 与前置 T0 | QA_BLOCKED |
| B04 | 板块/Market/Focus | TDX 板块成员真实 as-of、Owner 行守恒、市场关键分母 | QA_BLOCKED 或 OPEN_NONBLOCKING（只针对非发布硬门） |
| B05 | 新日 CAS/六接口 | predecessor 正确、完成 QA、六端点同新 token | PUBLISH_BLOCKED |
| C01 | 大行业 + 概念抽样 | 两套真实成员向量 + Native/LOO 独立对照 | P1 OPEN，不阻塞 B |
| E01 | 证据轻量完整 | SHA+关键回执+对照数据；Drive 实传回读 | DELIVERY_BLOCKED |
| E02 | 历史不被覆盖 | 10/09 旧 receipt、用户原始源、严格 PIT 未被覆写 | FAIL |


**最终总体状态必须唯一**：
- DATA_CHAIN_REAL_DAY_PASS_CANDIDATE：A 和 B 全部成功、等待我做独立复验签收。Codex 不能自签 EXTERNAL_ACCEPTANCE_PASS。
- DATA_CHAIN_READY_WAIT_REAL_SESSION：源码完成/预检可验证，但市场未进入交易日或来源未可用；不以此阻止 C 和其它不依赖功能继续。
- DATA_CHAIN_BLOCKED_PROD_RELOAD：需要用户正常重新打开工作台或获得现有授权，不得绕过。
- DATA_CHAIN_BLOCKED_SOURCE_OR_QA：真实源/数据/计算/发布出现具体硬失败；保留 last-good，只修第一项。
- DATA_CHAIN_BLOCKED_EVIDENCE：实际已运行但关键证据不足以独立验证；提供最小缺口，不请求 4GB 原始 Owner。


## 7. 文件与 Drive 交付硬上限


仅交 **一个主报告 MD + 一套精简证据 JSON/ZIP（如有独立复算材料才打包）**。建议如下：


1. DD_R2_2_DATA_REAL_DAY_RESULT.md：BASE_SHA/RESULT_SHA、A/B/C 分域结果、10/09→新日期合法迁移情况、首个真实失败、生产身份与是否手动重载、代码变更、下一动作和一行最终状态。
2. DD_R2_2_CRITICAL_EVIDENCE.json：包含相关 Head、source readiness 的各源摘要（日期/count/digest/观测时间）、复权/周月/Core/RPS/板块/Market 样本核查、CAS 事务与六端点 token 的极简原始收据及全部 SHA、实际测试命令/退出码。
3. 可选 DD_R2_2_SECTOR_MINI_ORACLE.zip：只含 P1-C 两个板块的完整 compact 成员贡献和一个独立复算脚本。不得重复上传已有 R2.1 的 3MB ZIP。


**预算**：本张新任务卡关联的所有新增 Drive 文件累计硬上限 **10 MiB**（建议 5 MiB 内），单文件 **≤5 MiB**；≤5 个文件。若超标先减少日志、去重、截取真正必要列/窗口，最后报告 NOT_VERIFIABLE，不分卷逃避上限。报告+JSON 正常情况下应 < 1 MiB。GitHub 只提交代码/少量证据，不要把数 GB 产物提交或重新压包。无需 Windows 机器重启，也不需要完整历史重新生产。


所有大 Owner、551MB ZIP、现存数 GB 数据仅留 G:（源 TDX 仍在 D: 只读），本地 manifest 记录 path/size/SHA 即可。绝不强制传上 Drive，也不强制由我下载大包。


**正式归档**：Codex 按既有 V4 项目归档目录上传轻量 Markdown 和关键证据，上传之后回读 SHA；GitHub push 后精确比对远端 HEAD。上传失败报告具体环节，不以“本地已写”声称完成归档。


## 8. 建议最小测试和回报格式


下列是目标行为而**不是断言仓库已经提供对应脚本路径**，Codex 需根据实际已有模块/测试填写真实命令与退出码，不得伪造：


~~~text
git fetch --all --prune
git status --short
git rev-parse HEAD


（已有 pytest 测试集：test_dd_r21_source_orchestration.py、test_dynamic_daily_r21_repair.py、test_operational_daily_periods_v1.py）
（无生产权限时仅在 G:/codex_tmp 隔离复验 SOURCE_READY、V2 IO、period oracle）
（生产可安全重载后，调用已有 /api/operations/status、/api/v4/context、
 /api/v4/stocks、/api/v4/sectors、/api/v4/market、/api/v4/focus）
（真实下一交易日官方数据可用后，再执行自动更新与实际日期读回）
~~~


交付报告必须能直接回答：
- “当前工作台到底跑的是哪一个源代码提交、哪个 PID、实际是否已正常重载？”
- “下一交易日到底是哪个 T0？TDX、BaoStock 日线、因子各自实际拿到什么，时间和 SHA 是什么？”
- “有效交易 Bar、停牌、身份、GBBQ、RAW/QFQ、周/月、Core/RPS、板块与 Market 是否达到正式合同 QA？哪些未证？”
- “新数据有没有真正合法 CAS 发布？六接口是否真的读到同一新日期 token？”
- “如果失败，第一真实数据错误在哪个文件/字段/交易日？10/09 last-good 和严格 PIT 是否未变？”
- “Drive 本轮实际上传几个文件、总多少字节？有无上传完整数据？下一步由谁按什么条件执行？”


## 9. 证据入口与回归锚


- 前轮正式外审：https://drive.google.com/file/d/1H3LSm_4T58sfPmkdrVQ-yACQn5SzLk4n/view
- R2.1 结果：https://drive.google.com/file/d/1xiXFW2FnfPAmKItmUY36mA8VpC0WfvGt/view
- R2.1 原小包：https://drive.google.com/file/d/1D9eln-o5zdYV24eHCuQEQ9tFH9WsH4HE/view
- GitHub 冻结：https://github.com/NanOns/a-share-market-structure-research/commit/302a40113576b38bb4b7e0b01192c415e320d67c


本合同不撤回前轮 DATA_NUMERIC_SAMPLE_EXTERNAL_PASS；新一轮的升级条件聚焦于**生产实际装载＋真正下一个交易日的可靠数据链**。辅助维护仍留待日更主线稳定后再处理。
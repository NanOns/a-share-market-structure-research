# 大A V4 全量切换：当前进度独立审计及后续连续执行任务卡 R2

- 版本：R2 / 2026-10-13（北京时间）
- 文档性质：最新进度审计 + Codex 接续执行合同；不覆盖原设计文档及完整合法范围，不代表已执行生产切换
- 审计基线：`NanOns/a-share-market-structure-research` / `codex/v4-full-closeout-20261012` / `d7f632fad2282e2314ca707cd5a6461394be836a`
- 前序基线：`codex/s1-b-20261012` / `2a8cc696086b78be4ccf443c23489e15ba2eaad2`
- 旧在役代码分支记录：`codex/v4-fp14-r2-repair` / `fbd23a6ba08d0948fe7ad421d1765fe363648522`
- 审计证据截止：上述远端 Git 已推送提交。用户 Windows 机器上的**未提交改动、正在运行的进程、最新本地验收产物**，本审计无法远程确认；Codex 接续时应先就地核查，绝不能直接重置/覆盖。

## A. 审计结论和准确边界

**当前总状态：ENGINEERING_IN_PROGRESS / PRODUCTION_CUTOVER_NOT_DONE / FINAL_ACCEPTANCE_OPEN。**

与 S1-B 相比，本轮已有 **31 次远端提交**，工程推进真实，但不能用提交数等同完成百分比。本轮已获得正式 PG 角色/88 Owner 迁移和全载荷读回/Focus 2,805 Episodes/桌面六入口阶段读回/历史多日期独立聚合/故障测试修复等有效成果。尚不能证明全部活动生产路径都在同一个已接受版本上正常工作，不能认定 V4 全量切换完成。

### A1. 可以复用且不应无故重算的证据

1. 正式 PG staging：正式集群 `system_identifier=7688198230782699460`、数据库 `market_research` 的受限读/写身份验证；`FORMAL_FUNCTIONAL_STAGING_PROGRESS_R1.json` 记录 88 Owner、完整 payload 差异 0、Focus 2,805、32 个可读表、14 条阶段 HTTP 验证。报告仍写 `active_production_changed=false`、`production_cutover=false`。
2. Windows 桌面阶段：编译入口在隔离工作树 `G:/codex work/v4-production-20261012` 的 **28871** 端口运行，六路 HTTP 200，engine RUNNING、stock 5224、sector 400、Focus 2805、统一 token；**原用户服务 127.0.0.1:28765 未替换**。这是阶段功能验证，不是原端口成功切换。
3. Focus 独立解码验证：2,805 Episodes、10,329 观察路径、61,908 数值比较、170 实际公司行动路径、103,180 谓词公式检查、15,345 结算检查，独立实现对照 PASS_SCOPED；11 条缺失路径维持 DATA_UNAVAILABLE，绝不脑补。
4. 通达信 GBBQ：独立 Feistel 解码覆盖 193,597 记录/1,935,970 标量一致；共享密钥表而独立实现，对其他业务入口的语义不提供一键接受。
5. 历史精确聚合：2026-09-28 5,222 证券、RAW/QFQ 周月聚合 18,320,512 字段比较 0 差异；2026-09-30 18,320,640 比较 0 差异。`FROZEN_DESKTOP_FUNCTIONAL_STAGE_R1.md` 后续称 2026-10-08 两域写入完成、独立 oracle 当时仍运行；之后另称五日聚合完成。**是否每个日期都封存完整 oracle，必须以逐日 RESULT 和源哈希检查，不因一句总结就写五日全部 PASS。**
6. 历史测试修复：原完整运行 5,463 节点，4,975 PASS、269 FAIL、157 ERROR、62 SKIP。多轮失败子集 FULLFIXR2、FULLFIXR3 保留；`FAILURE_CONTINUATION_RECOUNT_R1.json` 对其中 173 个节点记录定向 PASS **173/173**，但 `current_frozen_full_acceptance=false`：不同源版本的局部 PASS 不能替代最终同一源版本的一次完整执行。
7. 历史/原生 fixture：Clean Phase0 29 PASS；原生 R2 fixture 16 PASS；旧历史测试 149 节点首轮 145/4，后二次 4 PASS；CLI 和 exact archiver、原生产约束下旧原始 AST 均有定向记录。
8. 精确文件恢复：Owner 依赖调查 10,357 个引用，精确找回 363 个缺失文件；剩余 184 个含表名、通配路径、伪路径、负例，不可一概算成真实生产缺件。Git LFS 23 对象、约 2.98GB 已报告 SHA 匹配。
9. 无硬编码个股：当前 no-symbol 扫描零硬门命中；历史原版保留但不可放进 V4 当前生产路径。
10. 生产 Heads 保留：正式 Data/Operational Head 曾记录 `38e7c9b69aa1b47224aa367bcc58bd2ee6127a...` / `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；具体精确 SHA 一律以最新本地冻结元数据为准，禁止使用本段省略号的值作程序参数。

### A2. 未完成的真正工程项（按实际影响优先级）

| 优先级 | 缺口 | 已知事实 | 结束条件 |
|---|---|---|---|
| P0 | 最新代码/来源/测试版本冻结 | 当前 HEAD `d7f632f`；Codex 可能还有本地未提交工程 | 工作树、源 SHA、旧 Head、任务状态和在跑进程就地记录；确认不覆盖活动进程或未提交文件 |
| P0 | 真实自动日更闭环 | 2026-10-12 定时任务曾 `CANCELLED` / `SOURCE_EXECUTION_FileNotFoundError`；后续独立 capture-only 取得 TDX 5561、BaoStock 5224 行，但 `derived_ready=false`、`published=false` | 正式受限 PG 调度→数据冻结→Core/Profile/Sector/Focus/Forward/周期→独立数值对照→原子发布→默认桌面消费，完成同日/同来源读回；失败和重复请求不破坏旧 Head |
| P0 | v0.3 精确复权的当前日更合同 | 原 V1.1 不可改；V2 `publication_ready=false`，旧候选曾 Profile 历史版本查找失败；R2 中断于 namespace 修复 | 当前版本和前任版本各有不可变 source identity；新 V2 通过真实输入、精确坐标、公司行动分类负例、跨阶段消费核验，取得发布权限才执行 CAS |
| P0 | 现行 PG-only 所有真实消费入口 | 88 Owner/Fous/桌面部分入口通过，但完整真实消费者动态证明未闭环 | 全部当前启动/页面/定时任务/重放/比较/结算/Forward/FEP 当前入口均有明确 PG 主链和拒绝 legacy SQLite/DuckDB 的动态证据；原历史兼容测试仅隔离运行 |
| P0 | 56 路/族复权消费和字段语义 | 现有 trace 的 56 项仅观察到 7 项在选定入口运行，不能当作剩余 49 项自动 FAIL 或 PASS | 每项分类 `ACTIVE_REACHABLE / HISTORICAL_ONLY / RETIRED / NOT_REACHABLE_WITH_PROOF`，对 ACTIVE 逐项源→算法→PG→HTTP 独立计算；待确定类别必保留 UNKNOWN，不通过缩分母蒙混 |
| P0 | 完整回归 | 5463 节点首次运行 269 FAIL+157 ERROR+62 SKIP；173 定向 PASS 已记录 | 冻结合法 V4 节点唯一集合，合法历史测试按原始 Git AST 和独立 fixture；在同一版本完成一轮全套完整测试、逐节点零未解释 FAIL/ERROR/非合同 SKIP，结果不含旧 V3 无关套件 |
| P0 | 真正 Windows 原端口切换 | 28871 阶段运行，28765 旧服务保留，`full_product_release` 当前未入正式 PASS | 原端口 28765 由新冻结版本服务、唯一在役 PID、同一生产正式 PG/业务 token/Head、六个桌面入口真实字段通过，并核对重启后一致；不能以 28871 阶段服务代替 |
| P1 | Amount A 交叉来源 | 原生金额 5,561×6=33,366 标量守恒，BaoStock 比较 136 项不同 float32，12 条缺失原生对应 | 根据权威源、单位、float32 精度、停复牌/缺失等分层处置；不可硬凑两源相等。若只影响旁路诊断，单独记录非生产依赖；若影响现役字段必须实际修复和重验 |
| P1 | 页面与功能缺口 | 六入口阶段 200 不证明 300114→302132 跨代码历史、比较页字段 `sector_rs` 与 `rps`、Focus去重或状态解释正确 | 六页实际数据断言、个股/板块/回放/比较/Focus/Forward、过滤搜索日期切换、UNKNOWN、无数据解释，修复当前真实可复现问题 |
| 未来客观事实 | 真正 T+N 成熟、H21/PIT 首获/OOS | 2026-10-12 的事后 capture 不等于原时点首次可用 | 保持 `PIT_ELIGIBLE=false/AS_RECORDED=false`；下一个符合实际时间的交易日连续运行收证。不阻断已确认功能上线，但不能虚构成熟验证通过 |

### A3. 根本耗时来源及必须避免的浪费

- 5,463 节点多轮全量及失败子集交叉重跑，且历史旧阶段 fixture 与当前 runtime 混跑；本轮已有 173 项定向 PASS，只需最终冻结后一次完整回归，而非再次循环跑旧日志。
- 约 2.98 GB LFS 校验、363 个精确缺件回补、10,357 个引用枚举、GBBQ 19 万记录、五日周月海量数值对照已形成大量原始证据；严禁在输入/代码 SHA 未变时重新生成。
- 39 个跨阶段审计条目在 `AUDIT_ITEMS_PRESERVED.json` 全写为 `IN_PROGRESS_NOT_ACCEPTED`，**这只是保留历史 OPEN 的总表，不能反过来抹去已经完成的局部验收**。必须重新形成每项当前证据/余缺/是否当前生产可达/独立状态；禁止新增无实际发现的泛化 OPEN。
- `2026-10-12` 历史采集重放 `REAL_CURRENT_SESSION_REQUIRED` 是时间门；不是 Python 模块缺陷。其后可生成**重构候选**供比较，但不得回填“实际首次采集”证据。下一真实交易日正向首获必须按实时时点执行。

## B. 本轮 Codex 连续续跑合同（覆盖旧的阶段暂停要求）

### B0. 保留现场，不停机、不删文件、不重新开全工程

1. 当前还可能存在 Codex/Windows 工作进程：先用只读命令记录工作树 `git status`, `rev-parse HEAD`, 进程 PID、完整命令、启动时间、当前阶段、G 盘日志增量和最新产物 mtime；先判断是否仍在计算、I/O、死锁或已退出。
2. **不强制停止健康运行**。如已有五日期间任务仍在运行，优先完成对应子任务，不要启动第二份全量任务争夺 PG 锁；必要时在事务边界留检查点。避免并发重复处理相同 T0/Head。
3. 保护 `D:/new_tdx` 和其他 TDX 根（只读）；仅 G:/codex_tmp 和 G:/codex work 作开发运行及工件输出。正式数据/头文件严格按发布合同写入。
4. 记录与正式生产 Head/旧分支/活动端口的差异；未经生产发布门不要碰旧进程。
5. 后续任何阶段不能以 `Drive 上传/下载/读取` 作前置条件。**Codex 全程无 Drive 操作**；用户手动最终一次上传。

### B1. 收口真实自动日更（本轮最优先）

1. 用 2026-10-12 **实际 SOURCE_CAPTURED 输入**（已存 G 盘）查清自动日更失败：比较真正定时 scheduler 与独立 capture-only 的工作目录、路径分隔、来源绑定、存在性、文件权限和事务时序。定位 2026-10-12 取消任务的精确缺件，不得把 `source_ready` 误当 `derived_ready`。
2. 对日更 Policy V2 的每个依赖源保存历史 V1.1 字节及当前源码独立地址；使用 `docs/upgrade/V4_AUTO_EXACT_DAILY_CONTINUATION_R1_20261013.md`，严禁修改旧已接受 Source SHA 后伪装已接受。
3. 在隔离正式 PG staging 执行：Source→Core→Profile→Sector/Market→Focus→Forward/settlement→RAW/QFQ 周月 period→字段→PG readback。中间使用持久化 checkpoint，不从头读数千万原始记录。
4. 第一次真实未来 T0 若尚未进入可采集时间：明确 `CURRENT_CAPTURE_NOT_YET_ELIGIBLE`，利用已有**历史已收盘重构数据**核验算法、真实 source/corrected lineage，不授予首次捕获/PIT。不要因等待未来时点阻断其余代码上线工程。
5. 只有 `numerical_oracle / exact_56_disposition / pg_consumer / field_semantics` 等当前发布硬门具证据，才允许 `publication_ready=true` 和 CAS；逆序、旧 generation、混合坐标、价格影响 UNKNOWN、失效来源必须 fail-closed。
6. 本工作包出口：一条完整正常调度成功记录（可在符合当前时间条件的真实交易日执行）或“功能演练 PASS、未来首获待真实交易日”的明确区分；必须说明这是否阻断生产已接受功能。禁止把模拟成功当正式日更成功。

### B2. PG 消费链和真实数值，按业务入口闭环，不按文件名凑 56

1. 对 6 个桌面入口及当前定时任务扫描真实 `producer→PG writer→accepted authority→PG reader→HTTP/页面` 调用图，特别检查：股票全量画像、领先行业/概念、当前与提前观察、Focus、Forward、对比与历史、回测/未来成熟标记、市场事件、字段 FEP。
2. 对每个入口固定 `T0 + accepted Head + input digest + source version + output counts`。逐字段验证基础价量、金额/换手、复权、日/周/月指标、板块所属成员、指数、比较页、RPS 与 `sector_rs` 不混用、UNKNOWN 和未来不可用处理。
3. 56 清单逐项审定是否现役可达；现役项必须有真实调用和独立正确性证明；历史隔离项验证不能重新进入 production；未知一律不得跳过或归零。
4. Focus 当前局部 2,805 Episodes 与 170 实际公司行动的旧证据复用，但要验证最新 PG/HTTP/Forward 状态及 source identity 的连续传递。11 不可用路径保留。逐个真实当前消费者确认无 SQLite/DuckDB 业务回退。
5. `Amount A` 建立 136 差异/12 缺项逐来源证据表。原生通达信与 BaoStock 可能由于定义、采样与 float32 精度不同而不可强求相同；只有当生产字段合同要求同源一致时才以来源差异作为阻断。
6. 子包出口是一张**按实际当前生产入口**的矩阵：入口、PG 对象、主键与版本、T0、数值验证、UNKNOWN 边界、`PASS/BLOCKED`。不得用仅 HTTP 200 取代业务正确性。

### B3. 一次收敛最终完整回归

1. 不要再次刷新 10,357 文件目录、不再执行原始已封存的 2.98GB LFS 下载/复制，也不重复五日聚合，只做源/输入 SHA 漂移检测；发生真实变化时仅重跑所依赖范围。
2. **唯一冻结版本**：固定 Git commit + test source SHA + 数据 Head + PG 集群 identity + 策略合同，再确定完整合法 V4 测试集合。保留原 4,568 baseline、4,789 诊断与新增 5,463 全套节点的来源对照，明确每份集合内外差异；禁止用 173 子集替代总集。V3-only 不属于当前 V4 必要执行集合，但需要有可查规则证明，不能随意删 V4 原始节点。
3. 历史旧 Git-stage 契约必须通过独立、可复现的只读 fixture 运行，不能因老测试使用 DuckDB 的历史输入就放开当前 V4 生产代码的 DuckDB 禁令。
4. 对最近全量失败先按性质聚类：失效源字节、PG fixture、当前业务算法、版本差异、真正数据/字段错误。修复一组，定向跑一组；记录每组原始失败和修复回执，不重复全系统。
5. **只在完成最后一轮核心修复后进行一次统一 clean-slate full run**；冻结代码后不再乱改源。输出所有 5,463（若新节点合法增加则说明新数字）的 PASS/FAIL/ERROR/SKIP 一致性和合法跳过理由。不能只拿历史的 173/173 PASSED 做发布凭证。
6. 39 审计项逐条登记：`CURRENT_PRODUCTION_GATE_PASS`、`FIXED_NEEDS_FINAL_RUN`、`HISTORICAL_ONLY`、`FUTURE_DATA_WATCH`、`TRUE_BLOCKER` 五类，提供证据路径。范围类总项不能永远统称 OPEN，也不能因前置日期数据未成熟阻止其他工程验收。

### B4. Windows 桌面实际生产切换（明确是执行任务，非再写计划）

**用户已授权：只使用 Windows 桌面 `127.0.0.1`，无互联网/移动端；性能压测、正式 rollback 演练本轮不作为门禁。** 仍保留静态快照/旧服务启动资料，防止失败时造成无法使用。

1. 最终服务要求**实际运行在用户使用的原端口 28765**；28871 只是阶段隔离服务。核对编译包的源 revision 与已冻结测试 SHA 一致，不允许二进制对应旧 HEAD。
2. 切换前做只读现场记录：当前 PID、端口、工作树/服务入口、PG DSN 目标、Data/Research/Joint Head SHA、配置、任务计划程序、原有用户数据；新旧数据库绝不混用。
3. 只有 B1/B2/B3 当前**真实可执行功能硬门**完成并保留证据才能切换。把未来 OOS/H21/真实首获等未到时点的验证单独登记为 `FORWARD_PENDING`，禁止伪造通过。
4. 在同一轮受控替换新包与必要正式 PG read authority，按原启动入口启动（不要求再问用户许可），确认只有一个预期生产 PID 绑定 28765。当前引擎健康、数据/Head 版本身份一致，六桌面入口渲染真实 PG 数据及字段，对输入日期跨页、历史比较、Focus 跟踪、未知值、搜索、前后端响应时间和来源说明做实际交互。
5. 实际重启一次后验证读取一致与日更调度状态。无需性能压测、无需人为制造生产回滚；但切换失败时必须保住旧生产可用性，不允许留下半切环境，记录具体失败而不是虚报完成。
6. 精确报告：`V4_PRODUCTION_CUTOVER_PASS` 仅限原端口新版本运行+功能/数据核对通过；否则 `V4_PRODUCTION_CUTOVER_BLOCKED`，给出第一故障点、已完成修复及保持旧服务可用证据。

## C. 并行与中止纪律（主要解决耗时）

- 正在运行的可复用长期计算 **优先收尾**；其他独立工作可并行（例如旧原版 test fixture、静态图源码分析），但同一个正式 PG owner/数据库/Head 只允许单 writer 互斥。
- 快速“检查点”只含：当前 SHA、当前阶段、完成/在跑/错误、下一条唯一动作、是否保护旧生产；不得反复重新汇报 39 项全部文字。
- 遇失败时**先判断是否阻断其它独立包**。如果不阻断，继续后续包；只有当前生产不可安全切换的硬门才阻断最终激活，不阻断其它工程开发。
- 性能压测、生产 rollback 演练和移动端 390px 检查已由最新用户直接排除；保留历史观察即可，禁止把它们重新设置为切换门。
- 不为了“全部绿”修改事实/缩分母/放宽精度/把旧 SQLite/DuckDB 迁回生产/用假 T0/未来日期/模拟分时充数。

## D. 唯一最终交付（不访问 Drive）

本地保存：`G:\codex_tmp\V4_R4_R3_FINAL_DELIVERY\V4_FULL_CLOSEOUT_FINAL_20261013\`

只在整个任务结尾生成单一 `V4_FULL_CLOSEOUT_FINAL_20261013.zip`，内容包含：

- `00_FINAL_DECISION.md`：真实生产 PASS / BLOCKED、在役 PID/端口、Git HEAD、正式 PG cluster/role、前后 Head、数据 T0、剩余客观未来样本；
- `01_CURRENT_ISSUES_MATRIX.csv`：39 个已存审计项逐项去重并写证据/状态/是否生产阻断；
- `02_LEGAL_FULL_TESTS.xml` + `02_REGRESSION_RECONCILIATION.md`：冻结合法测试分母、全量运行结果、前序 173 定向 PASS 的对照；
- `03_NUMERICAL_ORACLE_INDEX.json`：现有数值大证据的路径、SHA、复用原因和增量结果，不要再拷贝几十 GB；
- `04_PG_CONSUMER_MATRIX.csv`、`05_EXACT56_AND_FIELDS.csv`、`06_AUTO_DAILY_E2E.json`；
- `07_DESKTOP_CUTOVER.json`、`08_OPEN_FUTURE_WATCH.md`、`09_SHA256_MANIFEST.json`、`COMMANDS.md`。

只提供最后本地文件夹路径 + ZIP 文件名 + Git SHA + 唯一结论，**绝不在执行中读写/上传/下载 Google Drive**。用户会手动将 ZIP 上传到：
`https://drive.google.com/drive/folders/1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD`

## E. Codex 可直接执行的接续指令

> 继续执行当前 `codex/v4-full-closeout-20261012` 未完成工程，不重开任务、不重新全量复制历史输入。先核对本地 HEAD、未提交工作、在跑作业、最后变更和冻结证据，保住用户旧生产 127.0.0.1:28765。按照本 R2 的 B0→B4 合同继续推进：先完成真正自动日更与精确复权 V2 的现行 source/PG/consumer 全链，补齐 56 项现役范围、Amount A 分类和字段语义，冻结合法 V4 测试集合并只在最终源冻结后做一次全量完整回归。原证据不变就复用，不因历史旧测试而重开 V3 功能；未来 T0/PIT/OOS 不虚构通过，也不能拿来阻塞已具备证据的现役工程。全部真实硬门满足后，在同一轮将新版本切换至原 Windows 本地端口 28765，验证全部桌面业务入口及重启一致；本轮性能压测、生产回滚演练和手机端不作为门禁。若仍存在真实硬失败，保持旧生产正常运行并交付精确故障矩阵。Codex 全程禁止访问 Drive，所有最终成果仅集中 G 盘一次打包，留给用户手动上传。

## F. 本次审计限制

本次直接检查了 GitHub 远端最近 31 个提交、当前审计注册表、真实执行日志摘要、数值对照 RESULT、功能阶段报告、自动日更失败与 capture-only 结果。未连接 Windows 127.0.0.1 生产服务，也不能判断实时进程是否在执行、最新的未推送代码是否已完成。远端记录由开发方写入；独立外审结论仅限已经看到的代码和证据，并非重新运行了 5,463 个测试或全部 1,800 万次数值比较。

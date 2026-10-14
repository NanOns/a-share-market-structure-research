# V4 生产性能与真增量整改 R1 — 唯一主报告

用户授权执行任务卡 `docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`。按用户最新要求逐项先判定修复合理性；非停止授权，设计冲突单独列出。基线由文档5f322baa前进至远端c5a98cad。本轮所有临时/测试输出在G，TDX只读，保留原包、正式Head、原始输入和无关工作区改动。

## 最新执行状态（R1.1，2026-10-14）

**13日核心修复及正式发布已完成（PASS_SCOPED_PRODUCTION）。** G1/G2/G3/G4、实际PG与HTTP读回通过；正式T0=2026-10-13，包V4_PACKAGE_1.0.0_b06b274246d5，统一token=974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3。原28765的父EXE PID1172、独立同包Worker PID42336运行；正式job f6d227b93468464d8b7b548b9bec3949 为PUBLISHED_FULL，于2026-10-14 07:29:19（北京时间）完成。自动日更保持用户暂停。

原13日仅一次Core全链计算840.744秒；Market上下文仅目标日补算36.603秒。正式封存续接（独立周期数字复核、PG、读索引、CAS及HTTP）147.996秒，没有第二次Core重放。正式Worker真实CPU期间7路接口各20样本，CPU增长9.421875秒；所测实际阶段是REVALIDATE/PG_PREPARE，不冒称第二次全市场Core压力测试。独立真实Core CPU时的源码PG/HTTP成绩另存。

旧包及原错误候选、旧FAIL保留。安装前发现并修复取消竞态，弃用首个工程包，实际本地编译2次、正式切换1次（RI-04例外）；不能宣称遵守一次本地编译限制。后文R1原结论为历史记录，不能当成当前终态。

## 总体结果（原R1历史记录）

**源码与隔离工程验证已完成A/B/D；C已实现并实际对照，但严格身份/摘要一致性要求与旧Owner不可变发生设计冲突，未放行。E按任务卡“仅A—D通过之后”跳过，未打包/部署/恢复自动日更。不能宣称全文任务已完成或生产验收通过。**

生产只读实查：原28765，DaAV4.exe PID5296，包V4_PACKAGE_1.0.0_ef5f1ec494dc；正式T0=2026-10-12，token=d86b5a003704b52e72fefb81a23dc9d96c73df4db79d6c22f86ba08e7c6fcbfc；13日job CANCELLED、active_job=null，自动用户暂停。未将DERIVING/CANCELLED说成PUBLISHED。源码SHA见本报告所在Git提交；未产生新EXE。

## 逐包合理性、执行与验收

| 包 | 合理性与本次实现 | 验证 | 结果/下一步 |
|---|---|---|---|
| A HOTFIX-API | 合理：构建单飞在锁外，仅指针/小缓存加锁；各请求私有日期状态；生产者PG版本索引，SQL WHERE/ORDER BY NULLS LAST/LIMIT；Head身份、日期、授权、库身份不删；旧日未索引按原只读路径；详情保留完整字段；搜索300ms取消旧请求；重叠30条点击续取 | 正式PG只读冻结5224股票/400板块/3025Focus原投影，隔离PG36组查询及home对照0差异；真实隔离HTTP五接口各20次，5并发及独立CPU进程测试 | PASS_SCOPED_ENGINEERING；尚未正式端口安装验收 |
| B NEW-CODE | 合理：两源真实行情准入、稳定独立ID；IPO仅元数据，首见日期与已证IPO日期区分；消失非退市；异常证券版本化PARTIAL有效池、分母披露、不改原freeze；有效池再过因素/日期闸门；前端新代码说明 | 真实SZ.301660两源OHLCV一致；来源异常freeze不可变/幂等/因素失败仍挡；窗口/周期负例定向通过 | PASS_SCOPED_ENGINEERING；新证券全市场PG发布尚未验证 |
| C APPEND-ONLY | 合理部分已实现：计算日仅新T0；精确复权依赖窗口仍计算；Structure保存旧snapshot续接；Sector prior状态续接；D2与Forward引用旧发表状态；旧Owner绑定不变；来源修订显式RANGE_REPAIR、不会暗全量 | 近09/12/13三日30对象26104 OHLC有理数核验；Profile业务值/状态0差异；实际单日5225/400板块native/relative/rotation/seed全行0差异，69.52s；30对象实际Focus/Forward业务值同，但身份与摘要不等 | BLOCKED_DESIGN_CONFLICT；不得隐藏差异或覆盖旧身份 |
| D WORKER+PROGRESS | 合理：同EXE --daily-worker仅生产子进程；PG单writer/幂等/CAS保持；安全stdin暂停不强杀；PG同job行锁协调cancel/PUBLISHING；阶段/证券每200或2秒进度、心跳、真实耗时、未知ETA null；页面/托盘同端点；reader角色配置 | 真实隔离PG竞争writer/崩溃释放、暂停取消、终态时间、实际模式、取消发布竞态专项通过；真实短子进程QUIESCE通过 | PASS_SCOPED_ENGINEERING；Windows最终EXE与实际全日CPU尚未验证 |
| E ONE-RELEASE | 打包/切换/实测要求合理，但前提A—D完整验收目前不成立；若忽略C差异即部署，会冒用旧算法 admission 或污染身份链 | 未执行打包/切换/真实新增日正式发布 | SKIPPED_DEPENDENCY_DESIGN_CONFLICT，保留last-good |

最终整合定向：76 PASS / 9.91s；未跑全库7288测试，无重复外网采集、无重复EXE。范围明确：新代码/索引/缓存并发/Worker/增量规划。输入版本与真实对照见本目录JSON；完整样本/参考在G:/codex_tmp，未另生成大型ZIP。

## 独立设计审计RI-01（已定位，不可用数值相等掩盖）

文档0.3、4.1要求旧Owner只读、旧成果不能重写；4.4、7.C、8.3.6同时要求与原全日重放的Digest/前后引用一致。真实旧全日重放会重建旧日期的source_fact_digest、anchor/episode身份：生成路径、available_at进入输入摘要，即使原OHLC/价格边界/状态完全相同也变ID。新APPEND保持原正式12日锚点和episode身份。两者不可能既保留同一个原正式历史身份，又与另一个重建历史身份逐字一致。

真实证据：Structure 30样本7对象anchor_id不同，边界价格/质量/状态相同；Focus 30样本episode_id 8项、input_digest/prior_state_binding/publication_id各29项不同，目标Forward业务值一致，严格结果FAIL_PARITY。完整差异保留，未删字段、未改参考、未把FAIL换成PASS。详见DESIGN_CONFLICT.json与FOCUS_FORWARD_PARITY.json。

正确后续合同应分别验“数值/NULL/质量/状态精确一致”和“旧已发布身份/引用不变”；新摘要应重新核对其实际输入引用，不能要求它等于一套被全量重建的旧历史引用摘要。此为设计层纠正，不是要求放宽算法值或关闭因子。当前未擅自授予此替代合同生产验收。

RI-02 来源/算法修订最小影响传播：目前只实现修订检测及显式RANGE_REPAIR阻断，尚未实现并验收所有受影响对象的最小修复运行。不能声称修订用例全通过或普通APPEND永久可用。记录独立scope，不以A/B/D专项代替。

## 十项用例状态

| # | 状态 |
|---|---|
| 1 真实301660首日 | 两源/独立身份专项PASS；真实全链发布NOT_RUN |
| 2 非IPO新代码 | 定向PASS，元数据缺失不阻断行情准入、历史不拼接 |
| 3 消失代码 | 定向PASS，保留身份历史/不造退市或K |
| 4 来源矛盾 | 分证券PARTIAL freeze及有效池接线专项PASS；正式部分发布NOT_RUN |
| 5 2/5/20/60日窗口 | 现有窗口/新股不足/精确周期负例通过；全四时点真实运行NOT_RUN |
| 6 增量全量 | 数值与状态专项同；身份摘要严格FAIL_PARITY/设计冲突 |
| 7 修订传播 | 检测及拒绝错误APPEND通过；RANGE_REPAIR运行NOT_IMPLEMENTED |
| 8 SQL30条 | 完整真实5224/400/3025集合36查询PASS；不触project；NULL末尾/稳定排序/token与日期专项PASS |
| 9 Worker CPU浏览 | 独立合成CPU进程+真实PG/HTTP PASS；实际日更DERIVING/正式端口NOT_RUN |
| 10 中断/PG/重启 | writer与崩溃/取消/CAS边界专项PASS；最终EXE实际重启NOT_RUN |

## API性能（隔离真实PG+HTTP，不是原28765成绩）

| 接口 | 空闲median/P95秒 | 独立CPU进程median/P95秒 |
| context | 0.022/0.063 | 0.029/0.128 |
| stocks | 0.078/0.179 | 0.065/0.077 |
| sectors | 0.048/0.156 | 0.061/0.165 |
| focus | 0.076/0.180 | 0.077/0.177 |
| home | 0.228/0.452 | 0.225/0.263 |

五并发20请求最大：空闲0.360秒、独立CPU0.301秒。每接口20样本。stocks/sectors/focus首屏gzip约5.5/7.0/5.9KB；home仍约923KB，保留完整home响应值，后续可按真实首屏字段进一步拆摘要/证据。生产者构建耗时与原全量投影耗时见READ_INDEX_REAL_PARITY.json；不混入日更实际耗时承诺。

下一步仅针对RI-01修正参考/身份守恒验收合同，补RI-02最小修订传播与真实剩余门禁；通过后再一次完整新增日QA、一次EXE、原28765安全切换与六页面实测。当前所有阶段已处理或明确列为设计/依赖问题，未以“已推Git”冒充安装完成。


## R1.1 继续执行（2026-10-13）

用户新授权按 `docs/upgrade/V4_INCREMENT_IDENTITY_PARITY_AMENDMENT_R1_1_20261013.md`继续，优先替代原4.4/7.C/8.3.6身份逐字同一要求；原FAIL_PARITY及DESIGN_CONFLICT原样保留。新G1/G2/G3/G4独立验收进行中，不把数值相同直接写全链PASS。

T2真实无修订独立检查通过：13号固定ZIP对正式12号history全5224对象、2163109根历史bar重叠逐OHLC/amount/volume核对0差异；GBBQ及成员源与正式12 generation一致；新candidate policy实际执行9 numerical bindings与正式接受版本一致。21修订负例通过，修订明确RANGE_REPAIR_REQUIRED，不启动修订重放。开发驱动版本独立归档且publication_ready=false，等待四道门；未用旧运行证据批准新源码。

T1真实引用链检查继续：正式12 D2的episode早期前态可能指向自身生成批次内部历史D2而非Head逐日Owner；必须沿实际正式provenance解析，不能简单删ID字段判相同。生产active_job=null/自动用户暂停，未擅自恢复任务或切包。


### R1.1 全量汇合口进展（2026-10-14）

实际13日仅compute_sessions=[2026-10-13]完整派生840.744秒，正式Head未变。全5225 Structure、Focus/Forward 的G1/G2/G3通过；5225/400九域数值对照经独立accepted Profile/Seed6行参考订正后零差异，原FAIL保留。当前周月219436项数值检查PASS。PG/read-index准备完成120.194秒。实际派生CPU期间随机loopback的真实PG/HTTP证据另存，尚非新EXE正式28765。

新增全域Market比较抓到真实业务缺陷：breadth0/UNKNOWN和桥接路径与冻结参考不符，全域G123被拦截。RI-03独立审计已开，不采用局部PASS发布；正在核对前态与阶段缓存，并仅修受影响13日Market。正式包、Head和用户暂停设置仍不变。Windows最终验收与Git最终交付尚未完成，任务继续。


### T1—T3 运行准入结果

完整G1/G2/G3及Market单日修正全PASS；真实影子七路HTTP同T0/token成功与错误token回滚均PASS，正式指针原bytes未变。原20采样主要API P95：context0.391、stocks0.300、sectors0.290、focus0.319、home0.337、market0.154秒；新股chart4.012秒。Worker路径实际预检修复角色授权和前态引用别名，定向8项通过；最新66/604源码版本已通过独立元数据守恒及新token真实七路读回。最终policy deab6efe...、候选5742efd6...，仍STAGED_RUNTIME_ADMITTED_NOT_ACTIVATED。CATCH_UP已封存候选续接清单actual预检PASS，不重算Core。下一阶段仅一次EXE及正式28765验收，尚未生产发布。


### RI-04 发布检查点取消复查（已修）

首次本地工程包d076509e7aa5生成后、安装前发现新sealed续接模块在PUBLISHING checkpoint之后缺少取消复查，存在取消请求先赢PG行锁而后继续CAS的竞态。该工程包未安装/未发布；源码补独立cancelled复查，检查点注入取消负例证明不调用promote，7项续接定向PASS。此为本轮实现缺陷，不伪称数值/原身份门失败。为修复安全边界，必须例外重新生成本地修正版包，不能遵守一次本地编译限制；正式安装/28765切换仍只一轮。新66/604源准入、真实七路success/rollback、CATCH_UP清单预检均重新通过，policy80207ac8...、候选974c60e0...；原deab版本及失败包保留。


### T4 最终交付证据与界面范围

正式六条严格同T0/token读回（context、operations/status、stocks、sectors、market、focus），另七条性能与状态接口采样；完整native joint与PG读回PASS；已通过真实浏览器首页、股票、板块、Focus、市场、诊断六页面渲染。板块首屏30行，新股SZ.301660可搜索、独立SEC-7C8816903D4BA9B6267531D5705888B9，仅13日1根真实K线、关闭更早行情；不足5/20窗口保持UNKNOWN，不伪造历史。Focus读域3151个未结束对象；Market趋势WEAK、宽度IMPROVING、压力LOW，真实宽度分母5225/行情5212。实际frozen Win32托盘QA PASS（启动/安全停止/重启、worker重建、暂停保持、退出；模拟HTTP执行器范围明确，非真实Windows重启）。生产原实例安全退出、未强杀；新实例健康LIVE。

已知界面披露：可选代码状态字段仍显示“字段未接入”（首日行情/身份/数值来源已接入）；已终态进度横幅仍按最后进展年龄显示提醒；首页雷达/Forward统计摘要仍标来源未接入，真实Focus读域单独可读。这些不冒称全产品字段已接通，也不伪造元数据或高级能力。RI-02后续真正修订范围引擎按R1.1单列，不阻塞本次无修订APPEND。

正式Worker期间与空闲P95（秒）：

| 接口 | Worker P95 | 空闲 P95 |
|---|---:|---:|
| /api/v4/context | 0.205 | 0.298 |
| /api/v4/stocks | 0.312 | 0.230 |
| /api/v4/sectors | 0.439 | 0.324 |
| /api/v4/focus | 0.371 | 0.360 |
| /api/v4/home | 0.441 | 0.552 |
| /api/v4/operations/daily-update/progress | 0.141 | 0.154 |
| /api/v4/desktop/status | 0.154 | 0.153 |

主要证据：FORMAL_DELIVERY_R1_1.json、FORMAL_WORKER_HTTP_R1_1.json、FORMAL_POST_PUBLISH_HTTP_R1_1.json、FROZEN_TRAY_QA_R1_1.json；源码/准入提交007e9605b（前序1cbaaa7f3、1b4a680a4）。最终证据提交以本报告所在Git提交为准。未重跑7288回归、未重复采集、未上传Drive，所有新临时及交付在G，TDX只读。


### V4-R1.1-POST-CUTOVER-LIGHT-FOLLOWUP（2026-10-14）

阶段合同：外部 R2 审计的第四节为本次轻量工作包；已查阅最新 R1.1 身份修订与 R1 性能整改升级文档。本次只修显示语义，不重新授予生产验收，不覆盖此前 A/B/D、G1—G4 或失败证据。

F-01 工程修复：startup_snapshot 与 shutdown_snapshot 分开。兼容 cached_snapshot 只指启动快照，快照自带 captured_at/startup_only，顶层 cached_snapshot_semantics 明确 startup_only=true 和 current_context_endpoint=/api/v4/context；状态查询不额外读取/重算正式业务上下文。启动前清除上一轮启动值，停机不再覆盖启动快照。页面现有数据日期来源仍是原研究上下文，托盘不消费 cached_snapshot。

F-02 工程修复：只有 stage_state=RUNNING、没有 finished_at 且最后进展超过120秒才提醒；终态展示完成时间和接口给出的已冻结总耗时。F-05 已订正本报告六条严格版本检查与七条性能采样的口径；既有原始收据不改写。

验收：10项定向测试 PASS，包括实际 JS 组件的运行/完成/失败/取消/空闲，以及隔离 HTTP 的启动→新上下文发布→停机快照语义。额外尝试既有 PG 生命周期测试未到 HTTP 预检（entered.wait 超时），底层异常尚未确立，不声称真实 PG 集成通过。证据 POST_CUTOVER_LIGHT_FOLLOWUP_R1.json 保留范围与生产只读采样。阶段结果 ENGINEERING_ACCEPTED_NOT_DEPLOYED：源码变更等待下次确需部署统一打包，本次未构建/安装/切换，也未写调度设置或生产 Head。

独立开放项：F-03 范围是下个真实收盘日常规无修订 APPEND 全链及正式 EXE 冷启动；证据必须覆盖采集、Core、Profile、Sector、Market、Focus/Forward、Period、PG、CAS分段耗时、旧Owner、真实New Code、全量证券/板块、同T0/token及正式端口浏览。验收不能复用sealed-resume代替。下一阶段等待用户明确允许的收盘后维护/手动日更窗口，保持自动日更暂停。F-04 分为有源可接线/真实无源/尚未允许，现有代码状态及首页雷达/Forward摘要仍披露未接入，未伪造数据。RI-02 RANGE_REPAIR 继续独立backlog，修订检测fail-closed保留。以上开放项不扩大本次显示修复门。


### R3 / F-PG-01 定点测试消歧（2026-10-14）

阶段合同：按用户提供R3文档第4节，本轮仅处理F-PG-01，基线fbf3a395，保留10-13原生产验收和F-01/F-02源码PASS。执行前已查阅R1性能整改升级文档，不进入APPEND、冷启动或部署阶段。

原超时复现并记录完整启动线程traceback：未设置V4_NATIVE_PG_DSN，ManagedDailyJobs→DailyJobs→configured_dsn报V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK。线程约0.195秒退出，HTTP未绑定/预检，随后entered.wait(5)超时。该信号来自测试配置缺失，没有PG慢查询或显示修复故障的证据；未加大wait，原失败证据不覆盖。

环境补配过程：默认旧remainder隔离profile缺少该端口准入manifest，仍拒绝DISPOSABLE_PG_CLUSTER_REQUIRED；使用现役R4 native profile初次缺data_directory、随后缺connection ledger，两次内部配置错误均不计PASS。只读SHOW data_directory核验55791为G:/codex_tmp/full_system_r4_fbd23a6b/pg_data后补齐R4_NATIVE_ISOLATION、R4_PG_DATA_DIRECTORY、R4_CONNECTION_LEDGER；保留连接审计及数据库隔离保护，只写G盘测试root派生的独立schema，不使用生产schema。

原测试新增后台异常栈和factory/PG初始化/暂停持久化/HTTP绑定/预检/启动完成/停机分段时间；参数化managed旧兼容路径和process现役控制门面。最终Managed 1 passed in 1.60s，PG初始化约0.292秒、启动线程到RUNNING约0.732秒；Process 1 passed in 2.04s，PG初始化约0.161秒、启动线程到RUNNING约0.392秒。这些是隔离PG和模拟上下文的测试时间，不是正式EXE冷启动成绩。

Process专项使用真实ProcessDailyJobs、真实PG、真实子进程/monitor；子进程只读确认暂停，父子PID不同，监控线程存活，QUIESCE退出。仅替换完整任务体为受控读取体，不验run_daily_worker采集/Core/CAS，不能替代F-03。本轮只改测试和证据；未改生产源码、未全量回归、未构建/安装/切换、未开启调度。

独立审计项F-PG-01：范围为原等待超时消歧，验收F_PG_01_CLOSED_TEST_CONFIGURATION_WITH_SCOPED_RUNTIME_PASS。F_PG_01_R3_DIAGNOSTIC.json留存负例traceback、各阶段耗时、两条路径连接ledger、复现环境和生产只读状态。旧POST_CUTOVER_LIGHT_FOLLOWUP_R1.json不覆写，本节为后续闭环。F-01/F-02仍ENGINEERING_ACCEPTED_NOT_DEPLOYED；F-03普通APPEND/正式冷启动、F-04逐字段分类/接线、RI-02 RANGE_REPAIR、shutdown_snapshot历次时间语义P2仍开放。下一阶段等待真实收盘数据及明确手动维护授权，保持自动暂停；推送不是下一阶段准入。


### TRAY-UI-01 Windows弹窗关闭修复及正式生效（2026-10-14）

用户直接报告关闭不消失、关闭后托盘卡住，并要求修复。本阶段合同为托盘弹窗生命周期最小修复，已查阅R2.1打包设计、R1性能整改与本报告现役阶段，不进入新的算法/采集/APPEND阶段。TRAY-UI-01独立于F-PG-01及原数值门。

源码发现状态PG读取和MessageBoxW均同步运行于托盘消息回调，重复触发无单实例门；维护YESNO窗口也无Cancel，Windows标题栏关闭不可用。修复：状态读取/显示移到专用线程，状态窗口单实例锁在关闭/异常后释放；维护确认移到操作线程，重复请求不叠加，YESNOCANCEL的取消/×只撤销请求，唯有IDYES执行。原安全维护流程保留，不强杀引擎。

6项定向测试PASS；真实Windows隔离窗口经computer-use点击状态×及维护×，后者返回取消。正式冻结托盘8项启停/重启/暂停/退出检查PASS。构建前两次环境预检分别缺pystray metadata和PYTHONPATH，均未进入PyInstaller；随后使用现有G盘build env完成一次编译。新包V4_PACKAGE_1.0.0_88cc19deae3b资源集合与原包完全相同，仅tray.py、engine.py及desktop_status.js三文件改变，数值/政策资源逐SHA守恒；因此合入此前F-01/F-02显示修复。

当前生产空闲(active_job=null)后，保留旧包和任务XML，原PID1172通过既有核验owner的安全退出命令结束，未强杀；新PID34284运行原28765。正式context_token保持974c60e0...、T0=2026-10-13，三个Head/authority文件哈希保持，auto_daily_enabled=false。计划任务入口更新至新包（原任务路径与此前实际运行包不同，原XML保留），未启动普通日更。

新生产EXE真实状态弹窗×关闭成功；随后通过受支持的已有实例唤起消息重新打开，再以确定关闭成功，证明关闭后消息泵仍响应。没有声称已物理点击托盘菜单每个条目或验证双尺寸。验收PASS_SCOPED_DEPLOYED_DIALOG_CLOSE；证据TRAY_DIALOG_CLOSE_REPAIR_R1.json。F-01/F-02现在随本包正式生效，cached_snapshot语义现场读回正确；本轮未另行做全部终态前端页面矩阵，不扩展F-03正常APPEND/冷启动、F-04接线或RI-02验收。下一步在用户需要时正常使用托盘，其他阶段仍按其原准入条件。

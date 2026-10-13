# V4 生产性能与真增量整改 R1 — 唯一主报告

用户授权执行任务卡 `docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`。按用户最新要求逐项先判定修复合理性；非停止授权，设计冲突单独列出。基线由文档5f322baa前进至远端c5a98cad。本轮所有临时/测试输出在G，TDX只读，保留原包、正式Head、原始输入和无关工作区改动。

## 最新执行状态（R1.1，2026-10-14）

13日完整增量数值、Structure/Focus身份与摘要、周月已完成工程核验。新增Market前态缺陷已仅修13日，业务与真实摘要PASS，新PG候选准备成功351.639秒；正在汇总最终全域门、真实影子CAS及Windows唯一交付。原正式Head仍12日，未安装新EXE。下文R1原结论为历史记录，不能当成R1.1当前终态。

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

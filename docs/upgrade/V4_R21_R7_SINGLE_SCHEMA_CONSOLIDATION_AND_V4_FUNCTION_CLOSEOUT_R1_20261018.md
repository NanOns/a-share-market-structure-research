---
stage_id: V4_R21_R7_SINGLE_SCHEMA_CONSOLIDATION_AND_V4_FUNCTION_CLOSEOUT_R1_20261018
status: PARTIAL_DATA_AND_MODULE_ACCEPTANCE_OPEN
database: market_research
database_oid: 646711
business_schema: v4
development_http_port: 28766
production_http_port: 28765
production_changed: false
---

# V4 单一 Schema 收敛与模块续修阶段报告

## 范围与依据

按唯一任务卡 `V4_R21_R7_唯一Schema架构纠偏_76Schema迁移清理_全模块续修总任务卡_R1_20261018.md`、SOT `V4_唯一业务Schema统一存储架构_SOT_R3_20261018.md` 和本轮独立审计报告执行。此前 R21-R6 R2 旧任务停止；已完成且正确的算法、PG、功能改动和用户要求保留的三份 Owner 修改继续保留并复核。

唯一业务数据库为 `market_research`，唯一 V4 业务 Schema 为 `v4`。所有新运行时写入使用 `v4` 下固定版本化表；工作区、模块和版本不得决定物理 Schema。未创建 Alias 或附加 Schema；未使用 `DROP CASCADE`；不得批量导入 1,678 项历史绑定。

**日更日期口径：**本轮日更基线为 `2026-10-15`，目标/测试日为 `2026-10-16`。数据库已有两日的 BaoStock runtime acceptance receipts，10-16 目标日读回 5,226 条日行情和 48 条因子；这证明来源运行回执可读，不代表正式 Accepted 日更已发布。个股/日更页面的 `2026-09-30` 是当前 `V4_DATA_ACCEPTED_HEAD` 的研究快照 T0，不是日更最新日期，也不是本轮测试日。正式日更仍被接受交易日历与 Accepted Operational Head 缺失阻断。

## 阶段结果

| 阶段 | 结果 | 证据与范围 |
|---|---|---|
| S0 真实对象、消费者和权限盘点 | PASS | 合并前只读快照为 76 个 V4 物理 Schema；2026-10-19 最终只读快照确认 DB OID 646711、`127.0.0.1:5432`、只读事务开启，现只剩 `v4`。完整最终快照在 `G:\codex_tmp\v4_single_schema_inventory_20261019.json`。 |
| S1 停止动态 Schema 生成 | PASS | `workspace_schema()` 固定返回 `v4`；应用连接拒绝任何其他 Schema；Schema 创建边界拒绝非 `v4`；Alias 注册禁用；旧独立 live Shadow writer 在连接数据库前 fail-closed，R1/R2 导出 API 仅委托固定 v4 R3 writer。另在真实 `market_research` 中以 QA-only 记录完成 Snapshot/Series/Journal 各 A/B 两个不同 release 的写入、精确版本读回与隔离核验，前后业务 Schema 集合均为 `v4`。 |
| S2 固定表结构 | PASS | 最新 `REPEATABLE READ READ ONLY` 目录核验为 `v4` 下 124 张表、88 个例程、194 个非内部触发器。计数包括已部署的固定版本化存储迁移；这些触发器是现役关系的约束，不是旧 Schema 残留。 |
| S3 精确迁移与旧 Schema 清理 | PARTIAL | 当前全库非系统用户 Schema 仅 `v4`，旧 75 项均不在目录，跨用户 Schema 依赖为 0；但逐项清理执行收据不足：G 盘证据审计仅找到 37 项持久 `DROP_RESTRICT_SUCCESS` 收据，38 项没有可回读的逐项执行收据，其中 8 项 Forward/R8 在仓库也没有对应清理执行器。不能将目录缺席等同于逐项 RESTRICT 成功证明。Forward 映射 11 个来源 Schema 的 9,256 条行映射均为 `VERIFIED`，另有 R8 的独立 251 行 digest 回执。 |
| S4 全部运行时消费者切换 | PARTIAL | 主研究、股票图表、板块成员、Focus/Forward、诊断、Owner 精确 SourceIngress、日更仓储和 Shadow 导出/读回均经唯一 `v4` 边界；历史引用只通过固定表中的精确迁移回执解析。Shadow 固定存储已部署，真实接受清单仍缺失并 fail-closed。 |
| S5 全模块续修 | PARTIAL | 可执行的消费者修复和 28766 浏览器检查已推进。候选快照未发布为正式 Head；缺少接受交易日历及若干模块历史输入，不能将候选可读视为模块验收完成。 |
| S6 DB-01..12 与 28766 浏览器验收 | PARTIAL | 已完成的受控数据库及浏览器检查见下表；待到期、PIT 历史、日更作业回执和真实上游输入仍未满足全部验收门。 |

## PostgreSQL 迁移与核验

- 只读事务实测：数据库 `market_research`，OID `646711`，端口 `5432`，`transaction_read_only=on`，隔离级别 `repeatable read`。本机 PostgreSQL 子进程不是多个数据库实例。
- 最终目录状态：合并前的 76 个 V4 物理 Schema 当前只剩 `v4`；75 个旧 Schema 均不在目录，`v4_*` 为 0，目录跨用户 Schema 依赖为 0。对清理方式作证据复核后，现有可持久读回的 `DROP_RESTRICT_SUCCESS` 收据为 37/75；38 项仅能证明最终目录缺席与相应迁移/清理合同，其中 30 项有使用 `RESTRICT` 的清理脚本但没有逐项执行输出收据，另 8 项（7 个 `v4_forward_*` 与 `v4_r8_forward_64d0f9c30983a3ac`）在当前仓库找不到相应清理执行器。未发现 CASCADE 执行证据，但也不能把未留存执行收据表述为已证实 RESTRICT 成功。逐项核对文件为 `G:\codex_tmp\v4_single_schema_evidence_audit_r1_20261019.json`。
- 已把初始快照 76 项与迁移/退役台账、最终 `pg_namespace` 结果交叉核对，形成 75 个旧 Schema 名称级退役矩阵；75/75 均已不在最终目录。分类为 Research 32、Forward 12、R8 Forward 1、History 3、Jobs 9、ReadIndex 2、Journal Registry 2、Owner/其他旧模块 13、`v4_meta` 1；保留的唯一业务 Schema 为 `v4`。矩阵记录逐项来源映射表/回执行数及最终存在性，位置 `G:\codex_tmp\v4_single_schema_retirement_matrix_20261019.json`。没有迁移映射的 `v4_meta` 与 R8 Forward 行单独依赖 Schema 清理/退役证据，不伪装成数据迁移行。
- Forward 固定表：`forward_schema_migration_map_r1` 有 9,256 条映射，9,256 条回执均 `VERIFIED`，覆盖 11 个来源 Schema。最大旧 Forward 关系 2,457 行、8,394,104,832 字节，作为零复制、只审计的 `v4.forward_legacy_evidence_r1` 保留；活动精确映射 390 条仍指向固定 `v4.forward_facts`。该存档保留原始字节，不代表活跃旧 Schema。
- 固定 Forward 目标表在最后只读盘点中有 `forward_facts=9,280` 行、`forward_r7_facts_r1=312` 行。按来源版本/工作区继续分表或建 Schema 已禁用。
- 2026-10-19 再次以 `REPEATABLE READ READ ONLY` 查询关系尺寸：`v4.forward_facts` 总尺寸 6,188,883,968 字节（主表 3,268,608）；`forward_r7_facts_r1` 2,182,561,792（主表 139,264）；`forward_legacy_evidence_r1` 8,394,104,832（主表 647,168）；`read_items_r1` 4,230,397,952；`read_items_r2` 1,951,940,608。总尺寸包含 TOAST/索引，因此主表尺寸明显较小不表示数据缺失。Legacy Forward 最大表使用原 OID 原地改名归档，迁移回执 `payload_bytes_copied=0`、2,457 行、源摘要一致；这说明没有复制 8.39GB 负载。统计目录的估算行数可能滞后，精确行数以迁移回执/约束核验为准。
- 固定 `forward_facts` 的三键等值点查 `EXPLAIN (COSTS, FORMAT TEXT)` 选择 `forward_facts_pkey`，估算成本 0.41..8.43，无全表扫描。
- `workspace_namespace_aliases_r1` 活跃映射表已移除。保留的 7 条记录位于不可变 `workspace_namespace_alias_history_r1`，`migration_state=MIGRATION_HISTORY_ONLY`，仅作历史审计；应用 Alias 解析及创建均关闭。
- 未迁移独立审计指出的 1,678 项历史绑定。仅对当前 PG Data Accepted Head 明确引用的 30 个 path/SHA/bytes 绑定执行核对：原有 8 项已在 PG，缺失 22 项（43,957,203 字节）经工作树/Git 精确字节恢复后写入固定 `v4` SourceIngress，并对全部 30 项作 PG 只读快照读回，路径、SHA、字节数逐项一致；绑定集合摘要 `78d1d7ca03263fadc16dc74c00f2cca05080c6eebb5cc390e0452fdddee0b87a`。其中 Stage Head 采用 Head 绑定的历史精确版本（8,574 字节），未替换当前工作树文件。回执位于 `G:\codex_tmp\v4_data_accepted_head_bound_source_ingress_20261019.json`。这 30 项是当前 Head 的活动绑定，与 R14 的 1,678 项历史清单分离。未把约 23GB 历史 Forward 数据整体复制；保留的旧大关系以 OID/回执核验后在统一 Schema 内只读归档。
- Data Accepted Head V2 在 PG 中存在且精确绑定 2026-09-30（SHA `38e7c9b6…48ff3e40`、16,890 字节），其外部接受范围明确为 `RECONSTRUCTED_CORRECTED`，`AS_RECORDED=false`、`PIT_ELIGIBLE=false`，Focus/Production/Shadow 权限均 false。Head 绑定的日历文件包含 789 个交易日，覆盖至 2026-09-30；另有官方日历扩展只接受到 2026-09-30。统一 PG 的 `market_calendar_sessions` 与正式 `v4.publications`、`v4.publication_heads`、`v4.operational_research_heads` 仍为空；R4 延伸至 12-31 仅为本地待审候选，不能生成正式日历 Head，因此后续日更仍 fail-closed。

## DB-01..12 状态

| ID | 状态 | 任务卡验收与证据 |
|---|---|---|
| DB-01 | PASS | 当前只读 RR 事务实查唯一 V4 业务 Schema 为 `v4`，`v4_*` 为 0；真实 PG 中 6 个 QA-only 版本（Snapshot/Series/Journal 各 A/B）分别写入并读回；单 Schema 守卫拒绝非 `v4`。 |
| DB-02 | PASS | 六个不同 Research Release 分别在固定 `v4` 版本表中完成 descriptor、T0、release_id、完整内容摘要验证；每个 release 精确只读回自己的 QA key，A/B 无串读。 |
| DB-03 | PASS | RAW/QFQ Series、多日 Journal 固定表正向样例读回并回滚；错 T0/缺版本校验 fail-closed。 |
| DB-04 | PARTIAL | Forward 数据按 namespace/run/T0 使用固定 `v4` 表并保留旧键碰撞身份；Focus 历史到期/自动写入与完整成熟 outcome 尚缺真实验收输入。 |
| DB-05 | PARTIAL | 75 个旧 V4 Schema 的最终缺席、来源映射和 37 项持久 `DROP_RESTRICT_SUCCESS` 收据已交叉核验；另 38 项无逐项持久执行收据，8 项 Forward/R8 名称无现存清理执行器。Forward 9,256 条精确映射回执仍为 `VERIFIED`，当前 Data Head 30 条原始绑定字节级读回也保持通过。未发现 `CASCADE` 执行证据；完整逐项清理方式尚未全部证明。 |
| DB-06 | PASS | Research 旧 descriptor 原始字节/SHA 保留；固定 `v4.research_releases` 记录旧 Schema、旧 digest 与新 release/manifest 的对照，迁移不伪称旧/新 descriptor digest 相同。 |
| DB-07 | PARTIAL | 现役连接入口固定 `v4`，此前 28766 首页/Forward 来源审计页可读固定 `v4` PG 候选；本次检查确认当前监听 PID 27332 在 06:21 启动，早于 06:39–06:41 的后续提交，因此不能把这次页面结果认作最新代码验收。开发端受控重载调用被执行策略拒绝，28765 未触碰；需在 28766 最新代码实际加载后复核。 |
| DB-08 | PARTIAL | 四日 Core 独立 Oracle（09-28、09-29、09-30、10-08）已有 0 error 结果；四日完整 Sector/Focus/Market/Forward 数值闭环受 10-08 PIT、前序成员和成熟结算来源缺失阻断。 |
| DB-09 | PARTIAL | 当前 Data Head 的 30 项精确 Path/SHA/bytes 绑定共 60,488,930 字节均在 PG 读回相等；另用 64 MiB+1 字节事务内工程负载验证 5 块写入、重组读回、长度/SHA 与回滚。未把真实 551 MB TDX ZIP Base64 复制到 Forward facts；其真实包/独立接受合同仍未验，历史 1,678 项未导入。 |
| DB-10 | PARTIAL | 日更和 Jobs 只读/幂等路径可运行；`market_calendar_sessions` 与正式 publication Head 为空、没有 worker 回执，故不签发 Accepted/DEV Head、不宣称重试/增量真实作业通过。 |
| DB-11 | PARTIAL | 仓库唯一、28766 单槽已复核。旧 baseline、治理恢复证据及其他历史目录经实际计量；存在未提交/独有内容或不可替代恢复证据，保留，物理工作区清理未完成。 |
| DB-12 | PASS | 当前 RR/RO 库目录仅 `v4`，交叉 Schema 依赖 0；2026-10-19 最新目录复核为 124 张表、88 个例程、194 个非内部触发器。Schema owner 为 `postgres`、ACL 为默认值；目录中只有 `postgres` 登录角色有 `v4` USAGE/CREATE，已退出的 closeout 登录角色均为 false。系统 Schema 未改动，所有已审阅迁移删除均显式使用 `RESTRICT`。 |

## 全模块缺口与可执行验收路径

| 模块 | 现有真实状态 | 尚缺的业务输入/权威 | 输入到位后的真实续验路径 |
|---|---|---|---|
| Research Core / Profile | 四个既有候选日的 Core Oracle 已报 0 error；研究版本固定写在 `v4`。 | 足以证明目标日期原始状态的完整 PIT 官方行情及独立来源合同；当前部分日期为 `RECONSTRUCTED_CORRECTED`。 | 复用既有四日样例，只对存储版本键/受影响算法跑最小数值回归；同一 T0 对照 OHLCV、MA 与 Profile 数值、版本摘要和来源身份。 |
| Sector / Rotation / Market | 当前 2026-09-30 候选截面可读；统计未知项显式呈现。 | 前序日期 PIT 行业成员与市场状态；官方事件/媒体来源及分钟炸板序列；缺少经接受的交易日历。 | 按接受日历固定 T0；核成员集合、LOO、宽度/强度/涨跌停分母和轮动状态的逐日数值；事件按来源合同核验原始时间戳与证据。 |
| Owner / Publication / Head | Owner 读取使用固定 `v4` 与精确来源绑定；DEV CAS 正/负路径已在回滚事务验证。 | 已批准 Owner/合同版本、真实 publication/module results 与可绑定来源的 Head；当前 publication、publication_heads、operational_research_heads 均 0。 | 用真实批准来源执行 Owner→模块结果→DEV publication/head 端到端写读与 CAS/失败重试；校验精确 T0、digest、row_count、数据库身份及 stale-CAS 拒绝。不得写正式对外 Head。 |
| Focus | 候选快照显示 469 条，来源为冻结重建；缺项以 Unknown 表示。 | 已批准结构谓词/失效合同、完整跟踪事件与真实后续交易日行情；成熟结算结果和历史账核对仍不足。 | 固定 candidate/run/namespace/T0 逐条核输入；仅用真实后续会话计算 D0/D2、到期/失效及 outcome，核对旧账、幂等重试和未成熟样本 Pending。 |
| Forward / Cohort / Settlement | 117 个候选、585 个期限计划、5 条已发布期限状态覆盖 1 个样本；成熟合格为 0。R7 事实读回为研究级且非 PIT。 | 同 namespace/run/T0 的完整后续 PIT 行情、已接受日历及明确 Owner/来源；成熟交易日尚无独立可接受结算事实。 | 精确绑定 Forward cohort 与 Owner；核每个 horizon 的交易会话日期、源行数、摘要、缺失/冲突键；只对真实到期样本结算并检验同 key 跨 namespace 隔离。 |
| SourceIngress / Data Head / TDX | 当前 Data Head 的 30 项精确 Path/SHA/bytes 绑定可从 PG 读回；64 MiB+1 chunk 边界已回滚验证。10-08 ZIP 字节/CRC 校验通过。 | 10-08 ZIP lineage 为 `RECONSTRUCTED_CORRECTED`；独立接纳 issuer 为空，不能签发 `AS_RECORDED`、PIT 或 Accepted。 | 有合同认可的真实来源后，以有界 chunk/stream 写入固定 Source Package/SourceIngress，读回逐块 SHA、长度、manifest 与引用；独立验收者确认后才更新接纳状态。不得灌入 1,678 历史绑定。 |
| History / Stock charts | 固定 `v4.history_versions_r1` 版本可读；候选版本 ba5ac5f7… 在 T0 2026-09-30 覆盖 5,224 证券、1,309,832 根；页面日/周/月 RAW/QFQ 图表真实渲染。 | 当前行情谱系不是完整 PIT/Accepted；需要合同认可的逐日官方行情和复权依据。 | 逐源对账目标证券各周期 bars、日期边界、RAW/QFQ、均线及摘要；T0 错配/缺 bar 必须拒绝，浏览器验证不能替代来源准入。 |
| Daily / Jobs / Calendar | 数据更新页正确禁用写操作；worker 未启动，来源请求 0，尚无作业回执。 | 当前接受来源 registry 无批准 issuer；`market_calendar_sessions`、publication/head、worker receipt 均为空。 | 用真实被批准的交易日和数据源执行一次完整 DM-01 runner；读回每 stage/job/source receipt，验证同日幂等、下一交易日增量、失败恢复、超时重试及无新 Schema。 |
| FEP | 固定 `v4` 存储迁移已部署（35 张关系，34 张带保护）；业务行为空；页面保持 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`，Champion 为 NONE。 | 经批准的 FEP Owner、真实信号/结果及成熟 PIT 样本、当前有效模型/合同签发；不得用历史 fixture 自我授权。 | 先按固定合同导入/生成带来源身份的真实 FEP facts，再核分母、校准与成熟度读回；只有独立授权和模块门通过后才评估展示/研究能力，不据此授予生产权限。 |
| Shadow | identity/facts 固定表与 immutable guard 已部署；表内真实探针行数 0；28766 正确显示 `NO_REAL_SHADOW_DATA`。 | 独立接受的真实 readback manifest、签发来源及 PIT 输入。 | 以完整签名身份与来源证据走 R3 writer；核全量内容摘要、逐 fact origin、数据库身份和只读 reader；无接受清单继续 fail-closed。 |
| Replay / Compare / Risk | Compare 的事后重建视图可读并显式标非 PIT；严格 Replay 可用日期为 0。Home 对未绑定 risk Owner 已修为显示来源缺失。 | 冻结 PIT 日线/成员/Owner、足够历史窗口、风险 Owner 和来源完整性。 | 对同一个已接受 T0 重放并核历史身份/无未来数据；Compare 区间对齐且报告来源；Risk 按 Owner 输出变更，否则必须保留不可判定状态。 |
| Workspace cleanup | 全仓 `.pyc` 已逐项清点；2,159 个可重建项与 6 个无对应源文件项均保留，旧目录中仍有独有/未归属证据。 | 精确逐目录依赖确认与可执行的受控清理操作；工具策略此前拒绝逐项缓存删除。 | 仅对已证可重建、无活动依赖且不含唯一证据的具体路径执行清理；清理后复扫尺寸/路径并保存前后差异。若同一操作仍被工具策略拒绝，记录为未完成，不换通道绕过。 |

以上路径把工程验证、真实 PG 读写、28766 交互和 Accepted/PIT 业务验收分开。数据库写权限不等于来源签发权；任何缺少独立来源或 Owner 的模块继续保持 fail-closed，不以工程探针、测试夹具或页面显示替代正式验收。

## 原 266 项与 R7 Delta

原始 P1 分母保持 **266**（Owner 200、其他业务 28、市场/源 38）。本轮不重算全仓 161,114 引用边、不覆盖历史 ID，也不把代码改造、PG 数据存在或浏览器显示混报为正式 accepted。历史核对仍记为 **正式 Head/T0/namespace 对账 0/266**，并保留此前登记的 22 条未映射历史 reference edge；此项待原矩阵拥有精确 source-edge 与 Head 证据后单独关闭。

R7 Delta 单独登记：Research snapshot/series/journal 固定表、Forward/History/ReadIndex/Jobs/Journal/Owner 迁移消费者、`stock_views.chart` 固定表读链、Owner 精确 PG SourceIngress、28766 R7 来源审计路由、当前 Data Head 30 项精确 SourceIngress。代码、PG、28766 实际浏览器、正式接受状态分别记录；这些 Delta 不回写成“原 266 正式项已通过”。原迁移矩阵仍应由后续明确的逐行 reconciliation 更新，不能通过总计或测试数量推定关闭。

## 28766 浏览器矩阵

浏览器实测候选：Release `05cf8913242f46c8af53b3d89f323b64`；T0 `2026-09-30`；数据库 OID `646711`；物理 Schema `v4`。API 路径均在 `/api/v4/*`；所有域 `released=false`，不代表正式 Head。

| 页面 / 路由 | 实测结果 | 验收 |
|---|---|---|
| 今日总览 `/v4/research/home` | 股票 5,213、板块 378、Radar 117、Forward 117；市场四轴真实投影；前一已接受板块状态/轮动事件缺失被标注。 | PARTIAL_DATA |
| 板块 `/v4/research/sectors` 与详情 | 378 个板块；区域地产成员 43，成员搜索表可读。强度/宽度当前值可读；前序成员、先前状态和 5/10/20 历史来源不足保持 Unknown。 | PARTIAL_DATA |
| 个股 `/v4/research/stocks` | 全市场 5,213；搜索 `SH.600675` 返回唯一“中华企业”。详情页可读实际行情及证据。日线 120/253、周线 54/54、月线 13/13，均为截至 T0 的 PG 历史绑定。 | PASS_UI / PARTIAL_DATA |
| Focus `/v4/research/focus` | 候选 469 条，显示 2026-09-29/30 冻结重建、状态和路径入口；旧账未完成核对，结构谓词、到期完整度和自动写入仍缺。 | PARTIAL_DATA |
| Forward `/v4/research/forward` | 候选 117；结算计划 585、已发布期限状态 5，覆盖 1 个样本，成熟合格 0；待到期保持 Pending。 | PARTIAL_DATA |
| FEP `/v4/research/forward?view=fep` | 范围为 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`；Champion 为 NONE；生产未授权，未训练预测槽保持 Pending。 | FAIL_CLOSED / PARTIAL |
| 市场与事件 `/v4/research/market` | 上涨 2,344、下跌 2,712、平盘 155、未知 13；分母 5,224、实际行情 5,213、成交额 14,378.36 亿元；涨停 56、跌停 12、停牌 11、未知 1。事件展示 33 项；官方/媒体事实源和分钟炸板序列未绑定。 | PARTIAL_DATA |
| 诊断健康 `/v4/research/diagnostics/health` | 股票 5,213、板块 378、Focus 469、Forward 117；未知字段数量按模块显示。 | PASS_UI / PARTIAL_DATA |
| 来源 `/v4/research/diagnostics/sources` | Release、T0、来源摘要、字段注册与 2 个明确 gap 可从证据抽屉读回；各域仍未正式发布。 | PASS_UI / PARTIAL_DATA |
| 日更作业 `/v4/research/diagnostics/jobs` | 只读候选快照；无 worker 回执，来源请求 0，明确 `PG_CANDIDATE_DOES_NOT_CONTAIN_DAILY_WORKER_RECEIPTS`。 | PARTIAL |
| 数据更新 `/v4/research/data-update` | 候选截至 2026-09-30、日历 `NO_ACCEPTED_MARKET_CALENDAR_HEAD`；所有写入按钮禁用。 | FAIL_CLOSED / PARTIAL |
| Replay `/v4/research/replay` | 严格 PIT 可用日期 0；缺少完整冻结/历史输入时返回受限状态。 | PARTIAL_DATA |
| Compare `/v4/research/compare` | 严格视图不可用；显式切到事后重建后返回股票 1.205%、市场 -0.136%，共同区间 2026-09-29 至 09-30，明确标注非 PIT。 | PASS_UI / PARTIAL_DATA |
| Forward 来源审计 `/v4/research/forward?view=source` 与 `/api/v4/candidates/cohort?limit=100&offset=0` | 2026-10-19 实浏览器/API 读取 2026-09-30 R7 历史工程事实；扇区规则全域 400（匹配 2），股票规则全域 5,224（匹配 121、未知 34）。证据抽屉标记 `READY`、`RETROSPECTIVE_RESEARCH`、`strict_t0_pit=false`、`R7_RESEARCH_ONLY`，固定 Schema `v4`，generation 3，source_run_id `8758c55d…ef89`。发布索引、日 Universe、聚合及 pipeline 四条 PG 事实的摘要与 API 返回值逐项一致。API cohort 117 条，`production_accepted=false`、`PIT_ELIGIBLE=false`。证据：`G:\codex_tmp\v4_28766_r7_source_audit_20261019.json`。 | PASS_AUDIT_READ / NOT_PIT |

完整的页面截图/AX 结果留在本轮浏览器会话；数据库目录和作业证据留在 G 盘临时目录。浏览器及 API 当前没有独立 `/events` 或 `/risk` 一级页面，相关事件/风险在 Market 与 Home/个股研究视图展示。

按路由、API、Release、T0、Schema、行数、状态和结果记录的精简浏览器矩阵：`G:\codex_tmp\v4_28766_function_matrix_20261019.json`。

## 代码续修与回归

- `workspace_schema()` / `create_schema()` / `connection()` 统一固定 `v4`；动态 Alias 和旧 Shadow 出口均在触库前关闭。
- 历史 Forward SourceIngress 读取改为验证 `forward_schema_migration_map_r1` 的精确路径、摘要、状态和目标摘要，再读固定 `v4.forward_facts`；不再按“最新”自动挑选候选绑定。
- Corrected/R43 Owner 的保护源与 Head 重核走 PG；歧义绑定 fail-closed。保留的三份 Owner 代码/测试修改已复核；13 项 Owner SourceIngress 定向测试通过。
- 日更状态 HTTP Handler 测试现注入候选适配器；DM-01 日更夹具和只读状态预检改为版本化表名及 `v4`，不再断言 `v4_jobs_*`。
- 定向回归：单 Schema/来源审计/Reader DSN 测试 24 项通过；日更服务、进度、Core 结果与 DM-01 PG 进度测试 41 项通过；候选 HTTP 模式 7 项通过；Owner PG-only 读取 13 项通过。
- 本轮在 G 盘测试临时根复跑单 Schema/Reader DSN/R7 来源审计/日更服务与 Core/DM-01 进度组 63 项通过；Owner PG-only 组通过仓库指定隔离插件、单独启用只读 `market_research` 后 13 项通过；候选 HTTP 组在暂停并恢复真实 28766 服务的隔离时段通过 7 项。该 HTTP 测试的 owner-schema fixture 已修为唯一 `v4` 并加入断言。另一次把固定端口测试与服务并跑的尝试已识别为端口占用，未计入通过项；期间没有启停 28765。
- 2026-10-19 真实浏览器的 Forward 来源审计页/API 再验通过；四条 R7 事实摘要均与 PG `v4.forward_r7_facts_r1` 一致。该项仅证明历史工程证据可读，未提升 PIT 或发布状态。
- 收尾时把 R1 ReadIndex 固定行插入占位符改为静态语句、把查询组合改为 Psycopg `Composed`，并把 Journal 的三种固定表读写改为静态语句；移除旧 Shadow dead writer 中硬编码的临时目录，数据库身份仍需配置且构造器在触库前 fail-closed。对应仓库暂存 Blob 准入检查通过（66 项）。附加尝试收集 `tests/test_v4_read_index_r1.py` 时，仓库隔离插件在测试体执行前要求 disposable PG cluster 并中止；未绕过该插件或创建额外数据库，因此该次不计为测试通过，数据库未被该次测试写入。
- 上述收尾修改后，`tests/test_v4_single_schema_guard_r7.py` 在 G 盘临时根重跑为 5/5 通过，覆盖固定 Schema、Alias 禁止、旧连接拒绝、Shadow 导出关闭及本地 staging 写路径。
- 已将本阶段提交 `bbebbb6bc62bf5d8f187dc59ee4ed6771d826a30` 推送到任务卡原分支 `codex/v4-workspace-cleanup`。按任务卡尝试更新 Issue #2 正文和 PR #3 讨论，GitHub 集成对两项写入均返回 HTTP 403 `Resource not accessible by integration`；未重试其他写入端点，分支提交/推送已成功。PR 仍为 Draft，不合入开发主分支。

## 尚未完成的门与下一阶段

1. 已复核完整 TDX 2026-10-08 ZIP：551,544,006 字节、SHA-256 与目录绑定一致、12,449 个 `.day` 文件、全 ZIP CRC 通过，抽样股票/指数记录有序且末日为 2026-10-08。原始下载收据确为 `TDX_PACKAGE_READY`，但关联既有下载适配器的 `knowledge_lineage=RECONSTRUCTED_CORRECTED`；冻结的目标日提取仅 5,557 行，明确标记由后续快照重建。10-09（5,559 行）和 10-12（5,561 行）提取也全部 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`。详见 `G:\codex_tmp\v4_tdx_archive_audit_20261019.json` 及原始包内 `capture_receipt.json`。包存在和官方 URL 不足以推翻既有谱系/接纳合同；不得自行授予其 PIT/Accepted 状态。需要已批准的 PIT 日线源与相应独立接纳回执。沿用已通过的四日期 Core Oracle，不回灌 1,678 项绑定。
2. 在满足合同的可用 PIT 输入下补齐 Accepted 市场日历（当前 Data Head 日历止于 2026-09-30，PG 日历事实/发布 Head 为空）、Owner/扇区前序 PIT 成分与状态、Focus 到期/结构事实、Forward 成熟结算、官方事件来源，再跑 DB-03/07/09/12 与对应 UI 验收。本次只读目录复核确认 `market_calendar_sessions`、`source_packages`、`source_package_facts`、Daily Core 发布表均为空；`V4_DAILY_SOURCE_ACCEPTANCE_AUTHORITY_REGISTRY_R1` 尚无当前批准版本，故不能用本轮操作自签接纳。
3. 对 28766 的全部模块逐项完成用户任务卡规定的 API、Release、T0、Schema、行数、状态和实际结果矩阵；复验失败重试、日更幂等、性能及 SourceIngress 恢复。缺失数据继续 fail-closed。
4. 完成 76 Schema 全量消费者最终盘点和清理凭证交叉核验；保留不可重建的历史证据，不因对象名含旧 Schema 而删除。
5. 仅在所有模块验收通过后进入 28765 正式切换和最终产品打包门。当前不切换 28765、不制作正式包。

**当前结论：** 全库 catalog 当前只含一个 V4 业务 Schema `v4`，消费者固定关系和版本迁移已有实证；但旧 Schema 逐项清理方式的持久执行证据仅覆盖 37/75，故 S3/DB-05 仍为 `PARTIAL`。同时候选读取与一部分功能页可用，全模块真实数据验收尚未完成，阶段状态维持 `PARTIAL_DATA_AND_MODULE_ACCEPTANCE_OPEN`。

## 2026-10-19 续行复核补记

本轮在未启动或重启任何服务、未改动生产端口的情况下，对开发 PG 与 `28766` 再作一次独立现场复核。仅用于补充当前执行证据，不提升尚未满足的模块/数据验收状态。

- PostgreSQL 只读 RR 会话确认 `market_research` / OID `646711` / `127.0.0.1:5432` / 用户 `postgres`，`transaction_read_only=on`。目录仅有业务 Schema `v4`；关系 232 个，总尺寸 27,752,103,936 字节；例程 57 个；非内部触发器 123 个；无 public V4 业务对象、无 `v4_*`、无 v4 到其他非系统业务 Schema 的目录依赖。数组类型随基础类型计数，故原报告的 86 个独立类型口径与目录原始类型行数不同。
- 迁移台账本次读回：Research `legacy_schema_migration_map` 169 行、Forward `forward_schema_migration_map_r1` 9,256 行、History 11 行、Owner 7 行、ReadIndex 16 行、Journal Registry 7 行。全部位于 `v4`。本次仅目录/计数查询，未执行数据库写入。
- `28766` 真实浏览器复核 `/v4/research/stocks?q=SH.600675&sort=id&offset=0`：异步加载完成后显示中华企业单条命中（收盘 2.520），第 1 页共 1 条。此前等待中的状态是尚未完成加载，不构成复现故障。
- `/v4/research/focus` 显示 469 条 Focus 清单与 117 条 Forward 样本；期限计划 585、已发布期限状态 5、成熟合格 0。界面保留结构谓词缺失、旧账未核对和成熟结算不足的状态。
- `/v4/research/market` 显示截至 2026-09-30 的盘后截面：上涨 2,344、下跌 2,712、平盘 155、未知 13，分母 5,224、行情 5,213、成交额 14,378.36 亿元；涨停 56、跌停 12、停牌 11、未知 1。页面不是实时数据，前序日/PIT 行业成分仍不完整。
- `/v4/research/diagnostics` 显示 RAW_DAILY 5,213 通过、TRADING_STATUS 5,224 通过、IDENTITY_UNIVERSE 5,224 通过、ADJUSTED_DAILY 5,213 降级通过。`/diagnostics/jobs` 明示 PG 候选快照不包含日更 worker 回执、来源请求为 0。`/diagnostics/sources` 的证据抽屉显示 T0 2026-09-30、`RECONSTRUCTED_CORRECTED`、`AS_RECORDED=false`/`PIT_ELIGIBLE=false`、各域 `released=false`。
- `/v4/research/data-update` 显示 `NO_ACCEPTED_MARKET_CALENDAR_HEAD`、后台任务未启动，检查数据源/立即补齐/自动更新/失败日重试/取消未发布部分均禁用。该行为与缺少接受日历及作业准入相符；日更验收仍未通过。

本次浏览器操作均为只读；本机端口核对仍为 PostgreSQL `5432` 与开发服务 `28766`，无生产 `28765` 监听。

本轮补充完成另外两项真实页面交互核验：

- `/v4/research/replay?as_of=2026-09-30` 显示该日期已绑定候选截面，但严格 PIT 可用日期为 0；说明无完整 first-available 证明，不展示未来状态/后续成员/结果。
- `/v4/research/compare` 先显示严格 T0 冻结回放不可用，再由页面控件明确切换至事后重建（非 PIT）。以中华企业 `SH.600675` 对比起点 Universe 市场等权，返回 1.205% 与 -0.136%，共同窗口 2026-09-29 至 09-30，并明确声明事后重建不代表 T0 当时已知。
- `/v4/research/forward?view=fep` 标注 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`，质量及当前覆盖不可得，未训练模型保持 `PENDING`；不构成生产模型或正式发布。

### 运行时 Schema 创建边界续修

发现兼容函数 `create_schema(pg, "v4")` 仍会在每次 Writer 初始化时发送 `CREATE SCHEMA IF NOT EXISTS v4`。虽然不会增加 Schema，SOT 规定 v4 只由受控 bootstrap migration 创建，因此已将该运行时边界收紧为只读 `to_regnamespace('v4')` 校验：仅允许已预置 v4，缺失即 `V4_CANONICAL_SCHEMA_NOT_PROVISIONED`，任何非 v4 名称仍在 SQL 前拒绝。该函数的所有常规 Forward/History/Journal/ReadIndex/Owner/Jobs/Research 调用因此不会再发出 CREATE SCHEMA。

- 单 Schema guard 定向验证从 5 项更新为 6 项，结果 `6 passed`；覆盖运行时已存在 v4 验证且无 DDL、缺失 v4 fail-closed、旧 Schema 拒绝、Alias/Shadow/Research staging 行为。
- 本机静态调用扫描确认剩余运行时 `CREATE SCHEMA` 字面量只在 `NativeShadowDatabase` 被构造器首行拒绝之后的不可达旧实现；Shadow export writers 同样在数据库访问前拒绝。历史版本 migration SQL 保持原样，运行时代码路径不执行这些旧 Schema 创建语句。

### 2026-10-19 继续复核：运行时护栏与最终目录

- 以 `WORKBENCH_PG_DSN` 建立 `REPEATABLE READ READ ONLY` 会话后调用 `create_schema(pg, 'v4')`，实际返回数据库 `market_research`、命名空间 `v4`、`transaction_read_only=on`；该路径只查询 `to_regnamespace`，未执行 DDL。
- 在 `G:\codex_tmp\test_temp\v4_single_schema_guard_r7_recheck` 复跑 `tests/test_v4_single_schema_guard_r7.py`：`6 passed`。
- 再次现场盘点的清理矩阵为初始 76 个非系统 Schema、已退役 75 个、最终仅 `v4`；最终 PG 目录没有 `v4_*` Schema、public 下没有 V4 业务对象，V4 到其他非系统业务 Schema 依赖为 0。矩阵逐项保存于 `G:\codex_tmp\v4_single_schema_retirement_matrix_20261019.json`。该只读复核没有发起 DROP；之前提交的 Research 32 项和 Forward 3 项 RESTRICT 清理结果分别保存在 `research_cleanup_applied_20261019.json` 与 `forward_remaining_cleanup_apply_r1.json`，本次逐条确认其结果为 `DROP_RESTRICT_SUCCESS`。其余已退役条目以其迁移台账证据与最终目录缺席状态复核。
- 固定 V4 命名空间中 `model_namespaces` 存在；当前 FEP 运行页仍为 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`。本次目录只读盘点未发现 v4 中的 FEP 领域表，因此不能把旧 FEP `fep`/`fep_e5_engineering` fixture 迁移代码算作统一 Schema 完成，也未通过旧 fixture 写入该模块。需在任务合同允许的数据来源及 FEP 固定表迁移方案下继续处理；现有界面保持只读、生产未授权、未训练槽 Pending。
- 对运行时代码和应用服务代码进行 `CREATE SCHEMA` / Schema 身份静态扫描：常规 Forward、History、Journal、ReadIndex、Owner、Jobs、Research 入口都经 `v4_native.connection/create_schema`，后者仅校验预置 `v4`。发现的旧 Shadow schema 构造器触库前抛错，Shadow 导出入口也 fail-closed；历史迁移 SQL、显式 Phase-0 bootstrap 及隔离测试/脚本未执行。
- 后续检查 FEP fixture 发现 `fep_e5.canonical_ledger.apply()` 可执行路径传入的旧 SQL migration；standalone `fep_e5/schema.sql` 也可创建旧 engineering Schema。已禁用旧 migration executor（缺少 v4 固定表迁移合同前直接 fail-closed），并在 standalone SQL 顶层拒绝 `market_research`；原 FEP migration rollback 测试不再克隆 PostgreSQL 数据库，改为验证 fail-closed。与单 Schema guard 合跑 9 项纯定向用例，`9 passed`，没有连接或写入 PG。这只停止非统一 FEP fixture 扩张，未迁移或虚构任何 FEP 领域表；现有 FEP 页面仍仅是历史工程证据，模块验收保持 PARTIAL。
- 2026-10-19 FEP 护栏提交后重新只读连接确认 DB `market_research` / `127.0.0.1:5432`、`transaction_read_only=on`，非系统 Schema 为 `public`,`v4`，`v4` 中 FEP 命名关系为 0。非历史迁移的应用源码 Schema-creation 静态扫描只剩：`NativeShadowDatabase` 构造器首行 fail-closed 后的不可达旧实现，以及当前数据库名受保护的 FEP fixture SQL；没有触碰 PG。

### Workspace 清点续记

- `G:\codex_tmp` 直接子目录实测：`v4_repository_governance_r3_20261016` 4,675,814,273 字节，含 WP3 recovery freeze、bundle、unreachable-object 与 owner-source/LFS 核验材料；`r7_active_baseline_20261015` 2,255,654,812 字节，当前仍有 5 个 tracked diff、独有 untracked source/data/docs/runtime 和长路径；`R20_R1_20261017` 833,189,333 字节；`v4_r6_tdx_20261016` 568,127,024 字节；`v4_historical_source_ingress` 276,321,223 字节；`test_temp` 473,341,452 字节。扫描时没有发现这些目标路径被其他进程使用，前述恢复证据/源码改动/行情及 SourceIngress 内容仍无法证明可以重建，均未删除。该实测不支持“已清理 2.67 GB”的旧汇报口径。
- 本轮新建的只读复核脚本和单测临时目录按 G 盘临时路径创建；结束后尝试删除确认为本轮生成的 3 个脚本及 `test_temp\v4_single_schema_guard_r7_recheck`，文件操作自动审核拒绝。随后新增的 `v4_fep_single_schema_ro_recheck.py` 仍留在 G 临时目录；未尝试其他删除/移动方式，也未修改保留目录。DB-11 仍为 PARTIAL，待允许的文件清理操作可执行且逐项证明可重建后续办。

### 原 266 基线与本轮 Delta

- `docs/upgrade/V4_R21_CALLSITE_MIGRATION_MATRIX_R1_20261017.json` 的历史 P1 基线、161,114 条引用边统计及 266 项正式待核计数保持原样；本轮不据新代码 diff 重算历史扫描口径，也不把“代码已改”折算为 PG、DEV 或 Accepted 通过。
- 以任务卡发布 HEAD `2d838f28342664e26cdd78c01d0a6638048da3e7` 为基线，当前开发分支 6 个提交的增量改动共覆盖固定 Schema 迁移、`v4_native` 运行时护栏、R2 Research Snapshot/Series/Journal、Forward/Focus/History/ReadIndex/Jobs/Owner/Publication/SourceIngress 消费者、BFF/股票图表/Replay/开发服务、Corrected/R43 Owner PG-only 精确来源读取及针对性测试。新增点名的 Owner Delta 为 `src/workbench_analysis/corrected_owner_replay.py`、`src/workbench_analysis/r43_owner_replay.py` 和 `tests/test_v4_r6_pg_only_owner_source_reads.py`；Forward/History/Jobs/ReadIndex 的 Schema Delta 由对应固定表迁移及消费者文件列在 `git diff 2d838f28342664e26cdd78c01d0a6638048da3e7..HEAD --name-only` 中。当前额外工作区修改没有计入这些已提交增量。
- 上述变动可证明指定路径已有单 Schema 代码实现及局部真实调用验收，不消除原 266 的历史源边界对账工作；在生产业务读全量盘点、PG 数据身份/Head 验收和 per-ID 对账完成前，266 仍保留为独立历史基线，新增 delta 继续按“代码 / 实际 PG / 28766 DEV / Accepted”分层追踪。
- R14 历史 1,678 项绑定继续处于暂停扩量状态；本轮未批量迁移，也未改写 append-only 历史绑定。仅已核验为活动依赖的确切 Forward/History/Owner/ReadIndex/Research 事实通过各自版本化迁移台账承载，不能把台账行数解释为 1,678 项整体验收。
- 按 R6 的原始绑定核验记录复审此前已导入的 50 项：它们来自 R14 Head 对 R8–R13 历史验收/运行证据的 path+SHA 绑定，原字节长度/SHA 与 PG 读回当时逐项一致；不属于 R20/R21 的 266 个现役业务调用点或 V4 当前业务源数据。归类为 `HISTORICAL_EVIDENCE_ONLY / R14_AUDIT_VALIDATOR_INPUT`，保留 Head 原件身份、PG append-only 记录与既有审计 receipt，不做删除或再复制；R14 validator 尚未全链通过，因此这 50 项也不宣称完成其历史验收。剩余 1,678 项维持停止线。

### 2026-10-19 FEP 旧读入口与隔离探针续修

- 复核发现历史 R4 `scripts/execute_r4_next_acceptance_r1.py::db_receipts()` 仍会连接 55547 隔离 PostgreSQL 并执行 `DROP SCHEMA fep CASCADE`。该入口现于任何连接前直接 fail-closed；不再保留该数据库探针。
- `tests/fep_e5/test_canonical_authority_read.py` 旧隔离 SQL 测试改为只读来源发现测试。`CanonicalExpectancyReadAPI` 与 FEP canonical identity availability reader 均不再查询旧 `fep.*`，在 `v4` 固定 FEP 表迁移合同缺失时返回/记录 `V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED`，且不进行 PG 读取或写入。对应身份负例测试改为纯内存输入核验。
- 追加盘点后，E1 dataset writer/migration、FEP metadata register、trusted-authority candidate reader 与 canonical ledger 的数据库读写入口也全部先行拒绝，或在 inventory 中返回未就绪；均不会接触旧 `fep.*`。真实数据库继续只读确认 `market_research` / 5432，业务 Schema 仅 `public`,`v4`，v4 FEP 命名关系 0；28766 PID 17632 仍在监听，28765 无监听。
- 全仓 `src/workbench_service`、`src/workbench_analysis`、`src/workbench_db` 的 Python 数据访问静态扫描，已无 `fep.*` SQL 引用；standalone FEP SQL fixture 现在对任意数据库在首个 `CREATE SCHEMA` 之前直接报迁移缺失。数据库保护测试在仅禁止 `execute()` 的假连接下覆盖上述 E1/E5 writer、migration、authority 与 inventory 边界。
- 额外收集旧 `tests/fep` 与 standalone E5 PostgreSQL 回归时，FEP fixture 已在建连前跳过；结果为 43 passed、13 failed、268 skipped。13 项未计验收：其中历史 FeatureOwner/Pipeline 用例的直接开发库读取被仓库隔离插件拒绝；其余主要期望旧的合成 FEP Owner 状态或旧迁移清单。未创建/连接隔离 PG、未写入共享 PG。单 Schema 与 fail-closed 定向验收独立结果仍为 16 passed。
- 28766 真实浏览器复看 `/v4/research/forward?view=fep`：范围仍为 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`，质量及当前观察覆盖不可得，未训练预测槽为 `PENDING`；没有声明生产模型验收。
- 扩展入口封闭后的定向回归与单 Schema guard 最新结果 `16 passed`；仓库暂存 Blob 准入检查通过。隔离探针修复提交 `7fbd6606f`、首次读入口修复 `8bf9bc519` 和其余历史适配器封闭 `60e082bd8` 已推送至 `codex/v4-workspace-cleanup`。没有连接 55547、没有新增数据库/Schema、没有改动 PG 事实。FEP 固定表迁移与缺失业务源仍未完成，整体阶段仍为 `PARTIAL_DATA_AND_MODULE_ACCEPTANCE_OPEN`。

### 2026-10-19 28766 受控重载后的真实浏览器续验

按任务卡在本机开发槽位 `127.0.0.1:28766` 完成受控重载后，使用浏览器逐页等待异步渲染，并对 API 做串行现场抽查。快速连续导航时的短暂骨架态/客户端取消曾在服务日志留下 `ConnectionAbortedError`；等待页面请求完成后各页面正常渲染，不能将该瞬时态记为页面验收失败。未启动或触及 `28765`。

- API 现场抽查：`/api/v4/context`、`sectors`、`stocks`、`focus`、`market/breadth`、`sources`、`diagnostics`、`forward` 均为 `200 READY`；`forward/fep` 为 `200 SOURCE_INCOMPLETE`，与缺少当日模型 Owner 的预期一致。候选上下文身份仍为 DB `market_research` / OID `646711`，Schema `v4`，Release `05cf8913242f46c8af53b3d89f323b64`，T0 `2026-09-30`；各域 `released=false`，不是正式 Head。
- 真实内置浏览器：Home 读到股票 5,213、板块 378、Radar/Forward 117；Sector 列表读到 378 条并展示当期强度/宽度，前序成员缺口保留为“来源能力不足”；股票列表读到 5,213 条，交互搜索 `SH.600675` 后显示中华企业、收盘 2.520、共 1 条；Focus 读到 469 条，并在同页展示 Forward 117、期限计划 585、已发布期限状态 5、成熟合格 0；Market 页读到上涨 2,344、下跌 2,712、平盘 155、未知 13，分母 5,224、实际行情 5,213、成交额 14,378.36 亿元及涨跌停 56/12/11/1，并实际打开价格规则/来源抽屉；Diagnostics 显示 RAW_DAILY 5,213、TRADING_STATUS 5,224、IDENTITY_UNIVERSE 5,224 通过，ADJUSTED_DAILY 5,213 降级通过。
- 日更页 `/v4/research/data-update` 显示快照截至 `2026-09-30`、`NO_ACCEPTED_MARKET_CALENDAR_HEAD`、worker 未启动；检查来源、立即补齐、自动更新、失败重试、取消均禁用。页面正确保持开发只读预览。
- FEP 仍只显示 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`，未训练槽 `PENDING`，质量/当前覆盖不可得。Home、Sector、股票搜索、Focus、Market、Diagnostics、Forward/FEP 与日更页的候选读取现均由受控重载后的 28766 实际服务提供；不把可读、候选或降级状态提升为 PIT、Accepted 或产品 PASS。
- 本次只读 API/浏览器核验未写入业务数据或改变 Schema。正式数据缺口仍包括合格 PIT 日线与独立接纳回执、覆盖目标日期的 Accepted 日历/发布 Head、前序 PIT 成分与 Owner、Focus 到期与结构事实、Forward 成熟结算、官方事件源；DB-08/10、模块完整验收及 DB-11 工作区物理清理依旧未关闭。

### 2026-10-19 单 Schema Owner 发布绑定触发器续修

- 消费者审查发现 `v4.publication_module_results` 的 R4 触发器仍以 `to_regclass(owner_schema.owner_relation)` 验证实体表；在单 Schema 迁移并清理旧哈希 Schema 后，合法的 Owner 来源绑定会因旧物理 Schema 不存在而被拒绝。`owner_schema` 实际是来源谱系标识，读侧用 `(family, source_schema, token, T0)` 精确查询 `v4.owner_schema_migration_map_r1`，数据实体固定读取 `v4` 中版本化 Owner 表。
- 新增并注册 migration 065/066，触发器现在校验来源 Schema 哈希格式、精确且 `VERIFIED` 的迁移回执、回执 digest/contract/row_count，以及相应 `v4` Owner 版本的 T0、digest、contract、计数、sealed 与数据库身份。旧 Schema 不会被重建；没有新增别名，也没有批量迁移历史绑定。开发库 `v4.schema_migrations` 已读回 065 与 066，触发器定义包含凭证校验；目录确认旧哈希 Schema 为 0，绑定表目前 0 行，因此尚无可用真实 publication 进行端到端绑定写入验收。
- 065/066 的源文件 SHA-256 均与开发库台账一致。057 的已记录校验和 `509e66d6…` 与仓库 SQL 当前散列 `4c473184…` 不同；为不改写既有台账，在迁移入口加入仅针对该精确历史校验和的兼容分支，并要求 `v4.schema_migrations` 四列类型/空值属性及 `PRIMARY KEY(version)` 精确匹配且 `v4_meta` 已不存在，否则仍以校验和冲突失败。随后常规 `apply_v4_phase0_schema.py --apply` 成功遍历注册迁移集，结果 `ALREADY_CURRENT`，057 状态为 `ALREADY_APPLIED_COMPATIBILITY_VERIFIED`，其余版本包含 065/066 均为 `ALREADY_APPLIED`；数据库台账没有被重写。
- 定向 Owner writer 回归 `1 passed`。初次关联旧测试集因 fake PG fixture 与旧静态断言未跟上固定表/共享只读事务契约，68 项结果为 29 passed、39 failed；随后更新 fixture 响应、物理关系断言，并将权限测试对齐 SOT 的共享连接显式只读事务要求，再运行 Owner/Publication/Schema 兼容回归，结果 `69 passed`，另覆盖只读事务关闭时 fail-closed。该结果是代码契约回归，不替代真实 publication 的端到端绑定写入。
- 阶段仍为 `PARTIAL_DATA_AND_MODULE_ACCEPTANCE_OPEN`；尚需真实 publication 端到端 Owner 绑定、迁移总入口校验和余下模块/输入门验收。

### 2026-10-19 再次真实浏览器复核

当前内置浏览器实际访问本机 `28766` 并等待异步数据渲染完成：Focus 路由返回 469 条；Forward 路由返回 117 条样本、首次冻结未知、期限计划 585、已发布期限状态 5（覆盖 1 个样本）、成熟合格 0；FEP 路由显示 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`、质量/当前观察覆盖不可得、未训练槽 `PENDING`。Market 路由显示历史截面截至 2026-09-30（上涨 2,344、下跌 2,712、平盘 155、未知 13、分母 5,224、行情 5,213、成交额 14,378.36 亿元），并明确非实时行情。日更路由显示 `NO_ACCEPTED_MARKET_CALENDAR_HEAD`，worker 未启动，源检查/补齐/自动更新/重试/取消按钮均禁用。以上是实际 UI 与当前降级/未知状态核验，不是模块通过；页面未执行任何写操作。

### 2026-10-19 Owner 固定表消费者真实读回纠正

- 首次用真实 `REPEATABLE READ READ ONLY` 会话逐项走 Owner 消费者，发现 `owner_schema_migration_map_r1.T0` 与固定 Owner 表 `T0` 是 `text`，绑定中的日期是 PG `date`；回执查询和版本查询均因此产生 `text = date`。已在消费者端严格规范化为 ISO `YYYY-MM-DD`，拒绝 `datetime` 和非规范日期字符串。该修复不改数据、不改迁移回执、不创建 Schema。
- 再次通过三个真实 Owner 读取器逐项读取 7 份迁移凭证并校验 payload/聚合 digest 和行数：operational_risk 3 份（各 3 行）、research_priority 3 份（5,625 / 5,625 / 5,626 行）、sector_lifecycle 1 份（400 行）。7/7 状态 `FIXED_V4_READBACK_VERIFIED`；同一事务 `transaction_read_only=on`，数据库 `market_research` / OID `646711` / `127.0.0.1:5432`。这验证了已迁移 Owner 数据的固定表真实读取路径；因为 `publication_module_results` 仍为 0 行，不能代替完整 accepted Publication 绑定链验收。
- 更新 Owner 测试夹具以覆盖迁移回执和日期文本对齐、固定 `v4` 表关系及显式只读事务；Owner 专项 `8 passed`。代码修改后仅重载了开发端口 `28766`（新 PID 30824），浏览器重新读取 Home 成功；`28765` 未启动。

### 2026-10-19 比较与市场来源抽屉续验

- 真实浏览器重新打开 `/v4/research/compare`：默认视图是“严格 T0 冻结回放”，绑定截面日期 `2026-09-30`，严格 PIT 可用日期 `0`；页面要求明确选择对象、日期及资料视图后才加载结果。此状态符合数据缺口合同，不构成严格 PIT 验收通过。
- 真实浏览器重新打开 `/v4/research/market`：页面显示历史截面截至 `2026-09-30`，上涨 2,344、下跌 2,712、平盘 155、不可判定 13，分母 5,224、实际行情 5,213、成交额 14,378.36 亿元；涨跌停/停牌/不可判定为 56/12/11/1。手动打开“价格规则、ST/新股与来源”抽屉后，真实 API 回执中的候选上下文为 `market_research` / OID `646711`、Schema `v4`、Release `05cf8913242f46c8af53b3d89f323b64`、T0 `2026-09-30`；域 `released=false`。规则样本明确为 `RECONSTRUCTED_CORRECTED`、`AS_RECORDED=false`、`first_available_at_target_proven=false`，故规则输出可作候选诊断，不得作为 PIT/Accepted 证明。
- 上述交互只读取 28766，无数据库写入。当前本轮复核没有执行生产端口切换。任务卡列出的 `r43_owner_replay.py`、`corrected_owner_replay.py` 与 `test_v4_r6_pg_only_owner_source_reads.py` 在本地无未提交 diff，已存在于已推送提交历史中；其 PG 精确来源校验路径须继续按固定 `v4` 读表审查，不得恢复旧物理 Schema 定位。

### 2026-10-19 大表有界读取复核

- `REPEATABLE READ READ ONLY` 当前目录查询测得 `v4.forward_facts` 总量 6,218,366,976 B（main 3,268,608 B、index 3,235,840 B；目录估算约 9,052 行）；`v4.forward_r7_facts_r1` 2,182,561,792 B（估算 312 行）；`v4.forward_legacy_evidence_r1` 8,394,104,832 B；`v4.read_items_r1` 4,230,397,952 B；`v4.read_items_r2` 1,951,940,608 B。估算行数只用于容量/计划判断，不代替精确逻辑数据账。
- 两个 Forward 固定表的精确 `(namespace, kind, fact_key)` 读取计划均命中索引：R1 `forward_facts_pkey` 直接按三键扫描；R7 使用 `forward_r7_facts_namespace_kind_ordinal_r1` 锁定 namespace/kind 后过滤 fact_key。未对大表做无界内容扫描或复制。逻辑版本映射与完整性以迁移映射和逐来源收据为准；历史 1,678 项绑定仍未批量导入。
- 本轮实际 gate 目录计数仍为市场日历会话、Publication/Publication Head、Operational Research Head、Publication Owner 绑定、Daily Core snapshot/rows 均 0；DM-01 仅 1 条 `AS_RECORDED=false` 且 production/focus/shadow 权限关闭的候选 Head。以上说明模块验收仍处于数据阻塞，不能将单 Schema 目录通过外推为业务通过。

### 2026-10-19 单 Schema 运行期边界回归

- 对 `tests/test_v4_single_schema_guard_r7.py` 与 `tests/fep_e5/test_single_schema_fail_closed.py` 执行定向回归，结果 `12 passed`。运行期 `workspace_schema()` 和 Owner/ReadIndex 版本定位器均固定返回 `v4`；`connection()` 拒绝其它 schema；`create_schema()` 只核验已存在的 `v4`，不会隐式建库。
- 现役 Shadow 旧 writer 在建立 PG 连接前 fail-closed；FEP E5 旧 `schema.sql` 先抛出固定存储迁移错误，后续旧 DDL 不会执行。代码库中仍能静态搜索到这些不可达的历史 DDL 文本；没有任何运行路径可执行它们。Risk Owner 的陈旧注释已改为明确说明物理 locator 固定为 `v4`、版本身份来自 `token/T0/digest`。
- 回归期间没有写业务 PG、创建 Schema、签发 Head 或触碰 28765。S1 的运行期防扩散边界继续为 `PASS`；S3 清理执行证据、Accepted 来源/日历、成熟结算、完整日更及其他模块门仍按当前矩阵保持 `PARTIAL`。

### 2026-10-19 迁移器 Schema 创建范围收紧

- 将 `apply_v4_phase0_schema.py` 的历史兼容收敛到唯一 foundation 文件 `001_v4_phase0_foundation.sql`：执行时只把其既有 `v4_meta.schema_migrations` ledger 重写到 `v4.schema_migrations`，保持原 SQL 文件与迁移 SHA 不变。后续任何已登记迁移若包含 `CREATE SCHEMA`（包括 `CREATE SCHEMA v4`）或引用退役 `v4_meta` 均 fail-closed。
- 定向回归 `tests/test_v4_r7_sql_schema_compatibility.py` 与 `tests/test_v4_single_schema_guard_r7.py`：`10 passed`；`git diff --check` 通过。未执行迁移 DDL，未写业务 PG。

### 2026-10-19 本轮 28766 最新代码加载状态

- 真实进程核查：28766 当前 PID `27332`，启动时间 06:21；晚于其启动的提交包括 `12f870237`、`9c4628d3a`、`e20547f56`。28765 当前未监听。
- 受控重载 28766 的进程停止调用被执行策略拒绝，进程未停止/重启；未尝试其它终止通道。内置浏览器仍可读当前候选股票页，日线 253 根、周线切换后 54 根，再恢复日线 253 根，均显示候选 T0 `2026-09-30`、候选 Release `05cf8913242f46c8af53b3d89f323b64`。此交互仅证明当前运行进程行为，不代表最新提交已加载或最新代码通过浏览器验收。`DB-07` 因此改为 `PARTIAL`，待安全可执行的 28766 最新代码重载后续验。

### 2026-10-19 Owner Publication 单 Schema 约束闭环

- 代码与目录审计定位到 `publication_module_results.owner_schema` 的历史 CHECK 仍只接受 `v4_<hash>`，与 067 的 canonical `v4` trigger 分支及固定表读写器冲突。新增版本迁移 `V4_PUBLICATION_OWNER_CANONICAL_SCHEMA_R1`，不修改历史 038/065–067 原文；候选构建、写入器、Reader 现均只接受 `owner_schema='v4'`，旧 locator 不再进入新 Publication binding。
- 通过正式迁移执行器在授权开发库实际应用 071，RR/RO 读回 CHECK 为 `owner_schema='v4'`，版本 ledger SHA `b21ae28a…d0c1d4db`，Publication module rows 仍为 0；Schema 清单仍仅 `v4`。这修复了 Owner binding 的必要条件，但无已接受 Publication/Head，尚无真实端到端绑定可验证，因此 `DB-10` 和 `DB-07` 继续 PARTIAL。
- `tests/test_v4_pg_publication_candidate.py`、`tests/test_v4_r7_sql_schema_compatibility.py`、`tests/test_v4_single_schema_guard_r7.py` 定向回归 `67 passed`；4 个修改 Python 文件 `py_compile` 通过。没有创建合成 Publication/Owner/Head 行，没有改变交易日历或来源准入状态。

### 2026-10-19 Forward R7 读事务边界续修

- 静态追踪发现 `ForwardR7Store` 的 R7 表存在性探测、storage verification 与独立 `_latest_publish_index()` 读路径使用裸连接执行 SELECT，未通过统一只读事务边界。现改为固定 `v4` 的 `connection(..., read_only=True)`，独立发布索引查询显式 `REPEATABLE READ READ ONLY`；写路径保持显式写连接不变。
- `tests/test_forward_r7_task.py` 与 `tests/test_v4_candidate_r7_source_audit_route.py` 定向回归 `11 passed`。随后用真实项目连接只读调用 `ForwardR7Store.verify_existing_storage()` 与 `read_counts()`，读回固定关系 `v4.forward_r7_facts_r1`、历史样本 39,366、匹配 924/不匹配 37,812/未知 630，最新历史 T0 `2026-10-13`、generation 7。该 R7 历史研究发布与 UI 的 `2026-09-30` 候选不是同一 T0，未将其替代为该候选的来源；`live` 与 `late` 仍为空。
- 本次数据库读回显式只读，无 PG 写入、Schema/Head 变化或 28765 操作。后续仍需独立签发的同 T0 来源/Owner 才能解除业务状态门。
- 相关窄范围检查 `tests/test_v4_history_locator_contract_r1.py` + `tests/test_v4_single_schema_guard_r7.py` 为 `7 passed`，四个本轮改动 Python 文件 `py_compile` 通过。PG 写入相关 pytest 因隔离钩子明确拒绝把开发库作为 disposable test DB 而未通过，其中包括 `DISPOSABLE_PG_CLUSTER_REQUIRED`；部分 Daily fixture 另因未配置 `TDX_ROOT` 报错。该运行记录为 `TEST_INFRA_BLOCKED`，不计入模块 PASS，也没有调整或绕过隔离钩子。

### 2026-10-19 现场目录与服务槽复核

- 再次从项目 Reader DSN 建立显式 `REPEATABLE READ READ ONLY` 事务，实查 `market_research` OID `646711`、`127.0.0.1:5432`，`transaction_read_only=on`；V4 目录仅 `v4`（123 表、5 序列、85 例程），无 `v4_*`，跨 V4 Schema 依赖 0。端口实查为开发服务 `28766` 正在监听，生产端口 `28765` 未监听。
- 本次复核只读，无数据库写入、服务重启、Head/Publication 改动或 28765 操作；此结果确认 DB-01 的当前目录事实，不补足 DB-05 缺少的历史逐项 DROP 执行方式收据，也不改变其 `PARTIAL` 状态。
- 同一 RR/RO 会话复查 `market_calendar_sessions`、`source_packages`、`source_package_facts`、`publications`、`publication_heads`、`operational_research_heads`、`publication_module_results` 均为 0 行。`config/v4_daily_source_acceptance_authorities_r1.json` 仍为 `BLOCKED_NO_INDEPENDENT_ISSUER_APPROVED` 且 `issuers={}`；来源验收与日更/Accepted Head 缺口仍无法由本机工程候选代签。

### 2026-10-19 FEP 与 Jobs 浏览器续验

- 真实 28766 浏览器打开 `/v4/research/forward?view=fep`：页面明确 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`，质量与当前观察覆盖不可得，未训练预测槽为 `PENDING`。
- 真实 28766 浏览器打开 `/v4/research/diagnostics/jobs`：候选 T0 `2026-09-30`，页面明确 worker 未启动、快照不含作业回执；来源请求 `0`，状态 `PG_CANDIDATE_DOES_NOT_CONTAIN_DAILY_WORKER_RECEIPTS`。未点击写入/启动操作；这些结果验证当前正确 fail-closed 行为，不构成 FEP 或日更模块验收通过。

### 2026-10-19 个股详情周期切换续验

- 真实浏览器打开候选个股三一重能 `/v4/research/stocks/SEC-00096141BD5420F5CB3120E687CDA5B9`。详情实际显示截至 `2026-09-30` 的日线 `120/253` 根、周线 `54/54` 根、月线 `13/13` 根；逐项操作“行情周期”控件后，状态/蜡烛图容器均完成重新加载。页面同时显示按目标日坐标的前复权口径、成交量单位为股、成交额单位为元。
- 同页接受状态、算法支持板块、资格判断、健康度、市场相对强度、相对板块等 Owner/历史事实不足字段保持“来源能力不足”；不把可显示图表或候选数值作为 Accepted/PIT 功能通过。本次只读，不改变 PG/Head。
- 真实浏览器进一步打开板块详情 `/v4/research/sectors/INDUSTRY:T0706`：电气设备成员 322 条，成员关系就绪标为“是”；实际检索 `SH.688349` 后为三一重能唯一命中（共 1 条）。因子/轮动历史注明最早有效日为 `2026-09-30`，5/10/20 日历史缺少 prior PIT 成分，未用当前成员回填；轮动/前序状态仍按来源不足显示。

### 2026-10-19 迁移只读预检

- 已用 `scripts/v4_migration_readonly_preflight_r1.py --out-dir G:\codex_tmp\v4_r21r7_preflight_20261019` 实际运行只读预检；结果 `READ_ONLY_PREFLIGHT_ONLY_NO_DDL_DML_NO_HEAD`，记录 67 个迁移 SQL 与重复序号 `010`，未执行 SQL migration、DDL/DML 或 Head 更新。证据 JSON 留在 G 临时目录。
- 预检通过配置连接检查后识别当前会话角色为 PostgreSQL `postgres` 超级用户，故 Reader least-privilege 项为 `BLOCKED_PRIVILEGED_READER`，自动 apply decision 保持阻止。此项只表示角色未达到该只读预检器的受限 Reader 契约，不否认前述由显式 `READ ONLY` RR 事务完成的目录/数据读取；也不授权把普通开发 DDL 与正式迁移角色混为一谈。
- 本轮当前工作树修改的 Python 文件完成 `py_compile`；`tests/test_v4_single_schema_guard_r7.py` 在临时目录 `G:\codex_tmp\test_temp\r21r7-single-schema-20261019` 定向重跑为 `6 passed`，`git diff --check` 通过。结果只证明固定 Schema 创建边界，不替代模块数据门。
- Focus 的“实际路径与到期结果”控件实际展开首批 30 个对象；进一步对中华企业打开“各锚点到期结果”，只读抽屉返回截至 `2026-09-30` 的 1 条修正历史重建记录，路径完整度、确认事实、锚点变化、最大向上偏离、当前回撤均无可确认值（`—`），同时明确结构证据缺失时保留不可判定。Forward 同页显示 117 样本、585 期限计划、已发布 5 项（覆盖 1/117）、成熟合格 0、待到期表 5 条；未发布/未成熟不转成零收益或质量结论。
- 对待提交的一次性 Schema 数据迁移/RESTRICT 清理脚本及历史验收脚本运行 staged-blob 策略时，策略拒绝了动态标识符 SQL、机器绝对路径和过程文件读取项。脚本与用户原有工作区修改均留在原位置、未修改策略或另找通道提交；本续行只提交通过准入检查的正式报告、只读预检器和 DB-01 SQL 检查更新。

### 2026-10-19 新续行数据库 gate 复核

- 再次使用项目 `v4_native.connection('v4', read_only=True)` 读回 `market_research` / `127.0.0.1:5432`，事务级 `transaction_read_only=on`。`market_calendar_sessions=0`、`publications=0`、`publication_heads=0`、`operational_research_heads=0`、`publication_module_results=0`、`daily_core_result_snapshots=0`、`daily_core_result_rows=0`；`dm01_data_accepted_heads=1` 但仍是 `AS_RECORDED=false` 且 focus/shadow/production 权限关闭的候选，不能作为 Accepted Head。
- Owner 固定表实际读回优先级 3 个密封版本（最近 T0 `2026-10-15`）、风险 3 个（最近 `2026-10-15`）、扇区生命周期 1 个（`2026-10-13`）；旧 Owner 数据可读不等于当日完整 Accepted Publication/Owner 链，Publication module binding 仍为 0。查询未写库。

### 2026-10-19 Research Series/Journal 双版本隔离现场核验

- 对固定表 Series 与 Journal 各构造两份独立 release（共 4 份），用 R2 Builder seal 后通过 `load_release(verify_content=True)` 和 release-scoped Reader 逐项读回。每个 release 只返回其自身唯一 marker，Series 固定表为 `v4.research_series_bars`，Journal 固定表为 `v4.research_journal_days`；没有版本串读。
- 四个样例均在开发 PG 事务内完成并回滚。回滚后临时 `research_releases` 行数为 0；事务前后 `v4`/`v4_*` Schema 集合均只有 `v4`，固定表目录清单不变。该核验没有新建业务 Schema、版本专属表或持久化合成业务行。与前述 Snapshot A/B 双版本回滚读回合并，补足 S1 两版本固定存储现场证据；此结果不替代历史 Series RAW/QFQ 聚合、行情来源或 Accepted 门验收。
- 后续在同一开发库再次以 `v4_snapshot_pg_r2.read()` 真实消费者入口读回这四个 Series/Journal release；每个 descriptor 先通过全内容 manifest 验证，reader 按 `release_id` 只读到对应日期行。将 descriptor 的 T0 改为不匹配值后，Reader 返回 `PG_SNAPSHOT_R3_DESCRIPTOR_MISMATCH`；不存在的 release 返回 `PG_CANDIDATE_RELEASE_NOT_UNIQUE`。该轮使用的四个 UUID 事务内写入后显式回滚，独立只读事务按四个精确 ID 查询持久化数为 0。该补充只增强固定表版本隔离与 fail-closed 消费者证据，不补足真实 RAW/QFQ 历史聚合或数据接纳来源。
- 只读容量复查进一步确认主要对象体量来自 TOAST：`v4.forward_facts` 总量 `6,218,366,976 B`（估算 9,052 行，TOAST `6,211,829,760 B`），`v4.forward_legacy_evidence_r1` `8,394,104,832 B`，`v4.forward_r7_facts_r1` `2,182,561,792 B`。没有因此扫描或复制大对象；估算行数不等价于精确业务行数。

### 2026-10-19 28766 诊断页真实交互续验

- 内置浏览器实际展开 `/v4/research/diagnostics/health` 的“上游与影响字段”：候选 T0 `2026-09-30`，股票 5,213、板块 378、Focus 469、Forward 117、Market 1；股票质量面板明确记录 `acceptance_state`、结构锚点、行业上下文等字段未知，不以零值代替缺失来源。`/diagnostics/sources` 与 `/diagnostics/contracts` 的诊断抽屉实际打开并返回 `READY` 源登记，身份均为候选快照 Release `05cf8913242f46c8af53b3d89f323b64`、数据库 `market_research` / OID `646711` / `v4`，域 `released=false`。
- `/v4/research/diagnostics/jobs` 展示现有 PG 快照的逐域记录计数，并明示未启动日更 worker、快照没有作业回执；展开“查看快照缺口与日更状态”返回 `SOURCE_INCOMPLETE`、worker `false`、来源请求 `0`、缺少 worker receipts。三页浏览器操作均为只读，不签发或伪造 Accepted Head/日更回执；日更/模块完整验收仍未通过。

### 2026-10-19 History 旧 locator 经固定表读回续修

- 代码审查发现 `CoreProductBFFR1.chart_history_pack` 只接受 `schema='v4'`，会在调用支持迁移映射的 History Reader 前拒绝冻结的旧 History locator。调整为只接受 `v4` 或合同格式 `v4_history_<16位十六进制>`；后者仍必须由 `v4_history_pg_r1.read` 在 `v4.history_migration_map_r1` 中精确匹配，实际条目、版本与条数校验仍在 `v4` 固定表执行，不连接旧 Schema，也不使用工作区路径定位。
- 在真实开发库以显式只读 RR 连接读取一条已迁移映射：旧 locator `v4_history_64d0f9c30983a3ac` → canonical version `51cbf9a29c866f9b7afa07e07fa8fd567af4059c617ce61e20a83bdac8c0f6b6`，T0 `2026-10-15`，证券 `SEC-00096141BD5420F5CB3120E687CDA5B9`；实际 Reader 经映射从 `v4.history_bars_r1` 读回 420 根，日期 `2025-01-16` 至 `2026-10-15`。实证旧名称仅作为迁移 locator，物理读 Schema 为 `v4`。
- locator 纯函数定向用例 `1 passed`，相关模块及用例 `py_compile` 通过。对旧集成测试文件的定向 pytest 因测试收集时模块导入触发仓库 disposable-PG 插件而在执行前被拒绝；没有绕过隔离、创建数据库或写 PG，该次不计通过。真实旧 locator 读回独立于此 pytest 收集结果完成。

### 2026-10-19 public History 遗留对象清理与目录终核

- 在同一 `market_research` 的 `REPEATABLE READ READ ONLY` 目录复核中发现，除 `v4` 外虽无任何 `v4_*` Schema，但 `public` 仍有旧 `history_versions_r1`、`history_bars_r1` 两表及 `reject_history_r1_mutation()` 函数。两表精确行数均为 0；四个触发器仅引用该函数；`history_bars_r1` 的唯一 FK 只关联这两张 public 表。源码消费者均经 `v4_native.connection('v4')` 限定 search_path，没有 public 定位入口。
- 将以上精确对象按 `DROP TABLE ... RESTRICT`（先 bars 后 versions）及 `DROP FUNCTION ... RESTRICT` 清理；未删除 `public` Schema、未用 CASCADE。DDL 事务提交后重新以只读 RR 核验：V4 业务 Schema 列表仅 `v4`，`v4_*` 为 0；public 用户关系为 0；对仍存在的 `v4_*` 对象做目录依赖计数为 0；固定 History 表仍在 `v4` 且保有 11 个版本、57,466 条证券历史 payload。
- 最终身份：DB `market_research` / OID `646711` / `127.0.0.1:5432`，用户 `postgres`，`transaction_read_only=on`，`REPEATABLE READ`。全量关系/Schema 目录输出 `G:\codex_tmp\v4_r21r7_catalog_recheck_20261019.json`；最终复核摘要仅报告此时仍在 `public` 的 V4 用户关系清单，不包含凭据。
- 本机 28766 受控重载后，真实浏览器重新读出个股详情 `SEC-00096141BD5420F5CB3120E687CDA5B9`：日线截至 `2026-09-30`，原生前复权 `120/253` 根；蜡烛图与详情字段均完成渲染。随后逐层追到实际路由 `ResearchBFF → stock_views.chart → v4_history_pg_r1.read`，API 返回历史版本 `ba5ac5f7…` 的 120 根分页；同一只读 RR 事务在 `v4.history_versions_r1` 查得该版 T0 `2026-09-30`、全量 1,309,832 根/5,224 个证券，`v4.history_bars_r1` 中本证券 253 根（首日 `2025-09-15`，末日 `2026-09-30`）。API 与页面均指向数据库 `market_research` / OID `646711` 和固定 Schema `v4`。该候选来源谱系为 `RECONSTRUCTED_CORRECTED`；不提升为 PIT/Accepted。页内接受状态、市场相对强度、相对板块等缺少 Owner 的字段继续显示来源不足。未操作 28765。
- 此清理关闭了 SOT R3 指出的 `public` V4 用户对象残留，不改变正式业务门状态；Source/PIT、Accepted 日历与 Head、当日完整 Owner/Publication、成熟 Focus/Forward 等模块验收缺口仍使最终产品验收保持未通过。

### 2026-10-19 R8 Forward 旧多 Schema 回归断言纠偏

- 全仓消费者扫描发现 `tests/test_r8_forward_namespace.py` 仍断言候选必须进入工作区专属的旧物理 Schema，并通过旧 alias/Head 候选枚举来选择存储；该回归与 R21-R7 固定 `v4` 合同相反。生产读取器当前只验证受限候选绑定并检查 `v4.forward_r7_facts_r1`，没有旧 Schema 搜索/建库。
- 将该旧回归改为固定关系验收：候选 locator 必须是 `v4`、绑定 root 必须精确匹配、目标固定表缺失则 fail-closed；所有场景均通过注入 PG 连接执行，不创建/改写 PG 对象。G 临时目录定向 pytest 为 `5 passed`；该次无共享数据库写入、无服务重载和无 Schema 变化。
- 这修复了会鼓励恢复多 Schema 的回归合同，不提升 Forward 的 PIT/Accepted 或成熟结算状态。

### 2026-10-19 其余 PG 消费者测试断言统一至固定 Schema

- 将 BaoStock runtime acceptance 测试夹具更新为固定 `v4` 连接，并按真实 `(workspace_namespace, kind, fact_key)` 查询参数验证固定表读取；操作执行器夹具使用 `v4` 身份，TDX 根路径仅用于只读源路径边界解析，不对源目录写入。
- 将 Daily Jobs 与 PG runtime consumer 测试中的旧 `v4_jobs_*` 断言改为 `v4`。三个受影响测试文件 `py_compile` 通过；BaoStock 纯夹具定向用例 `7 passed`。另外两个文件含共享开发库写入/HTTP 服务行为，本轮未运行其集成用例，需在遵守 28766 唯一服务槽位和数据库写入范围的前提下另行核验。
- 无 Schema/业务数据写入或服务重载；不影响模块数据门状态。

### 2026-10-19 开发库目录与 Workspace 现场复核

- 以 `market_research` / OID `646711` 的 `REPEATABLE READ READ ONLY` 事务重新核目录：连接用户 `postgres`，`127.0.0.1:5432`，事务 `read_only=on`；项目 Schema 结果仅 `v4`（owner `postgres`），未发现 `v4_*`、`fep`、`fep_e5_engineering`。`public` 项目关系数为 0；`v4` 表/视图关系为 86，所计关系对象占用 `27,752,079,360` 字节。Schema migration ledger 已读回 single-schema Research、History、Jobs、Forward R7、Journal Registry、ReadIndex、Owner 与 Publication Owner Guard 版本；没有 FEP single-schema 迁移记录。
- R21-R7 要求保留审查的三份 `r43_owner_replay.py`、`corrected_owner_replay.py`、`test_v4_r6_pg_only_owner_source_reads.py` 均无本地未提交 diff；历史已推送提交 `bbebbb6bc` 将相关消费者固定到 `v4`。这保留了精确 PG 来源读回，仍不等于其历史输入、Owner 或 PIT 已通过业务验收。
- Workspace 盘点：`G:\\codex_tmp\\r7_active_baseline_20261015` 有 3,646 个文件、2,255,654,812 字节（2.101 GiB），Git 有 5 个已修改跟踪文件及 `data/`、`docs/`、`runtime/`、`git/` 和多个新源码等未跟踪内容。没有其它进程命令行引用此路径；因此整体不是可确认的可重建临时物，完整保留，不删除其唯一修改、数据或证据。
- 此前只读检查的 9 个 `__pycache__` 目录是局部样本。2026-10-19 全仓精确盘点实际发现 143 个目录、2,165 个 `.pyc`，总计 28,981,840 字节；2,159 个存在同目录匹配 `.py` 源文件，另 6 个没有源文件，可能是唯一历史字节码，全部保留。按逐文件绝对路径删除 2,159 个可重建缓存的操作被执行工具策略拒绝，没有文件被删除，也没有尝试改用其它删除通道。DB-11 Workspace 物理清理保持 `PARTIAL`；不能把缓存清点计为已清理。
- 当前数据库目录通过单 Schema 计数，但此前定义的多表/索引空间统计口径与此处关系总占用口径不同；该数字不用于推导历史迁移前后数据库空间变化，也不表示全部 27.75 GB 都是基础表数据。
- FEP 相关遗留 SQL/合同仍列有独立 `fep`/`fep_e5_engineering` 命名，但现役总迁移入口仅执行显式登记集、已阻止非 `v4` Schema 创建，E5 `schema.sql` 在任何 DDL 前显式失败关闭；实库没有这些 Schema。FEP 当前仍是来源/Owner不足状态，需补固定 `v4` 存储迁移与完整模块验收，不能以目录中不存在旧 Schema 记作 FEP 通过。

### 2026-10-19 Forward Owner 只读夹具固定 Schema 纠偏

- `tests/test_v4_forward_pg_closeout.py` 中 PG-only Reader 的新绑定夹具原先仍写入任意 `v4_forward_test`，该值既非固定 `v4` locator，也不是符合格式且有迁移回执的历史定位符。已改为 `schema='v4'` 并绑定与测试 Workspace 对应的 `workspace_namespace`，同时保持 Reader 必须显式只读且使用 Reader DSN 的断言。
- 修改文件 `py_compile` 与 `git diff --check` 通过。该测试文件还含真实共享 PG 写入/immutability 集成用例，本次未启动其 pytest 收集/隔离数据库过程；因此只记录语法检查，不宣称定向集成通过。
- 没有写入开发数据库或启动 HTTP 服务。

### 2026-10-19 新 Owner 固定 v4 publication 绑定入口修复

- 复核 065/066 后发现它们虽校验 `v4` 固定 Owner 版本表，却无条件要求 `owner_schema` 是旧 `v4_<56hex>` 且存在旧 Schema 迁移回执。因此 canonical Owner Writer 写出的 `schema='v4'` 无法进入 publication binding，导致新数据虽然迁入固定表，新的 accepted publication Owner 仍会被拒绝。
- 新增 migration 067：`owner_schema='v4'` 时校验精确 Owner family、`owner_relation`、T0、token、contract、digest、row_count、sealed、database identity，直接读固定 Owner 版本表；冻结的历史 `v4_<56hex>` locator 继续要求匹配且 `VERIFIED` 的迁移回执。按合同对准 `market_research` 显式 apply；台账 readback SHA `69f7ac1e…` 与代码相同，实际 trigger 函数含 canonical 分支、relation guard 和历史回执分支；目录仍仅 1 个 V4 Schema。
- Workspace Owner mapping 校验现在接受 canonical `v4` locator，同时保留有界旧 locator 兼容。纯映射用例 `3 passed`，改动文件 `py_compile` / `git diff --check` 通过。
- `publication_module_results` 与 `publication_heads` 当前均 0 行，开发库尚无可绑定 publication。没有伪造 accepted publication 或 Owner 绑定做端到端验收；真实 accepted Head/来源门补齐后仍需运行一次全链路写读验证。

### 2026-10-19 067 变更后 28766 浏览器复载

- 在应用 067 Owner publication binding 修复后，按唯一开发服务约束停止并重启了 `127.0.0.1:28766`；首次启动因子进程缺少项目 `PYTHONPATH` 退出，补齐 `PYTHONPATH=G:\\codex work\\大A交易\\src` 后同一入口成功运行。28765 全程未启动或重启。
- 通过当前内置浏览器实际打开候选个股详情 `/v4/research/stocks/SEC-00096141BD5420F5CB3120E687CDA5B9`，页面完成实际 PostgreSQL 数据渲染：候选 T0 `2026-09-30`、候选而非正式 Head；日线实际成交图表 `120/253` 根；详情中收盘价、成交量、成交额、均线、波动等候选值可读，Owner/历史证据不足字段继续显示“来源能力不足”，并列出缺失的 followup/失效合同证据。页面可用不被计为 Accepted、PIT 或模块验收通过。
- 本次重载与浏览器复核没有产生 PG 写入、Schema 新建或生产切换；此项仅确认修复后的固定 Schema 开发版本能够通过真实页面读取现存候选数据。Publication/Publication Head 仍为空，端到端 Accepted Owner 写读继续待真实来源与 Head 门满足后执行。

### 2026-10-19 历史 Research locator 精确回执收紧

- 静态审查确认 `resolve_legacy_schema()` 没有现役调用者，但仍接受任意 `v4_research_` 前缀并只按 canonical version 去重。将其收紧为冻结的 `v4_research_<24位小写hex>` 形式，并要求该来源 Schema 的全部版本映射都带 `verification.status=VERIFIED` 后才返回唯一 canonical release；该函数只查询 `v4.legacy_schema_migration_map`，不连接或扫描历史物理 Schema。
- 新增纯读回夹具覆盖非法 locator 在触库前拒绝、混合/未验证映射拒绝、完整验证映射成功。定向用例 `3 passed`，相关文件 `py_compile` 与 `git diff --check` 通过；本补丁没有访问 PG 或改变候选数据。

### 2026-10-19 BaoStock 同日覆盖受限探测

- 按现存 BaoStock 合同的 bounded smoke gate 使用匿名固定版 `0.9.3`，对单只 `sh.600000` 请求 `2026-10-08` 日线；记录 UTC 时间 `2026-10-18T21:34:14Z`，实际端点 `public-api.baostock.com:10030`，登录/查询/退出均成功，返回目标日 1 行。请求预算 ledger 从当前仓库 ledger 读入后仅写 G 临时目录，原始 provider payload 未持久化、未写 PG。
- 收据位于 `G:\\codex_tmp\\v4_r21r7_baostock_20261008_smoke\\coverage_receipt.json`。`BAOSTOCK_DAILY_FINGERPRINT_V1.enabled=false` 且其状态仍为 `PUBLIC_ROUTE_B1_OPERATIONAL_FIELD_BINDING_PENDING`；这次单证券诊断不能证明全市场覆盖、数据字段容差/独立接纳、PIT、SourceIngress 或 Accepted 日更，不改变 DB-09/10 与模块数据门状态。

### 2026-10-19 FEP fixed-v4 storage migration and consumer cutover

- 按中央 migration runner 对 `market_research` 执行已登记的 `068_v4_fep_fixed_schema_storage_r1.sql`。事务已提交并读回 checksum；固定 `v4` 下新增 35 张 FEP 业务表和 27 个数据库函数，没有执行 `CREATE SCHEMA`、没有新增 alias，也没有使用 CASCADE。数据库目录复核为 `market_research` / `127.0.0.1:5432`，可见业务 Schema 仅 `v4`（另有 PostgreSQL 默认 `public`）；runner 的 `v4_table_count=121`。
- 对 migration 中 35 个表逐一目录核对：35/35 存在于 `v4`，34 张 append-only 表的 UPDATE/DELETE 防护触发器全覆盖，唯一可变头 `deployment_heads` 有 `controlled_head` 保护；从 migration 声明提取的 27 个函数全部在 `v4` 找到。以显式 `REPEATABLE READ READ ONLY` 事务读回所有 35 表计数，当前均为 0；没有旧 FEP 独立 Schema 或 FEP 业务行需要迁移，未合成候选或 Owner。
- FEP E1 repository、canonical identity、ledger fixture adapter、metadata binding、trusted authority 与 Expectancy API 的活动 SQL 均固定到 `v4`。旧不兼容 `fep_e5_engineering` payload-ledger 已替换为触库前失败的兼容壳；其旧 `schema.sql` 保留历史内容但在首条 DDL 前无条件抛出迁移错误。活动 FEP Python 路径不再包含物理 `fep` 或 `fep_e5_engineering` 定位。
- 真实 DB 的 FEP inventory 回报 35 表、34 受保护表，业务行仍为空；Canonical Expectancy 对不存在的 slot 返回 `NOT_READY`，MODEL_DISPLAY 与 PRIORITY_USE 仍不可授予。该结果证明固定存储已部署和缺少实际 Owner 时正确失败关闭，不证明 Focus/Forward/Market/FEP 的业务来源门、训练成熟度、Accepted Head 或产品功能验收已通过。
- 更新 FEP 单 Schema 定向夹具覆盖中央迁移注册、拒绝旧任意 SQL、拒绝 legacy payload-ledger Schema 触库、固定 v4 空库读路径及活动模块静态扫描。定向纯夹具及 Research locator 用例 `9 passed`；9 个相关 Python 文件 `py_compile` 成功。PostgreSQL 目录与业务读取复核独立完成，均使用只读事务；正式 28765 未触碰。

### 2026-10-19 Research 双 release 实库隔离读回

- 为验证 S1/DB-02，在 `market_research` 的两个独立事务中分别用真实 R1/R2 Builder 写入不同 release_id、T0 和仅含单个测试对象的 snapshot。两个 Builder 都只返回 `schema='v4'`；各自 `load_snapshot_release()` 与 `v4.research_objects WHERE release_id=...` 均读回各自完整身份与唯一对象，A/B 未串读。每个事务在断开前主动 rollback，随后使用只读连接核实两个测试 release 均未持久化、`v4_*` Schema 数仍为 0。该操作验证真实 PG 固定表和版本键隔离，不留下候选或历史假数据，也不构成全量行业数据与服务路由验收。

### 2026-10-19 FEP 部署后目录与 Forward 体积复查

- FEP 固定表迁移后的目录总表数为 121（迁移前 86 张固定表，加 FEP 35 张）；早先报告中的 86 是 FEP 迁移前快照，当前有效表数以本次迁移台账与目录读回为准。此前报告中 232 是关系类对象的不同统计口径，不能与表数混用。FEP 业务空表仍不等于 FEP 业务验收通过。
- 对三张主要 Forward 表只查询 `pg_class`、TOAST/索引关系尺寸和 `pg_stat_all_tables` 估算统计，没有扫描/复制 payload，也没有清理对象。当前目录尺寸为 `v4.forward_legacy_evidence_r1` 8,394,104,832 B（主关系 647,168 B、索引 1,409,024 B）、`v4.forward_facts` 6,218,366,976 B（主关系 3,268,608 B、索引 3,235,840 B）、`v4.forward_r7_facts_r1` 2,182,561,792 B（主关系 139,264 B、索引 180,224 B）。总尺寸包含 TOAST 与索引。目录统计估算分别为约 2,457、9,280、312 个 live tuples，不能当作精确业务行数；早先对 `forward_facts` 的总尺寸读数与本次不同，数据库统计/关系尺寸是各自观测时点的现场值，不据此推导 payload 变更或完整数据量。既有固定表主键和来源过滤索引仍在，无活动全表 payload 盘点。
- 28766 个股详情页在同一真实证券详情中逐项切换日/周/月 × QFQ/RAW 六种组合并等待异步渲染：日线均为 `120/253` 根、周线均为 `54/54` 根、月线均为 `13/13` 根，价格口径标签与选择一致，蜡烛图区域已渲染。页内月线 QFQ 与周线 QFQ 也由此前单独浏览器续验确认；本次恢复用户当前页至日线/QFQ。浏览器 error/warn 日志为空。浏览器/API 读取仍是候选研究数据，不能替代 PIT、Accepted Head、来源完整性或模块数据验收；28765 未触碰。

### GitHub 跟踪更新尝试

- 按任务卡“尽力更新现有 Issue #2/PR #3”的要求，先读取现有条目和最新评论，再分别尝试追加本轮准确进度。GitHub 集成对两次评论写入均返回 HTTP 403 `Resource not accessible by integration`，没有新增外部评论；没有重复重试或更换通道。分支提交已正常推送，Issue/PR 跟踪更新受该集成权限限制。

### 2026-10-19 28766 来源审计与日更安全门续验

- 当前 28766 Forward 来源审计页的真实浏览器抽屉返回 `V4_FORWARD_CANDIDATE_SOURCE_AUDIT_READ_R1@1.0.0` / `READY`，T0 `2026-09-30`，固定来源 Schema `v4`、namespace `R7_RESEARCH_ONLY`、generation 3、source_run_id `8758c55d…ef89`；同时明确 `evidence_class=RETROSPECTIVE_RESEARCH`、`strict_t0_pit=false`，因此仍非 PIT/正式候选接纳。
- 日更页真实显示开发快照 T0 `2026-09-30`、`NO_ACCEPTED_MARKET_CALENDAR_HEAD`、后台 worker 未启动；“检查数据源、立即补齐、自动更新设置、重试失败日、取消未发布部分”按钮均为 disabled，未执行触发操作。页面说明为只读 PG 状态预览，不创建日更任务或后台进程。
- 随后恢复浏览器到个股详情日线/QFQ `120/253`；本轮浏览器 error/warn 日志为空。28765 未触碰。

### 2026-10-19 Home 风险来源缺失提示续修

- 在真实 28766 `/v4/research/home` 页面发现风险 Owner 未绑定时，Home 将空 `risks` 列表误显示为“该已处理截面没有 owner 发出的风险变化”，把来源缺失混成无变化。修复 `static/research/app.js` 的空状态分支：有已绑定 risk Owner 才显示无风险变化；Owner 未绑定或来源不完整时显示缺失原因并明确“不能判定没有风险变化”。
- 直接重载 28766 浏览器页面并等待完整异步渲染，真实页面现显示 `DATED_OPERATIONAL_RISK_CHANGE_OWNER_NOT_PRESENT；不能判定没有风险变化`；候选 T0 `2026-09-30`、股票/板块计数和市场四轴仍按原候选快照渲染。此次只改开发前端静态代码并由 28766 在线资产读取，无 DB 写入、服务重启或 28765 操作。Risk 来源与业务验收仍为 `SOURCE_INCOMPLETE`。

### 2026-10-19 FEP 后最终 Schema 目录与 ACL 复核

- 在 `market_research` / OID `646711` / `127.0.0.1:5432` 以 `REPEATABLE READ READ ONLY` 事务重新查询最终目录。当前用户 `postgres`，事务 `read_only=on`；`v4`/`v4_*` 命名空间结果仅 `v4`。目录中固定表 121、索引 219、序列 5；视图/物化视图 0；例程 84、非内部触发器 182、用户定义类型 244（含 PostgreSQL 自动数组类型）。该组是 FEP 068 后的当前 `pg_class`/`pg_proc`/`pg_trigger` 口径，覆盖并更新此前 FEP 迁移前的 86 表及 232 关系类快照。
- `public` 用户关系 0，`v4` 到其他非系统业务 Schema 的目录依赖 0。`v4` ACL 精确列出的额外 FEP 角色为 `fep_application`、`fep_deployer`、`fep_adapter`、`fep_auditor`、`fep_cas_owner`、`fep_schema_owner`，均 `NOLOGIN` 且仅有 `USAGE`、没有 `CREATE`；当前唯一可登录的 `postgres` 同时有 `USAGE/CREATE`。未调整 ACL 或角色。

### 2026-10-19 Shadow 固定存储最新目录复核

- 当前 RR/RO 事务现场读回 `market_research` / OID `646711` / `127.0.0.1:5432`，`transaction_read_only=on`；所有 `v4`/`v4_*` Schema 搜索结果只有 `v4`。最新目录为 123 张表、85 个例程、184 个非内部触发器；迁移台账中 `V4_SHADOW_FIXED_SCHEMA_STORAGE_R1` 与 `V4_SHADOW_FACT_ORIGIN_BINDING_R1` 均有对应 checksum。Shadow identity/facts 固定表探针行数为 0。

### 2026-10-19 Operational Head DEV-only CAS 回滚核验

- 在当前 `market_research` 上对空的 `v4.operational_research_heads` 执行事务内工程 CAS 核验；先以 `EXCLUSIVE` 表锁确认目标无当前行。插入并精确读回 payload bytes、JSONB、SHA-256、generation 1；用旧 SHA 条件更新到不同候选并读回 generation 2；再次以过期旧 SHA 更新返回 0 行，确认 stale CAS 被拒。
- 候选仅含 `ENGINEERING_CAS_ROLLBACK_TEST` / `not_accepted=true` 标记；整个写入事务显式 rollback。后续独立 `REPEATABLE READ READ ONLY` 事务确认 `operational_research_heads` 仍 0 行、只读开启。没有签发或持久化 DEV/Accepted Head、Publication、Owner 或日更回执；没有改动其他业务表。该实测补足固定 `v4` 行上的 CAS 正/负路径机制证据，DB-10 与完整日更产品验收仍为 `PARTIAL`。
- 回滚后调用活动的 `v4_operational_live_head_pg_r1.read_current()`，它在零行状态下准确抛出 `PG_ACCEPTED_OPERATIONAL_HEAD_REQUIRED_NO_FILE_FALLBACK`；独立 RR/RO 核对仍为 0 行。这验证应用读者拒绝从工作区文件合成/回退 Operational Head。


### 2026-10-19 SourceIngress 小包事务读写与 Jobs 页面续验

- 在 `market_research` 的既有开发连接上用事务内工程字节探针验证 `ingest_captured_bytes`：45 字节精确输入写入 `v4.forward_facts`，PG 绑定读回 SHA-256 `6e98c67a81988c7a9e7ce3b5ed859cb5c6a01ed2cd26b89184c491c1af4076e8`，同一字节/路径重试返回 `ALREADY_PRESENT`。随后显式回滚；新的 `REPEATABLE READ READ ONLY` 会话按精确 `(workspace_namespace,kind,fact_key)` 查询确认持久行数为 0，`transaction_read_only=on`。该结果只验证小包写读与幂等机制，不生成历史接受证据。
- 28766 内置浏览器打开 `/v4/research/diagnostics/jobs` 并等待异步加载后，真实页面显示候选 T0 `2026-09-30`、`PG_CANDIDATE_SNAPSHOT`、events 33 / Focus 469 / Forward 117 / Market 1 / Sectors 378 / Settlement 5 / Sources 4 / Stocks 5,213；worker 未启动，快照无作业回执，来源请求 0。页面如实 fail-closed；DB-10 的实际日更和 worker 回执仍未验收。

### DB-09 大包分块边界续验

- 以 67,108,865 字节的工程测试字节（超过 64 MiB 内联上限 1 字节）走 `ingest_package_bytes`，分成 5 个 16 MiB 上限内的 chunk，并由 `read_package_bytes` 在同一事务重组读回；长度与 SHA-256 `21cb3b4aac53f4501245ed1913e95357c443705cb68dd01addccd764f3811b29` 精确一致。事务随后回滚，独立 RR/RO 查询使用唯一 workspace namespace、manifest/chunk kind 与全部精确 fact_key 核对，持久探针行为 0 行。该工程探针验证边界、分块、SHA 和读回，不向数据库沉淀 67 MiB 测试内容；也不替代真实来源或历史 551 MB ZIP 的接纳。

### DB-04 Forward 同名键跨 namespace 隔离续验

- 在 `market_research.v4.forward_facts` 单个 RR 写事务中，使用一个随机探针 ID，写入两个不同 namespace、相同 `kind/fact_key`、不同内容与 SHA-256 的行；按三个主键列精确查询均读回各自原始内容和摘要。再对 namespace A 提交相同主键但不同 payload 的 `ON CONFLICT DO NOTHING` 重试，原始 payload 保持不变，没有覆盖或跨 namespace 合并。
- 写入后显式 rollback；独立只读事务按探针 kind/key 和精确 namespace 族核实持久行数为 0。该工程样例证明固定表主键/追加写身份隔离，不代表实际多 workspace Forward 业务读链及 Focus 成熟结算验收通过，DB-04 仍为 `PARTIAL`。

### 2026-10-19 Focus、Forward 与日更页面续验

- 28766 `/v4/research/focus` 异步加载后显示候选冻结源重建 Focus 469 条（首屏 30 条），并提供搜索/排序/证据控件；页面显式提示结构谓词缺失和旧账未核对。独立 Forward 分母 117、期限计划 585、已发布期限状态 5（覆盖 1 个样本）、成熟合格 0，明确不计算胜率和收益分位数。
- `/v4/research/forward?view=settlement` 显示 T0 `2026-09-30`、当前页 5/5 个期限投影、状态记录 5、`PENDING` 5、成熟合格 0；均为候选快照，不作为正式 Head 或 T0 可知证明。
- `/v4/research/data-update` 实际页面显示 `NO_ACCEPTED_MARKET_CALENDAR_HEAD`、worker 未启动、只读预览；检查源、补齐、自动更新、失败重试、取消均禁用，作业进度表为空。未触发任何写操作。
- `/v4/research/market` 实际显示盘后候选 T0 `2026-09-30`：上涨 2,344、下跌 2,712、平盘 155、不可判定 13；分母 5,224、行情 5,213、成交额 14,378.36 亿元；涨跌停统计 56/12/11/1。官方/媒体事件源未绑定，页面不宣称实时状态。

### 2026-10-19 迁移回执目标连接与 Forward 索引计划复核

- 当前 `market_research` 的 RR/RO 事务读回迁移台账：Research 169/169、Forward 9,256/9,256、History 11/11、Owner 7/7、ReadIndex 16/16、Journal Registry 7/7、Jobs 历史 8/8 和 Jobs 版本 1/1 均为 `VERIFIED`。Forward 9,256 条回执与 `v4.forward_facts` 按 `(workspace_namespace,kind,fact_key)` 精确连接；缺目标或目标 SHA 不符为 0，回执 `target_sha256=payload_sha256` 为 9,256/9,256。此项证明现有迁移台账对应目标行仍在，不能替代逐来源业务语义/活跃消费者验收。
- 只读 `EXPLAIN (FORMAT JSON)` 使用当前真实 workspace namespace 检查 `forward_facts`：精确 `(workspace_namespace,kind,fact_key)` 查找使用 `forward_facts_pkey`；`source_path + source_origin` 的有界候选查找使用 `forward_source_ingress_path_origin_sha_r1` 并有 `LIMIT 2`。没有实际读取大 payload 的 ANALYZE 扫描。
- 当前目录统计尺寸：`forward_facts` 6,219,431,936 B（统计估计 live/dead tuples 9,280/37），`forward_legacy_evidence_r1` 8,394,104,832 B（2,457/0），`forward_r7_facts_r1` 2,182,561,792 B（312/0）；尺寸含 TOAST/索引，行数为 PostgreSQL 统计估值，不当作精确业务计数。

### 当前接受来源与日更 Head 阻断事实复核

- 配置 `config/v4_daily_source_acceptance_authorities_r1.json` 现场仍为 `BLOCKED_NO_INDEPENDENT_ISSUER_APPROVED`，`issuers` 为空。当前 DB RR/RO 只读计数 `market_calendar_sessions=0`、`source_packages=0`、`source_package_facts=0`、`publications=0`、`publication_heads=0`、`operational_research_heads=0`；`v4.daily_core_result_snapshots` 与 `v4.daily_core_result_rows` 固定表已部署；RR/RO `COUNT(*)` 确认为 0。相同事务内 `market_calendar_sessions`、`source_packages`、`source_package_facts`、`publications`、`publication_heads`、`operational_research_heads` 的精确计数也全为 0。缺失的独立签发来源与日历/Head 无法由本机工程探针代替，日更/Accepted 门继续关闭。

### 2026-10-19 Shadow 导出器固定 v4 迁移

- 审查发现 `v4_shadow_pg_r1/r2` 的真实 builder 仍含每次导出创建物理 Schema 的实现，虽然以运行时异常提前停用；相应读回 descriptor 也原先绑定独立 Schema。为关闭单 Schema 消费者缺口，新增中央登记迁移 `069_v4_shadow_fixed_schema_storage_r1.sql` 与 `070_v4_shadow_fact_origin_binding_r1.sql`，在 `v4` 中部署 `shadow_readback_identity_r1` 和 `shadow_readback_facts_r1` 两个版本化固定表，绑定数据库身份、完整内容摘要、来源环境及逐事实 evidence origin，并以 FK 和不可变触发器保护。中央迁移 runner 对目标 `market_research` 成功应用两项；目录仍只有业务 Schema `v4`，固定表数由 121 增至 123。全量业务表数口径包含此次新增表。
- 当前 R1/R2 Python API 作为兼容入口统一委托到 `V4_PG_SHADOW_READBACK_R3` 固定 `v4` writer/reader；已移除旧每次导出 `CREATE SCHEMA` 写实现。descriptor 只接受 `schema='v4'` 并核验完整数据库身份、导出内容 digest、每条事实 digest 和完整身份。Shadow UI 读取器也只接受精确 R3/v4 descriptor 并查询固定 R3 事实关系，旧通用表/旧 Schema 路径不再留作 fallback。后续纯负向验收以完整且签名绑定的历史 R2 descriptor 为输入，确认在触碰 PG 前以 `PG_SHADOW_R3_FIXED_V4_BINDING_REQUIRED` 拒绝其物理 Schema locator；测试 `11 passed`。
- 真实 PG 工程事务内通过该 writer 插入单条 `ACTIVATION_SIMULATION` 探针、执行完整 descriptor/content/fact 校验并确认更新被不可变触发器拒绝；外层事务显式回滚。独立 RR/RO 连接显示迁移后的 identity/facts 探针行数均为 0，`transaction_read_only=on`。没有写入 REAL/PIT Shadow 数据、没有创建 Schema。
- 28766 内置浏览器实际打开 `/v4/shadow`：页面显示 `NO_REAL_SHADOW_DATA`、真实样本 0、完整字段 UNKNOWN，并说明等待独立接受的真实 Shadow 发布；六个域均明确无已接受真实数据。该固定存储和浏览器 fail-closed 证据关闭“Shadow Schema 未迁移”的架构缺口，但缺少签发来源、接受 readback manifest 及真实 PIT 输入，Shadow 业务模块仍为 `PARTIAL`；不计为模块验收通过。

### 本续行的现场复核与清理策略拒绝

- 再次使用 `REPEATABLE READ READ ONLY` 查询确认当前 PG 为 `market_research` / OID `646711` / `127.0.0.1:5432`，事务只读，V4 命名空间仅 `v4`；目录当前计数 123 表、85 例程、184 个非内部触发器。另按全库非系统命名空间核对：`public` 表/视图/序列均为 0，用户 Schema 仅 `v4`（123 表、5 序列），v4 到其他非系统用户 Schema 的目录依赖为 0。端口监听为 PostgreSQL `5432`、开发服务 `28766`；没有 `28765` 监听。现有 28766 浏览器仍在个股详情页，显示候选 T0 `2026-09-30`、日线 QFQ `120/253` 根及未具备来源的字段状态。
- 依用户本轮“按任务卡继续完成”要求，尝试仅删除本仓库内与同目录 `.py` 源文件对应的 `.pyc`（此前清点为 2,159 项、28,981,840 字节），保留 6 个无对应源码文件；执行工具策略在 PowerShell 命令启动前拒绝该精确操作。未删除文件，未改用其他删除通道，DB-11 Workspace 物理清理仍为 `PARTIAL`。
- 已补齐“全模块缺口与可执行验收路径”矩阵，将现有 PG/UI 工程状态、缺失的真实来源/Owner/日历/PIT 输入以及输入到位后的数值和浏览器验收路径逐模块对应。该报告变更已按暂存区策略检查后推送；本次未写入业务 PG、未重启服务、未改动 28765。

### 2026-10-19 旧 Shadow writer 死代码移除

- 继续静态扫描发现旧 `v4_shadow_live_pg_r3.NativeShadowDatabase` 虽然构造器开头已 fail-closed，但类体仍保留独立 PG 连接、路径哈希 Schema 和不可达的创建/写入逻辑。已删除整段退役 writer 实现；仅保留旧导入表面、构造即拒绝的兼容类以及仍有测试合同调用的显式模拟资格辅助函数。源码中不再有 Shadow 路径的 `CREATE SCHEMA` 或数据库连接实现。
- 新增回归断言检查旧文件不含 Schema 创建语句且实例化在连接前按迁移错误拒绝。`tests/test_v4_single_schema_guard_r7.py` 定向运行 `7 passed`；两个变更 Python 文件 `py_compile` 成功，指定文件 `git diff --check` 通过。所有 pytest 临时目录与 Python 缓存均在 `G:\codex_tmp`。
- 本次只改源码/回归/阶段报告；未连接或写入 PostgreSQL、未改变 Schema/业务 Head、未启动/停止服务，也未触碰 28765。数据库目录现状仍依据最近 RR/RO 实测；本条是运行时能力进一步移除，不构成新 PG 清理或模块数据验收。

### 2026-10-19 Forward 迁移 locator 入口精确化

- Market Fact、Period Owner 与 Cohort Reader 对旧来源 locator 的前置门原先只判断 `v4_forward_` 前缀；虽然下游 migration-map resolver 会再次用严格正则拒绝非法值，但入口本身允许非合同格式进入后续逻辑。新增共享纯函数，只接受冻结的 `v4_forward_<16位小写hex>` 与 `v4_r8_forward_<16位小写hex>` 格式，并用于三个消费者及精确迁移/只读解析入口；实际历史内容仍只能凭 `v4` 固定表的 `VERIFIED` 精确映射回执读回。
- 新增纯单测覆盖两种合法历史定位、畸形/大小写/尾缀/其他模块/空 locator 拒绝，以及无效 locator 在建立 PG 连接前 fail-closed。定向 Forward locator + History locator 回归 `3 passed`；5 个变更 Python 文件 `py_compile` 通过，变更文件 `git diff --check` 通过。测试临时目录与字节码缓存均置于 `G:\codex_tmp`。
- 未触碰数据库、28766 或 28765；该改动是 locator 格式收紧，不改变已验证映射、数据行或模块来源状态。

### 2026-10-19 续修后数据库与分支实测

- 在代码推送后再次由项目连接层建立 `REPEATABLE READ READ ONLY` 事务并读回：`market_research` / OID `646711` / `127.0.0.1:5432`，用户 `postgres`，`transaction_read_only=on`；`v4` 与 `v4_*` 名称查询仅返回 `v4`，目录 123 张表、5 个序列、0 个视图，`v4` 到其他非系统用户 Schema 依赖为 0。
- 实测监听端口为 PostgreSQL `5432` 与开发服务 `28766`；`28765` 当前未监听，未启动或操作生产服务。续修提交 `f529970b8`（移除退役 Shadow writer）和 `67b88781a`（精确校验旧 Forward locator）均已推送到 `origin/codex/v4-workspace-cleanup`，远端 ref 与本地 HEAD 相等。
- 这次目录核验确认单 Schema 实际结果仍成立，不追补缺失的历史 DROP 收据，也不改变 S3/DB-05、DB-07、外部来源、日更或全模块状态。

### 2026-10-19 10-15 交易日 TDX 回溯文件补采与固定 SourceIngress 读回

- 用户纠正本轮目标交易日为 `2026-10-15`。调用项目既有官方 TDX 捕获合同核对该日时，官方页公布的最新更新日期为 `2026-10-16`，因此 10-15 目标查询返回 `WAIT_TDX_PUBLICATION`；精确页、更新信息与捕获回执绑定均只作为来源元数据写入固定 `v4` SourceIngress，不将元数据当作 10-15 行情包。
- 按同一合同捕获官方 10-16 包：`https://data.tdx.com.cn/vipdoc/hsjday.zip`，549,184,442 字节，SHA-256 `c0ea0dffad66e06351596fb3855ffde0d80536e3d962867a09f42ddf32448219`，官方 update date `2026-10-16`。ZIP CRC 校验通过，12,205 项、解压 949,447,040 字节。该包于 10-18 捕获并晚于目标日，故仅作为回溯重建来源。
- 从该包只读提取 10-15 的 32 字节 `.day` 原始记录，保留包 SHA、成员路径及 SHA、原始记录字节及 SHA；不使用 10-16 或更晚记录。经严格顺序/长度核验的目标日成员为沪 4,869、深 4,506、北 352，共 9,727。排除 `sh000833.day`（历史段非递增）及 `sz131804.day`、`sz131807.day`（空文件）。抽取文件 5,143,445 字节，SHA-256 `aa9c9689b19251fcb5335234b4d28c5797214851738a78d3cc1239cfd7e880ca`，过程证据位于 `G:\codex_tmp\v4_tdx_target_20261015_from_20261016.jsonl`。
- 抽取物以 `TDX_OFFICIAL_PACKAGE_TARGET_DAY_EXTRACT_RETROSPECTIVE_NON_PIT` 明确身份写入历史 SourceIngress；开发库精确路径/摘要读取回读字节相等。抽取内代码身份仅来自 TDX 文件名，尚未和 10-15 接受 Universe/代码身份 Owner 对接。状态保持 `RECONSTRUCTED_CORRECTED`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`formal_accepted=false`；未创建 Source Package、Universe、日历、Publication 或任一 Head。
- 写入后独立 `REPEATABLE READ READ ONLY` 复核为 `market_research` / OID `646711` / `127.0.0.1:5432`、`transaction_read_only=on`；V4 命名空间仍仅 `v4`。`source_packages`、`source_package_facts`、`market_calendar_sessions`、`publications`、`publication_heads`、`operational_research_heads` 仍各 0 行。该补采为 10-15 DEV 回溯输入，不解除独立签发、Accepted 日历、真实 Universe/Owner 或生产门。

### 2026-10-19 续行：Schema 生成残留与 10-15 开发页核验

- 对 `src/workbench_db` 与 `src/workbench_analysis` 的运行时源码扫描显示，V4 仍有 `create_schema` 调用点，但中央 `v4_native.create_schema` 只允许名称为 `v4` 且仅核验该 Schema 已存在；任何其他名称均以 `V4_SINGLE_SCHEMA_ONLY_SCHEMA_CREATION_BLOCKED` 拒绝，运行时不会建业务 Schema。历史只读目录唯一命中动态 Schema 关键词的函数为 `v4.reject_forward_legacy_schema_retirement_mutation_r1()`；RR/RO 读回定义确认其只是阻止旧退役账目修改的触发器函数，不含 Schema DDL。业务 Schema 目录仍仅有 `v4`。
- 真实 28766 个股详情页再次显示候选 T0 `2026-09-30`，提示 `PG 候选快照 · 不代表正式 Head`；指标来源缺失仍展示为“来源能力不足”，页面未把 10-15 回溯 SourceIngress 误展示为新日更数据。当前浏览器渲染和数据模型尚未接上 10-15 DEV 回溯行，日更仍需接受日历、Universe/身份映射、Source Package 与 Head 才能完整验收。
- 当前开发分支仅固定业务 Schema `v4`；本次没有运行 DDL、清理旧 Schema、改变数据库行或启动服务。下一步按固定迁移与消费者矩阵，逐一将运行时表/保护器 DDL 收敛到版本化中央迁移，再继续 10-15 DEV 日更和模块验收；Accepted/生产切换仍关闭。

### 2026-10-19 10-15 日更目标口径纠正与真实任务账本复核

- 更正前文日期表述：`2026-09-30` 仅是 28766 当前个股/诊断页使用的旧 PG 候选快照 T0，不能代表日更流水线的最新任务日期。日更账本确有 `through_date=2026-10-15` 的任务，但任务日期上界不等于该日已发布。
- 在 `market_research` 使用项目只读连接、`REPEATABLE READ READ ONLY` 现场读取 `v4.jobs_update_jobs_r1`、`jobs_update_job_days_r1` 与事件：Scheduler job `83a9fbbfafde4402ad0da97846481a1d` 的 through_date 为 2026-10-15、状态 `QA_BLOCKED`；同一 job 下 2026-10-14 为 `QA_BLOCKED`（`SOURCE_EXECUTION_FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED`，attempt_count=2），2026-10-15 为 `QUEUED`（attempt_count=0）。因此没有证据表明 10-15 已完成日更发布。10-13 的 `PUBLISHED_FULL` 是此前手动作业，不会改变上述结论。
- 按用户最后更正将 `2026-10-15` 作为本轮目标交易日，实际调用 `execute_sources(root,'2026-10-15','CATCH_UP',capture_only=True)`。入口返回 `BLOCKED / OFFICIAL_SESSION_NOT_VERIFIED`，细节 `PG_MARKET_CALENDAR_IDENTITY_REQUIRED`；流程没有转为 Accepted，也没有发布日更、Publication 或 Head。阻断发生于 PostgreSQL 日历身份验证，故不应把该结果说成 TDX/日更任务完成。
- 当前 28766 浏览器候选 T0 仍为 2026-09-30；此前 2026-10-16 官方 TDX 包中抽取的 10-15 原始记录仍只作为 `RECONSTRUCTED_CORRECTED`、非 PIT、非 Accepted 的开发 SourceIngress。它们并未自动接入该网页候选快照，也不能替代 PG 接受日历、Source Package、Owner/Universe 或正式 Head。

### 2026-10-19 28766 日更诊断页日期口径浏览器复验

- 在真实 `127.0.0.1:28766/v4/research/diagnostics/jobs` 浏览器页面核对静态资产更新后的完整异步渲染。页面明确标注 `研究候选快照 T0：2026-09-30（此日期不代表日更任务账本最新日期）`，并将“worker 未启动”限定为当前没有运行中的 worker，说明本页面不展示日更任务记录；按钮也标注只查看本页快照诊断。顶部仍标示“PG 候选快照 · 不代表正式 Head”。
- 该修正不硬编码或伪造任务日期、不改研究数据/日更账本/Head；没有重启 28766，没有启动 worker，也未触碰 28765。数据库日更账本仍以此前 RR/RO 实读结果为准（10-15 任务日期记录存在但当日 `QUEUED`）。

### 2026-10-19 ForwardFactStore 运行期 DDL 收敛

- `ForwardFactStore` 初始化不再调用 `create_schema()`，也不再内嵌创建 `forward_facts`、迁移账目、不可变函数或触发器的 DDL；消费端物理 Schema 固定为 `v4`，仅校验中央迁移 050/059 建立的三张固定关系和 `forward_facts` 上处于启用态的追加写保护触发器，随后执行原有 Forward 业务写读。workspace 只作为 `workspace_namespace` 行身份使用。
- 当前开发 PG 的 RR/RO 只读现场核对通过上述关系/触发器校验，身份为 `market_research:5432`；非系统用户 Schema 仅 `public` 与 `v4`（`public` 无 V4 表），未建新 Schema。
- 用 G 盘临时空目录执行真实 `ForwardFactStore` 构造路径，拦截事务仅为显式回滚；返回 `schema='v4'`。独立 RR/RO 事务按唯一 workspace namespace 读回迁移标记为 0，确认测试插入未持久化。语法编译成功，源码扫描不再发现该消费者中的 `CREATE SCHEMA/TABLE/FUNCTION/TRIGGER` 或 `create_schema()`。

### 2026-10-19 Journal Registry 运行期结构部署移除

- Journal writer 固定将 `registry_schema` 绑定为 `v4`；初始化不再调用 `workspace_schema()`/`create_schema()` 或运行 `CREATE TABLE`，而是校验中央迁移 061 部署的 `v4.journal_heads` 与迁移映射表。Journal 仍使用 PostgreSQL 事务内临时表暂存版本数据，不创建第二个业务 Schema。
- 修复 Journal 从精确旧 descriptor 读取临时表时 `with read(previous)` 代码块的缩进错误；该错误此前会使整个模块无法导入。新旧 descriptor 的数据库读取及历史迁移映射语义保持不变。
- Python 编译成功，开发 PG RR/RO 对中央关系的现场校验通过；真实 `JournalConnection` 构造探针使用 G 盘临时目录并显式回滚，独立只读事务核验 `journal_heads` 对应唯一键 0 行，`transaction_read_only=on`。临时目录已清理；源码持久表 DDL、`create_schema()` 和 `workspace_schema()` 调用均已移除。

### 2026-10-19 10-15 日更复跑与 PG 回执读回续修

- 按用户纠正以 `2026-10-15` 为目标交易日、冻结的官方 TDX `2026-10-16` 包为回溯包重跑日更采集。验证 Accepted 基础日历与 R4 本地审计候选日历的精确 SourceIngress 绑定后，诊断会话确含 10-15；候选日历保持 `LOCAL_READY_FOR_EXTERNAL_AUDIT`，仅在进程上下文内使用，`production_admission=false`。
- 复跑暴露 BaoStock 回执写入/读回哈希口径错误：Forward 事实保存原始 smoke receipt 文件摘要，而 loader 误用 PG JSON 重编码后的摘要比较。改为把原始 receipt 按绑定路径与 SHA 导入固定 PG SourceIngress，并在只读 loader 中精确读回原始字节、核对 SHA 和解析值；同时修正日更证据路径对内存 `PGSourceBytes` 使用 `Path.relative_to` 的不兼容。
- 真实复跑读取 `market_research` / OID `646711` / `127.0.0.1:5432` 的固定 `v4` BaoStock runtime fact：目标日 `2026-10-15`，日行情 5,226 行，复权因子 22 行，PG 接受运行时回执读回通过。使用 TDX 10-16 包 SHA `c0ea0dffad66e06351596fb3855ffde0d80536e3d962867a09f42ddf32448219` 生成的目标日 TDX 候选 PG 读回状态为 `DIAGNOSTIC_ONLY`、5,565 行。落盘日更冻结绑定 SHA `a28b104e65714fb0be3b3c4a8145c45c2f06a4e0d7949823e26085e45d693870`，`AS_RECORDED=false`、`PIT_ELIGIBLE=false`，不构成 Accepted 日更。
- 入口随后停在严格的 Owner 依赖校验：`v4_operational_live_head_pg_r1.read_current()` 返回 `PG_ACCEPTED_OPERATIONAL_HEAD_REQUIRED_NO_FILE_FALLBACK`。开发库目前无 Accepted Operational Head；未创建/伪造 Head、未发布 Owner/Publication 或生产 Head。当前唯一 Accepted Data Head 仍是 9-30 候选，10-15 日更没有发布完成。
- `tests/test_v4_baostock_runtime_acceptance_pg_r1.py` 定向回归 7 项通过；合并执行的日更 executor 套件共 14 项中 12 项通过、2 项受测试环境阻断：一项 mock PG 对象缺少真实 `execute()` 接口；另一项导入路径试图访问非 disposable 本地 PG，被测试隔离插件拒绝。真实日更入口已越过回执与证据路径两处错误，并在缺少 Accepted Operational Head 的设计门禁处停止。
- 本次开发只使用当前 `market_research` 数据库与 `v4`，没有新建 Schema；28766 是当前唯一监听的项目网页端口，28765 未监听且未操作。后续需补齐真实接受日历/Universe 身份和 Operational Head 的完整前置证据，才能继续 Owner 与当日日更验收；不能将 10-15 冻结候选或 9-30 页面 T0 表述为已发布 10-15。

### 2026-10-19 固定 v4 消费者保护迁移 072

- 为消除风险/优先级 Owner、Sector Lifecycle、ReadIndex R1/R2 与日更作业历史消费者中的运行时持久 DDL，新增并登记 `V4_FIXED_SCHEMA_CONSUMER_GUARDS_R1`。中央迁移 072 在固定 `v4` 关系上统一部署保护器；消费者现在只核验中央迁移创建的固定表、列、策略行与启用触发器，不再动态创建 Schema、表、函数或触发器。
- 迁移前先对同一开发数据库检查 15 个先决关系，并在 RR/RW 事务中完整执行迁移 SQL 后显式回滚，确认 SQL 可执行。正式使用项目迁移 runner 应用到 `market_research`；迁移台账 SHA-256 为 `2dbdeca42b48930c0b4e10d0813cdf2ee9aacd609d2546f4e3f5837eeb4c4db5`。迁移后 RR/RO 连接确认身份 `market_research`、OID `646711`、`127.0.0.1:5432`、`transaction_read_only=on`，且 072 台账读回一致。
- 在生产数据外未新增探针行的情况下，通过已存在记录执行 12 项 update/truncate 负向探针（风险版本/载荷、优先级版本、Sector 版本/明细、ReadIndex R1/R2 版本/明细、作业尝试/事件），均被保护器拒绝，SQLSTATE `P0001`。探针外层事务显式回滚；之后 RR/RO 对 14 张固定关系逐表 COUNT 前后完全一致。核验的 26 个相关启用触发器均存在，现有业务行数包括 Sector Lifecycle 400、ReadIndex R1/R2 明细 78,857/62,671、作业事件 406。
- 本阶段测试：迁移 allocator 2 项通过，Sector Lifecycle 与日更进度回归已运行；风险、ReadIndex 与部分 Owner 测试在 collection/import 时触发测试隔离插件对非 disposable `market_research` 的访问拒绝，另有 Owner closeout 测试同类环境阻断。未绕过隔离，也未因此写入额外业务数据。Python AST/语法、指定 diff whitespace、消费者源码无持久 DDL 检查通过。
- 这项迁移只完成消费者保护与持久 DDL 收敛，不代表 ReadIndex/Owner/日更等模块已完成真实业务验收，也不代表迁移清理可以删除其他旧 Schema。10-15 日更仍须从 10-16 冻结包获取 10-15 数据，并满足接受日历、Universe/身份映射和 Accepted Operational Head 的正式门禁；当前 9-30 仅是页面使用的旧候选 T0，不能混作日更任务日期。

### 2026-10-19 冻结作业导入回执固定版本化

- 源码扫描发现仅供 G 盘隔离冻结作业 oracle 使用的 `v4_job_migration_r1.import_oracle()` 仍会按调用创建未版本化 `migration_receipts` 表。先用 RR/RO 核对实际 PG：`v4.migration_receipts` 与新目标关系都不存在，因此没有遗留回执行需要搬移。保留导入器用途，将目标定为固定版本表 `v4.jobs_frozen_oracle_migration_receipts_r1`；导入前要求 `jobs.schema='v4'` 并校验中央迁移关系/不可变保护器，移除运行时持久 DDL。
- 由迁移登记器分配 074，正式迁移 runner 在 `market_research` 应用 `V4_FIXED_JOB_MIGRATION_RECEIPTS_R1`，SHA-256 `f2aa7a088731e813bbade4244b42214df1a52fc70aa799c1a1a0101be1e6e055`。应用后固定 v4 表数为 124；RR/RO 连接身份为 `market_research` / OID `646711` / `127.0.0.1:5432`，事务只读且回执表初始 0 行。
- 在 RR/RW 外层事务内插入唯一 64 字节摘要探针，更新、删除、截断三种修改均返回 SQLSTATE `P0001` / `IMMUTABLE_JOB_MIGRATION_RECEIPT`；显式回滚后独立 RR/RO 计数仍为 0。未导入业务 oracle，也未改变其他作业历史。
- 新增本地纯单元断言覆盖固定关系/guard 校验和无运行期表 DDL。代码与 074 迁移已提交并推送到开发分支；本次报告追加待随阶段记录提交。其他未相关工作区修改未纳入。

### V4 PG 运行期持久 DDL 全源码复扫

- 在上述迁移后再次扫描 `src/workbench_db`、`src/workbench_analysis`、`src/workbench_service` 中 Python 源码的 `CREATE TABLE/INDEX/FUNCTION/TRIGGER`、`ALTER TABLE`、`DROP TRIGGER` 与 `create_schema()`。V4 PG 业务持久结构创建现在只通过固定迁移 runner 管理：Research/Journaling/Series builder 中的未限定 `CREATE TABLE` 由 builder 转换为连接私有 `pg_temp` staging 表；`v4_native.create_schema()` 只验证已部署的 `v4`，不执行创建；本地生产/评估与 product-pack 的 DDL 属于 SQLite 文件库。上轮发现的作业 oracle 持久回执 DDL 已于 074 移除。
- 扫描未发现 V4 业务运行期 `CREATE SCHEMA` 或可按 workspace/purpose 选择物理 Schema 的路径。`workspace_schema(root,purpose)` 返回固定 `v4`，workspace/purpose 只参与数据行身份；`connection()` 拒绝所有非 `v4` locator。该静态结果与此前目录中仅存在 `v4` 的 RR/RO catalog 读回一致。仍需持续审查隔离迁移脚本和全模块业务验收，静态扫描不代表每个业务模块的 PIT/Accepted 验收已通过。

### 2026-10-19 日更增量目标更正：基线 10-15，目标 10-16

- 按用户最新说明，本轮日更增量目标是 **2026-10-16**；系统此前已处理到的日更基线是 2026-10-15。前文将 10-15 当成本轮目标的记录只表示此前做过的 10-15 诊断，不再作为本轮目标定义。个股页此前的“当前已处理截至 2026-09-30”来自页面绑定的旧研究快照 T0，和日更任务日期不是同一口径。
- PG 精确日期读取确认用户所说的 10-15 日更源数据确实存在：10-15 BaoStock runtime fact manifest `ACCEPTED`，5,226 条日行情、22 条因子；10-16 对应 manifest 也为 `ACCEPTED`，5,226 条日行情、48 条因子。这里的 `ACCEPTED` 是 BaoStock runtime receipt 合同状态；独立查询的 `V4_DATA_ACCEPTED_HEAD` 仍为 9-30，故页面展示 9-30 不是日更源数据最新日期。
- 实际日更捕获尝试目标 10-16 后，开发目录新增不可变冻结件 `data/v4/dynamic_daily_sources/daily_freezes/2026-10-16/81ef2d58c8df9ee23564d7ba142c75016a3c8838273e7d13673901aacf0ef419.json`，字节 SHA-256 `32093deff93b0baed3f59fcee8dffae1c3303302788948b4bb3e7c6879f1c408`。该冻结件标记 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`，仅为开发诊断候选。
- TDX 10-16 官方包 SHA `c0ea0dffad66e06351596fb3855ffde0d80536e3d962867a09f42ddf32448219` 的目标日抽取覆盖 `2026-10-16`，5,567 行，固定 v4 PG 事实读回 `PASS`、`DIAGNOSTIC_ONLY`。BaoStock 10-16 固定 v4 运行时接受事实按合同读回成功：5,226 条日行情、48 条复权审计因子，manifest 与 payload 绑定 SHA `6d709f1f049ebd3aa1481e8d8479c71dcd1b03a88c03a0c953561548a76e8820` / `9c5e0c6d78ba328aa4293301f50e150907fd2beedbe85ed5094c07e536b2f82d`。这证明输入候选可读，不等同于 Accepted 日更发布；TDX 包于目标日后捕获，不能标为 `AS_RECORDED` 或 PIT。
- 非 capture-only 的正式执行入口在读取日历时以 `PG_MARKET_CALENDAR_IDENTITY_REQUIRED` 停止；capture-only 路径能落盘/读回候选，但无法通过正式 Owner/Head 门。当前开发 PG RR/RO 实读仍为 Accepted Data Head T0 `2026-09-30`、Accepted Operational Head 缺失、接受市场日历事实 0、Source Package/Publication/Head 事实均 0；日更作业账本 through_date 目前为 10-15 且状态 `QA_BLOCKED`，10-15 日期仍 `QUEUED`。因此不更新正式 Head 或伪造 10-15 基线；本轮可确认的 10-16 结果是回溯诊断候选，正式日更验收仍被现有日历与 Owner 门阻断。
- 为避免旧研究快照日期被读成日更最新日期，三个研究前端入口的顶栏现显示“研究视图 T0”并说明该日期属于本页快照、日更状态查看数据更新/日更作业。真实 `127.0.0.1:28766` 个股浏览器页刷新后实际显示新文案，同时保留 `PG 候选快照 · 不代表正式 Head` 与图表截至 9-30；没有重启服务或触碰 28765。

### 2026-10-19 日更日期口径与官方交易日证据复核

- 更正对用户的表述：10-15 BaoStock runtime manifest 中已有 5,226 条日行情和 22 条因子，因此本轮业务增量基线是 10-15，目标是 10-16；作业账本中 10-15 的 `QUEUED` 只表示该日期的日更作业验收状态，并不否定来源事实已在系统中。个股页的 9-30 仅是 `V4_DATA_ACCEPTED_HEAD`/研究视图 T0，不是日更基线。
- 交易日核对：上交所 2026 年中秋、国庆休市公告说明 10-1 至 10-7 休市、10-8 起照常开市；深交所同日通知给出相同复市安排。10-16 为星期五且不在公告休市范围，因此本轮目标日期是 10-16。官方来源：[上交所公告](https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/announcement/general/c/c_20260915_10832273.shtml)、[深交所通知](https://www.szse.cn/www/disclosure/notice/general/t20260917_622911.html)。此网页核对可确认日期，但不会自行创建或接受 PG 日历合同/Head。
- 本轮新鲜 `REPEATABLE READ READ ONLY` 开发库复核身份仍为 `market_research` / OID `646711` / `127.0.0.1:5432`；`v4.model_namespaces`、`v4.operational_research_heads`、`v4.publications`、`v4.market_calendar_sessions` 当前分别为空、空、空、0 行。数据库没有正式日历或 Operational Head 的事实继续阻断正式日更验收；不得将来源回执、公告网页或 9-30 研究 T0 伪装为已接受发布。

### 2026-10-19 日更中心来源日期可见性修复与真实浏览器验收

- `src/workbench_service/v4_server.py` 的只读候选状态增加从 `v4.forward_facts` 读取最新五笔 BaoStock runtime acceptance facts；使用固定 `v4`、精确 forward namespace 与 kind 查询，并校验 PG payload SHA、业务合同、交易日、manifest 状态和 smoke target。回执字段明确标注 `ACCEPTED_RUNTIME_RECEIPT`，并返回 `publication_status=NOT_IMPLIED`；查询为 `REPEATABLE READ READ ONLY`，不创建任务或写入数据。
- `src/workbench_service/static/daily-update/app.js` 与 `index.html` 将研究快照 T0 和日更来源运行回执分开显示。真实 PG 数据显示最近两日为 2026-10-15（5,226 日行情/22 因子）与 2026-10-16（5,226 日行情/48 因子）；文案注明来源运行回执不等于正式发布。无接受日历时，检查、补齐、自动更新、重试、取消按钮仍全部禁用。
- 目标 28766 服务按原 G 盘启动脚本在同一端口重载；真实 `http://127.0.0.1:28766/v4/research/data-update` 浏览器验收显示 T0 2026-09-30、`NO_ACCEPTED_MARKET_CALENDAR_HEAD`、Worker 未启动及上述 10-15/10-16 来源事实。截图证据：`G:\codex_tmp\v4_daily_update_28766_20261019.png`。检查时 28766 监听 PID 46304，PostgreSQL 5432 PID 8640；28765 无监听且未触碰。
- 正式日更仍为 `PREVIEW_ONLY`，任务 worker 未启动，页面和 API 均未声称发布 10-16；全链路正式验收继续等待 PG 接受交易日历及 Operational Head 等既有前置项。

### 2026-10-19 DB-05 PostgreSQL 错误日志补充审计

- 对同一 `market_research` 实例执行 `REPEATABLE READ READ ONLY` 检查，身份为 `postgres` / `127.0.0.1:5432`，PostgreSQL 启动时间 `2026-10-18 11:06:30+08`。检查并筛读 2026-10-10 至 2026-10-19 的 14 个现存日志文件；当前用户 Schema 仍只有 `v4`。
- 日志配置为 `log_statement=none`、`log_min_duration_statement=-1`、`log_min_error_statement=error`。筛选到的 `DROP SCHEMA ... RESTRICT` 文本来自错误日志上下文（`v4_meta`、`v4_jobs_2169e77ca47db3a6`、`v4_00bd3ea17fe4cd57d84f9171aa8e725fbd9edab55a754087aac5b2f5`）；这些只证明相关受限语句出现在错误上下文，不能证明成功删除。由于成功 SQL 默认不入日志，此日志无法补齐 38 项缺失的成功回执，也不能证明全历史绝无 `CASCADE`。
- 机器可读审计结果保存在 G 盘临时证据 `G:\codex_tmp\v4_pg_log_drop_audit_r1_20261019.json`；DB-05、S3 继续为 `PARTIAL`，没有把错误上下文升级为 `DROP_RESTRICT_SUCCESS`。

### 2026-10-19 最新 PostgreSQL 单 Schema 目录复核

- 新鲜 `REPEATABLE READ READ ONLY` 查询确认数据库 `market_research` / OID `646711` / 角色 `postgres` / `127.0.0.1:5432`，事务 `read_only=on`、隔离级别 `repeatable read`；当前 V4 用户 Schema 名称仅 `v4`。
- 当前 `v4` 目录计数为 124 张表、88 个例程、194 个非内部触发器。该结果更新本报告开头 S2 与 DB-12 的“最新目录”计数；本报告中先前按时间记录的 123/85/184 仍是当时现场值，不代表本次复核。
- 机器可读结果：`G:\codex_tmp\v4_single_schema_catalog_recheck_r2_20261019.json`。

### 2026-10-19 28766 全模块交互补充核验

- 在真实内置浏览器对 `127.0.0.1:28766` 继续进行页面操作，当前研究身份为 Release `05cf8913242f46c8af53b3d89f323b64`、T0 `2026-09-30`、物理 Schema `v4`。板块列表搜索“煤炭开采”返回 1 条；打开详情有 25 名完整成员；成员搜索“中国神华”返回 1 条（`SH.601088`，收盘 47.800），并从成员页进入个股详情。
- 个股详情的行情周期控件实际从日线切至周线和月线；Focus 页面读取 469 条候选、117 个 Forward 样本、585 个期限计划、5 条已发布期限状态覆盖 1 个样本、成熟合格 0。打开 Focus 来源抽屉确认 `FP08_FOCUS_SUCCESSOR_PUBLICATION_V1`、source_as_of `2026-09-30`，该行事件值为 `DATA_UNAVAILABLE`。
- Forward 期限结算页展示 5/5 条候选期限均为 `PENDING`，展开 T+10 后到期日、收益和路径仍未知。FEP 证据抽屉显示 Champion `NONE`、生产 `UNGRANTED`、范围 `HISTORICAL_ENGINEERING_EVIDENCE_ONLY`。市场页实际显示分母 5,224、行情 5,213、涨停 56、跌停 12、停牌 11、未知 1；价格规则来源抽屉保留 `RECONSTRUCTED_CORRECTED`、`AS_RECORDED=false`。诊断健康与来源页的抽屉可读：股票来源 `BOUND`；来源诊断合同摘要前缀 `f3e6c986`，缺口含 profile_identity 11 项及未准入 Focus 独立写入。
- 机器可读交互记录：`G:\codex_tmp\v4_28766_browser_interaction_addendum_r1_20261019.json`。这些操作证明页面功能和证据抽屉可交互，不把候选数据或研究 T0 算作正式接受；研究 T0 `2026-09-30` 与日更基线 `2026-10-15`、本轮日更测试目标 `2026-10-16` 分开记录。模块业务验收仍为 `PARTIAL_DATA`，缺 PIT、成熟结果或独立来源的字段保持未知/受限。

### 2026-10-19 旧 R7 基线工作区只读盘点

- 只读盘点 `G:\codex_tmp\r7_active_baseline_20261015`：该独立副本位于 `master` / HEAD `9d40f3750b73465b59139dccb24d3a886271ea5e`，有 5 个跟踪文件修改（合计 34 行新增、111 行删除）及未跟踪的 `data/`、`v4/`、`runtime/`、文档和第三方资料目录。3 个未跟踪 Python 适配器里，Forward API 路由和 Accepted Head 后的 R7 捕获逻辑已由当前分支原生代码覆盖；R6 runtime compatibility wrapper 不在当前启动路径。副本还含有未归属数据，无法据当前证据证明全部可重建且无活动依赖，因此没有执行清理或搬迁。
- 逐文件 SHA-256、分支/HEAD、跟踪改动和目录清单保存在 `G:\codex_tmp\v4_r7_baseline_workspace_inventory_r1_20261019.json`。当前仓库中的 `source_view.py` 与该副本哈希相同；其余 4 个跟踪文件有差异，3 个未跟踪适配器在当前仓库不存在。该清单仅记录状态，不把缺失的旧 hook 恢复到当前运行时。

### 2026-10-19 S1 固定版本表真实 PG 双版本写读验收

- 在授权开发库 `market_research` / OID `646711` / `127.0.0.1:5432` 中，使用代码分支 HEAD `9db4c23ecaba6d9306c094c9c6eb92aaff1e0dff` 创建明确标记 `V4_R21_R7_S1_RUNTIME_QA_R1` 的 QA-only 微型版本：Snapshot A/B、Series A/B、Journal A/B 共 6 个 release，T0 均为 2026-10-16。QA 元数据与键均显式标为 `qa_only`，不属于接受业务来源，不绑定任何 Research/Operational/Publication Head。
- 对每个 release 使用 `load_release(..., verify_content=True)` 与只读 `read()` 路径完成版本摘要校验，并分别只读回本版本的 QA object；Series bar 和 Journal day 按精确 key、T0、payload 读回。A/B 的 release ID 与逻辑摘要均不同，未跨版本串读。创建前后同一只读事务核验的用户 V4 Schema 集合均为 `[v4]`。
- 六条 QA 版本保留在固定 `v4.research_*` 版本表中，供本轮架构回归审计；它们没有更改正式 Head、Publication 或日更作业状态。完整机器证据与只读复验脚本位于 `G:\codex_tmp\v4_single_schema_s1_runtime_qa_20261019\S1_RUNTIME_QA_R1.json`、`audit_s1_runtime_qa_r1.py`、`S1_RUNTIME_READBACK_AUDIT_R1.json`。该工程验收证明固定版本表的版本隔离，不替代完整业务数据或模块 Accepted 验收。

### 2026-10-19 28766 最新代码运行状态复核

- 真实监听进程为 PID `46304`，命令行指向 `G:\codex_tmp\start_v4_28766_single_schema.py`，创建时间 `08:03:50 +08:00`；最新应用代码相关提交 `b7be7effe` 于 `08:05:00 +08:00` 提交，因此该进程未加载该提交后的 BFF 代码。启动脚本目标为当前仓库和 `market_research` OID `646711`；当前 `/api/v4/context` 返回 PG 候选 release `05cf8913242f46c8af53b3d89f323b64`、研究 T0 `2026-09-30`，仍不是日更日期。
- 对 28766 执行受控重载的命令被本机执行策略拒绝；拒绝后没有换用其他进程控制通道。28765 当时无监听且未操作。故本报告不将旧进程页面算作最新提交的浏览器验收，DB-07 继续保持 PARTIAL，需在允许的 28766 重载后再实测。

### 2026-10-19 Forward history-only 别名迁移回执只读核验

- 修正 `scripts/verify_v4_forward_active_alias_receipts_r1.py`：别名迁移后只在 `v4.workspace_namespace_alias_history_r1` 留存 `MIGRATION_HISTORY_ONLY`，原活跃别名表已不存在；校验器改为核历史表，并支持明确的 `--verify-only` 只读模式与单独的 `--apply` 回执写入模式。
- 对 `v4_forward_812843566da3f180` 与 `v4_forward_eb17ba1165c8c2a5` 运行 `--verify-only`，数据库身份为 `market_research` / `127.0.0.1:5432`，目标均为固定 `v4.forward_facts`。96 行和 2,769 行映射分别与目标完整行键、payload/source SHA 摘要一致，摘要分别为 `4cbc1744…09bc48` 与 `106155b4…9d8a454`；旧源表当前均不存在，固定 `v4.forward_migration_r1` 中已有回执，未执行数据库写入。
- 代码提交 `bf858f380` 已推送到开发分支。该核验补强的是两组数据迁移完整性；仍不补造旧 Schema 的历史删除收据，也不改变 S3 的 38 项历史 `DROP RESTRICT` 证据缺口。

### 2026-10-19 固定 Schema 迁移工具与测试消费者续修

- `migrate_v4_current_accepted_ingress_bindings_r1.py` 与 `migrate_v4_read_index_single_schema_r1.py` 将剩余关系名改为 `psycopg.sql.Identifier` 组合；ReadIndex R1/R2 guard 函数按固定合同定义，不再由字符串插值生成 DDL。`cleanup_v4_verified_legacy_schemas_r1.py` 仅接受零参数旧函数并用 `RESTRICT` 删除；遇到其他函数签名即 fail-closed。
- 仓库准入规则补充识别 Psycopg 的安全 Identifier/Literal 组合，同时继续拒绝不可信 SQL 文本与原始 SQL 字符串拼接。`tests/test_git_repository_policy.py` 与 `tests/test_v4_r7_sql_schema_compatibility.py` 合并执行 20 项通过；3 个迁移工具 AST 解析通过，暂存内容通过 `tools/git_repository_policy.py --staged`。
- 本项没有重跑已退役源 Schema 的迁移/清理写操作；当前开发库只读核验仍仅有 `v4`。代码推送提交为 `3e7e0df40`、`e3b03751d`、`d9a2b62fd`。历史 `DROP RESTRICT` 回执缺口和业务 Accepted/模块验收门保持原状态。

### 2026-10-19 注册迁移清单的单 Schema 冷启动续修

- 全面规范化当前 PG runner 的 55 个已登记迁移时，发现 `057_v4_schema_migration_ledger_r1.sql` 仍含历史 `v4_meta` 条件搬账语句，而 runner 仅对已在 ledger 的 057 跳过规范化；现役库因已有记录未暴露问题，但新库从零初始化会在 057 处被 `V4_SINGLE_SCHEMA_RETIRED_META_SCHEMA_REFERENCE_BLOCKED` 拒绝。
- 未改历史 SQL 字节或其登记 SHA。`scripts/apply_v4_phase0_schema.py` 现在仅对文件名与原始 SHA-256 `4c473184…af2d885` 同时匹配的该 057 文件做执行期 `SELECT 1` 规范化；实际旧 ledger 的复制、逐行校验已由 runner 在执行登记迁移前完成。文件内容任何变化都会 fail-closed。基础迁移 001 仍仅在受控初次部署时创建 `v4`，并执行期移除 `v4_meta` 创建与引用。
- `tests/test_v4_r7_sql_schema_compatibility.py` 现在遍历并规范化完整 55 项 runner 登记清单，要求 001 外的 SQL 不含 `CREATE SCHEMA` 或 `v4_meta`；057 哈希身份及被修改后拒绝路径也有断言。定向回归 `5 passed`。同轮独立只读审计确认 DB `market_research` / OID `646711` 唯一 V4 Schema 仍为 `v4`，55 项迁移都可被规范化，固定 workspace 定位抽样均返回 `v4`。
- 当前源码扫描中的 `workspace_schema()` 均汇聚到中央固定 `v4` 定位器；`physical_schema` 命中属于仅供迁移审计的历史表，`pg_namespace` 命中用于固定对象/触发器目录核验，没有 `pg_candidate_schema` 或按 `v4_forward_%`/`v4_research_%`/`v4_history_%` 扫描的现役 Reader。历史 FEP `028` 不在当前 runner 登记集，固定 FEP 表迁移 `068` 已登记；FEP E5 旧 ledger 适配器在 SQL 安装前 fail-closed。
- 机器证据与只读复验脚本保存在 `G:\codex_tmp\v4_live_schema_locator_audit_r1_20261019\LIVE_SCHEMA_LOCATOR_AUDIT_R1.json` 与 `audit_live_schema_locator_r1.py`。该项关闭的是迁移清单冷启动与固定 Schema 定位代码缺口；不改变当前库业务数据、Head 或生产状态，也不代表日更/模块 Accepted 通过。

### 2026-10-19 用户要求按最新已发布日补跑 10-14 至 10-16

- 在 `market_research` / OID `646711` / `127.0.0.1:5432` 现场核对 `v4.jobs_update_jobs_r1` 与 `jobs_update_job_days_r1`：最新 `PUBLISHED_FULL` 是 2026-10-13；10-14 为 `QA_BLOCKED`、attempt_count=2，原因为 `SOURCE_EXECUTION_FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED`；10-15 仍为 `QUEUED`、attempt_count=0。该“最新已跑至 13 日”指成功日更作业回执；正式 `publication_heads` 与 `operational_research_heads` 当前均为空，不能把作业回执误称为现存正式 Head。
- 按用户授权使用 10-16 官方 TDX 包 `c0ea0dff…32448219`，依项目 `TDX_LATEST_PACKAGE_TARGET_SESSION_V2` 提取并将三天目标行追加至固定 `v4.forward_facts`，每个候选都以精确 PG descriptor 再读回并核验 rows SHA：10-14 为 5,563 行（`d6d28030…a53587a`），10-15 为 5,565 行（`e8c68133…b87d73b1`），10-16 为 5,567 行（`da7d7fdf…d4ffd27`）。三项均为 `DIAGNOSTIC_ONLY`、`accepted_head=false`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`；10-15/10-16 为既存行的幂等读回，10-14 为新补充候选。
- 初次只读复核时，BaoStock PG runtime 回执精确存在于 10-15（5,226 日行情/22 因子，payload SHA `24682bbd…2bffc`）及 10-16（5,226/48，payload SHA `9c5e0c6d…b2f82d`），10-14 尚无回执。初次对 10-14 捕获在业务日期来源检查处返回 `OFFICIAL_SESSION_NOT_VERIFIED / PG_MARKET_CALENDAR_IDENTITY_REQUIRED`；后续诊断候选补采结果见本报告末尾，不把该回执误作外部来源批准。
- 10-16 capture-only 读取真实来源后，在 Head 校验处返回 `PG_ACCEPTED_OPERATIONAL_HEAD_REQUIRED_NO_FILE_FALLBACK`；普通 Catch-up 仍不能取得 `v4` Accepted 市场日历、Publication Head 或 Operational Head。10-13 的历史日更事件虽记载 `PUBLISHED_FULL`，事件引用的候选路径当前不存在，工作区仅存 10-09 Operational Head 文件；未用旧文件倒灌、覆盖或倒退开发 Head。故本轮已完成三天 TDX 输入的真实 PG 写入/读回，但 10-14→10-16 的完整 BaoStock→Owner→日更发布链尚未完成，不能报日更验收通过。数据库连接与写权限均正常；剩余门为 10-14 可批准的来源/交易日历、可验证的 10-13 开发 Head/Owner 链及原 Owner 守恒差异。
- 应用户要求再次对 10-14、10-15、10-16 分别调用完整 `execute_sources(..., 'CATCH_UP', capture_only=False)`；三日均在 Accepted PG 日历读取处返回 `PG_MARKET_CALENDAR_IDENTITY_REQUIRED`，尚未进入 Owner/发布阶段。随后以 `capture_only=True` 重跑：10-14 返回 `OFFICIAL_SESSION_NOT_VERIFIED`，10-15 和 10-16 在 PG Operational Head 检查处返回 `PG_ACCEPTED_OPERATIONAL_HEAD_REQUIRED_NO_FILE_FALLBACK`。最终只读复核显示 10-14→10-16 三个 TDX `DIAGNOSTIC_ONLY` 候选仍各有 5,563 / 5,565 / 5,567 行，15 日 BaoStock 5,226/22 与 16 日 5,226/48 回执存在；正式 Operational Head、Publication Head、Publication 仍各 0 行。该复跑没有将任何候选升级为 Accepted，也没有创建成功日更回执。

### 2026-10-19 日历诊断范围内的三日来源补采

- 按代码既有 `bind_dm01_calendar_for_diagnostic_candidate` 机制组合 PG Data Accepted Head 精确绑定的 789 日历与 R4 候选扩展，得到 2023-07-04 至 2026-12-31 共 850 个候选交易日；10-14/15/16 均在范围内。该上下文的 `production_admission=false`，扩展 2024-01-01 至 2026-10-16 的 673 个会话与当前 TDX 官方包内 SSE/SZSE 指数日记录完全相符，但 `formal_acceptance=NOT_GRANTED`。机器证据 `G:\codex_tmp\v4_calendar_extension_postcheck_20261019.json`；当前数据库 S0 目录快照 `G:\codex_tmp\v4_r7_live_s0_inventory_20261019_r1.json`。
- 在该候选上下文逐日调用 `execute_sources(..., 'CATCH_UP', capture_only=True)`。10-14 通过真实 BaoStock 公开匿名接口新增 PG `daily_runtime_acceptance` 回执，5,225 行日行情/22 因子，payload SHA `1a26b487…fa1f9d1e`；其 runtime manifest 标记 `ACCEPTED`，但 SDK schema 证据明确 `independent_external_acceptance=NOT_GRANTED`。10-15、10-16 分别读回现有 5,226/22 与 5,226/48 回执。三日都在 `verify_source_gate` 读取缺失的 `v4.operational_research_heads` 时停止，错误为 `PG_ACCEPTED_OPERATIONAL_HEAD_REQUIRED_NO_FILE_FALLBACK`；未生成 Owner、日更发布或正式 Head。
- 三日各自最新的源冻结件均以固定 path/SHA 通过 PG `read_bound` 精确字节读回：10-14 为 1,795,598 字节、SHA `3a387cbe…a7e1b6`；10-15 为 1,796,766 字节、SHA `20e056bb…047b028`；10-16 为 1,797,502 字节、SHA `4e8badb9…be8a3`。冻结件仍为 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`。这些是采集/存储链验收证据，不是 Jobs 成功回执或日更 Publication。
- 新鲜 RR/RO PG 目录快照仍仅有业务 Schema `v4`（`v4_*` 为 0）；正式 `market_calendar_sessions`、`publications`、`publication_heads`、`operational_research_heads` 与 Daily Core 发布表仍均为 0 行。最新 `PUBLISHED_FULL` 日更回执仍是 2026-10-13。补采后 `v4.forward_facts` 精确 9,344 行、总尺寸 6,263,750,656 字节；最大的只读遗留关系 `forward_legacy_evidence_r1` 为 8,394,104,832 字节，均由 G 盘 catalog delta `G:\codex_tmp\v4_r7_live_storage_delta_20261019_r1.json` 记录。本轮没有全表扫描或复制这些历史数据。


### 2026-10-19 用户纠正后的 10-14 至 10-16 日更入口复跑

- 对 10-14、10-15、10-16 再次调用完整 `execute_sources(..., 'CATCH_UP', capture_only=False)`。三日均在来源采集前由缺失的 PG Accepted 市场日历身份拒绝（`PG_MARKET_CALENDAR_IDENTITY_REQUIRED`）；未进入 Owner/Publication，也未写入新的 Jobs 成功回执。
- 随后按现有 `bind_dm01_calendar_for_diagnostic_candidate` 诊断入口逐日执行 `capture_only=True`。三日均完成来源冻结/PG 输入路径后，在缺失的 `v4.operational_research_heads` 处停止（`PG_ACCEPTED_OPERATIONAL_HEAD_REQUIRED_NO_FILE_FALLBACK`）。新鲜 `REPEATABLE READ READ ONLY` 复核 `v4.forward_facts` 中 BaoStock 回执 SHA 均匹配：10-14 为 5,225 行/22 因子（`1a26b487…fa1f9d1e`）；10-15 为 5,226/22（`24682bbd…2bffc`）；10-16 为 5,226/48（`9c5e0c6d…b2f82d`）。这些是已写入并读回的来源事实，不等同正式日更。
- 日更 Job 表现状仍为 10-14 `QA_BLOCKED`（attempt_count=2，Owner/lifecycle 守恒差异）、10-15 `QUEUED`（attempt_count=0），无 10-16 日的 Job Day；正式市场日历、Operational Head、Publication Head、Publication 仍均 0 行。未构造 predecessor 或伪造 `PUBLISHED_FULL`。完整入口结果和采集复跑结果分别记录于 `G:\codex_tmp\v4_daily_catchup_user_rerun_20261019.json`、`G:\codex_tmp\v4_daily_capture_user_rerun_20261019.json`。

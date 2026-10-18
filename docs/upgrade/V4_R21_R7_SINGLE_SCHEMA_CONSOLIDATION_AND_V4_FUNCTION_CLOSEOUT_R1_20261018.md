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

## 阶段结果

| 阶段 | 结果 | 证据与范围 |
|---|---|---|
| S0 真实对象、消费者和权限盘点 | PASS | 合并前只读快照为 76 个 V4 物理 Schema；2026-10-19 最终只读快照确认 DB OID 646711、`127.0.0.1:5432`、只读事务开启，现只剩 `v4`。完整最终快照在 `G:\codex_tmp\v4_single_schema_inventory_20261019.json`。 |
| S1 停止动态 Schema 生成 | PASS | `workspace_schema()` 固定返回 `v4`；应用连接拒绝任何其他 Schema；Schema 创建边界拒绝非 `v4`；Alias 注册禁用；旧 Shadow 写入/导出在访问数据库前关闭。 |
| S2 固定表结构 | PASS | 最终目录中 232 个关系对象、57 个例程、86 个类型、123 个非内部触发器，均在 `v4`。这些触发器是现役版本化表的约束，不是旧 Schema 残留。 |
| S3 精确迁移与旧 Schema 清理 | PASS | 只读目录确认 `v4_*` Schema 为 0，跨 Schema 目录依赖为 0。所有删除使用 `RESTRICT`。Forward 映射 11 个来源 Schema 的 9,256 条精确映射均为 `VERIFIED`。 |
| S4 全部运行时消费者切换 | PARTIAL | 主研究、股票图表、板块成员、Focus/Forward、诊断、Owner 精确 SourceIngress、日更仓储均经唯一 `v4` 边界；历史引用只通过固定表中的精确迁移回执解析。Native Shadow 仍 fail-closed，尚未迁入统一存储。 |
| S5 全模块续修 | PARTIAL | 可执行的消费者修复和 28766 浏览器检查已推进。候选快照未发布为正式 Head；缺少接受交易日历及若干模块历史输入，不能将候选可读视为模块验收完成。 |
| S6 DB-01..12 与 28766 浏览器验收 | PARTIAL | 已完成的受控数据库及浏览器检查见下表；待到期、PIT 历史、日更作业回执和真实上游输入仍未满足全部验收门。 |

## PostgreSQL 迁移与核验

- 只读事务实测：数据库 `market_research`，OID `646711`，端口 `5432`，`transaction_read_only=on`，隔离级别 `repeatable read`。本机 PostgreSQL 子进程不是多个数据库实例。
- 最终 Schema：合并前的 76 个 V4 物理 Schema 收敛为 `v4` 一项；75 个旧 V4 Schema 已清理；`v4_*` 为 0；目录跨 Schema 依赖为 0。旧 Schema 清理未用 `CASCADE`。
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
| DB-01 | PASS | 当前只读 RR 事务实查唯一 V4 业务 Schema 为 `v4`，`v4_*` 为 0；Research 双 Release 写读回并回滚；单 Schema 守卫拒绝非 `v4`。 |
| DB-02 | PASS | 两个 Research Release 分别在固定 `v4` 表中读回；descriptor、T0、release_id 和内容摘要经验证，不跨版本混读。 |
| DB-03 | PASS | RAW/QFQ Series、多日 Journal 固定表正向样例读回并回滚；错 T0/缺版本校验 fail-closed。 |
| DB-04 | PARTIAL | Forward 数据按 namespace/run/T0 使用固定 `v4` 表并保留旧键碰撞身份；Focus 历史到期/自动写入与完整成熟 outcome 尚缺真实验收输入。 |
| DB-05 | PASS | 75 个旧 V4 Schema 逐项有退役矩阵并 `RESTRICT` 清理；Forward 9,256 条精确映射回执为 `VERIFIED`，本轮另完成当前 Data Head 30 条原始绑定的字节级读回。无 `CASCADE`。 |
| DB-06 | PASS | Research 旧 descriptor 原始字节/SHA 保留；固定 `v4.research_releases` 记录旧 Schema、旧 digest 与新 release/manifest 的对照，迁移不伪称旧/新 descriptor digest 相同。 |
| DB-07 | PASS | 所有现役连接入口固定 `v4`；28766 的首页、Forward 来源审计页实际读取固定 `v4` PG 候选 Release；缺失来源仍明确 fail-closed。 |
| DB-08 | PARTIAL | 四日 Core 独立 Oracle（09-28、09-29、09-30、10-08）已有 0 error 结果；四日完整 Sector/Focus/Market/Forward 数值闭环受 10-08 PIT、前序成员和成熟结算来源缺失阻断。 |
| DB-09 | PARTIAL | 当前 Data Head 的 30 项精确 Path/SHA/bytes 绑定共 60,488,930 字节均在 PG 读回相等；未复制 551 MB TDX ZIP Base64，且历史 1,678 项未导入。超 64 MiB 的整包 typed/chunk SourceIngress 未在本轮执行端到端验收。 |
| DB-10 | PARTIAL | 日更和 Jobs 只读/幂等路径可运行；`market_calendar_sessions` 与正式 publication Head 为空、没有 worker 回执，故不签发 Accepted/DEV Head、不宣称重试/增量真实作业通过。 |
| DB-11 | PARTIAL | 仓库唯一、28766 单槽已复核。旧 baseline、治理恢复证据及其他历史目录经实际计量；存在未提交/独有内容或不可替代恢复证据，保留，物理工作区清理未完成。 |
| DB-12 | PASS | 当前库目录仅 `v4`，交叉 Schema 依赖 0；最终目录核对 232 关系、57 例程、86 类型、123 触发器。Schema owner 为 `postgres`、ACL 为默认值；目录中只有 `postgres` 登录角色有 `v4` USAGE/CREATE，已退出的 closeout 登录角色均为 false。系统 Schema 未改动，所有迁移删除为 `RESTRICT`。 |

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

**当前结论：** 单 Schema 数据架构与物理清理已通过；候选读取与一部分功能页可用。全模块真实数据验收尚未完成，阶段状态维持 `PARTIAL_DATA_AND_MODULE_ACCEPTANCE_OPEN`。

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
- 单独审计的 9 个 `__pycache__` 目录共 30 个 `.pyc`（513,843 字节），均为可重建缓存；递归删除这些缓存的命令被执行工具策略拒绝，故没有文件被删除。DB-11 Workspace 物理清理保持 `PARTIAL`，须保留该工具拒绝事实，不能把缓存核验计为已清理。
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

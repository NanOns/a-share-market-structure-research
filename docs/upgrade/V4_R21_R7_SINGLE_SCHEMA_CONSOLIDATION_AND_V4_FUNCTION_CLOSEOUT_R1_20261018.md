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
| DB-11 | PARTIAL | 仓库唯一、28766 单槽已复核。`G:\codex_tmp\r7_active_baseline_20261015` 含未提交代码和未跟踪 data/docs/runtime，存在路径过长项且无进程使用；因其内容未证明可重建而保留，物理工作区清理未完成。 |
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

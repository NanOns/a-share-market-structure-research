# 大A V4｜R4 第二批工程成果独立外部增量复审 R2

> 版本：R2 / 2026-10-11（北京时间）  
> 性质：独立外审结论与下一轮整改入口；不是生产切换许可。  
> 目标仓库：`NanOns/a-share-market-structure-research`  
> 隔离候选分支：`codex/r4-pg-only-20261011`  
> **本次冻结 HEAD：`14a4b61876ce64f77f001623d0b13554da2744a2`**；上一轮审计 HEAD `5f67ce474d0b1ed474a8b8bb02b8e794df10629e`；新增6提交、89个变更文件。  
> 指定正式目标分支：`codex/v4-fp14-r2-repair`，截至审计仍为 `fbd23a6ba08d0948fe7ad421d1765fe363648522`，**本轮代码未合并**。  
> 上位合同：`V4_R4_CONSOLIDATED_EXECUTION_MASTER_PG_ONLY_20261011.md` 和 `V4_R4_PG_ONLY_INDEPENDENT_EXTERNAL_AUDIT_R1_20261011.md`；范围限定 **V4 实际业务及可达依赖、PostgreSQL-only**，不执行/计入独立 V3 与更早历史产品测试。  
> **唯一总状态：`EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE`。**

## 0. 本轮已核实证据及审计方法

1. 先查 Drive 正式项目任务夹：最新已有的是上轮外审报告，尚无本次 Codex 第二批的独立 Drive 归档。再查隔离分支及正式目标分支 HEAD、GitHub compare、全系统审计当前入口。
2. 阅读 `docs/audits/r4_external_repair_20261011/REPAIR_REPORT.md`、`docs/audits/r4_external_repair_batch2_20261011/REPAIR_REPORT.md`、`BATCH2_DISPOSITION.json`、`STAGE_ENTRY/EXIT.json`、`SHADOW_CAPABILITY_SCOPE.json`、四表迁移、字段溯源、Focus 身份、默认产品 HTTP 回执、JUnit、逐节点台账及实际源码。
3. 独立查看 `src/workbench_db/v4_shadow_pg_r1.py`、`v4_snapshot_pg_r1.py`、`v4_native.py`、`v4_history_pg_r1.py`、`src/workbench_service/shadow_context.py`、`core_product_bff_r1.py`、`core_product_server_r1.py` 和 `scripts/migrate_r4_old_snapshot_exact.py`，核对错误边界、身份语义、迁移流程和负例。
4. 仅能复核 GitHub 远端源码、证据文件以及回执的内在逻辑；**未在用户 Windows/G盘实机重跑60项用例、未连接本机隔离 PG/在役 PID、未亲自浏览器交互或重新计算740703个字段差异**。因此“60 PASS”“全表摘要零差异”定性为**源码和原始收据支持的范围内工程证据**，而不是本人重执行结论。
5. 本轮未修改代码、TDX、在役 Head、生产数据库或 Git 分支。

## 1. 增量审计总览

| 事项 | 第二批证据主张 | 独立判定 | 仍缺什么 |
|---|---|---|---|
| R4-E01 / Shadow异常 | 删除未绑定 `sqlite3.Error`；`psycopg.Error` 负例映射 | `PASS_SCOPED_CODE_AND_RECEIPT` | 真实历史 first-observed 与外部授权 |
| DB12 / Shadow原生 PG | 原生不可变 PG 导出、REPEATABLE READ + READ ONLY、descriptor/fact/hash/context/quality 验证 | `PASS_SCOPED_ENGINEERING` | 真正 accepted Shadow 来源、角色/权限、生产消费者准入 |
| V4-only Shadow测试 | 60 PASS、0 FAIL、0 ERROR、0 SKIP，原 V3 `app.py` AST 三节点单独处置 | `PASS_BOUNDED_CAPABILITY_ONLY` | 合法 V4 全部用例分母仍 NULL，不能替代全量 |
| R4-E02 / 默认产品HTTP | 一个真实冻结证券×一个 T0×D/W/M×RAW/QFQ 6种图表，六产品路由，token/SQLite负例 | `PASS_SCOPED_DEFAULT_HANDLER` | 五 T0、跨证券、多大小/浏览器、合法周期、容量、正式 PG authority |
| R4-E03 / 新投影字段差异 | 740,703 个差异全部有源及规则分类，未解释0 | `PASS_EXPLANATION_NOT_ADMISSION` | 新语义采纳、原始质量合理性、正式消费者、Amount A 及PIT |
| R4-E03 / Focus身份 | 469实体、328个变更ID，解释为 `UNKNOWN` 质量订正，episode_id/T0/end_date/parent不变 | `PASS_EXPLANATION_NOT_IDENTITY_GRANT` | 正式ID迁移合同、消费者重建、历史及CAS验证 |
| R4-E03 / 旧出版物四表 | 6337 objects / 12106 aliases / 50162 members / 1 metadata，旧读进程与 PG 全表摘要零差异 | `PASS_SCOPED_STORAGE_EQUIVALENCE` | 正式绑定、Series、联合CAS/回滚、长期存储身份硬化 |
| R4-E04 / 全量回归 | 独立 Shadow 能力60项，三旧AST/compat节点逐节点解释 | `GLOBAL_DENOMINATOR_OPEN` | 原4568台账中所有V4真实依赖、失败、跳过和合法排除逐项终结 |
| R4-E05 / 保护门 | 两个正式 Head SHA 和旧 research.sqlite SHA 前后一致 | `PASS_SCOPED_PROTECTION` | 全历史保护基线、硬链接多进程强制只读、未消费深层依赖 |
| 生产合并/加载 | 修复仅在隔离分支，未换当前 authority / PID | `NOT_ADMITTED` | 用户许可及独立正式验收 |

## 2. 核对过的客观数值

- 最新批次能力测试 `r4_batch2_capability.xml`：`tests=60, failures=0, errors=0, skipped=0`；本次读取的是原始JUnit而非仅依赖 README 叙述。60 是独立的小范围能力分母。
- 当前默认产品处理器的六组图表返回 `200 / READY`：D RAW、D QFQ 各420条历史总记录（请求最多取120）；W RAW、W QFQ 各91；M RAW、M QFQ 各22。其独立旧图表 oracle 报六组 **0 差异**。冻结 trade_date `2026-10-09`，一个证券 `SEC-00096141BD5420F5CB3120E687CDA5B9`。另外产品路由 home/stocks/sectors/focus/events 为 `200 READY`，forward 路由仅为 `200 SOURCE_INCOMPLETE`，不能说 Forward 功能完成。
- 旧出版物直接迁移四表分母：**6337 / 12106 / 50162 / 1**，读取旧 SQLite 的 oracle 子进程明确使用 `mode=ro&immutable=1`，检查源SHA并输出行级规范摘要；PG 回读用相同 ORDER BY、JSON 规范化和逐表 hash 对照；源前后哈希一致。这比仅比数量更强，但仍属于**单个旧出版物的有界数据存储等价**。
- 新投影与旧已接受版本的字段差异合计 **740,703**：板块分母投影5670、原始换手金额等10426、哈希绑定单位投影688116、股票分母26065、字面 UNKNOWN 质量修正10426；上述五类合计一致。**规则分类为零未解释**不等于新结果已被批准。
- Focus：469个实体无增删、328个ID因字段质量变化而不同；业务身份关键字段在登记范围未发生变化，但内容哈希变化有版本含义，不得悄悄把旧ID映射覆盖。
- 当前保存的两个生产 Head 和旧快照文件哈希未变；未能证明运行期全部G盘挂接硬链接/10,171保护对象的原字节完整性。

## 3. 新增需要治理的实现风险（R4-EXT-R2-01）

**级别：P1，架构身份硬化缺口；不是对本轮四表迁移数值的否定。**

`src/workbench_db/v4_snapshot_pg_r1.py:31–38` 的 `Builder.seal(meta)` 用 `sha256(json.dumps(meta))` 生成 `snapshot_identity.digest`，随后 `read(descriptor)` (`:47–52`) 只核对该行的元数据摘要与契约ID。**这个 `logical_digest` 没有直接涵盖 objects、aliases、members、metadata 四表全量行内容**。普通 DML 的触发器有一定不可变性约束，但触发器不等于内容哈希证明；跨备份/恢复、管理员DDL、迁移错误或者物理故障后的内容偏离，单靠这个标识不能实现全表内容寻址。

本轮独立迁移脚本确实另外计算了四表完整摘要并对照成功，所以不应将其迁移PASS改成FAIL。但在**正式切换的封存及恢复**阶段应：

1. 版本化加入四表按规范列序/类型/NULL/JSON单位的 canonical row digest，绑定表分母、manifest身份、source SHA 与 PG descriptor（必要时使用总 Merkle/root digest），不可只hash metadata。
2. seal完成后以及正式发布/恢复时执行独立验证；未达到值一致时fail-closed，防止对象内容不等却沿用同一个 `logical_digest`。
3. 建立差异、失败回滚、部分表缺失、内容篡改、schema串错、跨PG库/数据库身份切换的负例；考虑新描述符版本，不原地修改旧接受 digest/Head。
4. Shadow PG descriptor也应明确服务器/数据库实例身份、最小角色权限及跨实例恢复合同，目前只凭schema和logical_digest无法完成完整基础设施来源证明。此项是准入硬化，不能因现有64位SHA值就声称自动满足。

直接源：`https://github.com/NanOns/a-share-market-structure-research/blob/14a4b61876ce64f77f001623d0b13554da2744a2/src/workbench_db/v4_snapshot_pg_r1.py#L31-L52`。

## 4. V4-only 测试范围复核

- 本批明确排除且保留原件的三个 `test_v4_17_shadow_ui.py` 节点，是旧 `workbench_service.app` / V3 AST保持不变或旧V3 HTTP页面兼容的义务；报告提供 V4 原生替代测试 `test_v4_shadow_pg_r4.py` 的 HTTP/非法写/合同阻断。**这三个具体排除理由有当前V4调用路径证据，范围内可以支持**，不等于其余历史失败都可以按目录或名称剔除。
- 测试台账没有将两个相异的定向suite同原4568节点简单相减；全V4合法分母继续记 `null`，这是合规的克制。下一轮必须完成 real V4 reachability graph × normative capability matrix × exact selected node IDs，同时针对PG-only用例实际clean rerun、保存JUnit及无法运行的具体原因。
- 不对旧V3和更早工作台做泛化全回归；若 V4 当前代码真实调用旧位置函数，应只迁移和验证那部分V4义务。

## 5. 仍然必须继续开发，不必等交易日

**P0（可以立刻并行）**

1. DB01–DB09及DB12剩余真实运行时路径闭环：自动日更实际executor/Windows恢复、Series/Journal真实消费者、research snapshot全部消费者、FEP/Forward相关PG存储；最终生产路径必须无SQLite/DuckDB可达业务数据库，保留独立冻结oracle不算生产违例。
2. 完成 PG Snapshot/Series/Journal 及联合Head的CAS并发、失败恢复、回滚、旧版本完整性、外部源与DB digest绑定；补充本报告 `R4-EXT-R2-01`。
3. 默认产品路径扩大为五个真实冻结T0、跨证券跨行业、D/W/M/RAW/QFQ/分页/复权/无数据/别名变更，六入口浏览器与并发/容量，保持旧 Head 直到另批次授予。
4. 建立唯一V4测试分母；从原4568账逐节点推进，而不是把60或之前103项定向PASS冒充总体PASS；不运行V3独立旧测试。
5. 精确复权系数 typed transport × 所有真实可达消费者（历史、板块、Focus、Forward），复核RPS及来源PIT；FA-009全语义需求分母与FA-012原生有效PIT日期，避免数值样本通过泛化正式解锁。
6. 将本次Codex两批工程 `REPAIR_REPORT`、关键测试摘要与SHA清单补齐同一Drive正式任务文件夹并读回；GitHub仅有证据不满足项目“自动正式Drive归档”的交付规则。

**等待事实或另行准入（不得阻断以上P0）**

- 2026-10-12及之后真实交易日数据首获、新文件PIT/first observed、真正新交易日更新；不能预造。
- Forward/FEP真实成熟样本和OOS统计门；当前60项合成场景不能计为真实Shadow Grant。
- 真实Windows安装/重启/托盘/登录验证和在役PG切换，需用户正式允许、维护窗口、备份回滚/独立验收；本审计不授权。

## 6. 结论与恢复入口

- 相比上一轮，Shadow未定义异常和PG reader已从明确缺陷升级为**范围内源码+回执支持修复**；默认产品已经具备一只证券/一个T0的真实Handler隔离PG验证；旧出版物四表无损迁移已获较强受限证据。
- **不能**宣布R4完成、PG-only生产全链通过、正式原快照已接管、五日图表全测、性能PASS、全V4回归绿色或Shadow/FEP已授权；差异分类、局部测试、push均不能替代正式门。
- 本次新增 `R4-EXT-R2-01` 内容寻址身份不充分问题，须在下一批正式设计与源码修复中关闭。
- **唯一总状态 `EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE`。建议保持隔离分支推进、逐批留证，再作独立外审和经过授权的生产切换。**

审计入口：`docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md`；新批次 `docs/audits/r4_external_repair_batch2_20261011/REPAIR_REPORT.md`、`BATCH2_DISPOSITION.json`、`r4_batch2_capability.xml`、`EXACT_OLD_SNAPSHOT_RESULT.json`、`FIELD_PROVENANCE_SUMMARY.json`。

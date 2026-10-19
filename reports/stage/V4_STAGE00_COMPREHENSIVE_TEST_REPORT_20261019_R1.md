---
stage_id: V4-00
code_sha: e21849b21226d364d4f79678d416126e58ffb5b1
test_scope: V4-00A-H、R3 PG-only合同纠偏、定向测试与只读数据库核验
conclusion: STAGE00_REPAIR_PARTIAL
approval_status: USER_AUTHORIZED_STAGE00_ONLY
---

# V4 阶段00｜清理后基础能力恢复与八子阶段验收

日期：2026-10-19。本文是阶段00唯一当前报告；不表示阶段01开始、V4业务验收通过或生产切换。

> R2 独立审计纠偏于 2026-10-19 追加在文末。该 R2 结论是 A–H 与阶段00准入的当前权威状态；文中原 R1 状态仅保留为审计历史，遇到冲突以 R2 为准。R2 代码提交：`da5b72f0e`。

## 一、现场与授权

- 唯一仓库：`G:/codex work/大A交易`；分支：`codex/v4-workspace-cleanup`。
- 开始 HEAD：`720ffc92c6e4ffefd86c1c212ed82a21545eb733`；开始时工作区无未提交改动，远端跟踪分支与本地 HEAD 一致。
- 环境：Python 3.13.14（`E:/python/python.exe`）、pytest 9.1.1、`PYTHONPATH=src`；测试缓存、临时目录均位于 `G:/codex_tmp/test_temp`。
- 本轮授权限阶段00修复、定向测试、只读数据库核验、开发分支提交推送及更新 Draft PR #3。没有改变用户既有 ignored 项；其中包括本地安全配置 `config/.env` 和原样备份 `config_back/`、`script_back/`。
- 未运行来源批量采集、未启动28766或28765、未触发 GitHub Actions；未执行任何数据库写入、DDL/DML、迁移、大表操作、Head 切换或生产部署。

## 二、八子阶段真实验收

当前 `src/v4/contracts/phase0_gate.py` 与恢复的 `v4_phase0_final_gate_v1.json` 明确列出 A–H、三项必需 scope Owner 及 E 对 RAW 的派生责任；它们没有为 A–E 提供完整的独立子阶段标题/需求到函数的注册表。下表不补造这些缺失名称；对照具体必需能力列出可追溯入口。静态/夹具测试不能代替真实来源和业务结果验收。

| 子阶段 | 当前目标、关键入口及消费者 | 实际证据和限制 | 状态 |
|---|---|---|---|
| V4-00A | 现行 gate 将其列为必需阶段；当前仓库没有找到更细的 A 目标、Owner、专属输入输出或收据映射。下游为阶段00总 gate。 | 源码和配置只证明阶段 ID 存在，不能证明原业务目标已验收。 | `NOT_VERIFIABLE` |
| V4-00B | 身份生命周期 Schema；`src/workbench_db/migrations/v4_postgres/010_security_lifecycle_history_r5.sql` 至 `012_provider_lifecycle_fact_r6_2.sql`；V4-01 消费 `LIFECYCLE_SCHEMA`。 | 只读目录确认 `security_lifecycle_history` 有记录、`security_lifecycle_facts` 无记录；没有对应已确认的身份/生命周期范围收据。迁移未执行。 | `BLOCKED` |
| V4-00C | Publication 身份；`src/workbench_db/v4_publication_candidate.py`、`src/workbench_db/v4_publication_reader.py`；V4-01 消费 `PUBLICATION_IDENTITY`。 | 只读 PostgreSQL 中 `model_namespaces=0`、`publication_heads=0`。发布身份能力当前没有可验收的 namespace/head。 | `BLOCKED` |
| V4-00D | A 股通达信来源；`src/v4/contracts/source_overlap.py`、`src/workbench_analysis/tdx_local_snapshot.py`、来源包/修订入口；V4-01 消费 `A_STOCK_TDX_SOURCE`。 | `source_packages` 表存在但为空；`source_revisions` 有记录不能单独证明其为已接受、完整的 TDX 来源包。本轮没有读取/导入真实行情或官方包，也没有确认沪主板、深主板、创业板、科创板完整覆盖。 | `BLOCKED` |
| V4-00E | RAW bootstrap；Owner 为 E，由 gate 从全部必需阶段及 B/C/D Owner scope 派生；V4-01 消费 `RAW_BOOTSTRAP`。 | DM01 Data Head 表有记录，但这不等同于已验收 RAW 输入或 Publication Head。其余必需 Owner scope 未满足，RAW 派生保持阻断。 | `BLOCKED` |
| V4-00F | BaoStock 补充来源；`config/baostock_supplemental_contract_v1.json`、`tests/v4_phase0/test_baostock_supplemental.py`；补充来源为可选消费者。 | 合同及夹具通过；合同状态仍为 `PUBLIC_ROUTE_B1_OPERATIONAL_FIELD_BINDING_PENDING`。未访问在线源，不声称实时或完整来源通过。 | `DEGRADED_PASS` |
| V4-00G | 算法合同及参数框架；`src/v4/contracts/algorithm_contract.py`、恢复的框架/参数注册配置及对应合同测试。 | 合同解析和夹具验证通过；配置仍注明模块合同待补齐，参数为候选而非发布值。没有更改算法、数值阈值或 MA5/20/60 口径。 | `DEGRADED_PASS` |
| V4-00H | 阶段聚合、能力切换与性能记录；`evaluate_phase0`、`config/v4_capability_cutover_policy_v1.json`、`config/v4_performance_measurement_contract_v1.json`。 | Gate 规则测试通过。标记相对基准阈值未定、若干 V4 性能指标未实现；合同规定阶段00不因空性能测量阻断。`scanner_permission` 仍为 `NOT_APPLICABLE_UNTIL_V4_05`。 | `DEGRADED_PASS` |

## 三、V4-01 必需范围及聚合结果

| Scope | 指定 Owner | 本次核对 | 最终状态 |
|---|---|---|---|
| `LIFECYCLE_SCHEMA` | V4-00B | 生命周期表存在，但 facts 为空且未取得经确认的目标范围身份/生命周期收据。 | `BLOCKED` |
| `PUBLICATION_IDENTITY` | V4-00C | `model_namespaces` 和 `publication_heads` 均为0行。 | `BLOCKED` |
| `A_STOCK_TDX_SOURCE` | V4-00D | `source_packages` 为0行；修订记录不等价于已接受且四板覆盖通过的 TDX 包。 | `BLOCKED` |
| `RAW_BOOTSTRAP` | V4-00E | 只由全部阶段与前三个 Owner scope 满足后派生；当前不得单独声明授权。 | `BLOCKED` |

使用上述真实数据库状态和阶段限制输入现役 `evaluate_phase0` 聚合，结果为 `phase0_status=BLOCKED`、`v4_01_entry_permission=BLOCKED`、`raw_bootstrap_permission=BLOCKED`；四项必需 scopes 全部列入 `blocked_required_scopes`。非阻断限制不替代真实 Owner 证据。合成 gate 测试只验证规则，不是本轮业务验收收据。

## 四、修复与精确恢复

1. 将 `src/workbench_analysis/tdx_local_snapshot.py` 改为默认仅做受控文件快照和本地摘要校验；PostgreSQL manifest 写入需要显式 `persist_to_pg=True`，读取绑定需要显式 `require_pg_binding=True`。本轮调用默认路径，未连接该写入接口。
2. `tests/v4_phase0/test_tdx_local_snapshot.py` 增加禁止默认调用 PG 读写函数的回归；`tests/v4_phase0/test_phase0_final_gate.py` 增加相同阶段证据重复聚合的确定性检查。
3. `tests/runtime_isolation.py` 原来要求配置文件第一个字符就是 `tdx:`，且未剥除 UTF-8 BOM；现有 `config/paths.yaml` 以注释开头并含 BOM，导致测试隔离插件在收集阶段失败。现在按 UTF-8-SIG 读取，并检查顶层 `tdx:` 键，继续要求且只允许一个显式来源根。
4. 从忽略 Git 的本地备份逐文件精确恢复下列必要测试/合同依赖；目标文件 SHA256 与备份逐项一致。未复制整个目录，未读取/打印安全配置：
   - 阶段00 gate/政策/性能测试依赖：`config/v4_phase0_final_gate_v1.json`、`config/v4_capability_cutover_policy_v1.json`、`config/v4_performance_measurement_contract_v1.json`。
   - 活跃测试隔离与历史测试边界依赖：`config/dm01_go_forward_runtime_contract_r4.json`、`config/v4_frozen_test_profiles_remainder_v1.json`、`config/v4_18_migration_replay_contract_v1.json`、`config/v4_frozen_test_profiles_full_closeout_r1.json`、`config/v4_historical_moving_head_registry_r17_v1.json`、`config/v4_legacy_api_test_profiles_remainder_v1.json`、`config/v4_legacy_identity_test_profiles_remainder_v1.json`、`config/v4_unavailable_v3_historical_receipts_r3.json`。
   - 阶段00/01合同回归依赖：`config/v4_algorithm_contract_framework_v1.json`、`config/v4_parameter_registry_v1.json`、`config/v4_01_history_lineage_policy_v1.json`。
   - 被多个当前 PostgreSQL 合同/DSN 测试导入或静态检查的迁移入口：`scripts/apply_v4_phase0_schema.py`。本轮只导入/编译/静态检查，未运行 `apply()`。
5. `src/workbench_db/migrations/v4_postgres/001_v4_phase0_foundation.sql` 的历史字节含 `v4_meta`，且被迁移入口显式登记。恢复入口中的 `normalize_migration_schema` 仅对精确 foundation 文件把旧 ledger 路径改写到 `v4`，阻止其他迁移创建额外 Schema；现有静态测试覆盖该改写。没有执行 SQL、创建 `v4_meta` 或迁移数据库。
6. 未恢复 `config/v4_current_stage_authority_v2.json` 指向的旧 `data/`、`reports/` 内容；没有把历史阶段文件作为真实 Head。

## 五、验证结果

- `PYTHONPATH=src python -m pytest -q tests/v4_phase0 --ignore=tests/v4_phase0/test_postgres_schema.py --basetemp G:/codex_tmp/test_temp/stage00_phase0_final_20261019`：**106 passed**。覆盖 gate owner/阻断、身份分类、四板与 BSE 分离、来源包身份/重叠、TDX 快照和算法合同夹具；这些是独立软件/夹具证据，不是实时行情完整性证明。
- `python -m pytest -q tests/test_v4_r7_sql_schema_compatibility.py --basetemp G:/codex_tmp/test_temp/stage00_schema_20261019`：**5 passed**，包括单 Schema 迁移规范化静态测试。
- 对 `tests/v4_phase0/test_postgres_schema.py`：**未运行**，记为 `DB_WRITE_TEST_NOT_AUTHORIZED`；其中含 PostgreSQL INSERT/rollback。rollback 不能替代授权。
- `python -m compileall -q src/v4 src/workbench_analysis/tdx_local_snapshot.py scripts/apply_v4_phase0_schema.py tests/v4_phase0 tests/runtime_isolation.py`：通过；字节码缓存重定向到 G 盘临时目录。
- `git diff --check`：通过。
- 额外扩展检查的真实结果：`tests/test_v4_pg_publication_contract_static.py` 与 `tests/test_v4_r7_sql_schema_compatibility.py` 合跑为 **15 passed、2 failed**；两项失败只因缺少仓库外/当前设计树中已不存在的 `docs/design/sql/V4_PUBLICATION_OWNER_BINDINGS_CANDIDATE_R3.sql`，未恢复此非阶段00设计草案。另 `tests/test_v4_native_reader_dsn.py` 与 `tests/test_v4_universe_pg_r1.py` 在收集时分别缺少非本阶段入口 `scripts.apply_pg_runtime_heads_v1` 和 Python 依赖 `cryptography`；这两项不计为阶段00通过，也未为此扩展恢复脚本/安装依赖。
- PostgreSQL 使用显式只读事务及3秒 statement timeout核验：数据库 `market_research`；`v4` Schema 和相关表存在；`publication_heads=0`、`model_namespaces=0`、`operational_research_heads=0`、`market_calendar_sessions=0`；`source_packages` 无记录，`source_revisions` 有记录；`security_lifecycle_facts` 无记录、`security_lifecycle_history` 有记录；DM01 Data Head 表有记录。该核验没有扫描大表或读取业务 payload。

## 六、工作包验收、遗留与结论

| 顺序工作包 | 结果 | 说明 |
|---|---|---|
| S00-A 冻结现场和断链定位 | `PASS` | 基线、ignored 保护边界、当前缺失调用及精确恢复对象已核实；A–E 更细目标在现役材料中缺少映射，已标为不可验证。 |
| S00-B 八子阶段规则/入口修复 | `PARTIAL` | 缺失静态依赖已恢复，TDX 快照默认 PG 副作用已去除；真实四板来源、生命周期、Publication 与 RAW bootstrap 没有接受证据，未伪写 PASS。 |
| S00-C 聚合和 V4-01 准入 | `PASS_WITH_BLOCKED_RESULT` | 现役 gate 及其回归工作；真实状态给出 BLOCKED，不能准入 V4-01。 |
| S00-D 安全验证 | `PARTIAL` | 无写测试、编译、静态和只读检查完成；写入型 DB 测试和超出阶段范围的失败收集测试未执行/未通过。 |

**阻断阶段00本能力：** A–E 原始子目标/证据映射不完整；V4-01 四项必需 Owner scope 当前均未获真实接受，当前 Phase0/V4-01 gate 为 BLOCKED。下一步应先补齐可追溯的真实来源、身份/生命周期及版本证据，再重新验收本阶段；不得直接跳到阶段01。

**转交后续具体阶段：** BaoStock live route/field binding；参数从候选到正式值、模块算法合同覆盖；性能采样及可选 benchmark threshold；migration 入口与其余迁移的专项设计。保持既有算法，不做全域重写。

**需单独授权：** PostgreSQL 写入型测试、Schema 迁移、Head/Publication 切换、大表处理及生产部署。以上均未执行。

最终结论：**`STAGE00_REPAIR_PARTIAL`**。阶段00已修复部分清理后断链并通过受控代码验证，但真实业务必需范围仍阻断，未形成阶段00 PASS 或 V4-01 准入。

实现代码与精确恢复文件提交：`052baa28400a95035946f94c361501891971ef89`。本报告随后作为单独文档提交；最终分支 HEAD（包含本报告提交）另在 PR #3 评论与交付回报中给出。此报告不授权恢复日更、阶段01或生产运行。

## 七、R2｜独立审计纠偏与定向续修（当前权威结论）

本节按任务卡附录“阶段00 R2｜独立审计纠偏与定向续修”执行；不重复 R1 的恢复和修复，不恢复历史文件，不运行 overlap、不执行数据库写入、DDL、迁移或 Head 切换。原 R1 对 B/C 将空运行表等价为能力缺失的结论已由本节更正；D/E 的真实数据阻断继续保留。

### R2 原始目标溯源与合同/运行态分离

通过 Git 历史 `a4b3412b3` 找到旧正式记录 `docs/V4_00A_BASELINE_FREEZE_20260925.md` 至 `docs/V4_00E_HISTORICAL_ADJUSTMENT_COORDINATES_20260925.md`，确认原始目标如下；这些文件只作 Git 来源证据，不恢复到工作树：

- **00A**：REV2 §78，冻结 HEAD、数据库备份/恢复回执、accepted/Focus Head、旧输出和继承审计；原记录状态为 `DEGRADED_PASS / BASELINE_IDENTITIES_FROZEN_RECOVERY_EVIDENCE_OPEN`。历史报告明确当前 PG 的备份/恢复证据未闭合。
- **00B**：REV2 §5.1–5.3、§6A、§7.10、§78；日期有效身份、知识时间、历史覆盖与不支持范围。当前 Universe 不冒充 PIT Universe；旧正式记录将 PIT 历史身份标为不可用，并将阶段判为 `DEGRADED_PASS`，而非因缺少数据行判定 Schema 不存在。
- **00C**：REV2 §4.1–4.9、§6A、§78；publication 身份/修订、实际消费来源、前一会话状态、事件修订投影及 Execution Namespace。原目标是冻结合同语义；没有证据要求 00C 自行生成被接受的正式 Head。
- **00D**：REV2 §3B.4、§3E、§3F、§78；官方来源声明日期门、有界下载、source manifest、包校验及全市场 overlap。旧包虽曾被比较，但历史结论是 `NOT_ACCEPTED`，并有开放的 mismatch 判据审计项。本轮依 R2 明令不重跑 overlap。
- **00E**：REV2 §3B、§3F、§7.7、§41A.3、§78；固定复权合同和坐标语义，并独立保留真实经验验收未完成状态；RAW readiness 与 adjusted readiness 分离。

### R2 有界运行证据

- **B｜代码合同与 Schema**：只读连接确认数据库 `market_research`、`transaction_read_only=on`。`security_lifecycle_history`、`security_lifecycle_facts`、`security_membership_interval_history`、`provider_lifecycle_fact_history` 均存在。Catalog 核对了生命周期列、有效区间、来源修订/替代关系、provider/observed/ingested/system 时钟、主键、有效期与 cutoff 索引、时间约束、来源 revision 外键及 append-only 触发器。SQL 合同与独立静态回归通过，因此 `SCHEMA_READY=PASS`。
- **B｜正式数据**：`security_lifecycle_facts` 无行；`security_lifecycle_history` 有行，但有界读回的 6 条排序样本均为北交所 `BEIJING`，其有效期止于 2025-10-08，且只证明该小样本引用的 source_revision 可解析。它不证明沪主板、深主板、创业板、科创板的完整生命周期覆盖，也不证明 PIT/AS_RECORDED 全链。故 `DATA_READY=NOT_PROVEN`；此结果不反推 Schema 错误。
- **C｜代码合同与 Schema**：Publication 候选代码校验稳定 `publication_id`、日期、namespace、revision 和来源身份；迁移定义 Head 只能指向已接受且日期/namespace 一致的 publication，namespace 与 state identity 有外键/唯一约束，reader 有身份校验。只读 catalog 确认 `model_namespaces`、`publication_heads` 表及约束存在。因此 `PUBLICATION_IDENTITY_CONTRACT=PASS`。
- **C｜正式运行 Head**：`model_namespaces`、`publication_heads` 当前均无行，`ACCEPTED_HEAD_OPERATIONAL=NOT_PRESENT`。按找到的 00C 原文，不要求在阶段00创建正式 Head；本轮没有伪造 Head。该状态不是代码合同失败，也不单独证明正式发布已运行。
- **D｜本地只读真实 TDX 样本**：源根 `D:/new_tdx` 下的 `T0002/hq_cache/tdxhy.cfg` 可读，当前身份解析有 5,589 个 A 股 ID。抽查固定证券 `SH.600000`、`SZ.000001`、`SZ.300001`、`SH.688001`，均通过现有身份分类并各有对应 `.day` 文件；每个文件大小为 32 字节记录整数倍，末条记录可解析为 TDX 原生 RAW OHLC/amount/volume，样本交易日分别为 2026-09-10、2026-09-11、2026-09-10、2026-09-10。完整读取并校验的四个文件大小均小于 300 KB；本地修改时钟为 2026-09-10、2026-09-14，早于本轮，不能代表当前来源更新时钟。未遍历全历史、未改动源文件、未重跑 overlap。此证据证明本机存在有界真实四板文件样本，不证明官方来源包验收。
- **D｜来源接受**：只读 PostgreSQL 确认 `source_packages` 表存在但没有记录；`source_revisions` 有记录不能建立已接受包身份。既无当前已接受官方 package，也无 package-to-revision 的接受证据，所以 `REAL_SOURCE_ACCEPTANCE=BLOCKED_REQUIRED_SCOPE (A_STOCK_TDX_SOURCE)`。文件样本日期较旧，且样本末日存在跨证券日期不一致；不将其描述为当前交易日完整包。
- **E｜RAW bootstrap**：`.day` 文件可读只证明本地 RAW 输入存在；现有 Stage00 合同要求 RAW 权限从已接受的阶段和 D/B/C owner scope 派生，单独自声明不算授权。当前无已接受 source package / RAW bootstrap receipt，故 `RAW_BOOTSTRAP=BLOCKED_REQUIRED_SCOPE`。未合成四板清单、未倒填 PIT、未把 DM01 Head 或未绑定 package 的 revision 当作 V4 RAW 正式 Head。

### R2 入口安全与定向回归

- 修复 `scripts/apply_v4_phase0_schema.py` 的使用面：该历史入口注册了 **57** 项迁移，包含 Phase 0 到后续 V4 阶段。当前 `apply()` 在连接 PG 前抛出 `NOT_AUTHORIZED_TO_EXECUTE`，CLI 的 `--apply` 也明确拒绝；模块普通导入仍不连接数据库。保留迁移定义，不在本任务执行任何 DDL/DML。将来需在获批的具体迁移阶段重新评估该入口范围。
- 新增 B/C 静态合同测试，覆盖生命周期日期/知识时间、来源 revision、关键索引与 append-only，以及 publication/namespace 身份约束；断言不把事实行或正式 Head 存在作为静态合同成立条件。现有 gate 聚合器保持原样，没有降低 required scope，也没有新增第二套总 gate。
- 定向测试：`tests/v4_phase0`（排除含写入的 `test_postgres_schema.py`）**108 passed**；`tests/test_v4_r7_sql_schema_compatibility.py` **6 passed**。`compileall` 与 `git diff --check` 通过。实际执行迁移入口 `--apply` 仅验证拒绝保护，返回 `NOT_AUTHORIZED_TO_EXECUTE`，没有尝试连接或迁移数据库。
- 数据库目录/小样本查询均显式只读并设 3 秒 statement timeout；无写入、DDL、迁移、大表扫描、Head 操作、来源下载或服务启动。00D overlap 性能/全市场 workload 未重跑。

### R2 当前八子阶段与准入

| 子阶段 | 当前状态 | 合同实现与运行数据判定 |
|---|---|---|
| V4-00A | `DEGRADED_PASS` | 原目标已由 Git 历史定位并冻结本轮 HEAD/数据库身份；当前数据库备份及恢复回执未验证，沿用原 00A 开放项，不扩大恢复工作。 |
| V4-00B | `DEGRADED_PASS` | `SCHEMA_READY=PASS`；`DATA_READY=NOT_PROVEN`。空 `security_lifecycle_facts` 不再作为 Schema 失败依据；现有 history 小样本不证明完整四板与 PIT。 |
| V4-00C | `DEGRADED_PASS` | `PUBLICATION_IDENTITY_CONTRACT=PASS`；`ACCEPTED_HEAD_OPERATIONAL=NOT_PRESENT`。原文没有要求阶段00生成 Head；未伪造或切换 Head。 |
| V4-00D | `DEGRADED_PASS` | 本机 RAW 文件/固定身份样本真实可读；当前无接受的 V4 source package，`A_STOCK_TDX_SOURCE=BLOCKED_REQUIRED_SCOPE`。未重跑 overlap。 |
| V4-00E | `BLOCKED` | 没有真实被接受的 RAW bootstrap 输入及派生 receipt；不接受合成样本或孤立 Head。 |
| V4-00F | `DEGRADED_PASS` | 延续 R1：BaoStock supplemental contract/fixture 状态通过，正式 live route/field binding 仍待后续阶段；R2 未声称在线来源验收。 |
| V4-00G | `DEGRADED_PASS` | 延续 R1：算法合同和参数框架夹具通过，参数/部分合同仍属候选；本轮未改算法成果。 |
| V4-00H | `DEGRADED_PASS` | 延续 R1：Gate 与性能规则测试通过；没有重跑基准或设定未授权阈值。 |

| R2 汇总项 | 状态 | 依据 |
|---|---|---|
| `CODE_REPAIR` | `PASS` | 00A 原始合同溯源、B/C 合同/运行态区分、迁移入口拒绝保护及其回归已完成。 |
| `SCHEMA_CONTRACT` | `PASS`（B/C） | 静态 SQL/代码合同与只读 catalog 相符；未执行迁移。 |
| `REAL_SOURCE_ACCEPTANCE` | `BLOCKED` | 本机存在真实 TDX 样本，但无已接受且完整的 V4 source package/revision 证据。 |
| `OPERATIONAL_HEAD` | `NOT_PRESENT` | 当前没有 V4 namespace/publication Head；00C 不以阶段00造 Head 为验收前提。 |
| `STAGE00_ENTRY_GATE` | `BLOCKED` | `A_STOCK_TDX_SOURCE` 和派生 `RAW_BOOTSTRAP` 未接受；不因 B/C 合同通过放行 V4-01。 |

### R2 未关闭项和权限边界

- 保持阻断：D 的官方来源日期/包身份/接受证据与所需来源 revision 尚缺；E RAW bootstrap receipt 未从被接受的真实输入派生。B 的真实生命周期事实完整性与四板覆盖仍未证实；C 暂无正式运行 Head，但这不是本阶段静态身份合同的缺陷。
- 00A 当前 PG 实例的备份/隔离恢复验收仍未完成；历史回执只能定位目标，不能替代当前实例证据。
- 若后续要完成 D/E，需另按授权将官方包及合同接受后的 source package/revision/必要 typed facts 追加至现有 `v4` 结构；本轮未执行。事务提交前可回滚未接受候选；已接受不可变记录不得删除，应按合同追加修订。任何 DML 与具体对象范围应在后续明确授权任务中核定。本轮不要求 B/C Schema DDL，也不要求阶段00创建 Publication Head。
- `test_postgres_schema.py` 写入/rollback 测试未运行；不因 rollback 视为已授权。备份目录未读取、删除或恢复，生产服务未启动。

**R2 结论：`STAGE00_REPAIR_PARTIAL`，独立复核状态 `EXTERNAL_REVIEW_PENDING`。** 合同/schema 修复范围完成，但真实 source acceptance 和 RAW bootstrap 仍阻断阶段00准入及 V4-01；本报告不表示阶段00 PASS、阶段01启动或生产发布。

## R3｜合同与参数 PG-only 纠偏（当前权威结论）

本节仅执行 R3 最高优先级订正，R1/R2保留为历史。开始现场为分支 `codex/v4-workspace-cleanup`、HEAD `7b05b47f454b9e4decd0d0beaea2cf5d72296156`、工作区干净。范围限阶段00及其直接 V4-01 合同读取测试，不扩展重构其余阶段；未写 PG、切换 Head、执行 DDL/DML、处理大表或触发 CI。

### 运行消费者与测试边界

- 对任务卡列出的阶段00合同文件及 `src/v4/contracts` 的调用点定向搜索结果：产品源码没有读取这些 JSON 的调用点；`evaluate_phase0` 与算法合同校验器是纯输入函数，当前没有被产品运行链调用。故本轮确认的阶段00“业务合同 JSON runtime consumers”为 **0**，没有真实文件消费者可迁移；不能把新增未接线包装函数宣称成已迁移 runtime。`src/workbench_analysis/contract_registry_pg_v1.py` 的既有只读 reader 保留原样、无文件回退，且不新增第二套 registry。
- `tests/v4_phase0` 原有合同配置读取已改为 `tests/v4_phase0/fixtures/` 固定样本；PostgreSQL schema 测试所需的schema断言样本也改为测试夹具。夹具只服务独立代码/catalog断言，不代表 PG 已登记、批准或当前生效。指定阶段合同 JSON 在 `src/` 和阶段00测试中不再作为运行读取路径。
- 更新了 `AGENTS.md`、`PROJECT_SPEC.md`、`config/AGENTS.md`：明确 `market_research.v4` 是业务合同正文/版本、算法参数、Owner、业务结果及发布身份的唯一运行权威；`config/` 例外仅限采集/临时传输路径、机器连接、凭据环境变量与部署配置；PG 缺记录或读取失败不得回退文件。
- 增补既有 reader 的缺失合同版本、多 namespace 歧义 fail-closed 回归；更新原测试以验证已存在迁移 `043_v4_contract_registry_approval_events_r1.sql`，不再引用已删除的历史 R21 草案 SQL。reader 对应测试明确覆盖只读 RR 快照、审批/摘要校验与无文件回退。

### 只读 PG 合同核验与待授权迁入

所有目录查询均使用 `REPEATABLE READ, READ ONLY` 及 3 秒超时。确认唯一 `market_research.v4` 中现有 `contract_versions`、`contract_approval_events` 模型及约束存在；当前有 **19** 个合同版本记录和 **16** 个审批事件。该计数不表示阶段00所需合同齐备。

| 状态项 | R3 结果 | 说明 |
|---|---|---|
| `PG_CONTRACT_MODEL_PRESENT` | `PASS` | 已有表、版本摘要、namespace、source_revision、版本不可变及追加审批事件模型；不新增表或 registry。 |
| `PG_CONTRACT_VERSION_DATA_PRESENT` | `PARTIAL` | PG中有19版本/16事件，但以下五项阶段00精确合同版本均无记录：`V4_PHASE0_FINAL_ACCEPTANCE_R3/3.0.0`、`V4_ALGORITHM_CONTRACT_FRAMEWORK_V1/1.1.0`、`PARAMETER_REGISTRY_V1/1.1.0`、`CAPABILITY_CUTOVER_AND_ROLLBACK_V1/1.0.0`、`V4_PERFORMANCE_MEASUREMENT_CONTRACT_V1/1.1.0`。 |
| `RUNTIME_CONSUMER_PG_ONLY` | `PARTIAL_NO_RUNTIME_CALLSITE` | 阶段00源码无文件读取消费者可改；算法/聚合函数无产品调用链。现有 PG reader 经模拟验证 fail closed，但这不等于阶段00业务已有 PG runtime 接线。 |
| `PG_IMPORT_PENDING_AUTH` | `BLOCKED_NEEDS_SEPARATE_AUTHORIZATION` | 未写入。下列精确原始文件字节及 SHA 可作为复用现有表的一次性受控迁入输入；不包含审批事件。参数注册表明确标记候选值非正式，不得由导入自动变为 approved。 |
| `REAL_SOURCE_ACCEPTANCE` | `BLOCKED` | 延续 R2：没有当前被接受的完整 TDX source package/revision 证据。 |
| `RAW_BOOTSTRAP` | `BLOCKED` | 无来自已接受真实输入的 RAW bootstrap receipt。 |
| `STAGE00_ENTRY_GATE` | `BLOCKED` | D 的 source acceptance 与 E 的 RAW bootstrap 仍不满足 required scopes；无阶段01准入。 |

如用户之后单独授权向共享 PG 追加**未批准版本字节**，范围只涉及现有 `v4.contract_versions`，影响为新增最多5条不可变版本记录；不会新增/修改审批事件、Head、Publication、Owner绑定、参数生效状态或计算结果。需将以下参数绑定为源文件原始字节（hex）、列示 SHA、`schema_version=version`、`namespace=V4_BOOTSTRAP_PENDING`、列示 source revision，并在同一事务读回校验摘要；任何主键已存在但 SHA 不同必须回滚并人工审查。此 SQL 未执行，`contract_approval_events` 不提供可伪造的用户授权者、授权引用或发生时间，故本轮不提出/执行审批 INSERT。

| psql 变量 | 唯一字节输入 | SHA-256 |
|---|---|---|
| `phase00_final_gate_hex` | `config/v4_phase0_final_gate_v1.json` 原始字节转小写hex | `2a5b4c6b5b6be107636c49c79806c62fbc05ba18e2acf474bd5d25116bb5ab28` |
| `algorithm_framework_hex` | `config/v4_algorithm_contract_framework_v1.json` 原始字节转小写hex | `a03fda92aaf608edfb5dd86b533fae576c3d121bc413a61768985e6e53cb4455` |
| `parameter_registry_hex` | `config/v4_parameter_registry_v1.json` 原始字节转小写hex | `b02d267d95456f557ddf5acf450eb01ff95ba661231e3f88fe84f355e85f0ef7` |
| `capability_cutover_hex` | `config/v4_capability_cutover_policy_v1.json` 原始字节转小写hex | `26aa335d3c59d8fd5b4454bfa142ba5064f8ea6b176bfd405b0b810da8a83de3` |
| `performance_contract_hex` | `config/v4_performance_measurement_contract_v1.json` 原始字节转小写hex | `266558fb6137d6cc6894b85fbf51b45e8a05fd32a661f6a0d5c27f556fefac55` |

```sql
BEGIN;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
INSERT INTO v4.contract_versions
    (contract_id, version, raw_content, raw_sha256, content_format,
     schema_version, namespace, source_revision)
VALUES
    ('V4_PHASE0_FINAL_ACCEPTANCE_R3','3.0.0',decode(:'phase00_final_gate_hex','hex'),'2a5b4c6b5b6be107636c49c79806c62fbc05ba18e2acf474bd5d25116bb5ab28','JSON','3.0.0','V4_BOOTSTRAP_PENDING','git:7b05b47f454b9e4decd0d0beaea2cf5d72296156:config/v4_phase0_final_gate_v1.json'),
    ('V4_ALGORITHM_CONTRACT_FRAMEWORK_V1','1.1.0',decode(:'algorithm_framework_hex','hex'),'a03fda92aaf608edfb5dd86b533fae576c3d121bc413a61768985e6e53cb4455','JSON','1.1.0','V4_BOOTSTRAP_PENDING','git:7b05b47f454b9e4decd0d0beaea2cf5d72296156:config/v4_algorithm_contract_framework_v1.json'),
    ('PARAMETER_REGISTRY_V1','1.1.0',decode(:'parameter_registry_hex','hex'),'b02d267d95456f557ddf5acf450eb01ff95ba661231e3f88fe84f355e85f0ef7','JSON','1.1.0','V4_BOOTSTRAP_PENDING','git:7b05b47f454b9e4decd0d0beaea2cf5d72296156:config/v4_parameter_registry_v1.json'),
    ('CAPABILITY_CUTOVER_AND_ROLLBACK_V1','1.0.0',decode(:'capability_cutover_hex','hex'),'26aa335d3c59d8fd5b4454bfa142ba5064f8ea6b176bfd405b0b810da8a83de3','JSON','1.0.0','V4_BOOTSTRAP_PENDING','git:7b05b47f454b9e4decd0d0beaea2cf5d72296156:config/v4_capability_cutover_policy_v1.json'),
    ('V4_PERFORMANCE_MEASUREMENT_CONTRACT_V1','1.1.0',decode(:'performance_contract_hex','hex'),'266558fb6137d6cc6894b85fbf51b45e8a05fd32a661f6a0d5c27f556fefac55','JSON','1.1.0','V4_BOOTSTRAP_PENDING','git:7b05b47f454b9e4decd0d0beaea2cf5d72296156:config/v4_performance_measurement_contract_v1.json')
ON CONFLICT (contract_id, version) DO NOTHING;
SELECT contract_id, version, encode(sha256(raw_content),'hex') AS actual_sha256,
       raw_sha256, namespace, source_revision
  FROM v4.contract_versions
 WHERE (contract_id,version) IN (
    ('V4_PHASE0_FINAL_ACCEPTANCE_R3','3.0.0'),
    ('V4_ALGORITHM_CONTRACT_FRAMEWORK_V1','1.1.0'),
    ('PARAMETER_REGISTRY_V1','1.1.0'),
    ('CAPABILITY_CUTOVER_AND_ROLLBACK_V1','1.0.0'),
    ('V4_PERFORMANCE_MEASUREMENT_CONTRACT_V1','1.1.0'))
 ORDER BY contract_id,version;
-- 只有逐行身份与摘要全匹配后才可由另行获批的操作 COMMIT；否则 ROLLBACK。
ROLLBACK;
```

该 SQL 仅供后续单独授权时审核，当前事务以 `ROLLBACK` 收尾，不表示已执行。五份原始字节对应 SHA 已按本地原文件计算；`V4_01_HISTORY_LINEAGE_POLICY_V1/1.0.0` 也未见 PG 版本，属于后续 V4-01 直接依赖，本轮不迁入。其文件仅由测试夹具覆盖，不扩展改造其他阶段。

### R3验证与八子阶段真实状态

- `PYTHONPATH=src python -m pytest -q tests/v4_phase0 --ignore=tests/v4_phase0/test_postgres_schema.py --basetemp=G:/codex_tmp/test_temp/stage00_r3_pass`：**109 passed**。含 gate/算法独立夹具、无 config runtime 文件读取回归及原阶段00用例。
- `PYTHONPATH=src python -m pytest -q tests/test_v4_contract_registry_pg_v1.py --basetemp=G:/codex_tmp/test_temp/stage00_r3_registry_pass`：**26 passed**。PG版本读取通过模拟 cursor，不触达真实 PG。
- `python -m compileall -q src/v4/contracts tests/v4_phase0 tests/test_v4_contract_registry_pg_v1.py`：通过；`git diff --check`：通过。
- `tests/v4_phase0/test_postgres_schema.py` 未运行；其用例包含对共享 PG 的 INSERT/rollback，继续标记 `DB_WRITE_TEST_NOT_AUTHORIZED`。此轮只执行 PG只读目录查询。未执行 DDL/DML、Head操作、来源采集、大表、服务切换或 CI。

| 子阶段 | R3状态 | R3更新后的事实 |
|---|---|---|
| V4-00A | `DEGRADED_PASS` | 00A原始依据与冻结记录沿用R2；PG合同数据缺口不替代仍未闭合的备份/恢复回执。 |
| V4-00B | `DEGRADED_PASS` | Schema目录结构沿用R2 `SCHEMA_READY=PASS`；业务数据覆盖仍 `DATA_READY=NOT_PROVEN`，PG现役合同记录也未齐。 |
| V4-00C | `DEGRADED_PASS` | 静态Publication身份合同沿用R2；无正式Head不等于代码合同失败，且没有阶段00产品 runtime callsite。 |
| V4-00D | `DEGRADED_PASS` | 本地真实TDX小样本存在；正式source package/revision未接受，required scope仍阻断。 |
| V4-00E | `BLOCKED` | 缺真实接受输入及其派生RAW receipt，仍不能准入。 |
| V4-00F | `DEGRADED_PASS` | 沿用R2限度；不将bootstrap namespace合同记录或夹具升级为live-source验收。 |
| V4-00G | `BLOCKED` | 算法校验代码与测试夹具存在，但阶段00算法框架及参数版本未在PG找到，夹具不能替代正式运行版本。 |
| V4-00H | `DEGRADED_PASS` | gate规则纯函数与夹具回归通过；无Stage00业务runtime接线，最终准入合同版本未在PG找到。 |

**R3结论：`STAGE00_REPAIR_PARTIAL`，`STAGE00_ENTRY_GATE=BLOCKED`。** `RUNTIME_CONSUMER_PG_ONLY` 仅证明没有阶段00本地 JSON 运行读取，不代表已有 PG runtime 消费链；阶段00合同版本迁入及其原始批准事实需要单独授权和事实依据。D/E真实来源阻断继续存在。本报告不表示阶段00 PASS、阶段01启动或生产发布。

R3代码、测试及规范实现提交 SHA：`e21849b21226d364d4f79678d416126e58ffb5b1`。最终报告提交及分支 HEAD 由现有 PR #3 注释给出。

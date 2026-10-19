---
stage_id: V4-00
code_sha: 052baa28400a95035946f94c361501891971ef89
test_scope: V4-00A-H、阶段00配置与入口修复、只读数据库核验
conclusion: STAGE00_REPAIR_PARTIAL
approval_status: USER_AUTHORIZED_STAGE00_ONLY
---

# V4 阶段00｜清理后基础能力恢复与八子阶段验收

日期：2026-10-19。本文是阶段00唯一当前报告；不表示阶段01开始、V4业务验收通过或生产切换。

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

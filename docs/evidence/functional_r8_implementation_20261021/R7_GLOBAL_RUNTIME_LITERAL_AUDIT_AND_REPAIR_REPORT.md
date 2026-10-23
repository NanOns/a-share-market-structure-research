# V4 R7 全仓运行时固定业务字面量审计与实修报告

**状态：`GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED`**
**审计对象：** `NanOns/a-share-market-structure-research`，`codex/v4-unified-development`
**扫描基线：** `0f60ce4abd0dbc61e55e8fece2c24023caea627b`
**源码修复提交：** `d6eed78eb8ef72b193323210b56b8ece789d468e`
**审计日期：** 2026-10-23（Asia/Shanghai）

## 结论

本轮已对 Git 跟踪的源码、脚本、配置、迁移、SQL、UI 和运行入口候选执行全量文件清单与固定日期/证券/板块字面量召回扫描，建立 38 个静态入口、10,326 条静态依赖边，并实修复权起始日、R43 候选日期作用域、BFF 固定默认日期与 V4-02 冻结合同读取。新增全仓防新增回归和逐命中 JSON 清单。

全仓门**不能判通过**。扫描器发现 3,190 条位于保守静态可达路径、尚未逐条完成语义核验的候选（2,213 日期、965 证券身份、12 板块身份），分布于 136 个文件。候选中含版本化源事实/历史权威数据的可能性，但没有逐条来源合同与运行消费者证据时不得批量豁免。另有 131 个 Python 动态导入/执行点没有运行时闭包证据。按任务门禁，未知可达性与未核实配置不能视为通过。

因此本报告证明的是**源码实修与静态扫描已实施，独立运行时全仓通用性验收未完成**。没有将静态候选数冒充为真实违规数，也没有将其降成零。

## 阶段 0 与边界

阶段 0：`DEGRADED_PASS`，限定为本地 Git 源码/配置读取、静态依赖追踪与代码修复。分支与远端在开始时均为 `0f60ce4abd0dbc61e55e8fece2c24023caea627b`；既有未跟踪的 `.githooks/`、`config_back/`、`script_back/` 保持不变。

没有启动或重启网页/API 服务，没有切换 `28765`、生产 Head 或调度，没有修改 PG/业务数据，也没有写入 TDX 源根。28766 修复版未加载，记为 `UI_RUNTIME_NOT_RELOADED`。PG、正式消费者与开发 Owner 的新读回均未在本轮验收，不能以旧 API 或旧进程结果代表新代码。

## 全仓扫描清单

扫描命令：

```powershell
$env:TMP='G:\codex_tmp'; $env:TEMP='G:\codex_tmp'; $env:TMPDIR='G:\codex_tmp'
python scripts/check_v4_business_literals.py --output docs/evidence/functional_r8_implementation_20261021/PRODUCTION_LITERAL_INVENTORY.json
```

| 范围 | 文件数 |
|---|---:|
| 总扫描文件 | 3,958 |
| Python（含 tests） | 3,264 |
| JavaScript/TypeScript | 32 |
| 运行脚本候选 | 1,539 |
| 配置 | 544 |
| SQL | 100 |
| UI（HTML/JS/TS） | 44 |
| 静态可达节点 | 694 |
| 静态入口 / 依赖边 | 38 / 10,326 |
| 测试专用文件 | 1,055 |
| Python AST 解析失败 | 0 |
| 动态导入/执行点 | 131（未运行时闭包核验） |

清单逐项记录 ID、路径、行列、字面量、候选类型、AST 节点、环境、入口与静态调用链、可达标记、影响、处理状态、替换来源、修改提交栏及回归 ID。纯 `docs/evidence/` 与 `docs/audits/` 不作为运行命中；精确历史证据路径单条标为 `HISTORICAL_FROZEN`，测试目录标为 `TEST_ONLY`。未把整个目录豁免。

召回与分类计数：

| 分类 | 数量 |
|---|---:|
| 固定字面量候选总数 | 39,169 |
| `TEST_ONLY` | 6,830 |
| `HISTORICAL_FROZEN`（逐条命中在证据路径） | 794 |
| `UNRESOLVED` | 31,545 |
| 静态可达且未解决 | 3,190 |

当前未解决可达候选主要集中于 `config/v4_joint_release_authority_v1.json`（899）、`config/v4_replay_compare_authority_v1.json`（805）、`config/operational_daily_exact_release_policy_v2.json`（720）以及 V4-02 日期规则/日历配置与构建脚本。它们可能是已绑定来源的历史发布事实，也可能构成运行默认；本轮没有完成逐字段合同和消费者读回，故逐项留在机器清单中，状态为 `UNRESOLVED`。

## 本轮源码修复

| ID | 修复 | 当前行为 / 来源 | 回归 |
|---|---|---|---|
| LIT-P0-01 | [market_source_acquisition.py](../../../src/workbench_analysis/market_source_acquisition.py) | 移除因子查询固定 `2026-01-01`；按来源身份 `query_stock_basic` 的 IPO 日求覆盖起点，身份/上市日缺失则记录 `SOURCE_INCOMPLETE` 并关闭该身份的因子查询，不回退固定日期。 | `test_factor_coverage_starts_at_source_identity_ipo_date`；缺失/格式异常负例 |
| LIT-P0-02 | [r43_operational_sources.py](../../../src/workbench_analysis/r43_operational_sources.py)、[r43_operational_publication.py](../../../src/workbench_analysis/r43_operational_publication.py) | 移除生产模块四个日期常量；来源日期须由调用者传入并与显式来源清单回执一致，候选 API 从候选自身日期集合校验、展示与选择。 | `tests/test_r43_operational_sources.py`、`tests/test_r43_operational_bff.py` |
| LIT-P0-03 | [build_r43_operational_successor.py](../../../scripts/build_r43_operational_successor.py) | 移除固定接受日期与假定前态；CLI 必须显式提供 `--source-manifest`、`--trade-date`、`--predecessor-head`，并校验候选日属于来源清单。R43 R1/R2 消费者测试循环改读 candidate dates。 | R43 候选/发布回归 95 项集合 |
| LIT-P0-04 | [v4_02_canonical_daily_pit.py](../../../scripts/v4_02_canonical_daily_pit.py) | 报告 cutoff 改读已加载的版本合同 `inputs.source_cutoff`；指数日历身份改从版本合同 `periods.calendar_sources` 读取，保留指数参考与该精确历史快照身份。 | `tests/v4_02/*` 相关六组 |
| R7-R43-UI | [r43_operational_bff.py](../../../src/workbench_service/r43_operational_bff.py) | 页面/API 默认研究日随候选最新日期变化；缺来源不再回退到固定 2026-09-30 历史诊断端点。 | `tests/test_r43_operational_bff.py` |

R43 历史重建现在要求显式、日期匹配的来源清单、前态与权威路径。现有旧清单缺少新版本要求的若干来源绑定时会按 `SOURCE_MANIFEST_*_REQUIRED` 关闭；本轮没有编造新来源、补写 10/22 PIT 或重写旧 receipt。新的完整来源输入尚未提供，故这条新日期全链尚未获得真实来源验收。

V4-02 指数是市场参考身份而非个股筛选，本轮将其留在 `V4_CANONICAL_DAILY_PIT_PERIODS_V2` 版本合同的 benchmark/calendar 输入中。`source_cutoff` 仍是该不可变 R2 历史快照合同中的固定截点，不作当前行情默认值。

## 测试与业务证据状态

最终本地回归命令覆盖全仓准入、行情采集、R43 Owner/成员/发布/BFF 与 V4-02 当前相关测试，共 **95 passed**，`27.85s`。`py_compile` 覆盖本次修改的脚本、模块和测试；`git diff --cached --check` 无差异问题。

- `CI_NOT_RUN`：没有运行远端 CI。
- `UI_RUNTIME_NOT_RELOADED`：遵守禁止重启；旧服务未作为新源码验证。
- 三个官方历史交易日 + 下一真实可用来源日的实源对照：`NOT_VERIFIED`。
- 10/20 Priority、10/21 Sector/Focus、10/22 SourceIngress/PG、D0/D2、真实 Owner/Head 读回：本轮未执行，保持各自已有 `OPEN / SOURCE_AUTHORITY_WAIT / CONTRACT_BLOCKED`，不冒称通过。
- R8 与既有 PG、历史 `NON_PIT` 文件没有改写或删除；本轮没有 PG DDL/DML。
- 开发分支代码已提交；推送本报告与证据后，仍不表示独立验收或生产准入。

## 尚未关闭的门

1. 对 3,190 条可达候选逐项区分现行规则、精确日期数据事实、上市身份来源、taxonomy/成员来源、冻结历史权威与无效误报；需要每个保留项的合同路径/版本、消费者、授权范围和可复核证据。
2. 补齐 131 个动态导入/执行点及 SQL/配置/UI 动态引用的运行时闭包；当前 JS/SQL/YAML 的候选召回不是语义 AST/运行时解析证明。
3. 为生产准入检测器建立经过人工逐条裁定的基准例外；当前 `config/v4_business_literal_admission_baseline_v1.json` 是 **`NON_WAIVING_BASELINE_FOR_CHANGE_DETECTION`**，只阻止新增候选，绝不批准其中已有命中。
4. 在用户手动决定启动新版后，另行核验 28766 实际加载代码、真实来源/PG Owner 读回和未完成业务链；本轮未启动服务。

下一阶段只能从上述清单继续，当前状态不能宣告全仓正常运行路径违规为零。

# V4 R8 全仓字面量与功能闭环阶段报告

- 任务：V4_R7_外部独立审计_R8硬编码实修与功能闭环_20261023.md
- 仓库/分支：NanOns/a-share-market-structure-research / codex/v4-unified-development
- 远端基线：aaaf641e8495c08939dea788e385795463189b1b；fetch 后本地与远端一致。
- 本轮代码提交：abb6c63920ebdd0122bbfa828345492edee7e779。
- 阶段结论：DEGRADED_PASS（仅限现役 V4 静态代码、定向本地回归和开发 PG 只读目录核验）。总体验收 EXTERNAL_REVIEW_BLOCKED；全局硬编码门仍阻断。

## 执行合同与阶段 0

执行前读取了项目约束、Drive 执行单和 CURRENT 恢复入口；仓库内查阅正式功能合同 docs/plans/V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md、Forward 合同 docs/upgrade/V4_R7_FORWARD_SIGNAL_SPEC_R1.md、现役来源合同 docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md。S00–S08 是本轮业务范围依据。

阶段 0 为 DEGRADED_PASS：允许现役 V4 源码修改、静态扫描、相关本地回归和现有开发 PG 的受控只读核验；不允许重启服务、写正式 Head、碰生产 28765 或改变数据源权限。沿用最新远端 HEAD，不退回外审冻结旧 SHA。保留原有未跟踪目录 .githooks/、config_back/、script_back/，没有清理或移动任何工作区文件。

## 已实施修改

| 工作包 | 文件/符号 | 修复前后行为 |
|---|---|---|
| P0-A / P0-D | scripts/check_v4_business_literals.py：global_gate、gate_exit_code、date_component_literals、semantic_candidate_key | 旧门只验证候选是否超出现有 baseline，普通扫描即使有可达 unresolved 也以零退出；date(year, month, day) 未召回，candidate key 含行号导致插行伪报新增。现将 baseline 差分和全局门分开，严格全局门默认对可达 unresolved 返回 exit 1；加入 Python AST 日期构造器召回及独立稳定语义 key，inventory 升为 V4-PRODUCTION-LITERAL-INVENTORY/2。 |
| P0-A / P0-D | tests/v4_policy/test_no_production_hardcoded_identities.py | baseline 继续保持非豁免、未扩大；从只读 R7 原始 inventory 在内存迁移稳定 key，校验旧 unresolved 仍阻断全局门、插行稳定性和 AST 日期构造器。 |
| S01 | src/workbench_service/core_product_bff_r1.py：_read_index_r2 | ReadIndex authority 缓存签名从 mtime/size 改为 authority 原始字节数与 SHA-256；相同 mtime/size 下内容替换会触发重载。 |
| S06-P | src/workbench_db/forward_r7_store.py：_matured_count_watermark、read_matured_count | 水位从数据库身份+MAX(ordinal) 改为数据库身份+行数+最大 ordinal。序列低值事务晚提交时，行数变化使缓存失效。无缓存读取不再访问缓存 schema key。 |
| S01 / S06-P | tests/test_r8_candidate_priority_cache_key.py | 增加同最大 ordinal 行数变化、相同 mtime/size authority 内容替换的回归。 |

Priority 的缺 close/null、非有限数、坏质量、错日期/坐标 fail-closed 行为已存在于当前源码；本轮相关合同回归通过，没有改变评分、分母或资格规则，也没有将代码回归冒称为真实日数值验收。

## 分层结果

| 门 | 状态 | 证据与边界 |
|---|---|---|
| CODE | PARTIAL | 三处现役实现改动已提交，只覆盖本报告列出的准入、ReadIndex 缓存和 Forward 水位问题。 |
| STATIC | PARTIAL / BLOCKED | 3,958 文件、3,264 Python、32 JS/TS、544 配置、100 SQL、44 UI；694 可达节点、38 个入口、10,327 静态依赖边、131 个动态导入/执行候选位点、0 AST 解析失败。召回 39,491 项；可达 unresolved 3,190：日期 2,213、证券身份 965、板块身份 12。确认违规计数 0 仅表示目前没有逐项确认记录，不代表已证明为零；全局门仍为 GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED。严格扫描 exit 1 是预期阻断。 |
| NO_NEW_LITERAL | PASS（旧规则差分） | 全仓差分测试通过；以 R7 原 inventory 中已存在的逐项证据迁移稳定 key，未重生/扩大 admission baseline。新增 AST 类由全局门独立处理。 |
| NUMERIC | NOT_VERIFIED | Priority 代码负例回归通过；没有重新取得 10/20、10/21 股票/板块 Owner 全量或市场/D0 数值，旧报告数据不作为今态。 |
| DEV_PG | PARTIAL | 通过现有配置连接 market_research:5432，事务明确设为 READ ONLY。实际连接角色为 superuser；按开发 Head 日期在 4 个 Forward schema 中发现 2 个匹配，无法唯一绑定当前 Owner，因此停止于目录核验，没有读取业务事实、没有写数据、没有 PG consumer PASS。 |
| API | NOT_VERIFIED | 现有 28766 的只读 /api/v4/context 返回 READY、T0=2026-10-21；/api/v4/health 和 /api/v4/priority 返回 409。服务未重载本轮代码，旧响应不作为新代码验收。 |
| UI | NOT_VERIFIED | UI_RUNTIME_NOT_RELOADED；没有重启服务。 |
| SOURCE | NOT_VERIFIED | 未捕获新来源、未变更 TDX_ONLY 或 SourceIngress 授权，未提升隔离 BaoStock 候选。 |
| CI | CI_NOT_RUN | 未运行或等待远端 CI。 |
| PERFORMANCE | NOT_VERIFIED | 未执行 50 样本 P50/P95。 |

严格扫描临时 inventory：G:/codex_tmp/R8_GLOBAL_LITERAL_INVENTORY.json，41,104,804 bytes，SHA-256 7d1c90d2a9e03e0ec30e95e7a6924886983f5e500fb9ee3031cfa213856688a。生成命令：python scripts/check_v4_business_literals.py --output G:/codex_tmp/R8_GLOBAL_LITERAL_INVENTORY.json。未裁定候选令严格命令按设计返回 1。清单留在 G 盘临时目录，不提交 Git。

## 回归与本地检查

命令（TMP/TEMP/TMPDIR 均指向 G 盘）：

    python -m pytest tests/v4_policy/test_no_production_hardcoded_identities.py tests/test_v4_functional_r8_s01_s03.py tests/test_r8_candidate_priority_cache_key.py tests/test_r8_s3_ledger.py tests/test_v4_ux_r2_contract.py -q

结果：87 passed in 26.31s。修改文件 py_compile 通过，git diff --check 通过。SOT R2 指定的 python tools/git_repository_policy.py --staged 无法运行：仓库没有该文件（rg --files 检查确认），状态为 LOCAL_REPOSITORY_POLICY_SCRIPT_MISSING；没有伪造通过。待恢复脚本后补验。

## PG、监听和运行边界

PG 核验只读，不输出密码或 DSN；目标库 market_research、端口 5432，连接角色实际为 superuser。Forward owner schema 匹配不唯一，未做 Owner 读回。没有 DDL/DML、候选 Owner 发布或 Head/CAS 写入。

监听核对：开发服务 28766 已监听（PID 52916）；生产 28765 未监听；PG 5432 已监听（PID 8640）。这些进程未由本任务重启。没有删除文件、清理工作区、切正式 Head/生产调度、改 TDX 源根或强推 Git。

## S00–S08 增量状态及剩余工作

| 阶段 | 本轮状态 | 尚缺的最小证据/工作 |
|---|---|---|
| S00 | PARTIAL | 代码、分支与阶段门已核实；开发 Head 日期对应两个 Forward namespace，Owner 未唯一绑定。 |
| S01 | CODE PASS / API、PG NOT_VERIFIED | ReadIndex 改为内容 SHA 缓存键；仍需同 token 换源负例、跨日 token 读回及 Focus/生命周期真实消费者验证。 |
| S02 | NOT_VERIFIED | 趋势 limiter Owner 唯一性/来源错配尚未重新追溯；需绑定来源及独立公式核验市场趋势和 D0 输入。 |
| S03 | CODE PARTIAL / NUMERIC NOT_VERIFIED | Priority 输入防护 fail-closed；股票/板块正式 Owner、完整分母和 10/20、10/21 数值未读回。 |
| S04 | NOT_VERIFIED | D0 两候选场景 TRUE/FALSE/UNKNOWN 真实来源和状态仍需验收。 |
| S05 | CONTRACT_BLOCKED（受限子能力） | Forward 保留 NO_AUTHORIZED_COHORT_OWNER，不补造 first capture；D2 frozen_level 合同仍未裁定。 |
| S06 | CODE PARTIAL / DEV_PG PARTIAL | Forward 乱序提交缓存水位已修；完整候选链、G1–G4、受控候选 PG 写入及消费者读回未完成。 |
| S07 | NOT_VERIFIED | 旧 28766 未加载本轮代码；六入口新运行读回待用户允许重载时完成。 |
| S08 | OUT OF SCOPE / NOT_ACCEPTED | 没有生产包、accepted Head、调度或 28765 操作；开发推送不等于发布验收。 |

## 尚未关闭的问题

1. 全局有 3,190 条可达候选未裁定，不能宣称正常运行逻辑已无硬编码。扫描入口仍把 run_*.py 等旧入口作为静态 seed；活动 launcher 白名单、真实 Windows Scheduler、服务路由与运行动态边闭包未建立。
2. 动态导入、runpy、Python 字符串拼接、SQL 动态构造、JS/TS AST、配置字段→读取者→默认/分支追踪未闭合。新增日期 AST 只覆盖显式 date/datetime/Timestamp(year,month,day)。
3. 候选中的真实缺陷、版本化市场参考、不可变历史证据、测试样例和误报仍需按字段及调用链裁定；已有 baseline 不是豁免。
4. Priority、Sector lifecycle、市场趋势/D0、SourceIngress、Focus、Forward、D2、跨日 ReadIndex 消费者和真实 API/PG 全量数据链尚未完成对账。来源或授权缺失继续按合同关闭相关能力。
5. PG 使用 superuser 只读目录核验，Forward Head→namespace 匹配不唯一；需合法最小权限 Reader 配置与唯一绑定后再做消费者读回。
6. tools/git_repository_policy.py 缺失；CI 未运行；新代码尚未加载到 28766。总状态仍是 EXTERNAL_REVIEW_BLOCKED，供 ChatGPT 下一轮独立审计。

代码提交：abb6c63920ebdd0122bbfa828345492edee7e779。本报告与证据提交在其后；推送开发分支不等于独立验收或生产准入。
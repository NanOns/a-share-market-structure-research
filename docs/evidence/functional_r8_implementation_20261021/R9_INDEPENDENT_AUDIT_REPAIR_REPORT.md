# V4 R9 独立外审缺陷实修报告

本轮已实际修改并推送 V4 业务源码，完成真实 Parquet 查询、候选 PG Owner、SourceIngress、Forward 并发及分日读链验证。结论为**代码实修交付、分层验收部分通过**；全局准入、完整新日日更、D2、冷启动性能与新版 UI 仍未通过。未切正式 Head、未重启服务。

## 范围、版本和权限

正式任务：Drive `1uJ59hmr8_rGYtXAyUR2EPGdjvkZJg9MA`，目录 `CODEX线下系统开发`。按最新远端 `20ec78b3e9f9fd8490e2c7c73d802368083bb2f4` 施工，提交前再次 fetch 无额外差异。七提交比较为 `aaaf641e…20ec78b3e`，75 文件完整列于末表。全仓仅指现役 V4 模块和实际依赖，旧 V1–V3 未扩张重构。

业务提交：`d69c9d2ec4681bf32c1d69af45da2917f912c38d`；跨平台指数合同摘要修正：`20c2ab27a26c3855828316b4faa5ff6d156de539`。两者已推送统一开发分支；报告所在提交由 `git log -1 --format=%H -- docs/evidence/functional_r8_implementation_20261021/R9_INDEPENDENT_AUDIT_REPAIR_EVIDENCE.json` 定位，最终远端 HEAD 在交付消息核对。

已读 R9、CURRENT/长期 SOT、AGENTS、PROJECT_SPEC、功能 R2、增量四门 R1.1 和适用来源合同。阶段 0 以哈希绑定的 `V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json` 结束为 DEGRADED_PASS，随后执行扫描器；测试不作为发布证书。唯一源码目录为 G:/codex work/大A交易，临时数据均在 G:/codex_tmp，未创建工作树或额外源码工作区。只复用现有候选数据根，未执行其归档源码。

数据库仅 `127.0.0.1:5432/market_research`，一实例、PID 8640、启动时间仍为 2026-10-18 11:06:30.720868+08。新增写入限定候选 token/日期/版本、SourceIngress 和显式测试 schema；读事务 READ ONLY，Forward 结算使用 REPEATABLE READ。28766 仍为旧 PID 52916；28765 无监听。未删除、清理、重启、改调度、合入 main 或强推。

## 已修复的业务问题

- **R9-P0-01 — FIXED**：两份V4-04离线Parquet构建器的四处参数路径/截止日倒置；改为安全绑定路径在前。真实内存DuckDB+Parquet执行，未访问旧业务DuckDB库。
- **R9-P0-02 — FIXED_WITH_GATE_OPEN**：图初始化后合并静态UI边；解析JS/JSX资产、字面量Python动态导入，tests被生产路径引用仍为活动未知；未解析动态和浏览器位点阻断。
- **R9-P0-03 — FIXED_RUNTIME_HISTORICAL_REPLAY_PARTIAL**：日更来源上下文V2从freeze、精确前态及配置只读根解析；不再默认10/09来源；核心无显式来源即拒绝；日历不足禁止负索引环绕。历史模式冻结actions/member，真实10/09全数值流水线本轮未重跑。
- **R9-P1-04 — FIXED**：指数基准绑定有类型、角色、来源类别、版本、price basis和SHA的参考目录与实际包成员；字段缺失只关闭指数能力。保留旧v1目录字节，新增v1.1目录；修正Git LF与工作区CRLF的摘要差异。
- **R9-P1-05 — FIXED**：--asof必须显式给出；目标universe/status/bar不齐阻断。真实微型Parquet跨周/月、暂停交易、未来行，以及日历超前负例均执行。
- **R9-P1-06 — FIXED_ADMISSION_GLOBAL_BLOCKED**：打包prepare在任何准备写入前调用严格字面量门；不重置baseline，不按SHA或tests目录全文件豁免。全局闭包仍未裁定完毕。
- **R9-F-01 — FIXED_REAL_PG**：Priority末轮展示丢弃合法TARGET_COORDINATE，10/20出现伪INVALID。保留两代精确坐标；Sector总体动态、缺历史保持UNKNOWN、非有限值拒绝；生命周期消费者也纳入缓存身份。
- **R9-F-02 — FIXED_NON_PIT_DERIVATION**：10/19按绑定Market限价、generation/freeze和原始daily行筛选来源；10/20旧Core与新Core的身份/amount包络不同，严格相等门保留，新候选明确重投影并同时绑定两版，未冒称原市场Owner一致。
- **R9-F-03 — FIXED_FROZEN_VECTOR_NOT_SEALED**：R43日更曾复制四场景聚合，诊断UNKNOWN污染正式双场景；统一到LAUNCH_CONFIRM/RECOVERY_TURN的现役合同，保留旧诊断、legacy结果和源seal缺口；Focus使用本次sector namespace。
- **R9-F-04 — FIXED_REAL_PG**：SourceIngress从固定历史两天改显式日期和版本化来源manifest；逐条回放真实ZIP；可用时间取完整下载后最晚时钟，旧缓存不可借提前时间。10/22、23真实PG全字段读回及重复幂等。
- **R9-F-05 — FIXED_REAL_PG**：as_of统一为数据日期，冲突拒绝；同token历史Index绑定对应日Owner。历史Home趋势取对应日轴，避免携带快照日趋势；损坏摘要与跨token拒绝。
- **R9-F-06 — FIXED_REAL_PG**：Forward observation/settlement使用请求内REPEATABLE READ只读快照；保留count+max水位以覆盖低ordinal迟提交。真实双连接、后提交低序号、高revision替换、并行读和精确结算分母校验通过。
- **R9-F-07 — FIXED_SCRIPT_EXECUTION_UI_WAIT**：R8预览页错误读取顶层published_sessions/trade_date，真实context包络下日期为空；按context.available_trade_dates和accepted_trade_date读取，Node实际执行脚本通过。

## 真实业务路径及 PG 结果

| 数据日 | 股票总体 | 可排序 | 不可排序 | 板块总体 | 可排序 | 不可排序 | Core/QFQ 坐标匹配 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-10-20 | 5224 | 675 | 4549 | 400 | 46 | 354 | 5217 |
| 2026-10-21 | 5224 | 936 | 4288 | 400 | 8 | 392 | 5216 |

路径一：真实 Core/adjusted/sector → 五会话 Lifecycle → Priority → 限定开发 PG → 全量独立 ID/score/排序/tie-break/排除原因/分母对账；两天均通过，重复写同版本幂等。10/20 Core 总体 5226，展示股票总体 5224，不能将坐标匹配数当作可排序数。10/20 板块 maturity UNKNOWN 332、health UNKNOWN 349；10/21 分别 386、391，未补造。最终 token、实际 revision schema、来源 SHA、完整排除分布见 JSON。原报告只看 canonical PG 表所得“Priority 至10/15、Lifecycle至10/13”不是整个数据库最新结论；本轮核对了实际 authority 绑定的 revision schema。

路径二：真实 TDX 官方 10/23 包（550096488 bytes，SHA `8e9a9f0cf51dcefe6c7a537eac710b716dabd2f8d4f5711984a6e74ec089b356`）→ 精确提取 10/22、23 → SourceIngress → PG 全字段读回。两日分别 5570、5572 条，第二次追加 receipt=false 且全部数值相同。schema `v4_r8_batch04_source_ingress`，收据5→7、bars27832→38974。可用时间为完整下载后 2026-10-23 18:40:53+08，10/22 为 RECONSTRUCTED_NON_PIT，10/23 为 CAPTURED_AFTER_CLOSE_NON_PIT。未把包日期当 SourceReady，也未将新数据切入正式 Head。

10/22 冻结 BaoStock 5225 行/38因子，与共同证券 TDX OHLCV 全部相同；新增代码 SZ.301718 仅是诊断证据，未写代码分支，同日 Identity/Member authority 仍缺。4789 条 amount 差异保持独立审计及 TDX 原值。10/23 缺对应 BaoStock 日线/因子；既有免费 ledger 10/10，本轮未增加 BaoStock 请求。本地 D: 只读 .day 全量尾部检查也不支持假报已更新至10/23。

路径三：真实候选 → 分日 PG ReadIndex → 主仓库新版 BFF。交付21 token 同时准备20/21两天，交付20 token另备20；真实分页不重叠、详情日期、坏 digest、跨 token、as_of 冲突、同一快照下历史数据日和 Home 趋势日期测试通过。snapshot_context_trade_date 与 data_trade_date 分开保留；不存在拿21数据伪装20的通过口径。

路径四：真实限价/Market/history/Core → 三日市场轴候选；10/19 known5194/5224、coverage0.9942572741，10/20重投影 known5195/5226、10/21 known5198/5224。10/20 breadth0.5815738964、participation0.7632092077；10/21分别-0.2131210435、0.7126576150。旧市场消费Core5224和新Core5226不同，不能签“消费相同”；新候选显式绑定两版且仍 NON_PIT。趋势仍 TREND_REFERENCE_NOT_BOUND_TO_CURRENT_PUBLICATION，综合 NOT_PUBLISHED_V4_03。

路径五：Forward 在既有候选事实 schema `v4_r8_forward_0c2b84fb3e1a0c42` 的历史研究计数73115，最新T0为10/21；精确成熟数与read_settlement的SETTLED合计均3260。双连接真实PG工程回归验证低ordinal后提交、高ordinal先提交、同observation高revision替换、请求中并发更新和6路并行读；工程schema `v4_r9_forward_contract` 留存21行合成事实，不作为业务来源。LIVE_OOS仍无首捕获，不用历史事实回填LIVE。

D0 冻结向量：10/20正式 TRUE141/FALSE5033/UNKNOWN52；10/21旧四场景为TRUE99/UNKNOWN5125，正确双场景为TRUE99/FALSE5076/UNKNOWN49。5076 条转换源于明确排除诊断场景聚合，保留旧状态/逐场景诊断，不是无依据将UNKNOWN改FALSE。source seal仍 CUTOFF_CONTRACT_UNRESOLVED，未改历史Owner或发行已接受新D0。

## 扫描、测试、性能和运行边界

严格扫描（未加allow-incomplete）：3973文件、Python 3275、JS 32、config 548、UI 44；652可达文件、11186边、38437候选。活动未知2214、维护未核验5003、动态未决82、浏览器位点25；自动确认违规0。状态 **GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED，exit1**。119个动态相关文件不能等同位点数。静态图保守包含配置证据引用，不凭路径就宣称实际执行，也不豁免可达tests。大清单仅留G，SHA/大小/复现命令见JSON。

新增/修改38个Python文件 AST错误0。业务代码扫描保留指数参考合同的明确类型例外、三项工程阶段权威的逐字段/消费函数/精确SHA例外；普通股票/板块和目标日由输入驱动。历史路径未获得整文件豁免。现存旧路线和未裁定配置继续OPEN；中文帮助、页面、报告及提交已检查。

最终主回归329 PASS+2 SKIP；两个需要外部真实候选输入的跳过分别以Owner 1 PASS、ReadIndex 1 PASS补证。后续指数可移植性17 PASS、查询/图/预览脚本/跨周月周期主流程11 PASS，集合重叠不相加。DuckDB只用于任务指定离线脚本的内存查询和测试Parquet；未查询或改用历史业务DuckDB数据库。命令、环境、库版本和全部XML尝试列于JSON。

失败均保留：早期SQL fixture别名、只读快照mock边界、历史默认路径触发非豁免基线、测试自行散列遗漏canonical换行导致token不一致、坏摘要更早在schema门拒绝，以及一次PG连接关闭。后续改用生产digest并真实读回，旧尝试不充最终Owner，不删除失败PG版本。一次官方下载器便利审计指针刷新已恢复原字节，新捕获有独立G盘收据。

真实规模性能：13桶各1冷+50热，663/663成功，另交付版Home51/51成功；总714次错误0。原批Home热P95 1227.250ms，交付版Home 1211.619ms；Forward带水位缓存P95 145.360ms、每次精确读取1748.175ms。首次Home冷读91655.908ms、交付版111933.049ms，**冷启动仍失败**。冷样本各1，不估算冷P95；完整图表/三并发计算未证。CPU i5-14600KF/14核20逻辑，Windows11；均为新版模块进程内BFF+真实PG，不冒称新版HTTP或浏览器性能。

旧PID HTTP：不带context token除context外409；先读context后携带其token，health及六入口、priority均HTTP200，但health/priority等仍可能SOURCE_INCOMPLETE，HTTP200不等于业务通过。旧token为14ee0cf8…ad378，T0为10/21。未重载新代码，S07仍UI_RUNTIME_NOT_RELOADED。

主仓正式运营Head仍10/09（55d78be5…dc83e），Accepted Data Head仍09/30（38e7c9b6…f3e40）；既有候选数据Head仍10/21（14ee0cf8…ad378）。真实Owner回归在前后比较了保护字节。GitHub branch Actions 查询为0 runs，不报CI PASS。

## 阶段、剩余事项与下一轮输入

| 阶段 | 本轮状态 |
|---|---|
| S00 | DEGRADED_PASS |
| S01 | PARTIAL_最新SourceIngress至10/23_全链Derived至10/21 |
| S02 | PARTIAL_实值市场轴_趋势和综合许可未闭合 |
| S03 | PARTIAL_真实Priority_Lifecycle_PG全量对账通过_新版HTTP未加载 |
| S04 | PARTIAL_双场景真实冻结向量通过_SourceSeal未闭合 |
| S05-D | BLOCK_CONTRACT |
| S05-I | NOT_IMPLEMENTED |
| S06-P | PARTIAL_受测热P95通过_冷Home明显超预算 |
| S06-I | PARTIAL_G2与单日计划通过_全链G1_G3_G4未重演 |
| S07 | UI_RUNTIME_NOT_RELOADED |
| S08 | NOT_RUN_NOT_AUTHORIZED |

G1/G3：Priority独立全量数值与来源绑定已验，但不冒充完整日更APPEND证明。G2：真实20/21前态Owner引用完全不变，compute_sessions各仅目标单日，历史仅窗口依赖；修订负例要求RANGE_REPAIR。G4：未发行R9新日PG publication，未重演真实完整候选CAS一胜/失败恢复；存在旧PG发布记录不能作为R9证明。

- **OPEN-01 严格字面量闭包**：活动未知2214、维护未核验5003、动态未决82、浏览器25；自动确认违规0不等于通过。旧路线维护项不列为V4重构授权；V4当前消费者与未知动态仍须独立裁定。
- **OPEN-02 D2合同**：入场冻结失效价的生成规则未定；S05-D BLOCK_CONTRACT、S05-I NOT_IMPLEMENTED，875旧episode不得伪回填PIT。用户明确交下一轮ChatGPT独立审计。
- **OPEN-03 D0来源封口**：CUTOFF_CONTRACT_UNRESOLVED；正式三态重放通过，不等于新已封口D0 Owner或PG发布。
- **OPEN-04 市场趋势与综合许可**：TREND_REFERENCE_NOT_BOUND_TO_CURRENT_PUBLICATION；综合仍NOT_PUBLISHED_V4_03；breadth正收益指示器与SIGN公式对照保留待裁定。
- **OPEN-05 真实续接来源/身份**：10/22多一个实际代码SZ.301718（只作证据，未写业务分支），same-day Identity/Member authority未发行；10/23缺BaoStock对应日线与因子。原免费来源ledger10/10，本轮BaoStock新增请求0。
- **OPEN-06 新完整日更与G1-G4**：真实PG Priority/Lifecycle/ReadIndex为新派生候选；未将其冒充Source→Core→全链新日发布。新日更代码不得偷换旧冻结policy；完整日更G1/G3、PG publication/CAS一胜及失败last_good本轮未重演。
- **OPEN-07 新版API/UI**：28766 PID52916未重载；正确token的旧HTTP六入口200仍含局部SOURCE_INCOMPLETE，不能证明新源码浏览器验收；28765无监听。
- **OPEN-08 性能**：13桶663次+交付Home复测51次共714次错误0；热P95通过受测2秒口径，首次Home91.656秒、交付版111.933秒；冷P95、完整图表/三并发日更预算未证。
- **OPEN-09 Focus/Forward权限**：Focus Priority排序规则未定义，仅对应子页阻断；其余关注页可读。LIVE_OOS无已授权首捕获cohort，不把历史73115条及3260成熟结算冒充LIVE。
- **OPEN-10 跨源Amount独立问题**：10/22共同证券OHLCV一致，4789条amount表示差异；保持TDX原值，无容差替换，不宣称跨模块审计通过。
- **OPEN-11 历史10/09全流水线复现**：只验证显式历史manifest冻结字节、两新日期和边界向量；原Owner/Head字节保留，未取得本轮真实10/09端到端数值/摘要重算证书。

D2两套待审规则：A按各场景已有结构锚点冻结失效价，缺锚点UNKNOWN，需要各场景源/时点/坐标闭合；B统一前20有效会话最低价，会新增退出语义，需要独立阈值裁定与回放差异。用户答复“交给下一轮ChatGPT独立审计”，本轮均未实施。

事件研究三文档保持DOC_PLAN_ONLY；event_batch.py未出现在当前V4静态闭包，未混入NE-01至NE-08或旧M14重构。

## 七提交75文件复核矩阵

CHANGED表示冻结七提交中的变更；下表状态表示R9处置。REVIEWED为差异/调用与合同复核，不代表完整运行验收；OPEN维护入口没有重跑全市场及重新接受历史输出。详细SHA和理由逐文件列于JSON。

| 文件 | R9处置 |
|---|---|
| `AGENTS.md` | NO_FUNCTIONAL_CHANGE |
| `config/core_product_index_benchmark_v1.json` | FIXED |
| `config/v4_active_runtime_entrypoints_v1.json` | REVIEWED |
| `docs/evidence/functional_r8_implementation_20261021/R8_GLOBAL_LITERALS_AND_FUNCTIONAL_CLOSEOUT_EVIDENCE.json` | REVIEWED |
| `docs/evidence/functional_r8_implementation_20261021/R8_GLOBAL_LITERALS_AND_FUNCTIONAL_CLOSEOUT_REPORT.md` | REVIEWED |
| `docs/research/da_event_research_sot_r1_20261023/A股全渠道新闻事件催化与题材映射研究流程规范_SOT_R1_20261023.md` | NO_FUNCTIONAL_CHANGE |
| `docs/research/da_event_research_sot_r1_20261023/INVENTORY_EVIDENCE.json` | NO_FUNCTIONAL_CHANGE |
| `docs/research/da_event_research_sot_r1_20261023/盘点与实施验收方案_R1.md` | NO_FUNCTIONAL_CHANGE |
| `run_breakout_prep_v2.py` | NO_FUNCTIONAL_CHANGE |
| `run_early_mover_v2.py` | NO_FUNCTIONAL_CHANGE |
| `run_forward_observation.py` | NO_FUNCTIONAL_CHANGE |
| `run_live_forward.py` | NO_FUNCTIONAL_CHANGE |
| `run_phase0_2b.py` | NO_FUNCTIONAL_CHANGE |
| `run_priority_v2.py` | NO_FUNCTIONAL_CHANGE |
| `run_r3_integrated_seal.py` | NO_FUNCTIONAL_CHANGE |
| `run_sector_leader_v2.py` | NO_FUNCTIONAL_CHANGE |
| `run_shadow_v2.py` | NO_FUNCTIONAL_CHANGE |
| `run_steady_trend_v2.py` | NO_FUNCTIONAL_CHANGE |
| `run_strong_pullback_v2.py` | NO_FUNCTIONAL_CHANGE |
| `scripts/a12_build_v4_05_r4_core_profile_r1.py` | OPEN |
| `scripts/a12_r2_build_v4_05_r4_core_profile.py` | OPEN |
| `scripts/accept_v4_dm01_baostock_runtime.py` | OPEN |
| `scripts/build_fp05_market.py` | OPEN |
| `scripts/build_fp06_sector.py` | OPEN |
| `scripts/build_v4_02_dated_trading_status.py` | OPEN |
| `scripts/build_v4_02_formal_periods.py` | FIXED |
| `scripts/build_v4_02_full_market_isst.py` | OPEN |
| `scripts/build_v4_02_price_limits.py` | OPEN |
| `scripts/build_v4_02_price_limits_generic.py` | OPEN |
| `scripts/build_v4_05_r3_core_profile.py` | OPEN |
| `scripts/build_v4_05_r3_market_regime.py` | OPEN |
| `scripts/build_v4_05_r4_core_profile.py` | OPEN |
| `scripts/check_v4_business_literals.py` | FIXED |
| `scripts/run_v4_04_full_market_candidate.py` | FIXED |
| `scripts/run_v4_04_full_market_candidate_r4.py` | FIXED |
| `scripts/v4_02_build_raw_selected_v2.py` | OPEN |
| `scripts/verify_a02_a05_a04_scoped_r3.py` | OPEN |
| `src/phase0_2a_runner.py` | NO_FUNCTIONAL_CHANGE |
| `src/phase0_2b_runner.py` | NO_FUNCTIONAL_CHANGE |
| `src/production/release.py` | NO_FUNCTIONAL_CHANGE |
| `src/upgrade_m1.py` | NO_FUNCTIONAL_CHANGE |
| `src/v4/accepted_input.py` | REVIEWED |
| `src/v4/replay_r3_guards.py` | REVIEWED |
| `src/v4/scoped_promotions_r3.py` | REVIEWED |
| `src/workbench_analysis/corrected_sector_replay.py` | REVIEWED |
| `src/workbench_analysis/dm01_accepted_builder_registry.py` | REVIEWED |
| `src/workbench_analysis/dm01_accepted_chain_v1.py` | REVIEWED |
| `src/workbench_analysis/dm01_publication_history_reader_v1.py` | REVIEWED |
| `src/workbench_analysis/dm01_publication_history_reader_v2.py` | REVIEWED |
| `src/workbench_analysis/historical_stage_governance_r17.py` | REVIEWED |
| `src/workbench_analysis/operational_daily_owner_v1.py` | FIXED |
| `src/workbench_analysis/operational_product_pack_v3.py` | FIXED |
| `src/workbench_analysis/source_authority_owner_bootstrap_r1.py` | REVIEWED |
| `src/workbench_analysis/tdx_member_retro_r43.py` | REVIEWED |
| `src/workbench_analysis/v4_current_stage_authority.py` | REVIEWED |
| `src/workbench_db/forward_r7_store.py` | FIXED |
| `src/workbench_desktop/qa.py` | REVIEWED |
| `src/workbench_desktop/qa_daily.py` | REVIEWED |
| `src/workbench_service/core_product_bff_r1.py` | FIXED |
| `src/workbench_service/core_product_server_r1.py` | REVIEWED |
| `src/workbench_service/operational_daily_server_v1.py` | REVIEWED |
| `src/workbench_service/operational_gap_bff_v2.py` | REVIEWED |
| `src/workbench_service/production_v4.py` | REVIEWED |
| `src/workbench_service/static/r43-operational-preview.html` | FIXED |
| `src/workbench_service/v4_control_server_v2.py` | REVIEWED |
| `src/workbench_service/v4_server.py` | REVIEWED |
| `tests/test_fixed_qfq_samples.py` | REVIEWED |
| `tests/test_phase0_2b_dynamic_anchor.py` | REVIEWED |
| `tests/test_r8_candidate_priority_cache_key.py` | REVIEWED |
| `tests/test_scoped_promotion_dynamic_dates.py` | REVIEWED |
| `tests/v4_04/test_accepted_input.py` | REVIEWED |
| `tests/v4_04/test_all_rule_branches.py` | REVIEWED |
| `tests/v4_05/test_replay_gate_a_r3.py` | REVIEWED |
| `tests/v4_joint/test_operational_product_pack_v3.py` | FIXED |
| `tests/v4_policy/test_no_production_hardcoded_identities.py` | FIXED |

上述75文件全部纳入矩阵：FIXED12、REVIEWED30、NO_FUNCTIONAL_CHANGE19、OPEN14。另有R9实际依赖修复和回归，共42个代码/合同/测试变更文件。原R7/R8报告及大型清单未覆盖或删除；用户原有.githooks、config_back、script_back及本轮未跟踪探索证据保留。

机器证据：`R9_INDEPENDENT_AUDIT_REPAIR_EVIDENCE.json`。该JSON不包含凭据；大型原始清单、样本、失败和PG绑定均有本地路径、SHA及大小。后续审计应重新取远端最新HEAD，以代码、PG范围和明确局部缺口核验；本轮自评及推送均不代表外部接受。

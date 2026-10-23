# V4 R8 硬编码实修与功能闭环报告

记录日期：2026-10-23（Asia/Shanghai）
开发分支：`codex/v4-unified-development`
本轮基线：`df6e312f773500f300d435cd51910961c79f7475`（与抓取时 `origin/codex/v4-unified-development` 一致）
实现提交：`e33e3243a`（已推送至 `origin/codex/v4-unified-development`）
验收状态：`V4_REPAIR_PARTIAL / EXTERNAL_REVIEW_BLOCKED`

## 范围和结论

本轮按用户最新限定只处理 V4 当前代码及模块功能。早于当前 V4 功能链的旧版业务代码和历史无用工具不属于本轮修复范围。目标交易日、证券全集、前态与来源应从当前调用、已接受输入/Owner 和交易日历解析；有日期的来源文件名、规则生效日、哈希绑定及历史合同只作为证据候选，不视作当前交易日计算参数。

本轮实际修改了 V4-02 输入解析、V4-04 候选运行、前向观察封存、来源/阶段治理、Owner/发布保护、市场基准合同及全局字面量扫描器；增加了回归测试。**代码与回归有实质进展，但没有达到 R8 完整功能闭环，也没有证据证明全部历史 V4 合同字面量都已逐项裁定。**扫描门仍阻断；不得据此报告全局硬编码 PASS。

## 实际改动

- V4-02 正式周期、交易状态、价格限制及全市场输入构建器改为显式输入来源路径；价格限制边界由当前接受输入/交易日上下文推导，移除业务默认的冻结路径和交易日。
- V4-04 全市场候选运行从已接受输入解析 cutoff，并参数化查询；接受输入解析器携带当前来源 cutoff。
- V4-01/V4-05 相关 Owner、Profile、行情、SourceAuthority 解析和发布校验改为由现行 Head、来源合同及输入参数确定目标范围；V4-02 raw selected 构建要求显式 `--asof`。
- 前向观察和 R3 集成封存入口要求调用方传入 cutoff；模型和基线按已封存身份/收据绑定读取，不以固定历史目录推断当前业务日。
- FP05/FP06 从接受输入读取当日 universe 与交易状态；BaoStock 运行接受要求显式日历收据，避免隐式使用旧日期日历。
- 核心市场产品的指数身份从带版本、SHA 绑定的市场基准合同读取；新增重复基准拒绝和动态合同回归。
- V4 服务、BFF、桌面 QA 与页面中的目标日/阶段读取使用当前上下文；阶段 0 anchor、Owner 来源及日期范围校验按接受输入解析。
- Priority 规则分支修正：已知 FALSE 主原因支配必需未知的组合，保留非支配未知场景的 UNKNOWN；补充两类分支回归。
- 全局字面量扫描器增加源码入口 SHA 绑定、显式入口清单、compact 日期/证券识别中的十六进制摘要边界，以及窄化的语法/证据误报判定。入口合同只证明源码清单，不证明正在运行的进程加载了该源码。

变更矩阵与完整文件清单以本次 Git 提交为准；未纳入提交的工作区文件保留原样。

## 回归与扫描证据

执行环境临时目录：`G:\\codex_tmp\\test_temp`；没有在 TDX 源目录创建或修改文件。

| 回归 | 命令覆盖 | 结果 |
|---|---|---|
| 功能/策略 | `tests/v4_policy/test_no_production_hardcoded_identities.py`、`tests/v4_joint/test_operational_product_pack_v3.py`、R8 S01/S03、Priority cache、S3 ledger、UX R2 合同 | 102 passed |
| V4 主链 | `tests/v4_02`、`tests/v4_04`、`tests/v4_05`、`tests/v4_scoped_promotions_r3`、`tests/upgrade_m1`、QFQ、Phase0 动态 anchor、scoped promotion 日期 | 243 passed |
| 变更 Python 语法 | 62 个变更 Python 文件 AST 解析 | 0 失败 |
| Git 空白检查 | `git -c core.whitespace=cr-at-eol diff --check`（含暂存差异） | 通过 |

全局扫描命令：

```powershell
python scripts/check_v4_business_literals.py --output G:\\codex_tmp\\R8_GLOBAL_LITERAL_INVENTORY_FINAL.json --allow-incomplete-inventory
```

清单 SHA-256：`cf29f40cdfb3b16faead7d6286b07c6ea061d1d872d9393f3615dce8a2260054`，大小 39,705,056 字节。扫描覆盖 3,962 个跟踪文件（3,266 Python、32 JS/TS、546 配置、100 SQL、44 UI）；Python 入口/依赖图 606 节点、10,348 边、133 个动态执行/导入站点，AST 失败 0。扫描结果为 `GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED`：活动未知候选 2,135、未核验维护候选 5,002、自动确认活动违规 0、活动入口状态 `SOURCE_VERIFIED`。其中活动未知候选主要集中于历史/版本化 V4 配置：`v4_joint_release_authority_v1.json` 828、`v4_replay_compare_authority_v1.json` 802；其余分布于规则有效期、日历事实、历史身份及证据绑定。零自动确认违规不等于逐条独立证明无违规。

此前提交修复了多处当前运行输入和目标日默认值，但全量复扫发现不能把结论扩大为“V4 所有业务代码已无固定日期”。例如 `src/workbench_analysis/operational_daily_owner_v1.py` 仍把 `BASE`、`ACQUISITION`、任务合同和种子回放来源绑到 2026-10-09 目录；这是可达的 V4 日更 Owner 路径，虽不是目标日比较分支，仍会让日更依赖固定历史来源。R4.3 回放/适配链的多个模块也保留固定证据根路径。本轮没有将这些路径改造为由现行 Head/调用输入解析，因此它们是明确未完成项，不能宣称全 V4 硬编码已修完或完整流程已不受影响。

### 全量 V4 非测试范围复扫（2026-10-23）

按用户补充要求，对仓库中 V4 相关源码、运行配置及 V4 维护脚本重新筛查，并排除 `tests/` 及文件名明确标记为 test/verify/audit/check/probe/reproduce/characterize 的测试或验证脚本。扫描器仍是字面量召回工具，不把结果数直接当作缺陷数。按本次 V4 路径筛选得到 25,337 个字面量候选，其中入口图可达 1,971 个；主候选簇是带版本和数据绑定的历史联合发布/回放合同、法规规则有效期和交易日历事实。

对活跃源码候选的语义核对结论：普通股票代码候选落在 SQL 排序哨兵、证券/身份术语或版本化市场指数合同；板块候选落在 TDX 元数据目录 `T0002`、Python 条件表达式误识别和动态 `industry` 值；未见这些值参与针对某个普通股票或具体板块代码的业务分支。日期候选多数为审计/证据路径，但 `operational_daily_owner_v1.py` 的固定历史来源目录已确认仍被其日更准备逻辑读取，是需要后续修复的业务依赖。V4 维护脚本中的固定历史来源/验证日期也仍待逐项裁定；凡其继续作为正式日常输入入口，必须改为从接受 Head、日历或显式调用参数解析。

因此，准确结论是：已修复部分当前业务默认/分支硬编码；未证明 V4 仓库所有日期型字面量均已消除，也未完成所有配置/维护脚本候选的逐项人工裁定；V4 日更 Owner 仍有固定历史来源目录依赖。全量候选清单仍由全局扫描器在 `G:\\codex_tmp\\V4_NONTEST_BUSINESS_LITERAL_INVENTORY.json` 生成；其 SHA-256 和复扫筛选统计记录在机器证据的 `v4_non_test_scope_scan` 字段。当前活跃普通股票/板块身份扫描结论不替代服务进程读回或全业务闭环验收。

#### 未去除候选与逐类处理理由

本节补充扫描候选的语义归类。候选数量是匹配次数，不能等同唯一代码/日期数量或缺陷数；同一值可能在文件中重复出现。扫描范围为 V4 非测试源码、配置及正式维护脚本，明确排除 `tests/` 和按文件名识别的测试/验证脚本。没有因“历史”标签而把所有候选判为正确：凡固定路径仍影响可达的日更/回放流程，均单列为未完成项。

**股票/证券形状候选。** 本次在活跃 V4 源码/配置中没有确认到针对某个普通个股代码的业务分支。仍出现的值及原因如下：

| 候选 | 位置 | 语义及未去除理由 |
|---|---|---|
| `000001`、`399001`、`399006`（含 `SH.000001`、`SZ.399001`、`SZ.399006`） | `config/v4_market_reference_instruments_v1.json` | 带类型/角色的沪深市场指数参考工具（`MARKET_INDEX`），用于市场基准与覆盖校验，不是个股默认值或个股专属分支。作为明确版本化的指数身份保留；若要更换，应更新基准合同及其摘要/消费者，不能仅删字面量。它们仍是固定证券身份，因此“普通股票代码分支未发现”不等同“全部证券代码字面量已消失”。 |
| `sh000001`、`sz399001`、`bj899050` | `config/v4_02_canonical_daily_pit_contract_v1.json` | 指数日线文件路径/市场参考来源标识，属于固定索引输入合同；保留以维持历史 canonical PIT 输入身份，尚未改为独立的动态指数来源目录。 |
| `621404` | `config/v4_02_price_limit_rules_r3.json`、`config/v4_02_price_limit_rules_v1.json` | 官方来源 URL 中的文档编号，不是证券代码；保留来源引用以便追溯规则依据。 |
| `152128`、`182128`、`846023` | `config/v4_joint_release_authority_v1.json` | 分别命中 `bytes` 字节数和时间戳毫秒数等字段，属证券形状误报，不参与证券选择。 |
| `646711` | `config/v4_read_index_authority_r1.json`、`config/v4_read_index_authority_r2.json` | PostgreSQL `database_oid`，不是证券身份，保留数据库对象身份元数据。 |
| `999999` | `src/workbench_db/postgres_repository.py` | SQL 排序/空值哨兵，不是证券代码，不驱动个股业务分支。 |

**板块/行业形状候选。** 活跃源码中未确认针对具体行业、主题或板块代码的业务分支。`T0002` 位于 `src/v4/contracts/source_overlap.py`，表示通达信元数据目录路径组件，不是业务板块分类代码，保留以定位元数据文件。`src/workbench_analysis/v4_15_settlement.py` 的 `industry:candidates` 是扫描器对 Python 条件语法的误识别，实际 `industry` 来自动态输入。配置/序列化候选仍须由调用链核验；本结论不覆盖将来新增的板块代码硬编码。

**日期候选簇及保留原因。** 最大的可达日期簇如下。保留的前提是它确实作为历史事实或证据身份被消费；不能把这些值当成当前目标交易日默认值。配置仍含固定日期，未来如需把历史合同变成可复用的运行合同，应新增动态输入/版本迁移而不是篡改既有证据身份。

| 文件/候选数 | 为什么没有删除 | 当前判定 |
|---|---|---|
| `config/v4_joint_release_authority_v1.json` — 823 | 联合发布历史快照、Owner、来源和 UI 资产的日期/身份绑定；下游按清单校验精确候选，另有历史 UI 回退消费者。删除/替换日期会破坏证据与摘要绑定。 | 历史权威合同事实；非当前交易日参数。消费者仍需逐项复核。 |
| `config/v4_replay_compare_authority_v1.json` — 802 | 历史回放数据集目录及 `as_of` 身份；回放入口校验 `trade_date` 与输入 Head。 | 历史回放样本身份；不是当前查询默认值。 |
| `config/v4_02_price_limit_rules_r3.json` — 44；`..._v1.json` — 32 | 价格限制规则的 `rule_id`、来源引用、`valid_from`/`valid_to`、边界/截止事实。需要按目标日选择有效规则，规则本身的有效日期不能删除。 | 版本化法规/规则事实；应由目标日动态匹配，不能硬编码选中某日。 |
| `config/v4_official_exchange_calendar_v2.json` — 32；`config/v4_dm01_bridge_calendar_v1.json` — 17 | 交易所日历/桥接日历的实际开市日期是业务事实。动态性来自按目标日查历，不是删除日历中的日期。 | 有来源的日历事实；保留并要求合同/来源可审计。 |
| `config/v4_02_canonical_daily_pit_contract_v1.json` — 10；`config/v4_02_formal_period_contract_v1.json` — 7；`config/v4_02_full_market_isst_contract_v1.json` 等 V4-02 接受合同 | 固定快照、历史接受输入、来源截止点和产物名绑定。其中特定 cutoff 属合同数据而非通用默认值；当前是否仍被生产型入口直接依赖尚未全部逐项确认。 | 版本化历史接受证据；若被当作常规运行默认，则仍需修复。 |
| `config/v4_11_*_candidate_d2_contract_v1.json`、`v4_11_confirmation_detector_contract_r2.json`、`v4_dm01_accepted_builder_registry_v1.json` — 每文件约 5–14 | R3/R4/R5 候选、探测和已接受构建登记合同中的历史窗口、日期及源锚点。它们用来固定可复现的候选/证据身份。 | 历史候选合同/登记事实；不应隐式替代当次调用日期。 |
| `config/v4_current_accepted_read_contract_v1.json` — 6；`config/v4_read_index_authority_r1/r2.json` | 接受读取锚点、索引版本及历史 `as_of` 身份。上下文代码按锚点 Head 派生日期，当前接受合同仍含固定回退锚点。 | 版本化回退权威；需要确认所有当前读取调用均优先走现行运行权威。 |

**仍未修复的可达日期/路径依赖。** 下列内容没有删除，不能以“历史路径”直接结案：

| 代码/脚本 | 未去除内容 | 为什么仍在/影响 | 后续处理状态 |
|---|---|---|---|
| `src/workbench_analysis/operational_daily_owner_v1.py` | `BASE`、`ACQUISITION`、任务合同及 replay/core/seed 的 `2026-10-09` 固定路径 | 被 `operational_daily_ready_owner_v2` 和 `scripts/replay_dynamic_daily_owners_v1.py` 使用；日更准备仍读取固定历史证据目录。此前没有改造为当前 Head/调用输入派生。 | **确认未修复的 V4 业务依赖**；需动态解析来源并覆盖 Owner 日更链回归。 |
| `src/workbench_analysis/r43_owner_replay.py` | `2026-10-09`、`2026-10-01` 的 replay/acquisition/frozen/snapshot/delta 路径 | 有服务侧只取证据 helper 的消费者，但模块自身也含固定日期回放逻辑；不能因部分消费者只 import helper 就认定整体无影响。 | 回放入口尚未逐个与当前 V4 正式调用合同解耦，列为待修/待证明。 |
| `src/workbench_analysis/r43_structure_replay.py`、`r43_focus_replay.py`、`corrected_owner_replay.py`、`corrected_focus_replay.py`、`corrected_sector_replay.py`、`producer_bootstrap_v1.py`、`tdx_member_retro_r43.py` | 日期命名的 acquisition、snapshot、replay 输入/输出路径 | 这些入口仍指向历史 R4.3 证据。保留源证据可用于复现，但如果它们仍承担正式可复用回放/构建入口，固定目录会妨碍换日/换输入。 | 未逐项确认所有调用是否仅历史复现；仍列为非测试 V4 源码候选，不能称全部已修。 |
| `scripts/run_dm01_a01_r3_chain.py` | 固定历史日历及 V4-02 R7 日/周/月/状态/ST/价格产物路径 | cutoff/目标 session 可从接受 Head/日历推导，但脚本输入文件名仍固定到历史产物。此前按旧 R3 链构建器保留；若继续作为正式日常 builder，必须从输入合同解析路径。 | **未证明可复用性**；需确认入口状态并动态化仍在用的路径。 |
| `scripts/build_v4_08_r2_membership_evidence.py` | R7 固定身份路径、接受 cutoff、ingested 时间及 stale/asof/validation 日期向量 | 用来构造冻结 R2 证据；部分日期是负例/校验向量，不是目标日默认。脚本位于正式 `scripts/` 而非测试目录，因此仍在本次非测试扫描范围。 | 保留原冻结证据生成行为；若作为维护工具持续使用，需把不可变证据复现与通用 builder 分离并显式参数化。 |
| `scripts/fp01_evidence.py`、`forward_final_bootstrap.py`、`next_round_bundle_r1.py`、`promote_dm01_a01_r3_data_head.py`、`promote_v4_09_accepted_head.py`、`v4_production_cutover_evidence.py` 等 | 日期化 evidence 目录、候选 promotion 或接受快照路径 | 多为单次/历史证据事务脚本，保留可重放来源与审计身份；并非因此自动豁免通用要求。当前是否仍有持续调用入口未逐项验证。 | 候选未逐项裁定；持续运行用途若成立，需改为显式输入并保留历史证据不可变性。 |
| `src/workbench_analysis/source_authority_producers_r4.py`、`dm01_accepted_chain_v1.py`、`src/v4/a02_a05_external_acceptance_r1.py`、`scoped_promotions_r3.py`、`parallel_scoped_acceptance_r1.py`、`stock_prewatch.py` | 日期化审计/任务文档和 SHA 绑定的来源路径 | 多数是精确来源/审计证据引用而非目标交易日参数；替换会破坏可追溯性。但尚未对每个消费者证明路径只用于审计、不参与业务输入选择。 | 保留证据绑定，同时保持候选状态；仍需消费者级核验。 |

另有 `src/workbench_service/legacy_feature_matrix.py` 中日期形状文本疑似 V3 工单编号，不是交易日；该模块不属于本轮 V4 功能链修复目标，但因为入口图/路径筛选候选，记录为范围识别结果而非已修复项。`src/v4/contracts/source_overlap.py` 的 `T0002` 和 settlement 的动态 `industry` 同理是语义误报，不涉及删除业务身份。

综上，股票/板块扫描没有确认出普通个股或具体板块的硬编码业务分支，但仍保留了明确类型化的指数证券身份、元数据目录和非身份误报；日期扫描发现的历史合同/日历/规则事实按身份保留。**这不代表用户要求的“V4 全部业务代码动态化”已经完成**：`operational_daily_owner_v1.py` 是确认的运行依赖问题，R4.3 replay 模块、R3 链构建脚本及维护脚本仍有固定日期路径，需按其当前调用用途逐项修复或以调用/部署证据证明只是不可变历史复现。候选全集及每条匹配仍以机器清单为准，以上表格是重点簇摘要而非逐项清单。

## 阶段状态（R8 R2）

| 阶段 | 本轮状态 | 证据与未完成项 |
|---|---|---|
| S00 基线/阶段0 | `DEGRADED_PASS` | 基线为远端 HEAD `df6e312…`; 阶段0限于代码修复、回归和 PG 只读核对。无候选 Head、正式 Head 或生产服务更新。 |
| S01 来源/摘要/缓存 | `PARTIAL` | 输入绑定与摘要路径有代码/测试覆盖；当前运行进程未加载本轮代码，不能完成真实冷/热 API、来源变更、坏 SHA 和消费者负例读回。 |
| S02 市场宽度/趋势 | `PARTIAL` | 目标日/来源路径更动态，市场参考有版本化合同；本轮未完成真实全市场独立数值对账及来源权限验收。 |
| S03 Priority | `PARTIAL` | 规则分支与数值边界回归通过；开发 PG 的 10/20、10/21 Priority Owner 缺失，`/api/v4/priority` 对旧进程返回 409，不能完成全集和真实 API 对账。 |
| S04 D0 | `PARTIAL` | 来源/日期/权限链检查改动；当前 Head 与开发 PG 无本轮对应 Owner，真实封存链和四场景全集未验证。 |
| S05-D / S05-I D2 | `BLOCK_CONTRACT` / `NOT_IMPLEMENTED` | R8 合同仍缺适用 D2 阈值生成、冻结时点和价格坐标裁定；不自行选择前低、均线或百分比，875 个历史 episode 未回填。 |
| S06-P / S06-I 日更 | `NOT_VERIFIED_THIS_ROUND` / `NOT_RUN` | 本轮未执行 G1–G4 独立比较、候选 PG 接续、CAS、故障恢复或日更性能采样；真实来源/Owner 前态不齐。 |
| S07 六入口 | `UI_RUNTIME_NOT_RELOADED` | 28766 仍运行旧临时脚本；`/api/v4/context` 返回旧 T0 2026-10-21，`/api/v4/health` 和 `/api/v4/priority` 返回 409。没有浏览器 DOM 或新代码页面读回。 |
| S08 正式发布 | `NOT_RUN / NOT_AUTHORIZED` | 没有 formal Head、生产调度、运行包或 28765 操作。代码推送不构成发布验收。 |

## PG、服务和保护边界

- PostgreSQL：`127.0.0.1:5432/market_research`。查询使用已有安全配置，首语句 `SET TRANSACTION READ ONLY`；`transaction_read_only=on`。本轮无 DDL/DML、Owner 发布、回填或重算。
- 只读核对未发现 2026-10-20/21 Priority Owner 或 Sector lifecycle Owner；最近已存在 Priority Owner 为 10-15，Sector lifecycle Owner 为 10-13。当前操作 Head 仍是 2026-10-09；Accepted Data Head 为 2026-09-30。
- 网页/API：28765 未监听；28766 仍为 PID 52916，命令行为 `E:\\python\\python.exe G:\\codex_tmp\\batch10r4_28766.py`。未停止或重启该进程。5432 的 PostgreSQL 主监听 PID 为 8640。
- 28766 的旧进程 `/api/v4/context` HTTP 200、状态 READY，但显示旧 T0 2026-10-21；`/api/v4/health` 与 `/api/v4/priority` HTTP 409。它不是本轮代码验证。
- 未删除或清理工作区文件/目录；未写入 D:/new_tdx 或其它 TDX 只读源目录；未切换正式 Head 或 28765。

## 剩余问题与下一轮独立验收

1. 在本轮代码部署/加载至获准的 28766 前，R8 S01、S02、S03、S04、S07 只能以回归覆盖，不可宣称实际服务闭环；下一轮需保持 28765 不动并按已授权的开发槽位流程验证。
2. 开发 PG 的 10/20、10/21 Owner 前态/来源缺失，Priority、D0、Sector、Focus/Forward 无本轮统一 token，需先判断可用输入和候选生成门，再按 R8 原合同逐日验证。
3. S05-D 业务合同裁定缺失，阻止 D2 实现和相关整链验收；这是语义门，不以代码选择代替。
4. S06-P/S06-I 的候选 G1–G4、增量日期范围、CAS/幂等/恢复和性能数据尚未产生。
5. 全局字面量扫描器仍为阻断。对 V4 当前配置中版本化来源/监管规则/日历事实与历史证据绑定需按消费者逐项核验；本轮没有把扫描器未分类候选列为通过，也不把旧非 V4 代码恢复为本轮目标。
6. `CI_NOT_RUN`；无全量性能压测；无外部来源调用、权限提升或正式发布验证。

本报告是开发修复记录，不是独立审计结论或生产准入。机器证据见同目录 `R8_GLOBAL_LITERALS_AND_FUNCTIONAL_CLOSEOUT_EVIDENCE.json`。

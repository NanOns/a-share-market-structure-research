# 大A V4｜R4.1 截至 2026-10-08 四交易日：通达信 + BaoStock 主动补采与数据源治理修复任务卡

> 版本：R4.1｜2026-10-09｜在 R4.0 基础上扩大交易日期范围，不改变历史收据｜性质：**纠正 R3 源获取策略的专项执行合同**（不是又一轮只读审计）  
> 目标分支：`NanOns/a-share-market-structure-research` → `codex/v4-system-reform`  
> 起始审计 HEAD：`f95835e8ee415367da623e656685b1aa5ad64c4c`。启动时必须重新核对并冻结当时 HEAD。  
> 正式衔接：Driver R3《三日数据算法修复：连续执行与强制闭环任务卡》、原三日专项总卡、`AGENTS.md`、R3 实际执行报告 `docs/evidence/three_day_repair_r3_20261008/R3_EXTERNAL_AUDIT_HANDOFF.md`。  
> **当前任务最后完成交易日：2026-10-08；四个目标交易日：2026-09-28 / 09-29 / 09-30 / 10-08。** 10/09 为执行日但不属于截至发卡时已完成的交易日。
> **本次用户纠偏：缺少数据或能力时，必须首先实查本机通达信、通达信官方可用源与 BaoStock；旧包、仓库归档和既存收据只能用于验证、缓存及可追溯回放，不是“上游无法提供”的证明。**

## A. R4.1 最高优先级：时间范围与交易日定义（覆盖本卡所有章节）

| 项目 | 统一规定 |
|---|---|
| 执行审计截止时间 | 2026-10-09，盘前；不要伪造 10/09 当天完整行情 |
| **专项目标区间** | **2026-09-28 至 2026-10-08（闭区间，按交易所日历过滤）** |
| **实际需处理交易日** | **2026-09-28、2026-09-29、2026-09-30、2026-10-08，共 4 日** |
| 非交易日 | 2026-10-01—2026-10-07 国庆节休市；不抓取假日 K 线，不创建假日期状态 |
| 已有三日证据 | 9/28、9/29、9/30 的 528 条 QFQ 能力缺口（176/日）、35 条停牌无 BAR 是**旧基线**；必须保留，不代表 10/08 的缺口数量 |
| 新增 10/08 | **全市场增量数据获取 + 新日数据头 + 个股/板块/指数/Focus/Forward 消费、专项差异排查**，不能只为上一轮 176 只股票补三日 |
| 历史链 T-1 | 对 2026-10-08，最近前一交易日是 **2026-09-30**，不是 10/07；按正式交易日历取窗口 |
| T-2 / T-3 | 对 2026-10-08，T-2=2026-09-29、T-3=2026-09-28；对于 2026-09-30，T-3=2026-09-24（9/25—9/27 为中秋休市）。不得把 9/25 标为 9/30 的 T-3 |
| 目标发布 | **优先完成 10/08 全量真实源读取及可接受数据的当日日更**，与前三日 corrected repair 分开准入；保留 9/30 当前已发布版本作为 last-good，直到 10/08 发布被正式验证并通过 CAS |

交易日来源：上海证券交易所《关于2026年部分节假日休市安排的通知》及深圳证券交易所 2026 年中秋节、国庆节休市安排（官方 URL：`https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml`；`https://investor.szse.cn/disclosure/notice/general/t20260917_622911.html`）。这些日历事实必须在本机交易日历/流水线再次核对。**禁止仅按自然日循环或采用旧的三日硬编码。**

**R4.1 新强制验收：**报告必须输出四个交易日各自的 `source_requested/source_received/accepted/raw_gap/qfq_gap/owner_ready/known_unknown/live_readback`。10/08 必须有真实通达信/官方和 BaoStock 对应源请求或带有真实错误的收据；如果缺数据，应先启动补采，不能因为最新已接受快照停在 9/30 就当成“没有新的完整交易日”并直接 NOOP。重放时要区分「10/08 官方确实尚未发布」与「尚未查询」「旧包不含当日」。

## 0. 审计确认的事实与根因

- R3 新增的 `execute_r3_remaining_evidence.py` / `execute_r3_closure_evidence.py` 基本围绕既有 accepted artifacts 和当前生产快照做证据回放，没有完成针对缺口的系统化 **live TDX/BaoStock 重新查询→对比→回填→正式准入** 链路。
- 2026-09-28 / 09-29 / 09-30 的**原三日基线**中，每天 176 条有交易的记录属于 `ADJUSTMENT_CAPABILITY_UNPROVEN`，总计 528 条**日证券记录**；另有 12 / 12 / 11 条停牌无 BAR 合计 35 条。原报告 RAW 可用性不缺的判断与 QFQ 能力未证明可同时为真。**先处理复权来源/算法，不得将 528 条叫作缺 RAW。**
- 9/30 股票基础 Profile 已有真实字段；但 5,213 股票七项结构输出 0 known、378 板块 Rotation 均 UNKNOWN。**历史有效成员、V4-12 Owner/前 ATR、V4-13 runtime、RPS T-3 属于不同种类问题，不能一律归因为“包里没有”。**
- 已有数据采集功能：`scripts/run_v4_dm01_daily_increment.py`、`scripts/capture_baostock_daily_update.py`、`scripts/capture_dm01_a01_r2_historical_baostock.py`、`scripts/capture_tdx_official_daily_package.py`、`src/workbench_analysis/baostock_supplemental.py`、`src/workbench_analysis/baostock_daily_update_source.py`。
- 当前 `config/v4_daily_source_freeze_v2.json`：TDX canonical RAW；BaoStock 为补充交叉验证；`ohlc_substitution_for_tdx=false`、`bao_stock_never_substitutes_tdx_raw=true`；`src/workbench_analysis/baostock_supplemental.py` 亦将 BaoStock 限制为非价格权威。**旧合同禁止的回填不能用改一个布尔值绕过，需要明确的新版本准入、迁移说明、独立检验。**
- 当前 live scoped 9/30 联合发布可用，`config/v4_joint_release_authority_v1.json` SHA-256 `8d342393fe129596d2f9438428b48ff3839f846313777d17adf7d6a65e9f2298`、snapshot SHA-256 `d9d052fdf912c0975f5bfca0cd1067fe4a47fde99d804ce356c266da960e72f3`。不得因为补采覆盖该快照或改旧收据。

## 1. 最高执行目标与不可接受的结束方式

**目标 A**：以 9/28、9/29、9/30、10/08 四个已完成交易日为范围，给全市场与缺口创建真正主动的数据源查询路径和可重复运行的差异清单；在用户本机能联网、接口可用时实际执行，而不是只检查已归档的 ZIP。  
**目标 B**：针对前三日每日至少 176 条既有复权能力缺口及 **10/08 实测得到的全市场新增缺口（数值动态确定）**，明确补获数据、QFQ 构建能力、跨源差异和不能修复的最小原因；对能修的逐日重建 corrected Owner。  
**目标 C**：完整复核股票结构、板块历史成员的真正依赖并继续修生产者；数据源补采不能变成免除算法代码修复的理由。  
**目标 D**：只在新的数值与来源门禁通过后执行安全 scoped successor 发布；旧 live last-good 继续可读。

**禁止结束理由**：仅凭旧 `PACKAGE_ORACLE.json`、本地 `.day` 截止 9/10、当前仓库 `data/` 无文件、以前的 `NOT_VERIFIABLE`、BaoStock 未通过“旧版只读运行时权限”之一就写成“全部外部不可获得”。必须区分：**没有尝试 / 尝试失败 / 被合同阻止 / 上游确实无数据 / 源可用但转换失败 / 正式 PIT 不可证明**。

## 2. P0｜先修“主动补采决策树”与来源冻结；不要直接重写核心策略

### 2.1 三层独立来源（按字段而非一刀切）

1. **本地通达信原始源**：只读 `D:/new_tdx/vipdoc/{sh,sz}/lday/*.day`、可配置的其他明确授权的本机 TDX 数据路径；对 9/28、9/29、9/30、10/08 逐个 security + trade_date 查是否真的包含目标 BAR、OHLCVA 的日期尾部，不用“目录存在”冒充数据就绪。保留本地未及时更新与本地缺股票两个不同原因。禁止改动、解压覆盖、重命名 `D:/new_tdx`。
2. **通达信官方最新可追溯源**：调用既有官方发布页/源获取逻辑，对 9/28、9/29、9/30、10/08 分日核对目标交易日、公布时刻、字节摘要、全量证券条目以及目标 BAR；已抓取的 `hsjday.zip` 等合法官方快照可做缓存/对照，但**不应只重查旧包后认定没有其他源**。不要把“官方 ZIP”当成非通达信源；关键是要有独立获取与更新动作。
3. **BaoStock 网络源**：在 TDX 目标日条目确实不存在、能力不够或需独立核验时，调用已实现的日期批量日 K / 因子接口；若该日期 batch 能力或运行时不支持，采用正式历史 K / `query_adjust_factor` 的有界逐股票 fallback（**前三日先以 176 个既有缺口证券及所需相邻历史窗口为主，10/08 先做全市场真实快照，再按新增差异定向补采**），明确 SDK 版本、入口、参数、返回码/分页、字段单位、时刻和结果摘要。必须分别试验不复权与前复权历史 K，不能默认为同一价格坐标。小规模真实 smoke 成功后再扩批，不做全市场每秒高频请求。

必须输出 `source_inventory_by_trade_date_security`，字段含 `security_id`、`trade_date`、`local_tdx`、`official_tdx`、`baostock_raw`、`baostock_qfq`、`baostock_adjust_factor`、`requested_at`、`response_status`、`provider_date`、`source_revision`、`hash`、`unit`、`price_basis_id`、`error_type`、`decision`。源请求数量计数必须单独列明；无网络请求时不可声称“上游查过没有”。

### 2.2 明确 source 状态机

`NOT_QUERIED` → `LOCAL_FOUND` / `TDX_OFFICIAL_FOUND` / `BAOSTOCK_FOUND` / `PROVIDER_EMPTY_CONFIRMED` / `PROVIDER_CALL_ERROR` / `SOURCE_CONTRACT_BLOCKED` / `COVERAGE_INSUFFICIENT` / `SOURCE_CONFLICT` → `ACCEPTED_CORRECTED` / `REJECTED_WITH_EVIDENCE`。

- 空响应≠停牌；停牌必须与证券身份、上市状态、交易日和独立状态源一致。
- 源请求失败不能被映射为 `NO_DATA_EXISTS`。要记录 DNS/连接/登录/SDK/限频/业务接口空返回/超时/参数字段不支持，每类给一次合理有界重试和可恢复入口。
- 日期批量 API 若返回当日数据，不代表原日 API 在当天已经发布；追溯查询记 `RECONSTRUCTED_CORRECTED`，不能证明旧 T0 `AS_RECORDED`。
- 若本地 TDX 最新记录仅 9/10，但官方 TDX 可取 9/28–30 或 BaoStock 可取，应继续而不是阻断。

## 3. P0｜正式数据源合同升级，不得静默伪造同源

新建（推荐命名）`config/v4_market_source_fallback_policy_v1.json` + 对应 registry、unit tests 和迁移说明；保留旧 V2 冻结合同/已发快照原样。

- **主要行情优先**：同日身份、单位、状态、时间可验证的 TDX 版本。TDX 已接受结果不要因 BaoStock 有值就被替换。
- **备选价格来源**：仅在 TDX 指定字段/窗口确实缺失，且用户已要求尝试 BaoStock，并通过证券代码身份、交易日、交易状态、单位、OHLC/量/额有效性、重叠日独立对照、来源专属容差与来源修订冻结后，才形成标注 `BAOSTOCK_FALLBACK_CORRECTED` 的**新版本候选**。不得冒充 TDX canonical / strict PIT / 原历史成交快照。
- **不同源冲突**：先保留两路事实，不静默选择均值、拼接前后复权曲线或覆盖 TDX；只对冲突字段 degrade，记录具体样本并判断是单位、日期、复权还是身份错误。
- **价格坐标**：Baostock `adjustflag=3` 不复权、`adjustflag=2` 前复权与 TDX 本系统 `TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE` **不得直接视为相同坐标**。交叉校验调整因子、分红送转、有效日和锚点；如果仅能跨源展示，可使用独立 `price_basis_id`，绝不能把异源 T-1 ATR / MA20 与 T 日价格直接混算。必要时保留该字段 UNKNOWN，但须证明补采已经执行。
- **先隔离，后审批**：新 policy 生成 corrected staging 与独立 Oracle，适用生产门禁后才发布 scoped successor；不通过绝不改旧 `V4_DATA_ACCEPTED_HEAD` 或 `V4_JOINT_RELEASE`。
- 兼容已有 `baostock_supplemental_contract_v1.json` 的访问速率/请求预算、会话、接口验收和凭证隐私要求；不要暴力修改老合同去骗旧测试。

## 4. P0｜前三日 176/日复权能力 + 10/08 全市场新增缺口专项修复（本轮核心）

- 依据 R3 `R3_QFQ_CAPABILITY_CROSSWALK.json` 得到 9/28–30 **528 日证券记录**，按证券去重请求，保留逐日结果；35 条停牌保留 `EXPECTED_NO_BAR`。**另对 10/08 全市场实际交易状态和行情独立重新生成缺口集合**：先取 TDX 真实源/官方日数据、BaoStock 的 10/08 记录及必要前史，再生成当天 `raw_gap/qfq_gap/suspended_no_bar/source_conflict`。不得把 176/日或 35 条停牌复制到 10/08，也不得漏掉本日全市场新增/退市/身份变更证券。
- 对前三日历史缺口和 10/08 新实测缺口的每条实际成交记录逐一回答：本地 TDX RAW 有无？最新 TDX 官方 RAW 有无？本地 GBBQ 与可用官方公司行为源能否算出前复权？BaoStock 的不复权日 K、前复权 K、调整因子是否可获取？是否与当前原始行情在可比坐标下匹配？
- 尽量使用同源 GBBQ 与 TDX 确定的复权链构建 V4 目标坐标；BaoStock 可作为因子和价格的独立核验、必要时单列新版本 corrected candidate。除权除息日、送转、停牌期间、上市日、跨日期以及源版本修订必须成对核验，不能只核验 `close` 而不核验 O/H/L/C。
- 对照清单至少分 `RAW_BAR_NOT_CAPTURED`、`TDX_SOURCE_STALE`、`TDX_OFFICIAL_AVAILABLE_NOT_BOUND`、`BAOSTOCK_AVAILABLE_NOT_BOUND`、`GBBQ_EVENT_MISSING`、`QFQ_FACTOR_UNAVAILABLE`、`CROSS_SOURCE_PRICE_BASIS_CONFLICT`、`ADJUSTMENT_ALGORITHM_GAP`、`TRADING_SUSPENSION_NO_BAR`、`PROVIDER_CALL_FAILED`、`HISTORICAL_AS_RECORDED_NOT_PROVEN`。
- 数值对照须独立于生产同一函数；不少于 20 条跨类别真实证券日样本和对应的错误/边界实例。交付四个目标交易日各自的 `before / fetched / usable_corrected / residual_unknown / exact_blocker`；10/08 额外输出 `full_universe_count/first_acquired_at/data_head_candidate`，不能只重复 176。

## 5. P1｜历史成员来源独立主动查询（不能用股票 K 替代）

- 9/28、9/29 以及新增 10/08 的行业/概念有效成员属于**另外一种源**。其中 9/30 已有接受的成员快照，10/08 必须按其当天有效日独立获取和冻结，不能沿用 9/30 成员作为 10/08 的当前事实。查通达信行业/概念分类文件及版本/修改时间、已有 TDX 官方快照、板块源的历史版本、真正包含 effective_date 的其他合法源。若 BaoStock `query_stock_industry()` 或其他基础资料接口有历史可验证的 provider revision，也可用于**其真正覆盖的行业字段**；不能把今天拿到的当前行业成员当成 9/28 当时有效，更不能拿它补概念历史。
- 已有 9/30 成员 50,162 条不能逆推 9/28、29 或 10/08。区分 `DATE_EFFECTIVE_RECONSTRUCTED` 与 `HISTORICAL_FIRST_AVAILABLE_UNKNOWN`。
- 立即建设未来交易日的**自动成员抓取/快照冻结/变动比较**，不必等待 20 日验证或历史 PIT 完备再继续新日功能开发。
- 若查过真实可达官方源后仍无法证明 9/28、29 或 10/08 有效成员，保留相关 `Rotation/entered/retention` UNKNOWN；列出 API、查询日期、结果、源码/时间证据，不能只给“旧 accepted 目录没有”。

## 6. P1｜与数据源相互独立的结构算法修复不得再次跳过

- 9/30 的 5,213 股票结构字段 7×全部 UNKNOWN（**历史基线**）；对新增 10/08 必须使用实际当日证券集合、T-1=9/30 真正重建并记录七字段实际 known/unknown，不得假定仍为 5,213，不能只靠 RAW 补采解决。逐步接通 V4-03 精确 T、T-1 Core/ATR/MA20/CLV、V4-12 合法结构 Owner 与相应前锚点；按真实交易日历排查 RPS T-3（9/30 对应 9/24，10/08 对应 9/28）、V4-13 read-only runtime 和目标日有效成员。
- 对 `OWNER_NOT_RUN`、`NO_ACCEPTED_OWNER`、`RUNTIME_NOT_IMPLEMENTED` 和 `SOURCE_TRULY_UNAVAILABLE` 分别处理。**代码明明缺实现，不可当成源不存在；数据源能拿到，也不自动证明已授权算法。**
- 原结构算法合同、七项字段映射和量化窗口不改；新增 source policy 不得使所有 UNKNOWN 突然变成 FALSE。真实算法恢复后的 known 数量按字段核验，不预设必须 5,213/5,213。
- 9/30 已有 378 个板块的 same-day 当前事实和 2,646 次数值对照，通过结果保持不回退。10/08 的板块数量与成员覆盖必须按当日实际重算，不能硬套 378；历史 Rotation 只在合法前一交易日成员已经到位的范围补算。

## 7. P1｜正式日更接入与发布控制

- 将主动补采 resolver 嵌入 **同一个**正式 DM01 日更入口，不能另写仅用于专项的一次性抓取脚本就宣布完工；参考 `scripts/run_v4_dm01_daily_increment.py` 和 `scripts/run_v4_current_daily.py`。独立专项历史修复可复用核心 resolver。
- 来源补采必须具备幂等、断点续采、请求预算、缓存冻结、API 异常日志、显式失败回退、重试上限；不能因为 BaoStock 不可达破坏原 TDX 已接受源，也不能因为 TDX 官方某天没有更新就把前一天的包冒充当天。
- **10/08 已是最新完成交易日**：首先检查官方日历、目标日 TDX/BaoStock 发布情况、已接受 head、当日真实源，再执行 10/08 `new_session_increment` 的补采与日更。仅当系统已经接受完全相同的 10/08 源/Owner/哈希时允许 `NOOP_IDENTICAL`；若尚无实际数据且网络调用失败，应记录 `WAIT_PROVIDER`/`SOURCE_CAPTURE_BLOCKED`，不可当作“没有新交易日”。对于真正无更晚完成交易日，普通日更 NOOP 保留 last-good。前三日 corrected repair 独立走 `historical_corrected_repair`。
- 生产新 successor 仅在来源、算法、QA 真正通过时发布；核验相同 context token、持久化、数据源标签、增量覆盖、并发 CAS、隔离失败回滚和 Codex IAB 最小验证；不要重做与本次修复无关的浏览器矩阵。

## 8. 不可省略的测试场景

1. 本地 TDX 无 9/29（或 10/08），官方 TDX 有 → 实际获取并标记 TDX 官方来源。
2. 本地 TDX 与官方 TDX 均无，BaoStock 有合法 RAW → **新 policy** 生成独立 corrected fallback candidate、不是直接覆盖 canonical TDX。
3. BaoStock 的 RAW 有值、QFQ 与本项目价格坐标不能验证一致 → RAW 可观测，QFQ 继续 UNKNOWN 并给原因；不得硬算 ATR。
4. BaoStock 不可达/超时/返回空/接口名不支持 → 有真实错误收据，不能显示 `NO_DATA_EXISTS`；允许之后重试。
5. 旧缓存包存在但目标日 BAR 不存在 → 必须继续原始源查询，不能只在缓存里找。
6. 除权股、上市短窗、停牌无 BAR、市场代码身份迁移、同一天源冲突、T+1 观察与历史 corrected/PIT 语义冲突 → 不污染正式接受快照。
7. 9/28/29 历史行业概念 effective_date 不可证明 → 轮动保持 UNKNOWN，但 current strength 仍正常、日更成员自动冻结已建立。
8. 10/08 已完成交易但最新 accepted 仅 9/30：正常执行当日 provider 请求与全市场补采、T-1=9/30，建立 candidate/校验/条件准入；不得跳过 10/08 直接返回无新交易日。
9. 国庆休市日期 10/01—10/07：必须完全跳过，并拒绝把其中任一天作为 T-1 或 9/30 的 T-3=9/25。
10. 结构 Owner 仍未实际物化 → 不可用“已经补采”给 V4-12/V4-13 算法 PASS。

## 9. 必交证据 / Git 提交 / 唯一完成判定

证据目录 `docs/evidence/source_acquisition_r4_20261009/`，至少包含：

- `00_R4_ENTRY_HEAD_AND_EXISTING_SOURCE_CONTRACT.json`
- `01_TDX_LOCAL_OFFICIAL_BAOSTOCK_REAL_REQUEST_LEDGER.json`
- `02_FOUR_SESSION_PER_SECURITY_SOURCE_MATRIX.csv` 与按日/证券/来源分类汇总 JSON（9/28、9/29、9/30、10/08）
- `03_FOUR_SESSION_QFQ_GAP_RECAPTURE_AND_ADJUSTMENT_ORACLE.json`（前三日 176/日为旧基线；10/08 动态重算）
- `04_BAOSTOCK_LIVE_RUNTIME_AND_HISTORICAL_QUERY_RECEIPTS.json`
- `05_HISTORICAL_SECTOR_MEMBERSHIP_PROVIDER_DISCOVERY.json`
- `06_SOURCE_POLICY_V1_MIGRATION_AND_FIELD_ADMISSION.json`
- `07_DM01_20261008_INCREMENT_AND_HISTORICAL_REPAIR_E2E.json`
- `08_STRUCTURAL_OWNER_AFTER_SOURCE_REPAIR.json`
- `09_SCOPED_RELEASE_OR_SAFE_BLOCKER_READBACK.json`
- `R4_EXTERNAL_AUDIT_HANDOFF.md`

**完成门禁**：必须提供真实请求数量、真实 TDX 本地读取、TDX 官方查询/快照和 BaoStock 接口真实响应/错误/时刻；对前三日 528 条既有缺口有完整逐条结果，且对 **10/08 完整市场及其新增缺口** 有逐证券交叉核查、真实采集与独立数量报告，列补采成功与剩余原因；接通未来补采入口；通过按源字段独立数值验证。允许历史有效成员、strict PIT、确实缺算法准入等**单项**停在 `NOT_VERIFIABLE`，但不得将**只查旧包**冒充原始源已穷尽，更不得只写报告结束此卡。

如果环境无法访问外网，须明确给出试过的 DNS/连接/登录/调用阶段与错误类别、命令、有限重试记录；可先提交采集链和离线测试，再把**联网运行的真实验证**明确标为 `NOT_VERIFIABLE`，不能标已完成。

## 9A. 四交易日最终对账与保留历史基线

Codex 最终交付必须包含严格日期表，每一行 `trade_date/official_session/canonical_tdx_raw_count/baostock_daily_count/gbbq_ready/qfq_capability_unknown/suspended_no_bar/identity_stock_count/industry_concept_membership_count/market_owner_ready/core_profile_ready/structure_known_count/rotation_known_count/accepted_head_before/accepted_head_after/live_context_token/real_request_count`。四行分别为 **9/28、9/29、9/30、10/08**，数据未知就如实 `NOT_VERIFIABLE`，**10/08 不得从 9/30 复制总数和缺口数**。旧三日数据不得被新行覆盖，也不可假定旧报告中的 9/25 RPS T-3 日期正确。新日与旧日分别作 anti-future/price_basis/PIT 限定范围验收。

新日交付状态建议单列 `OCT08_FULL_SOURCE_CAPTURE`、`OCT08_DAILY_INCREMENT`、`OCT08_OWNER_MATERIALIZATION`、`OCT08_SCOPED_READBACK`；任何一个未真正运行不可 `PASS`。在资源可用的条件下要持续修复到可执行环节完成，不因 10/08 是新增日而允许直接写 `NOT_MATERIALIZED` 收尾。

## 10. 直接交给 Codex 的一段式指令

> 本轮是 **R4.1 四交易日扩围**，不是重复 R3：目标 **9/28、9/29、9/30、10/08**，10/01—10/07 国庆休市，2026-10-08 是最新已完成交易日。用户明确要求 **通达信 + BaoStock 主动获取缺口数据**，不能只查仓库旧包。请从最新 HEAD 与当前成功生产联合指针冻结入场，先读 R4 全卡、原 R3 收尾和 `AGENTS.md`。按 P0 先执行原始源获取：本地 TDX 原始 .day → 通达信官方实际发布源/校验后可复用的快照 → BaoStock 日期批量与有界历史 K / 调整因子回查。对 9/28、29、30 的 176/日既有 QFQ 缺口及 **10/08 当日全市场真实新增缺口** 记录逐条真实请求与恢复前后状态，不把 RAW 已有误报为缺失；35 停牌不造 BAR。升级而非绕过现有“BaoStock 不可替代 TDX RAW”的冻结合同，建立新版本、来源清楚、校验严格的 corrected fallback policy。并行检查历史有效日板块成员的真来源并建立未来自动冻结；继续修 V4-12/V4-13/RPS 独立代码欠账。修好算法与来源才可以 scoped successor CAS。只审计/只生成缺口报告/只重跑旧 ZIP 不算完成。所有能做的代码及可联网的实采/测试都执行完，形成上述真实 receipts 后统一推送并请求独立外审。TDX 只读，保留旧 production、T0/PIT、价格坐标及用户数据。

---

*版本变更 R3 → R4：R3 默认使用已接受来源与本地包，缺少真实 provider acquisition 证明；R4 把主动补采、旧合同版本化准入、历史 effective-date 查询、日更一致入口和逐条真实请求审计变成首要 P0，并保留 R3 正确的安全/时序规则。*

## 11. R4.0 → R4.1 版本迁移记录（2026-10-09）

- 修改原因：用户明确要求将 R4 补采、来源修复、Owner、日更和验收截止交易日延伸至 2026-10-08。
- **新增的实际交易日只有 2026-10-08**；9/28、9/29、9/30 原三日样本与收据不改。10/01—10/07 为休市，不是数据缺口。
- 前三日缺口基线 176/日、528 合计与停牌 35 条仅为旧结果；10/08 实际证券集合、复权缺口、板块数、会员关系均需实源采集后重新计算。
- 最重要修正：10/08 不能按原 R4 “无新完成日则 NOOP”误处理。10/08 `new_session_increment` 与 9/28—30 `historical_corrected_repair` 都需执行，分别准入且相互不阻断。
- 新增 RPS/窗口交易日规则：9/30 的 T-3 是 9/24，10/08 的 T-1 是 9/30。修正之前任何提到 9/25 作为 9/30 T-3 的旧证据债务，不覆盖旧收据。
- 执行原始采集必须遵守当前用户授权、交易日源可得性、请求预算和既有只读 TDX 边界；新政策必须正式版本化和数值核验后才能发布。

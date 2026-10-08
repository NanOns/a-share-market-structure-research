# 大A V4｜c68964ee 独立数据与算法审计 R1

- 审计日期：2026-10-08
- 指定提交：`c68964eecc3653e3fb588113f615c925696959f9`
- 上次基准：`682ed2d779e33d5cef24188ff5fa727d41626f70`
- 范围：源码逻辑、生产发布权威、Focus 原生 Core、Forward 到期、每日增量、严格 PIT、110 字段状态及主要数据事实。不执行多分辨率 UI 专项。
- 方法边界：通过 GitHub 按指定 SHA 获取源码/配置/提交/冻结证据并交叉核查；没有接入用户 Windows 本机数据库与运行环境，不将 Codex 原有 pytest、数值 oracle 自述算成独立重跑通过。

## 1. 唯一结论

**SCOPED_PRODUCTION_CODE_AND_EVIDENCE_REVIEW_PASS_WITH_OPEN_DATA_GAPS；FULL_PRODUCT_ACCEPTANCE_NOT_PASSED。**

承认这轮代码及实际运行证据对正式分域研究有实质改善。当前日研究与历史 corrected 视图可以按准入域正式使用；不能把历史 corrected 视图包装为当时可得的严格 PIT。不能把完整产品缺口归结为 Edge、屏幕或单纯前端。主要剩余技术缺口集中在板块生命周期、个股结构/相对强弱/失效条件、当前 LOO、严格历史时序证据及需要真实来源的扩展事件。此结果是源码/证据独立审查结果，不是本机端到端复验签收。

### Git 基准异常（必须先核实，不代替代码审核）

GitHub Connector 可取到准确 `c68964ee` 提交，且它相对旧基线向前 37 个提交；但同一次读取中 `refs/heads/codex/v4-system-reform` 返回仍为 `682ed2d...`。该异常可能由远程分支引用尚未推进或读取缓存造成；不可据此断言用户未 push。由 Codex 在本地执行 `git ls-remote origin refs/heads/codex/v4-system-reform`、`git rev-parse HEAD`、`git status -sb` 并附完整 SHA，确认三者关系、修复远程指针或解释缓存。所有本报告源码引用严格固定 `c68964ee`，不读取旧分支 HEAD 代替。

## 2. 功能与数据事实

| 领域 | 现有可审查证据 | 判断 | 不能越界宣称 |
|---|---|---|---|
| 当前行情/个股画像 | 当前快照 2026-09-30；RAW 5213；Owner 日期匹配；报告含 41,696 RAW OHLC 与 653,526 字段单元检查 | 分域工程证据增强 | 不是完整信号算法独立重新验证 |
| 市场当前四轴 | 9/30 当前 Owner 与生产投影，对比研究源码和数据日期 | 可继续分域运营 | 旧/跨日市场与板块状态不能被冒充一致 |
| 板块 | 378 板块当前 RS5/RS20 等字段有真实来源 | 当前强度可展示 | `output_state` 378/378 UNKNOWN；无逐日成员/Seed 阶段依赖，不能宣称主线轮动链完整 |
| Focus | 9/29→9/30 两日 297→469 当前关注，766 observations，原生 ma20/ret5/severe_extension；READY66/PARTIAL572/UNAVAILABLE128 | 原生事实/日志追加进展真实 | 旧日 Core 不可倒灌，结构高优先级条件仍多未知；旧 PG 未迁移/对账 |
| Focus 路径/到期结果 | 当前 9/30 能观察到 297 个来自前日的次日路径结果 | 可作为 Focus 路径观察 | **不是** Forward 的 297 条到期结算 |
| Forward | 117 enrolled / 585 horizon plans，已冻结 117 个 T0；实际到期=0 | 当前不应因未成熟阻断研究域 | 从未经历真实到期结算的下一交易日完整现场验证，不能宣称收益验证完成 |
| 每日自动增量 | 两日期重放、候选、联合 CAS、失败恢复及无新日 NOOP 的证据 | 在当前已接受日期及范围内有可复核工程工作 | 不等于多未来交易日长期运行证明 |
| 严格 PIT | 9/28、9/29、9/30 0/3；新首获从 10/08 记录 | 坚持缺证不冒充 PIT 是正确的 | corrected replay、回算成员、后发模型不能称作 AS_RECORDED |
| 生产发布 | `V4_JOINT_RELEASE_V1`，当前 9/30，具体 scope 已启用，`full_product_release=false` | 分域生产可用 | 不等于全产品发布 |

## 3. 严格 PIT 的精确定义与处理

PIT (Point-in-Time) 的关键并非“历史行情真实”，而是：对历史决策时刻 T0，使用的每条记录、板块成分、公司身份、特征、模型/参数、发布版本均存在独立证据证明**首次可获知时间**不晚于 T0；且 T0 冻结包、哈希及未来数据防注入通过。

原始行情的 `trade_date`、数据文件 `source_as_of` 与在系统内实际 `first_available_at` 是三个不同时间维度。10/08 首次冻结 9/30 重建产物只能说明 10/08 首次观察到该版本，绝不证明它在 9/30 当时已发布。源码 `src/workbench_service/pit_observation.py` 显式 `strict_t0_pit_ready=false`、`AS_RECORDED=false`，此处处理是对的。

因此：

1. 当前日实盘盘后研究允许使用真实、正确标明截至日的 operational 数据；不因 0/3 strict PIT 全面封站。
2. 历史回看仍可用 `RECONSTRUCTED_CORRECTED` 作解释与反事实研究，但不能用来宣称历史冻结预测胜率或事件当时已知。
3. 从后续生产日建设实时首获账本，冻结运行前数据输入、模型/合同、板块成员、结果和决策记录，形成严格 PIT 的**未来可累计样本**。不能补造 9/28～9/30 的过去收据。
4. 无需等待 20 个交易日后才开发其余功能；但没有历史首获证明的算法回测不能被宣传为严格前视隔离的验证。

## 4. 110 字段真实状况（60 PASS 不代表准确率）

实读 `R2_PRODUCT_FIELD_COVERAGE.json`：总数 110，分域可接受 60，未通过 50；数值 oracle 条目 31，不可直接解释为对全部算法的独立数学正确性覆盖。

| 范围 | 仍未通过字段数 | 关键具体缺口 | 对交易研究影响 |
|---|---:|---|---|
| 板块研究 | 15 | `maturity`、`health`、`output_state`、`why_now`、`breadth_delta3`、`seed_width`、`exhaustion`、`emergence`、`confirmation`、成员变动等 | **高：主线/轮动判断会缺关键上下文** |
| 个股研究 | 18 | `relative_state`、`turnover_state`、突破/回踩/恢复、支撑、等待、失效、假设、对立证据、结构时间线等 | **高：右侧结构决策完整性不足** |
| Focus | 2 | `parent_episode_id`、`waiting_for` | 中高：持续跟踪、升级/失效可解释性 |
| 市场事件 | 2 | 炸板、可信事实事件 | 可独立延期；无可靠数据不伪造 |
| 诊断 | 3 | RPS20 矩阵、旧扫描器、LOO | LOO 为较高优先，其他按研究需要 |
| 严格 PIT/跨对象 | 6 | 历史冻结、冻结板块、当前 LOO、板块比较及生命周期 | 必须严格区分非 PIT corrected |
| 首页变化 | 4 | 轮动变化、板块变化、风险变化、成员预览 | **高：今日真正变化内容被稀释或漏报** |

50 项**不是 50 个软件 bug，也不是 50 个都要独立阻止当期生产的门禁**。应区分真实 Owner 输入缺失、算法未产出、API 映射缺失、时序证据不足和数据源未授权/未接入五类，并分域明确哪些是 P0/P1/P2。

## 5. 当前代码逻辑审计：证实的事实、风险、必要复核

### 5.1 已有实质性代码落地

- `src/focus_tracker/v4_native_core_adapter.py` 显式核对 observation 日、价格坐标、参数集、有限值及价格路径，将 ma20/ret5/severe_extension 传递给 `classify_stock_v2`；不能将未知当 FALSE。
- `src/focus_tracker/v4_native_core_daily_driver.py` 使用不可变 journal 候选与同日源摘要比对；同日改源拒绝沿用旧命名空间，失败不直接切换生产。
- `src/workbench_service/continuous_daily_release.py` 发布前核对 RAW OHLC、字段未知状态、Focus 时间边界、Forward 到期和来源摘要，再走联合 CAS；`src/workbench_service/joint_release.py` 实现原子权限、健康回读和失败回滚。
- `src/workbench_service/forward_daily.py` 强制冻结日历前缀、禁止重写 T0、检查到期结果真正有 Owner 发布。
- `src/workbench_service/pit_observation.py` 有真实首次观察冻结，且不冒充旧日 PIT。

### 5.2 需要继续审计或定点修复的领域（不伪称已出现错误结果）

**A. 板块主体高优先级：** `output_state` 当前 378/378 为 UNKNOWN；`NO_PRIOR_ACCEPTED_PIT_HISTORY`、Base/Seed 降级来源需要追踪到真实 Owner。要求把“历史首获不满足严格 PIT”与“真实有截止日的上一交易日研究数据能否支持日常轮动”分开；不能为了严格回测证明永久让生产轮动停摆，也不能未经证明用 9/30 成员回填 9/29。

**B. 个股信号表达：** 右侧突破、回踩、恢复、相对强弱、支撑、H1/H2、等待/失效等目前字段仍不全。应优先定位既有生产者是否已有真实事实/作用结果，不存在再建立版本化 Owner；不得由前端猜测虚构。对所有真实信号检查 T 日收盘 cutoff、历史窗口、停牌、价格调整、单位、缺值、交易规则、复权和相对基准。

**C. Focus 结构状态：** 当前原生 Core 只覆盖 3 类新增基础事实。两日 766 observation 中 128 不可用、572 部分可用，需以可复核谓词依赖图查明最高优先级的 UNKNOWN，避免把 Partial 包装成全链推断。

**D. Forward 到期：** 现有真实到期 0；不能因 585 个期限计划就说结算成功。新接受交易日出现到期后，必须验证 no data/停牌/除权/价格坐标/右删失/复核重跑/幂等/修订追加，且不得重写 T0。

**E. 发布/回滚安全：** 历史台账 `AUD-R2-SNAPSHOT-PREDECESSOR-MUTABLE-REF` 明确一个紧邻前驱的引用字节不能精确恢复。该项不是 UI 兼容性问题，应继续作为发布/回滚可用性债务检查，核实实际当前 release 的最少一个健康前驱及演练覆盖。

**F. Git ref：** 审计读取到 `c68964ee` 对象与旧 branch ref 的差异。必须附 CLI 证据复核远程分支指针；如果确实未推到指定分支，应修复 push/同步，不能以对象存在替代指定分支最终交付。

## 6. 下一轮验收口径（按用户新指令）

- **不再做** 1280、1366、移动端与跨浏览器适配专项；Edge 完全取消。1920×1080 和 2560×1440 仅保留必要启动、核心操作冒烟；不要重复生成几十张相似截图。
- 约 70% 审计精力给数据和算法：数据身份/日期/时序、数值独立抽样、现有 Owner 生产/适配、缺值与退化、信号和生命周期的实义；20% 给每日稳定生产/发布/回滚；10% 给功能可达性。
- 各能力分为 `CURRENT_PRODUCTION_SCOPED_PASS`、`CURRENT_PRODUCTION_BLOCKED`、`HISTORICAL_PIT_UNPROVEN`、`ONGOING_VALIDATION_DEBT`、`OPTIONAL_SOURCE_DEBT`。只有第二类阻断对应当前功能的正式生产。
- 验收先验证真实候选、当前代码与数据，再看证据日志，最后才看 UI。

## 7. 本轮复核路径

源码/快照在 `https://github.com/NanOns/a-share-market-structure-research/tree/c68964eecc3653e3fb588113f615c925696959f9`。重点：

- `docs/evidence/r2_read_domains_continuation_20261008/{R2_PRODUCT_FIELD_COVERAGE.json,OWNER_SOURCE_DEBTS.json,FP13_QA_V2_FINAL.json,FP14_RELEASE_V2_FINAL.json,R2_OWNER_DATE_MATRIX.json}`
- `docs/evidence/r2_focus_native_core_continuation_20261008/{ACCEPTANCE.md,NATIVE_CORE_ORACLE.json,ORACLE_RULE_CORRECTION.json}`
- `docs/evidence/r2_forward_continuation_20261008/{ACCEPTANCE.md,REAL_COHORT_ORACLE.json}`
- `docs/evidence/r2_continuous_daily_20261008/{ACCEPTANCE.md,QA_FINAL.json}`
- `docs/audits/R2_INDEPENDENT_REPAIR_ITEMS_20261008.md`
- `src/focus_tracker/v4_native_core_adapter.py`；`src/workbench_service/{forward_daily.py,continuous_daily_release.py,joint_release.py,pit_observation.py}`

## 8. 最终状态

- **生产分域范围：** 可以认可工程与证据已有阶段性闭环，但外部尚未重跑 Windows 真实源，因此声明为**源码与证据级有条件通过**。
- **严格 PIT：** 0/3，确实未通过；正确保留，不能改账。
- **全产品：** 60/110、缺 50，未通过；不能把历史 PIT 和 optional 事件导致的缺口升级为全站不可用。
- **优先动作：** 当前板块和个股核心算法产物、Focus 高优先级未知、Forward 到期执行日验证、历史前驱回滚和 git ref 状态，而不是屏幕兼容性。

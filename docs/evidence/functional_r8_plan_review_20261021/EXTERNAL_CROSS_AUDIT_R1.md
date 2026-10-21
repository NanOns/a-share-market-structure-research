# 大A交易 V4｜功能 R8 修复方案 R1 独立交叉审计与 R2 修订建议

> **文档编号**：DA-V4-FUNCTIONAL-R8-PLAN-CROSS-AUDIT-R1  
> **日期**：2026-10-21（Asia/Shanghai）  
> **文档类型**：方案级独立交叉审计 / Codex R2 修订依据  
> **审计对象**：`docs/plans/V4_FUNCTIONAL_R8_REPAIR_PLAN_R1_20261021.md`  
> **审计对象提交**：`129f49cbc0f57a9812f62d7072959eebae796349`  
> **受审方案采用的代码基线**：`6b02414cf5824e9e59a04c7decc3fc75713b083c`（R7）  
> **仓库/分支**：`NanOns/a-share-market-structure-research` / `codex/v4-unified-development`  
> **独立裁定**：`PLAN_CROSS_REVIEW_REVISE_REQUIRED`  
> **实现状态**：`IMPLEMENTATION_ACCEPTANCE_NOT_ASSESSED`  
> **生产授权**：`PRODUCTION_AUTHORIZATION_NOT_GRANTED`

---

## 0. 审计范围与重要声明

本审计针对 Codex **已经提交到 GitHub 的修复方案设计**，检查修复顺序、研究功能边界、来源和缓存、真增量、身份守恒、验收的可执行性及生产权限。审计时确认最新方案提交只新增 **224 行方案文件**，并非执行了方案中的业务修复。

本审计以远端方案文件、R7 现役相关代码、`AGENTS.md`、阶段性合同及已有执行报告交叉比对。对 Codex 提交的 10/12–10/14 数据和 28766 浏览器读回，仅将其视为其本地执行记录；本轮没有直接读取用户 Windows 本地 PostgreSQL、G 盘文件或亲自操作 28766。因此：

- **ACCEPT**：设计处理路线可接受；不代表已有代码实现或正式发布通过。
- **REVISE**：方案应定向补充合同、机制、依赖或验收条件；允许无依赖的其他工程包继续。
- **BLOCK**：对应施工范围缺少先决定义或存在错误准入风险；必须先修订/批准合同再实施，不等于阻断所有 R8 工作。
- 不能因「方案审计通过」「局部测试通过」「候选网页有结果」宣称全系统工程完成、正式 PIT 成立或生产已经获准。

**总判定**：保持“研究正确性 → 多模块整合 → 连续日更/恢复 → 独立正式发布”的总体目标，但 **R1 不宜原样作为完整施工合同**。D2 冻结阈值及跨日精确坐标应先冻结设计合同；其他有明确合同的修复与真实来源及时捕获可并行推进。无需重启 V4 以前的历史项目、M14、全面 PG/Schema/Owner 治理或另造研发平台。

## 1. 原问题 ID 逐项裁定总表

| 原问题 ID | 工作包 | 审计裁定 | 直接原因 | 最小修订 |
|---|---|---|---|---|
| `FA8-CORRECTNESS-01` | A1 宽度与趋势 | **REVISE** | `SIGN` 公式与实际 0/1 指示计算不一致；趋势合同及独立验收输入尚未完全固定 | 固定零收益、样本、时间、价格口径与阈值；独立重算数值和分类；趋势轴单独验证 |
| `FA8-D0-02` | A3 D0 场景 | **REVISE** | 2 个候选场景与 2 个诊断场景不能混用；UNKNOWN 与 FALSE、时间角色及来源准入须守恒 | 四场景能力矩阵、真实上游封存门、逐场景三态负例、诊断不升格 |
| `FA8-D2-03` | A4 D2 失效 | **BLOCK**（实施准入） | 失效价位**生成规则**未定；跨日 QFQ 精确映射、episode 冻结与实际 D2/Focus 传递缺合同闭环 | 先批准冻结阈值/坐标/事件合同，再改生产者、检测器、reducer 和消费者 |
| `FA8-INTEGRATION-04` | A5 / B 缓存及来源 | **REVISE** | 完整传递依赖及业务摘要稳定性未被验收定义覆盖；缓存存在冷热诊断进入 payload digest 的风险 | 业务内容摘要与 `cache_hit` 分离；多层来源摘要、合法换源/损坏负例及真实 API 校验 |
| `FA8-DAILY-05` | C 增量与连续运行 | **REVISE** | 后验候选接续不能冒充正式 accepted 前态；必须独立验证数值、旧身份、新引用和 APPEND | 区分候选链与正式链；按 G1–G4 四道硬门验收；时间/性能和未来 5 日运行分层 |
| `FA8-REVISION-06` | C3 / RI-02 | **ACCEPT**（有条件） | 无修订 APPEND 不应被尚未完成的 RI-02 永久阻断 | 修订真实发生时 fail closed、标记 `RANGE_REPAIR_REQUIRED`；不宣称修订自动修复已完成 |

**建议增补两个独立 ID**：`FA8-PRIORITY-07`（Priority 缺值/计分规则）与 `FA8-RELEASE-08`（发布权限和证据）。详见 §7。

## 2. 修复顺序审计：从“大包串行”改成“最小依赖并行”

R1 §4（第 70–82 行）提出：`准备检查 → A 研究正确性 → B 流程整合 → C 增量及运行验证 → 发布`。主方向正确，但不能要求 A 全包完成后才允许所有 C 工作：若 D2 阈值合同未定，就会连带阻塞及时来源冻结、只读性能测量、无修订 APPEND 的独立研究。

### 2.1 建议 R2 施工依赖

1. **立即：冻结准确基线与当日真实来源**。记录 HEAD、运行入口/PID、28766、真实 PG 身份、formal Head、候选 token、来源 T0/观察时间、Owner 与算法版本。若合法收盘来源已经就绪，在当前既有授权范围内及时捕获；涉及 PG 写入另列对象与权限。防止继续损失真实 first-capture 证据。
2. **并行工作流 P0-A（研究正确性）**：A1 宽度/趋势；A2 Priority 数值/缺值；A3 两个已支持的 D0 候选场景；A5 来源缓存和身份。仅修有合同和负例的路径。
3. **并行工作流 P0-C（增量工程基础）**：冻结输入的候选历史接续、无修订 APPEND 与 R1.1 四门比较器、只读热点定位、失败保护方案；不预先授权生产 PG 或 Head 写入。
4. **合同前置 P0-D2**：单独确认冻结失效价位的生成规则、阈值从何时起有效、跨日仿射坐标和状态优先级；审定前不把测试阈值写入正式 episode 生产者。
5. **汇合 B**：将已通过的生产者结果接入市场→板块→个股→D0/D2→Focus→Forward 的现役 Owner/BFF/UI。该阶段仅使用合法的同一研究视图/显式来源时间差，不强迫历史成员快照与行情写成同一日期。
6. **C 完整候选闭环及故障/性能**：在授权明确的隔离候选环境完成 APPEND、查询、恢复、缓存及分页的一致性；合法来源修订进入 RI-02 边界。
7. **单独发布授权与正式 Beta**：正式写入、Head/CAS、main 合并、EXE/28765 分别确认；正式启用后记录至少 5 个**实际逐日**盘后运行，不能用一次历史补跑代替。

**原则**：某一诊断场景、历史失效证据或 Forward 后继交易日尚未具备，不得阻断其他没有依赖的功能修复。反过来，某个模块「可显示」也不得绕过准入硬门。

## 3. `FA8-CORRECTNESS-01`｜宽度与趋势（REVISE）

**方案合理点**：R1 未直接选择旧标签所支持的公式，也没有用另外三轴投票代替趋势轴。

**源码差异**：`src/workbench_analysis/r6_candidate_market_stress.py` 中 `breadth_formula` 声明为 `MEAN(SIGN(RET1_T)-SIGN(RET1_T_MINUS_3))`，但核心计算使用 `(1 if ret>0 else 0)` 的指示函数。通常 `SIGN(-x)=-1`，指示函数对负收益返回 0；因此原始数值的意义不同，即使分类可能碰巧不变。已有市场 Owner 标签相等**不是**公式正确性的独立证明。

**R2 必须补充**：

- 固定宽度所用证券全集和比较日，明确比较集合是两端均可计算、停牌/IPO/退市如何处理；明确零收益定义、数据精度、复权口径、正负比例或标准 SIGN 的经济解释和阈值适配。
- 并列计算标准 SIGN 与正收益指示法的**原始数值和分类**。若原算法正确而文档误写，版本化订正文义；若算法错误，版本化重算受影响候选并披露所有分类变化及实际消费者变化，不能为了保留旧标签而选公式。
- 趋势轴先审查现役 `src/v4/factors/native.py` 中趋势原语和适用合同，固定指数/个股分母、输入窗口、规则阈值与坐标；不能只为 10/14 写特例，也不能以已有市场轴输出作为自己的独立 Oracle。

**可执行验收**：在冻结 10/12、10/13、10/14 输入下，另一段不调用原生产函数的计算器逐个核对可计算集合、原始数值、质量、阈值与分类，零**不明**差异；时间、数据或证据不足保留 UNKNOWN；趋势轴既有正例也有空源/错版本负例；复合市场状态只能在完整合同允许时发布。

## 4. `FA8-D0-02`｜四场景能力、三态与时间边界（REVISE）

**现役合同依据**：`src/v4/confirmation_input_closure_r3b.py::scenario_capability_matrix`（约第 168–180 行）实际区分：

| 场景 | 当前能力 | R2 接受范围 |
|---|---|---|
| `LAUNCH_CONFIRM` | `FORMAL_CANDIDATE`（需有效上游封存） | 候选真实谓词、来源、TRUE/FALSE/UNKNOWN 可修可验 |
| `RECOVERY_TURN` | `FORMAL_CANDIDATE`（同上） | 同上 |
| `STRONG_PULLBACK` | `DIAGNOSTIC_ONLY` | 保留诊断；prior episode 不得由同日下游反推 |
| `TREND_CONTINUE` | `DIAGNOSTIC_ONLY` | 保留诊断；LOO 宽度与同日来源依赖准入先审明 |

**关键边界**：

1. `src/v4/confirmation_candidate_r4.py::detect` 调用 `scenario_capability_matrix(r3a_sealed=True)`。不能因这个布尔参数被设为 True 就认定所有真实上游来源已经有效封存；应检查真正被引用的 source bindings、实际可得时间和权限链。
2. 生产者 `src/v4/target_fact_producers_r4.py` 把 `pullback_episode_confirmed` 和 `current_with_loo_breadth_support` 保留为 `None` 的诊断事实；不能以填默认值或把 diagnostics 改成正式事实来降低 UNKNOWN。
3. 当前治理包装器是 **UNKNOWN 优先**。一个原始 `check=False` 与其他必需输入未知同时出现，不得未经版本化语义变更就自动归 FALSE。记录 `legacy_eligible`（原布尔/三态结果）、场景治理状态、全 D0 聚合，避免相互覆盖。
4. 场景中的多个未知/失败原因可以同时成立，不应强行互斥。只有另外定义的**主原因**需要互斥分母，仍必须保留全部原始失败谓词。诊断场景的 UNKNOWN 不应直接被正式场景聚合吸收或默认为正式资格。
5. `STRONG_PULLBACK` prior-episode 与 `TREND_CONTINUE` same-day LOO 是不同的时间和上游问题，不应因为都 UNKNOWN 就作为一个通用缺源处理。

**R2 最小交付**：一张按场景的 `字段→Owner/生产者→time_role→source SHA/截止→quality→原始谓词→能力→治理结果` 矩阵；分别验证 known TRUE、known FALSE、unknown、诊断非法准入、同日反馈、未来输入和封存证据缺失。可用的两项候选场景可以单独 PASS；两个诊断场景留 OPEN，不据此虚报 D0 全覆盖。

## 5. `FA8-D2-03`｜冻结阈值与跨日复权（BLOCK：实施准入）

R1 §A4 认识到「比较规则 `close <= frozen_level`」不足以定义阈值，这是正确的，但**缺了可直接执行的阈值生成合同**。本项允许先做资料/合同核对、向量设计、接口草案；**禁止在阈值语义未审定前把某个低点、MA 或百分比擅自写为正式失效位**。

### 5.1 先审定失效位的业务来源

必须写明失效位取自哪一个已有结构/episode 合同，生成所需最小历史窗口、字段和参数；究竟是收盘结构位、区间低点、平台、前一 episode 的冻结条件或其他规则；从哪个事件/交易日起冻结，以及模型边界允许什么合法重置。不允许每天按当日最低价或最新均线重新计算并覆盖旧值，以免人为延长有效期。

episode 冻结的最小身份应包括：实体 ID、`episode_id`、起始会话/观察时间、阈值数值、阈值生成合同/参数版本、冻结价格坐标、源 Owner/input digest、阈值来源窗口、冻结时 available_at、适用状态/允许的比较方式。重跑同日同输入幂等，后继只引用冻结版本，不修改既有 episode。

### 5.2 跨日 QFQ 的精确坐标

若 T0 冻结位与 T+1 当前 QFQ 属于不同基准，先按现役有理数/精确仿射复权合同转换到**可验证的同一比较坐标**，保存转换规则与分子/分母或等价可复算的转换身份；有公司行动时验证整链，未经证据确认不允许比较。不能只把 `frozen_price_basis_id` 与 `current_price_basis_id` 替换成相同字符串。

**三个核心负例**：不同 QFQ 基准但合法转换；不同坐标且无有效转换时返回 UNKNOWN；公司行动/修订输入变化导致依赖版本更新，旧冻结值与原 episode 身份仍不变。必要时对公允比较坐标采用原合同允许的 RAW/固定仿射表达，但不能混用名义价与调整价。

### 5.3 当前实现确有断链

- `src/workbench_analysis/r7_frozen_invalidation_v2.py` 仅为候选检测器，存在硬编码 `trade_date > '2026-10-14'` 的拒绝门，不是可直接跑真实后继日的通用生产者。
- `src/workbench_analysis/r6_reason_attribution.py` 调用该检测器时把 `current_close`、`frozen_invalidation_level`、两个 basis ID、bar status、SHA 都传为缺失/UNKNOWN，因而只在解释“不能判断”，并未完成真实市场输入到检测器的接线。
- `src/v4/research_state.py::reduce_state` 已有 `core_price_damage`、`frozen_invalidation`、硬失效、延期、重入/模型边界等语义；R2 应明确优先级、无 prior 的 `NOT_APPLICABLE`、停牌/无实际 bar、同日重跑与后继重新入场，不得因接了一个 detector 破坏现有 reducer。
- 原 875 条 prior episode 缺冻结位/价格基准，不得回写旧历史或人为推导旧 PIT。允许另外建明确标记 `RECONSTRUCTED/NON_PIT` 的诊断版本，但不改变旧资格。

### 5.4 最小可执行准入和验收

**先决条件（BLOCK 解除）**：阈值生成合同、价格坐标合同、episode 冻结字段与状态优先级经过版本化审定并能写出反例向量。

**实现验收（合同解除后）**：一个真实来源建立的**新**候选 episode 冻结完整阈值和坐标；下一实际交易日 bar 按绑定日期/SHA 通过检测器 → reducer → Focus/API/页面；等于/高于/低于阈值的剩余分支由工程向量证明；真实市场不发生跌破不能成为“实现失败”或强迫等待的原因。不得把收盘失效规则误称盘中触碰失效。

## 6. `FA8-INTEGRATION-04`｜来源缓存、响应摘要及全链身份（REVISE）

**重点已见源码路径**：

- `CoreProductBFFR1._candidate_market_stress()` 返回 `cache_hit` 运行状态；
- `/api/v4/radar/priority` 将其装入 `priority['candidate_market_risk']`，随后 `hashlib.sha256(json.dumps(priority,...))` 计算 `candidate_payload_sha256`；
- 因此**同一业务输入冷读 `cache_hit=false`、热读 `cache_hit=true` 可以影响 payload 摘要**。这已足以确认业务摘要设计存在不稳定风险；真实端到端 hash 是否变化还应构造请求实测并留回执。
- 生命周期 `_candidate_lifecycle` 缓存键主要含 token、生产者和参数；Focus `_candidate_focus_reason_attribution` 主要含 token、日期、实体集合摘要；这些键并未直观覆盖所有变动的上游 Owner/来源身份，不应只看键名认定已完成全链失效。

**R2 最小修复**：

1. 规定 **稳定业务产物摘要** 排除 `cache_hit`、耗时、API 请求环境等诊断字段。运行诊断放在响应元信息，不能作为 immutable 研究业务 payload 内容。
2. 对市场轴、sector lifecycle、Priority、D0/D2 原因归因、Focus 及其消费者，使用实际依赖摘要：源文件 SHA/bytes、owner 绑定、交易日/窗口、成员关系、生产者版本、参数版本及下游派生逻辑。摘要绑定可复用既有 manifest 和递归已验证身份；无需请求마다全量重扫历史。
3. 同 token/同来源重复调用稳定命中且稳定**业务** SHA；同 token 下依法可修订的候选 Owner（或相应不可变修订身份）发生内容变化时，新派生结果必须失效旧缓存；正式不可变 Owner 被无授权修改则 fail closed 而非悄然更新。
4. 要有真实 API/页面的**冷读→热读→合法上游换源→破坏性错 SHA→切 token→切日期**负例。只测某 hash 函数或仅证明 token 变化不够。
5. 保证来源捕获时间与行情 T0、成员时点、研究发布时点分别可见；不能把合法的早期成员关系篡改成行情当日成员，不能混入 10/15+ 的未来输入给 10/14 研究结果。

**设计约束**：复用现役 Owner/PG/Head/来源版本机制；不引入新的全局缓存服务、DAG 引擎、平行 Head 或频繁读盘扫描大对象。

## 7. `FA8-DAILY-05`｜真增量、历史身份守恒及可执行验收（REVISE）

### 7.1 最重要的前态边界

已报告的正式 Head 仍停在 2026-10-09；10/12–10/14 为**后验候选链**，并带 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`。因此：

- **候选历史接续**可以用明示的后验候选前态验证每日值和状态衔接，但不能宣称 accepted publication 的正式身份守恒已通过。
- **正式 APPEND** 必须从真正已接受的前一主交易日 Head 出发，或在授权后先依合适的逐日正式准入把缺失前态补齐。禁止从“非正式 10/14 候选”直接越级生成“正式 10/15 accepted”的身份链。
- 实时捕获和按日补数是两种不同证据：10/20 后验采集 10/12–14，只能证明当日历史内容有出处，不能补造当时首次观察时间。

### 7.2 沿用 R1.1 四道独立硬门（不能相互替代）

| 门 | 精确定义 | 必须验证 |
|---|---|---|
| G1 业务值与状态等价 | 同一合法比较范围下数值、质量、结构、事件、周期一致 | OHLC/MA/ATR/Profile/Sector/D0/D2/Focus/Forward/周月等影响业务的值和状态；零**不明**差异；不按不同 ID 丢整行 |
| G2 已发布旧身份守恒 | 以实际 accepted predecessor 为唯一旧身份参照 | 原 Owner/source SHA/Anchor/Episode/历史引用不改；新事件合法引用、无孤儿/循环，历史语义可解析 |
| G3 新摘要及来源正确 | 新 digest 从真实新输入独立计算 | 新 token、source bindings、算法参数、T0、前态引用可重算；不能复制 full replay 的不适用摘要 |
| G4 真 APPEND 与发布 | 正常路径只生成新增 T0；历史窗口只读；失败保留 last-good | 幂等、没有双生产者、当日链衔接、CAS/PG/BFF 同版；有修订则拒绝误当 APPEND |

新全量重建可能合法生成不同的历史派生 ID：比较器必须语义匹配，与已有正式历史的引用守恒是两个不同要求。不要为追求逐字相同把重建身份回写到原正式历史。

### 7.3 增量与修订边界

- 正常 APPEND：计算日期只包含新 T0；允许读取历史窗口，不能把读取窗口误报为重新生成历史 Owner。
- 同输入重跑：不重复写 episode、事件、观察/结算；允许单独标识并计数的运行日志，不影响旧内容。
- 发现历史 RAW/复权/算法/成员修订：先建立影响范围、对象、日期与下游关联；若没有版本化的 `RANGE_REPAIR` 能力则 `RANGE_REPAIR_REQUIRED` 并保留旧 Head，不能静默全量回建或假称成功。
- RI-02 可以单独跟进，不作为**已被证明无修订**正常 APPEND 的无条件前置；真正发生修订时则不能豁免。

### 7.4 性能和稳定性：目标与硬门分离

R1 的「来源就绪后常规日更+发布 ≤15 分钟（争取 5–10 分钟）」可保留为**优化目标**，不是当前未经实测的已满足条件。必须先固定 5,225 股 / 400 板块或实际生产分母、硬件、日期、缓存冷热与阶段计时，报告 `source_wait/capture/Core/Profile/Sector/Market/D0/D2/Focus/Forward/period/PG/API`。源等待与纯计算分别披露。

建议以下阈值先当 **候选交互目标**，经真实基线审定后再冻结：预热首页/列表 P95 ≤2 秒；日更期间 3 并发 P95 ≤3 秒；图表冷读 ≤8 秒、热读 ≤2 秒。R1 的每组 20–30 请求样本对 P95 稳定性有限；应按接口类别、缓存状态、固定数据规模做有界重复采样，报告样本数、失败率、P50/P95，并且不能只报成功请求耗时。

**最小故障集**：未完整采集不发布、阶段边界中断恢复、PG/发布失败保持 last-good、重复执行无重复事实、切换时页面多请求不混合版本。共享 PG 禁止停掉他人服务或无授权压测破坏；只读预览时不启动真实写 worker。

### 7.5 M1 / M2 / M3 / Forward 研究线

- **M1**：有明确能力范围的研究链可用，不等于系统所有诊断场景或历史 PIT 通过。
- **M2**：固定真实输入的候选增量、四门比较、恢复和性能证明通过；不等于真实连续运行。
- **M3**：正式权限和发布完成后，至少五个真实交易日分别盘后采集/运行，构成有限 Beta 稳定证据；这五日不能由一次历史回放替代，不能反过来阻断先前 M1/M2 的工程完成。
- **Forward/FEP 独立实证**：真实首次捕获和后继到期由正式来源持续积累，不能把 `WAITING`、未到期或 late NON_PIT 当作模型失败或已经被验证的研究收益。

## 8. `FA8-REVISION-06`｜自动范围修订（ACCEPT，有条件）

同意 R1：不把尚未完成的 RI-02 自动范围修订引擎作为正常、已证无修订 APPEND 的永久阻塞。但 R2 必须明确以下两个可控负例才可以给**普通 APPEND 路径**相应 PASS：

1. 一条已接受旧日 bar/复权系数真实发生变化，正常 APPEND 必须 fail closed、标记 `RANGE_REPAIR_REQUIRED`，正式 Head/旧 Owner 不变。
2. 一个算法/参数新版本影响既有可达结果，必须识别影响域，不应悄悄按普通 APPEND 继续并混用旧逻辑。

RI-02 自动计算受影响范围、建立修订链、做有界重算，是后续独立 OPEN；在没有修订时不阻断其他代码验收，但不能宣称「修订功能完成」。

## 9. 新增遗漏问题 ID（建议纳入 R2）

### `FA8-PRIORITY-07`｜Priority 缺值及计分身份（REVISE）

R1 A2 有 Priority，但原 ID 台账中缺独立跟踪项。`src/workbench_service/research_priority_r1.py` 中 `distance` 路径在 `close` 缺失时有回退 `prior_low20` 的实现，可能让缺少有效收盘价的对象得到零距离分值，而非 `NOT_RANKABLE`。必须核对 `close` 的 `quality` 与有限值、`prior_low20` 坐标一致性、距离计算取值和极端值。另需确定 `rps20` 字段在现役筛选中是否真正参与资格/评分，或只是非空前提；别把使用了字段名当成有实际经济效果。

**最小验收**：5,225 总分母、4,258 排除原因、967 排名候选（以修订后实际输出为准）可独立逐行解释；关闭对真实缺 `close`、无效质量、异常低点、负/极端价格的静默补值；同价和同分排序可确定；不同源版本的计分摘要正确变化。不以提升入选率作为目标。

### `FA8-RELEASE-08`｜开发、候选、正式发布与权限（REVISE）

原 §5 总体边界正确，但应独立建 ID，防止把完成代码、候选 PG 验证和正式生产写入混为一谈。每个动作单列：

| 操作 | 当前计划许可 | 必要约束 |
|---|---|---|
| 普通代码、定向单测、离线候选、Git 提交推送 | 在既定授权范围内可执行 | 保留 R7 源证据和旧报告，不静默改冻结算法 |
| 28766 只读服务与现役来源读回 | 可执行 | 不启动重复采集/写 worker、不占生产 28765 |
| 共享 PG 的**候选**写入/namespace 变更 | **需明确对象与操作授权** | 指定表/schema、读写角色、预计行数、隔离、回滚、清理责任 |
| 正式生产 PG DDL/DML、accepted Head/CAS、生产调度 | **单独授权** | 准入门、前态、备份、失败恢复与读回计划 |
| 合入 main、正式运行包/28765 切换 | 按项目治理单独明确批准 | 固定代码 SHA、唯一入口路径、版本/配置/数据库可回滚性 |
| 物理删除、强推、破坏性回算 | **单独授权** | 提供影响、备份与不可逆性说明 |

需要检查当时适用的版本化发布硬门：既有合同所要求的合法数值回归、PG 原生消费者、特定 consumer 范围、冻结交易日验收等不能被 R8 的一轮定向单测自动豁免；但也不应反复重测与变更完全无关且有足够证据保留的内容。

## 10. 过度设计、过弱验收和不可执行标准

| 原方案/潜在执行习惯 | 审计结论 | 最小处理 |
|---|---|---|
| 每次修改都全量重新计算 5,225 股与 400 板块 | 不必要且拖慢推进 | 每工程包独立全量对照一次；日常受影响域定向回归 |
| 每次接口分页都重新扫描全历史字节与源码 | 可能引入显著性能问题 | 采用已绑定 SHA/owner manifest + 有界变更校验；只在合法修订边界失效 |
| 以旧生产者的分类当成“独立 Oracle” | 验收无效 | 独立原始数值和语义比较；留真实反例 |
| 真实市场必须出现跌破失效位才能关闭 D2 代码包 | 不可执行 | 真实输入链路 + 等于/高于/低于工程边界向量；未发生的实际分支不伪造 |
| 所有历史 `UNKNOWN` 清零才算通过 | 错误目标 | 只修有证据的错接/误 UNKNOWN；无法恢复的过去事实保留 UNKNOWN |
| 只有一条成功研究链就声称六入口完整 | 验收不足 | 至少真实成功、合法排除、源缺失三个不同路径及日期/时点核对 |
| 20–30 请求样本直接宣布 P95 强达标 | 统计依据偏弱 | 保留为烟测；正式目标扩大有界样本，明确失败率/冷热/负荷 |
| 以 5 日历史批处理冒充 5 次盘后正式运行 | 不可接受 | M3 必须有真实逐日运行记录，M1/M2 不因等待 M3 停工 |
| 为 D2 新增通用模型/缓存平台/平行 Head | 过度设计 | 用现役价格内核、Episode/Owner/PG/Head 和参数合同最小扩展 |

## 11. R2 推荐准入/关闭矩阵

| 工作包 | R2 方案准入条件 | 未来实现验收条件 | 可否独立推进 |
|---|---|---|---|
| A1 宽度/趋势 | 数据定义、阈值、对照基准冻结 | 全量数值/分类独立复核，完整趋势/环境来源接入 | 是 |
| A2 Priority / 07 | 缺值、坐标和计分字段语义清楚 | 全 5,225 行逐因、完整分母、真实 API/排序 | 是 |
| A3 D0 | 四场景能力与时间/上游合同冻结 | 两正式候选场景可信，诊断不准入，三态负例 | 是，限定场景 |
| A4 D2 | **冻结阈值和坐标合同先通过** | 新 episode 真实生产→后继 bar→reducer→Focus；旧 875 不回填 | **当前 BLOCK** |
| A5 / B 缓存 | 业务 SHA 与运行诊断隔离、来源图明确 | 冷热同业务 SHA；合法换源失效；坏 SHA 拒绝；真实接口/页面同版 | 是 |
| C 正常 APPEND | 前态 accepted/candidate 身份明确、来源与授权明确 | G1–G4 四门、无修订路径、故障/幂等、计时证据 | 是，先候选 |
| RI-02 | 检测与拒绝范围合同明确 | 修订负例 fail closed；真正有界修订另行验收 | 是，后续独立 |
| 发布/08 | 完整候选证据、适用硬门、独立明确授权 | 真实 Head/PG/API/28765 与回滚证据 | **不可自动执行** |

## 12. 建议 Codex 对 R1 进行的最小 R2 修订

1. 保留现有 0–9 节和 M1/M2/M3 骨架，不整体推倒重来；明确方案基线与新 ID 台账。
2. 把 §4 串行顺序改为 §2 的依赖/并行方案，确保及时真实收盘捕获和无修订 APPEND 不被 D2 合同阻断。
3. 补 D0 四场景能力矩阵、上游真实封存核验与治理三态语义；两个诊断场景不得因本轮修复自动晋升。
4. 给 D2 单独的**合同审定准入门**：明确失效价如何生成、何时冻结、如何在跨日 QFQ 精确仿射下合法比较、如何保留旧 episode 及异常边界；未经批准不实现正式 producer。
5. 给来源缓存增加业务 digest 与运行时诊断分离、传递来源绑定、稳定冷热读取与合法候选换源负例。
6. 将正式 Head 前态守恒与后验候选补跑**两类验收**分列，完整保留 R1.1 G1–G4 与 RI-02 fail-closed，报告的前瞻/真实首捕不能由补跑重建。
7. 新增 `FA8-PRIORITY-07`、`FA8-RELEASE-08`，修补收盘价静默回退及生产准入风险。
8. 对性能与浏览器验收声明“建议阈值/初步基线/正式 SLA”的区别；单次少量请求不可声明 P95 稳定可靠。
9. 每包输出 `现象→合同/代码证据→实际修改→独立数据分母→负例→候选 API/页面→PASS/PARTIAL/FAIL/OPEN→授权边界`，不为文档形式增加多套重复治理。
10. **本次修订只授权编写 R2 方案及在既有范围内开展独立代码/测试**；如果要进行共享 PG 写入、正式 Head 变动或正式部署，必须另外获得具体授权。

## 13. 本轮唯一外审结论

```
PLAN_CROSS_REVIEW = REVISE_REQUIRED
FA8-CORRECTNESS-01  = REVISE
FA8-D0-02          = REVISE
FA8-D2-03          = BLOCK_IMPLEMENTATION_PENDING_THRESHOLD_AND_BASIS_CONTRACT
FA8-INTEGRATION-04 = REVISE
FA8-DAILY-05       = REVISE
FA8-REVISION-06    = ACCEPT_WITH_FAIL_CLOSED_BOUNDARY
FA8-PRIORITY-07    = ADD_AND_REVISE
FA8-RELEASE-08     = ADD_AND_REVISE
IMPLEMENTATION_ACCEPTANCE = NOT_ASSESSED
PRODUCTION_AUTHORIZATION  = NOT_GRANTED
```

修订方案可单独进入下一次交叉审计；未触及 D2 合同/生产权限的代码修复无需等待全部设计条目通过。任何后续 `PASS` 都应明确限定为方案/代码/数值/PG/实际服务中的哪一层，不以其中一层代替其他层。

---

## 14. 依据与定位链接

1. [受审 Codex R8 原方案（最新提交）](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/docs/plans/V4_FUNCTIONAL_R8_REPAIR_PLAN_R1_20261021.md)
2. [R8 方案提交 `129f49c`](https://github.com/NanOns/a-share-market-structure-research/commit/129f49cbc0f57a9812f62d7072959eebae796349)
3. [R7 执行报告](https://github.com/NanOns/a-share-market-structure-research/blob/6b02414cf5824e9e59a04c7decc3fc75713b083c/docs/evidence/functional_audit_r7_20261021/FINAL_REPORT.md)
4. [D0 四场景能力矩阵](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/src/v4/confirmation_input_closure_r3b.py)
5. [D0 候选检测器](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/src/v4/confirmation_candidate_r4.py)
6. [D2 Reducer / 状态机](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/src/v4/research_state.py)
7. [R7 冻结失效检测器](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/src/workbench_analysis/r7_frozen_invalidation_v2.py)
8. [Priority 计分](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/src/workbench_service/research_priority_r1.py)
9. [BFF 与候选缓存/API](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/src/workbench_service/core_product_bff_r1.py)
10. [R1.1 四道身份/数值硬门](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/docs/upgrade/V4_INCREMENT_IDENTITY_PARITY_AMENDMENT_R1_1_20261013.md)
11. [真增量与性能总方案](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md)
12. [2026-10-20 连续候选日更执行记录](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/docs/evidence/continuous_daily_repair_20261020/README.md)
13. [既有同名 R8 来源修复合同](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md)
14. [项目 AGENTS.md](https://github.com/NanOns/a-share-market-structure-research/blob/129f49cbc0f57a9812f62d7072959eebae796349/AGENTS.md)

**版本治理说明**：本文件为对 **功能 R8 方案 R1** 的独立外审 R1，**不覆盖** 2026-10-15 已存在的 R8 来源修复合同，也不覆盖用户原始任务、Codex 原方案或 R7 已冻结的代码/数据报告。后续修订采用新文件/新版本并说明迁移影响。

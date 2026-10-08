# FEP R0 统计与算法独立交叉审计

日期：2026-09-30。范围：仅审计桌面 FEP R0（4338 行），未修改主合同、实现或 TDX。结论：CONDITIONAL_DESIGN_ONLY；下列 P1 未关闭前不得作为已冻结可执行预测合同。P1 指算法/证据有效性阻断；P2 指须补充的解释与执行约束。本文无实证 Alpha 结论。

| ID | 严重性 | 原文行号/章节 | 问题、反例与修正规则 |
|---|---|---|---|
| STAT-01 | P1 | 1101–1182 §17–18；1557–1563 §27 | 把 CONFIRMED、INVALIDATED、EXPIRED 直接说成互斥竞争结果不成立：同一 PREWATCH 可以第 2 日确认、第 4 日失效。必须分开 FIRST_EXIT_FROM_PREWATCH 与 ANY_EVENT_WITHIN_N。前者只认同一 episode 的首个事件，N 日内仍未退出增加 NONE 类，概率和为 1；后者是可重叠事件，不能强制和为 1。CONFIRMED 起始状态不进入首次确认风险集。冻结同日事件 reducer 优先级、退出后吸收规则、后续 episode 不回填旧标签。§27 的二分类示例须相应限定。 |
| STAT-02 | P1 | 1194–1265 §19–20；2333–2379 §52 | 训练行到底是入选事件、episode 首日还是每日存量未冻结。仅从 Validation Cohort 入选事件结算，却对每天 PREWATCH、CONFIRMED 或全市场调用，目标人群已改变。分别注册 ENTRY、DAILY_LANDMARK、MARKET_WIDE scope、采样单位和 settlement 请求来源；不能把 entry 模型用于存量/全市场。每日 observation 去重，并冻结日期/episode 权重；全市场无合法标签来源则仅标未启用，不能用入选样本冒充。 |
| STAT-03 | P1 | 1259–1265 §20；3017–3042 §78 | “只有 OBSERVED 训练”与“不全部 drop”缺少可执行桥梁。保留缺失计数仍可能得到按存活/可交易条件选择的有偏均值。各 target 分开成熟、行政右删失、停牌估值、真实缺口和退市。可观测结构标签不应因价格缺失一并删除。对不可识别连续收益不编造值；明确 complete-case estimand/缺失率与切片、敏感性界限，代表性门失败禁止推广为全部候选期望。若引入 IPCW/生存模型须另冻结可识别假设与权重，不能把所有退市当随机删失。 |
| STAT-04 | P1 | 1305–1341 §22；1704–1718 §32；2917–2938 §73 | 仅 label_matured_at ≤ training_cutoff 不足：早成熟标签可以被后来修订，训练 artifact 也可能在 T0 之后才接受。须要求 chosen_label_revision.available_at ≤ dataset_cutoff ≤ training_started_at ≤ training_finished_at ≤ model_accepted_at ≤ prediction_created_at ≤ observation_deadline；feature/system 可得性亦按 cutoff。每个历史 fold 独立选 as-of revision，不能今天选 latest corrected 再过滤成熟日。 |
| STAT-05 | P1 | 1647–1718 §31–32；1789–1818 §35；2847–2870 §70 | 有 walk-forward、purge 但没定义 tuning/calibration/test 三者隔离，也没冻结预处理 fit 范围。按时间设置训练、内层选参、独立校准、外层未使用测试，所有 imputer/scaler/winsor/bins/feature selection/OOD reference 均只在对应训练段 fit。模型拟合/校准数据必须不重用；默认随机 StratifiedKFold 不可使用。按标签实际观察终点和可得时间清除跨边界行，不能仅按名义 N 推算。 |
| STAT-06 | P1 | 1453–1469 §24.3；1480–1538 §25–26；2014–2015 §41；3085–3102 §81 | 286 行不等于 286 独立样本。同行业同日与同股重叠窗口会夸大 support/confidence；Market 每日仅一个独立 outcome，复制到 5000 股票不能扩样。最低门须同时检查独立日期块、entities、episodes、类别事件数及切片。先按日期算损失/同日候选 spread，再以时间块保留横截面一起评估不确定性，块长预注册且覆盖重叠窗口；不得以 IID Wilson/binomial 区间包装确定概率。 |
| STAT-07 | P1 | 1422–1445 §24.2；1516–1540 §26 | 给出 8 个初始分桶维度仍可能极稀疏；“remove minor condition”未定义，会成为挑选最好历史结果的入口。冻结条件顺序、各层精确键、缺失类别、统计权重、估计器、分位数约定；只按支持度选择层，不按结果正负 backoff。GLOBAL 必须仍限制 entity/scope/target/horizon/evidence lineage，不跨市场/股票/板块混合；fallback 后明确实际条件，不能继续声称精确匹配。 |
| STAT-08 | P1 | 1073–1097 §16；1571–1575 §27；2032–2055 §42 | ATR 标准化只有名称无公式。收益比例/ATR 元直接相除量纲错误。令统一坐标 P0、A0>0：MFE_ATR=max(0,max(Hj−P0))/A0；MAE_ATR=min(0,min(Lj−P0))/A0；PATH_MDD_ATR=min_j(Pj−max(P0..Pj))/A0。若沿用 MDD 百分比除 A0/P0，必须另命名，不能冒充峰谷价差 ATR。ATR 未知/0 输出 UNKNOWN。连续目标模型约束 q10≤q25≤q50≤q75≤q90；MFE≥0，MAE/MDD≤0；嵌套 horizon 的路径极值与 FIRST_EVENT CIF 具有相应单调性，收益均值则无该单调要求。 |
| STAT-09 | P1 | 2640–2655 §62；3137–3185 §83–84；3272–3286 §86 | “记录 experiment count/new lineage”不能消除同一测试集反复挑选的偏差。冻结 primary target/horizon/metric、试验预算、一次性外层评估窗口、成对 baseline 差值和晋级规则；调参后不能重用已看过的窗口作为独立证据，须新未使用窗口或预注册顺序检验。所有失败和停止试验留档。Shadow 同样若被用于不断调参，不再是最终独立检验。 |
| STAT-10 | P1 | 1847–1895 §37–38；3085–3102 §81 | Rank IC、top vs lower 的主验收没有对照 PRIORITY_V1，模型可能只学会已有 Core 排序。需同日、同 scope、同候选集、同可用 outcome、同 K/覆盖率，与 PRIORITY_V1 和基础 rate 成对比较；不能不同候选集合比较。固定 K/tie/UNKNOWN/OOD规则。OO D 拒绝覆盖下降不能提升表面成绩后冒充全 scope 改善；同时报全体覆盖与拒绝切片。 |
| STAT-11 | P2 | 1789–1818 §35；1956–1969 §40；2008–2021 §41 | CALIBRATED/READY 无方法、bin 边界、最低事件数和有效期；全局校准不能保证细分 regime/Top-K 校准。Brier/LogLoss 含区分能力，不能单凭它们认证 calibration。冻结 calibration 样本/方法/权重/可靠性图与不确定性，过期/支持不足分开 UNKNOWN。训练分布 quantile spread 是结果离散度，不能命名模型置信区间；confidence 必须有独立语义。 |
| STAT-12 | P2 | 2264–2303 §50；2308–2329 §51 | 同一 T0 的示例对 A 使用市场预测 +5%、B 用 −1%，未说明条件对象，容易混淆共同基准与条件化基准。直接建模 stock_R−benchmark_R 的分布；不要以 median(stock)−median(benchmark) 或两个概率相减构造超额分布。若展示条件化市场预测须标条件相同/不同。MFE/MAE 两个边际中位数不构成联合可实现交易收益或先后顺序，禁止当作可成交盈亏比。 |
| STAT-13 | P2 | 1899–1928 §39；2679–2715 §64–65 | OOD 与 drift 只有例子，无法判定。分离 schema/unseen category 硬失败、缺失率异常、单变量支持、联合支持和随时间漂移；参考分布仅用训练数据冻结，阈值另用可行性样本预注册。NO OOD 只代表未触发检测，不能证明未来无分布变化；concept drift 需成熟标签延迟监控。 |
| STAT-14 | P2 | 1109–1137 §17；2383–2457 §53–55 | TREND_CONTINUE/ACCELERATE/FLATTEN/BREAK、breadth continuation、regime transition 未规定起始风险集、终点/首次到达语义、阈值和 Contract Version。冻结逐 target 状态转移表；在旧 State Contract 的未来轨迹不足时该 target 禁用，不得混合后续新版状态结果。多 target 分别训练资格与 maturity，不能一项缺失使整行删除。 |

## 最小反例验收

1. PREWATCH 第 2 日确认、第 4 日失效：FIRST_EXIT=CONFIRMED；ANY_CONFIRM=1、ANY_INVALIDATE=1。第 N 日仍 PREWATCH：FIRST_EXIT=NONE。不能两个定义共用 target_id。
2. 100 股票同一天、20 天重叠窗口：support 不得等同 2000 独立观测；Market 标签同日不得复制扩样。
3. 标签 9 月 1 日成熟、10 月 1 日修正：9 月 30 日模型必须使用当时版本；10 月 artifact 回放 9 月不可标 FIRST_OBSERVED。
4. 预测日期相同，A/B 的候选列表和 PRIORITY_V1 对照必须完全相同；只排除模型未覆盖的差样本应触发覆盖门失败。
5. P0=100，A0=2，路径收盘 100→120→110：MDD_ATR=−5；MDD百分比=−1/12；后者除(A0/P0)=−4.1667，二者不是同一 target。
6. Calibration 输入重用基础模型训练行、或 scaler 对完整 train+test fit：测试必须阻断。

## 方法依据（仅用于审计方法，非 A 股有效性证据）

- [scikit-learn 概率校准 API](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV)：明确基础模型拟合与校准数据应隔离。
- [scikit-learn 数据泄漏说明](https://scikit-learn.org/1.5/common_pitfalls.html)：测试数据不得参与预处理 fit/特征选择。这里应用为逐时序 fold 隔离。
- [scikit-learn 嵌套验证示例](https://sklearn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html)：选参与最终性能估计需分离；本系统须将示例改为时序结构，不能照搬随机切分。
- [Petersen，金融面板标准误研究，NBER](https://www.nber.org/papers/w11280)：横截面及同实体相关性影响误差估计；本报告日期块/episode 检查为针对本系统的工程建议。
- [竞争风险首事件分析研究](https://pubmed.ncbi.nlm.nih.gov/16980152/)：首事件累计发生概率应正确处理竞争事件。本报告进一步要求先明确该系统的事件是否实际互斥，不能因有三个标签便称竞争风险。

下一步：主审合并架构/合同审计项，逐项记录采纳、修复章节、验证反例及保留限制；上述 P1 的设计语义须先关闭，再作为受限新增合同并入。统计阈值不在本次只读审计中拍定。
## 二轮独立复核：FEP R1

复核日期：2026-09-30；对象：artifacts/fep_20260930/FEP_R1_DRAFT.md，最终复核版本包含桶内归一化修复。结论：**DESIGN_ACCEPTABLE_FOR_INTEGRATION / PARAMETERS_AND_IMPLEMENTATION_PENDING**。可作为受门控的新增设计并入；不等于模型生产或实证预测能力通过。仅复核统计语义，SQL/跨表约束另由主审负责。

| 原问题 | R1处置 | 二轮结论 |
|---|---|---|
| STAT-01 | FEP.5区分FIRST_EXIT与ANY_EVENT、加入NONE及episode风险集 | 设计关闭 |
| STAT-02 | FEP.1/4分别ENTRY、DAILY、MARKET_WIDE；缺标签来源NOT_ENABLED | 设计关闭 |
| STAT-03 | FEP.6明确complete-case子集estimand和代表性权限门；target独立 | 设计关闭；效果/代表性等待数据 |
| STAT-04 | FEP.3冻结label revision可得性、训练/接受/激活/deadline时序 | 设计关闭 |
| STAT-05 | FEP.9时间选参、独立校准、outer test、训练内预处理及真实标签purge | 设计关闭 |
| STAT-06 | FEP.4/8/11日期权重、日期块/episodes支持、多相关性分析 | 设计关闭；具体支持阈值保留门控 |
| STAT-07 | FEP.8固定backoff、不跨base partition、不按收益选层 | 设计关闭 |
| STAT-08 | FEP.5正确价格差ATR公式，FEP.9输出coherence约束 | 设计关闭 |
| STAT-09 | FEP.9固定外层窗口、实验预算、禁止new lineage洗白已看测试 | 设计关闭 |
| STAT-10 | FEP.11同日同scope候选对PRIORITY_V1成对比较并保留拒绝覆盖 | 设计关闭 |
| STAT-11 | FEP.9/10/13独立校准、支持/有效期、概率与区间语义及UNSET门 | 设计关闭 |
| STAT-12 | FEP.5直接excess标签，禁止中位数/概率之差和MFE/MAE盈亏比 | 设计关闭 |
| STAT-13 | FEP.10分层OOD/训练reference、成熟标签drift、NO_TRIGGER限义 | 设计关闭；阈值未冻结不发OOD_OK |
| STAT-14 | FEP.5未完成结构target为REGISTERED_NOT_ENABLED，开启须另交转移表 | 设计关闭 |

二轮新增STAT-R1-01（P1）已修复：原初R1全scope日期权重直接用于条件桶会令均值/频率少归一化；现FEP.8第112行明确桶内D_B、n_dB重算w_iB且总和1。FEP.16第196行加入单样本桶反例：y=0.1，mean=0.1、positive_rate=1。复查已关闭，不再阻断设计并入。

剩余项属于显式实施/参数门：逐字段映射、模型与target实际可用性、cutoff具体配置、校准/代表性/support/OOD阈值、OOS样本与晋级规则、训练及生产功能验收。R1对这些未完成能力限制了权限，本次不要求先取得真实Alpha才能并入设计，也不把这些门描述为已通过。
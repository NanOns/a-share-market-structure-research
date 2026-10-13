# 大A V4｜增量日更身份守恒冲突订正与最小闭环任务卡 R1.1

- 日期：2026-10-13
- 适用仓库：`NanOns/a-share-market-structure-research`
- 目标分支：`codex/v4-full-closeout-20261012`
- 审计基线 SHA：`8a6cb616ee01fefb7e90538bb77168ab2aff8fe1`
- 上位原任务：`docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`
- 本轮唯一状态报告：`docs/audits/v4_runtime_repair_20261013/REPORT.md`
- 本文性质：**只修正原总方案 R1 的增量数值／身份验收冲突，并规定最少的继续执行与交付工作**；不是重开 V4 全量审计。保留 R1 的全部其他要求。

## 0. 判定与本轮目标

经核对原任务卡第 4.1、4.4、7.C、8.3.6 节以及实证报告，确认旧 Owner/Anchor/Episode/历史发表结果必须保持不变，而重新全量重放会因新生成的输入绑定、available_at、source_fact_digest 和相关路径生成不同 Anchor/Episode、D2/Focus 的 ID 或 Digest。**要求这些全新生成的历史身份与原已发布身份逐字相等，是设计冲突**。不能为了让比较器通过去替换、改写或重算原历史 Owner。

但是**业务数值一致≠完整增量正确**。结构生命周期衔接、旧 ID 的可解析性、新 ID 的确定性、输入摘要的真实引用、Focus/Forward 事件衔接都必须验证。

本轮最高目标：以不改原正式历史的方式，重新定义可执行的 **数值等价 + 状态等价 + 旧身份守恒 + 新引用正确** 验收；有条件闭环 10 月 13 日正常 APPEND；再依原计划仅打一次正式 EXE 和做一次正式端口切换。拒绝为了匹配重建参考而重写旧 Owner。

## 1. 最新实证与可复用成绩

- 本地生产原 28765 仍运行原 EXE；当前正式 Head/T0 为 **2026-10-12**；2026-10-13 未正式发布。不能把源代码 Git push 等同于生产安装。
- A API/PG 查询真分页、B 新股／新代码、D Worker／进度：各有范围限定的工程测试 PASS；76 项专项测试通过。不重新开始这些任务。
- A 隔离 PG/HTTP 的多接口延迟已明显下降，但尚非正式端口＋真实日更满负荷数据。
- C 正常 APPEND：已有 30 对象的历史／Profile 对照，以及全日 5,225 股票／400 板块的指定数值测试；已知差异集中于历史 Anchor／Episode／D2 provenance 身份链。需审慎核实所有**业务字段和引用语义**，不能把现有局部 PASS 宣布为全域 PASS。
- `docs/audits/v4_runtime_repair_20261013/ANCHOR_ID_ROOT_CAUSE.json`：原历史 raw、调整源文件 digest 和 affine 系数一致，但重放时的 `available_at` 与 `source_fact_digest` 改变，Anchor ID 因此改变。
- `FOCUS_FORWARD_PARITY.json`：30 个样本中 episode_id 8 项，input_digest/prior_state_binding/publication_id 各 29 项差异；参考结果 `FAIL_PARITY` 必须留存为旧合同失败，不可改写证据。新增改进后的 **R1.1 评估** 可独立记 PASS/FAIL。

## 2. 修订验收合同：四道彼此独立的门

### G1：业务值与状态等价（硬门）

在相同交易日、证券池、源价格、复权口径、代码／参数版本和比较适用范围内，比较 APPEND 与已冻结参考的：

1. **所有影响交易研究的数值**：OHLC、MA5/MA20/MA60、ATR、收益率、各周期复权因子、Profile 派生因子、Sector 宽度/强弱/Seed/Rotation、Focus/Forward 结果、当期日周月；包含精确数值、空值类型、舍入规则。
2. **状态与质量**：DATA_INSUFFICIENT/UNKNOWN/OBSERVED、停牌/缺源、新股首日、有效样本量、对象计数、日期窗口及预判状态。
3. **业务事件语义**：同一证券在同一 as-of 截面的结构锚点位置、关键价格、触发条件、有效／失效、事件类型、Episode 开始/结束日期、连续状态转换和 Forward 到期结果。
4. 不允许因 ID 不同而将整个结构字段或 Focus 记录从比较中删除。对 ID 字段做“语义匹配＋引用检验”（G2、G3），而非盲目跳过。

通过条件：应比较的全部业务字段零不明差异；允许不同的仅为被具体清单列出的**运行派生身份／来源字段**，且通过 G2/G3。负例：价格或质量不同不能用“ID 不同”解释过去。

### G2：已发布历史身份守恒（硬门）

以正式当前 Head 的原始版本作为唯一守恒参照（**不是**重新生成历史的全量副本）：

- 所有先前正式发布交易日的 Owner binding、source SHA、Anchor ID、Episode ID、D2/Focus publication ID 及已有引用**不变**。对比历史引用集合与前态链，可使用正式 Head 中已有的绑定和 hash，不按重建参考猜测旧 ID。
- 10 月 13 日 APPEND 只能新增当日 Owner 或显式追加新状态引用；需要延续历史锚点/持续事件的对象必须**沿用正式旧 ID**，不能因为重算参考导出新 ID，不能让已存在 Episode 作为另一个新 Episode 重复入库。
- 对所有从当日业务结果发出的 `previous_* / parent_* / anchor_id / episode_id / prior_state_binding` 等引用做递归可解析性、目标日期 ≤ T0、类型／证券一致性检查；不允许断链、循环、孤儿引用及不一致的历史别名。
- 相同已接受 Head + 相同当日源输入重复 APPEND，得到相同当天稳定业务实体 ID 与历史身份关联；**新发布的总体 token 可以不同于另一独立全量重建运行的 token，但必须对其自身实际输入可确定／可复核**。

### G3：新 Digest／来源完整性（硬门）

- 每个**新** `input_digest`／`publication_id` 必须按实际规则独立重算：读取真实 `source_bindings`、前版正式 Owner、对应数据日期、参数/算法版本和实际 raw bytes；核对 hash、source type、code、T0、provenance 可达性。
- 检查前代引用中的全部 digest 能和已正式接受版本对应，而不是指向一个在隔离全量重建中虚构的历史 owner。
- 禁止通过把新摘要硬替换成 full-replay 的摘要、关闭 hash 校验、设空 provenance、删除失败字段来通过。
- 对本轮 8 个 episode_id 差异、29 组 input_digest／前态绑定差异保留**逐类、至少代表样本和全量聚合**的说明与验证结果；不需要重复打印成千上万行，但须有可重现失败计数与检验条件。

### G4：增量执行与发布正确性（硬门）

- 普通 APPEND 的 `compute_sessions` 仅新增交易日；允许历史窗口只读加载，不得秘密重算已发布 Owner。
- 完整走当天源准入、新代码、Core、Profile、Sector、Focus/Forward、周期、PG 读模型准备、统一业务 token、原子 Head/CAS、读回；失败不得覆盖上一正式版本。
- 验证源／复权／算法版本未修订时启动正常 APPEND；修订被发现时必须转入 `RANGE_REPAIR_REQUIRED`，不能错误使用 APPEND。
- 真实生产端口与 EXE 验收只在上述全部必要门通过之后进行；不要求重新测试旧 V1/V2 历史功能。

## 3. 如何建立正确的参考与比较器（不需要再跑巨大全量）

**双参考**，职责不同：

- **参考 A：正式前态（production accepted predecessor）**。用于验证 10 月 12 日及以前不可变、旧 ID/引用守恒、新 APPEND 继续衔接历史。这是旧身份的唯一权威参照。
- **参考 B：固定真实输入下的隔离全量值（numeric/semantic oracle）**。用于验证 10 月 13 日业务值、结果、结构语义、状态和周期，不要求其重新创建的历史 Anchor/Episode ID、输入路径/available_at/publication_id 与 A 完全相同。

建议独立生成稳定比较键（仅比较器用，**不写正式身份 ID**）：

- 结构事件：`security_id + anchor/event 类型 + 初始触发 T + 原始区间或关键价 + 算法模式`，针对同一事件可能多个锚点时加严格时间序号/明确业务 disambiguator；无法唯一匹配则 FAIL 并人工定位。
- Focus Episode：`security_id + 事件来源 + 开始交易日 + 连续事件语义 + 适用状态`，对持续 Episode 必须反查正式版本旧 ID。比较 episode 数量、起止、是否延续、状态路径、后续结果。不得仅以数量相等认为通过。
- 来源引用：`old_reference == accepted_predecessor_reference` 与 `new_digest == independently_recomputed_digest(actual_inputs)`，不是 `new_digest == rebuilt_full_reference_digest`。

将旧 `FAIL_PARITY` 原记录保留，新增 `R1_1_SEMANTIC_AND_IDENTITY_PARITY.json`，逐类给出 `G1/G2/G3/G4` PASS/FAIL、差异数量、受影响对象与可复核说明。不要覆盖旧的证据文件，也不要再更改历史 Owner。

## 4. RI-02 修订传播：不应无条件拖延正常日更

现代码能识别修订但尚未完成最小 `RANGE_REPAIR` 计算。应做**两个明确范围的决策**：

1. **2026-10-13 正常新增日**：若独立证据确认源、复权、算法、旧历史参考窗口对本次无修订，则只走 APPEND，RI-02 的全套修订引擎**不作为这一次正常 APPEND 部署的无条件前置**。保留 `REVISION_DETECTED => FAIL_CLOSED/RANGE_REPAIR_REQUIRED`，不得把异常吞掉后发布。
2. **今后源或算法发生真实修订时**：应进入单独的 RI-02 精准修复任务；先完善对象/时间窗口影响图和不重写原正式 Head 的新修订版本链，做一例真实修订的对照，再授权自动按范围修复。若没有该能力，保持不发布受影响结果并显示明确状态；不暗中跑全市场历史。

这个决策不是取消 RI-02，只是不因为尚未发生的修订场景永久阻断无修订日更。若 13 日事实上存在复权或源历史修订，则不能套用上述豁免，必须先进入修订路径处理。

## 5. 最小 Codex 执行顺序（一次通过后统一部署）

### T1 — R1.1 合同及比较器修复，先不打包

1. 增加 R1.1 订正文件，指出原 R1 `4.4 / 7.C / 8.3.6` 的优先级被本文替代。旧文档保留版本，不静默覆写。
2. 从 8 个 episode、部分 Anchor、29 个 provenance 差异中拿固定小样本逐一分类；用真实前态 A + 数值 B 验证所有新引用。
3. 定向修改比较器，不随意改变生产核函数。对全部 30 样本执行 G1/G2/G3；Structure 的不唯一语义匹配必须明确 FAIL。
4. 若小样本通过，再执行一次全 5,225 证券、400 板块和当日 Focus/Forward、周期的必要差异检测。已冻结相同输入可以复用参考，不重新抓取、不重算旧阶段。
5. 保留原 `FAIL_PARITY`，新增结构化 R1.1 结论（只记录变化和聚合统计）。

### T2 — RI-02 有界分流验证

- 固定正常无修订样本：APPEND 一次，所有历史 Owner 未改；当日完整结果及 digest 可重算。
- 固定一个修改旧 raw/bar/factor 或调整版本的负例：明确拦截 APPEND、保留 Head，任务状态写 `RANGE_REPAIR_REQUIRED`，不要隐式全日重放。
- `RANGE_REPAIR` 正式执行功能单开任务，不在本轮为了演示再花数小时计算全量历史。

### T3 — 保留已通过 A/B/D，只补“真实汇合口”

- 对源码变更影响到的请求/进度/新代码仅跑定向回归，不重跑 76 项全部，除非修改共享底层影响范围。
- 跑一遍实际无修订新增日：`新股/代码集合变化 → Core/Profile/Structure/Sector/Market/Focus/Forward/周月 → PG 索引 → Head 发布门`。记录各阶段真实耗时和总耗时；不能把下载等待时间算成纯计算时间。
- **若已经有正在运行的真实派生任务，先检查状态与安全边界，不并行启动第二个生产者，也不要擅自取消、清空或重置当日数据。**

### T4 — 唯一正式交付（T1—T3 全过才执行）

- 仅一次本地 EXE 打包、一次安装／安全切换至原 `127.0.0.1:28765`，保留旧包；Windows 生产 PG、7 路 HTTP、首页/股票/板块/Focus/市场/诊断、同一 T0/token、托盘进度一轮实测。
- 测**实际 Worker 计算期间**的业务 API 延迟（此前仅隔离 CPU 模拟通过）；分页和新股 `SZ.301660` 第一日无历史伪造应在正式界面可见。
- 包成功之前仍标记 `ENGINEERING_ACCEPTED`, 不写 `PRODUCTION_ACCEPTED`；生产切换后再更新实际 T0/时间、发布 Token 及任务是否成功。
- 不要求重复跑 7288 项回归、做无关旧版本审计、多次打包、昂贵回滚/压测矩阵；保留一次必要的 last-good 安全机制验证。

## 6. 阶段定义与决策

- **当前唯一总状态**：`BLOCKED_R1_PARITY_CONTRACT_DESIGN_CONFLICT`；R1 A/B/D 的工程 PASS 保留；C 仍未被新合同正式接受；E 没有执行。
- **可继续的条件**：G1/G2/G3 在代表样本全部通过；正式真实新增日 G4 到 PG/Head/HTTP 全链通过；修订输入不存在或被 fail-closed 正确隔离。
- **绝对不允许**：改写历史 Owner 只为匹配 full-replay 生成的新 ID、禁用摘要验证、跳过 Focus 延续性、删除错误证据、把原未部署代码宣称已上线。
- **非本轮阻塞**：无修订正常日下的自动 `RANGE_REPAIR` 成熟化、旧 V1/V2 历史功能复验、无关高级功能、严格 PIT 或交易权限；单独 backlog 记录。

## 7. 给 Codex 的最短执行指令

> 读取最新 `docs/audits/v4_runtime_repair_20261013/REPORT.md`、`DESIGN_CONFLICT.json`、`ANCHOR_ID_ROOT_CAUSE.json`、`PROFILE_STRUCTURE_PARITY.json`、`FOCUS_FORWARD_PARITY.json`，按本 R1.1 文档继续原任务。禁止推翻 A/B/D 已验收成果。旧 `FAIL_PARITY` 永不覆盖；以正式 last-good 前态和隔离全量业务值建立双参考，分别审计数值/状态、旧身份守恒、新摘要/引用的独立可重算性。仅修比较器/实际确有缺陷的增量续接代码；不改旧历史 Owner 来凑全量重建 ID。无真实历史修订时，RI-02 仅做修订侦测与阻断负例，可把完整 RANGE_REPAIR 放后续任务。通过全部定向门之后做一次真实 10 月 13 日全链、一次 Windows EXE、一次原端口切换。所有时间和新旧 T0 真实记录，不要承诺耗时，也不要重跑 7288 项旧测试。唯一主报告追加 R1.1 结论、Git SHA、问题状态、实际是否发布和未完成项。G 盘临时产物；不上传 Drive。

# 大A V4｜R4.3 四交易日基础数据全闭环、通达信最新成员统一回算、正式验收与前端顺序门

- **版本**：R4.3 / 2026-10-09
- **性质**：下一轮唯一执行主任务卡；替代 R4.2.1 的后续执行调度，继承其已完成实现、原始收据、版本封存与未关闭的问题。**不篡改任何已接受历史事实。**
- **仓库**：`NanOns/a-share-market-structure-research`
- **执行分支**：`codex/v4-fp14-r2-repair`；本卡编制时远端 HEAD `1053f07afa9c5d16940c9aa7483eb1bad8690b3d`。Codex 启动时必须再次获取最新 HEAD、检查 working tree 和远端跟踪关系，不擅自移动 `codex/v4-system-reform`。
- **冻结的目标交易日**：**2026-09-28、09-29、09-30、10-08**；2026-10-01～10-07 休市。**2026-10-09 如尚未收盘，不得生成完整日 K、冒充目标交易日或与前四天混算。**
- **授权更新**：用户明确批准：**若无法取得以上各日真实的通达信行业/概念成分股历史快照，则可以冻结一份最新通达信行业/概念成员关系，并用同一份成员集合回算上述四个交易日的研究指标。**该批准仅扩大“运营研究的事后回算口径”，**不是**许可将 10/09 的成员集合伪称 9/28、9/29、10/08 当时所知，更不是 strict PIT 历史回测准入。
- **总执行顺序**：先四日基础数据与算法数据链彻底闭环 → 独立外部验收 → 安全发布并完成 10/08 同一版本线上读取 → **然后**按照已经归档的《V4全功能正式生产前端｜完整任务卡合集》处理页面验收剩余问题。不能颠倒顺序；也不得用等待真实 Forward 成熟样本来阻止独立可验的工程收尾。

---

## 0. 任务背景及当前已知真实状态（先核验，不能直接信收据为外审）

截至 `1053f07`，已有：

1. **官方通达信 ZIP**：父包与 2026-10-08 包已按 SHA/CRC 验证；typed A-stock delta V2 给出四天 canonical RAW BAR **5210 / 5211 / 5213 / 5209**；18 项指数、B 股、回购等异类数据不再阻塞全部 A 股日更，原始异常须保留。
2. **BaoStock**：10/08 正式入口已经到达 `BAOSTOCK_DAILY_SNAPSHOT_READY`；`GBBQ` 有本地实际文件及 SHA，但旧版正式 GBBQ 读取路径不正确；特殊时期/生命周期新版 corrected 输入存在，旧正式消费者不能直接接入；旧 Builder Registry 的 SHA 绑定与变更后源码不一致。
3. **基础数值**：9/28～9/30 旧 **528 条 QFQ/ATR20 相关能力缺口**在限定价格坐标和当前/T-1 窗口已有 528/528 corrected 可计算，旧 **35 条停牌无 BAR**不造数据；四天 Core/Profile 候选已存在，但 R4.2.1 明确 `corrected_candidate_rebuilt=false`，不能冒充本轮全部正式接受。
4. **板块体系**：唯一正式主体系为 **TDX 行业 + TDX 概念**（`INDUSTRY:`／`THEME:`）。9/30 有旧版已接受 **378 板块、50,162 成员关联**；9/28、9/29、10/08 无已接受的 exact-date TDX 成员证明。BaoStock 证监会 **83 个行业**仅可单独 `BAO_CSRC:` 辅助展示，**绝不可替换** TDX 的 sector、LOO、主线、Rotation 或板块排名。
5. **证券身份**：原先所说“348 条未绑定”不是 348 个缺价格的沪深 A 股，其中含北交所候选等；已有细分约 246 稳定候选、101 未解析、1 生命周期分支和 2 个排除指数，必须按日期再次真实核对，不能把代码前缀当正式身份。
6. **生产读数**：现有 `/api/v4/context` 仍以 **2026-09-30** 为 accepted trade date；前端 378 个板块及其他 last-good 仍可以用，不能因为准备新候选而清空。
7. **工程测试**：此前提交包含 scoped CAS/失败回滚测试，42 个定向测试报告通过；**工程自报测试、外部复算、正式生产发布是三个不同门**。

**本轮不得重做**已经哈希一致的整份 551MB 官方源下载、528 条旧修复，以及非目标产品的通用浏览器矩阵；发生实质源版本变化才作版本化增量重算。不得把未授权的生产切换简写成“已完成”。

## 1. 本轮最高优先级：通达信“最新成员回算历史”的正式新口径

### 1.1 以可执行合同替换此前的无期限等待

原 R4.2.1 将缺 9/28、9/29、10/08 exact-date TDX 关系当作正式板块历史计算整体的阻塞。**现由用户授权追加一个独立回算口径**，不再要求为了运营研究无限等待历史快照。

必须实现两套不可混用的语义：

| 层级 | 权威成员输入 | 数据性质 | 可以用于 | 不可以用于 |
|---|---|---|---|---|
| `TDX_HISTORICAL_PIT` | 真实日期有效、存在首次可见性证据的 TDX snapshot | `PIT_OBSERVED_ACCEPTED` | 有证据的历史 T0、严格回放 | 用最新集合替代无证历史 |
| `TDX_LATEST_MEMBER_RETRO_V1` | **一次冻结的最新** TDX 行业+概念成员集合（统一应用四天） | `RECONSTRUCTED_LATEST_MEMBERSHIP`、`AS_RECORDED=false` | 当下研究：按最新成分回算四日板块强度、宽度、排名、相对强弱、横向对照、观察与当前解释 | 冒充真实历史成员、回测/预测标签、历史首次可见、strict PIT、真实前瞻信号绩效 |
| `BAOSTOCK_CSRC_AUX` | BaoStock 证监会分类 | `AUXILIARY_ONLY` | 明确标识的辅助对比 | 替换 TDX 主板块 |

本轮**必须实际运行** `TDX_LATEST_MEMBER_RETRO_V1`，不允许只增加 enum、policy 或留一份 `SCOPED_ADMISSION_REQUEST` 就停工。对未取得可靠历史 PIT 的日期，正式**运营研究**可使用上述回算；历史严格 PIT 字段继续按其原权限保持 `UNKNOWN/NOT_GRANTED`，这两件事不矛盾。

### 1.2 最新成员快照抓取及冻结

- 先在 `D:/new_tdx` **只读**调查通达信行业/概念成员源，至少核查 `T0002/hq_cache/tdxhy.cfg`、`tdxzs.cfg`、`infoharbor_block.dat`、有效的 `block_*.dat` 所在真实路径及其他项目已验证来源；文件名存在不代表其内容能够还原全量成员。源不足时主动检查 TDX 可访问的官方下载/更新流程，不能只说目录没文件。
- 记录 `capture_id`、获取时刻（Asia/Shanghai ISO8601）、实际读取/下载地址、原文件 SHA/bytes、原版 sector IDs/名称、分类、成员证券代码及其身份映射、数据覆盖率、解析器版本与 hash。**禁止用本地 mtime 当作历史 effective_date 或首次可见时间。**
- 只生成**一份冻结的最新成员快照** `TDX_MEMBER_SNAPSHOT_S_20261009_<digest>`，四天都引用**同一 digest**。若抓取时正值 10/09 盘中，其 `observed_at` 是 10/09 的真实采集时刻，四日价格数据截止仍停在 10/08；不得夹带 10/09 未完结日 K。
- 成员需多对多：一只股票允许同时在一个行业和多个概念中。保留 TDX 原 `sector_id`、`sector_type`、`security_id`；不可映射则独立隔离报告，不得无声丢弃、重名合并或改用 CSRC 填空。
- 按四天各自的日期有效上市证券、停牌状态和真实价格覆盖做交集：**不能让 10/09 成员里在 9/28 尚未上市的股票倒灌 9/28 的价格或宽度分母。**记录每个板块 `current_member_count`、`target_date_eligible_count`、`quoted_count`、`unmapped_count`、`missing_bar_reason`。退市/历史已被移出的原成员无法由最新关系找回，其 **survivorship_bias_risk=true** 必须显式展示。
- 和 9/30 已接受的 378/50162 做同日集合差异（新增/移出/ID 合并/名称变化/金额与宽度口径），原 9/30 首次发布快照绝对不覆盖；另生成 9/30 最新成员**回算视图**，让四天比较保持同一成员口径。
- 如果 TDX 最新成员源本身只覆盖一部分行业/概念，立即进行补采、解析和覆盖验证；不允许用“最新”掩盖只有几十个板块、只采行业未采概念，也不许硬凑 378 个。基准 378/50162 仅用于比较，不是必须强制相等的魔术常量。

### 1.3 新数据结构和传播规则

```json
{
  "membership_mode": "TDX_LATEST_MEMBER_RETRO_V1",
  "taxonomy": "TDX_INDUSTRY_CONCEPT",
  "membership_snapshot_id": "TDX_MEMBER_SNAPSHOT_S_20261009_<digest>",
  "membership_observed_at": "<actual Asia/Shanghai timestamp>",
  "member_set_asof": "<actual observed date/time, not target trading day>",
  "trade_date": "2026-09-28 | 2026-09-29 | 2026-09-30 | 2026-10-08",
  "knowledge_lineage": "RECONSTRUCTED_LATEST_MEMBERSHIP",
  "AS_RECORDED": false,
  "PIT_ELIGIBLE": false,
  "HISTORICAL_FIRST_AVAILABLE_PROVEN": false,
  "production_eligible_scope": "DATED_OPERATIONAL_RESEARCH_REPROJECTION_ONLY",
  "survivorship_bias_risk": true
}
```

- 上述元数据要**逐消费者继承**，包括原 V4 Sector Native、Base/Seed 聚合、B0、Rotation、LOO、stock-relative-sector、板块主线/Focus 关联与所有 API/页面 tooltip，不得在某层转换时丢掉。
- **强制同口径比较**：四天板块排名、轮动差分、T-1/T-3、member retention、事件前驱均使用同一冻结 S；不能 9/30 的 original PIT 成员与 10/08 最新成员直接进行未标记的变化比较。真实观测的价格仍按四日各自 T0，成员是统一代理回算，前者可核对但后者存在事后组成偏差。
- 原 9/30 `PIT_OBSERVED_ACCEPTED` 仍按旧 namespace/旧 SHA 原样保留；新的 9/30 视图属于不同版本，禁止相互覆盖/用新的去给旧严格回测背书。
- 不得用 10/09 的成员代理给 9/28 生成“9/28 当时已经知道”的历史建仓提醒；最多作为当前对历史形态的事后结构研究。因不可避免的幸存者偏差与未来成员变化，**不作为严格历史回测盈利统计、FEP 预测特征冻结或 T0 首发信号**。

## 2. 四交易日全量数据闭环：按日期逐项完成

### 2.1 日历与目标 universe

- [ ] 冻结交易日 9/28、9/29、9/30、10/08；逐日确定 T-1/T-3：9/28=9/24、9/22；9/29=9/28、9/23；9/30=9/29、9/24；10/08=9/30、9/28。9/25 和 10/01～10/07 非交易日不造 K 线。
- [ ] 以已接受 canonical identity + 当日合法上市/退市日期 + TDX/BaoStock 名册交叉建立每日证券集。四日 RAW 基线依次 5210/5211/5213/5209（仅已有 canonical 主研究范围，须重验而非强制写死）。对北交所 246/101/1 和两个指数分别由真实身份来源处理；若原正式产品 scope 包含 BJ，不能为了宣称“全市场 PASS”擅自剔除 BJ。将不支持的市场与身份单列明确门禁。
- [ ] 逐日核验 open/high/low/close/volume/amount、合法交易日、暂停/复牌、复权现金/配股/送转事件、特殊代码迁移；跨源重叠冲突逐证券留下证据，不以 BaoStock QFQ 强行替代 TDX 坐标。
- [ ] 35 条既有停牌、10/08 新识别 15 条停牌需验证为**真实无 BAR**而非漏采；不能生成 0 成交假 K、沿用昨收假 K。

### 2.2 当前和历史补齐来源

- [ ] 复用已通过 SHA/CRC 的 TDX typed ZIP V2；有新来源版本时做 append/revision 判定，18 个异类条目继续原始留证，不得通过删除 ZIP entry 或放宽 A 股校验作弊。
- [ ] 正式日更 BaoStock 日线/因子/证券身份源要实际可调用并留下请求与日期覆盖收据；脚本不得将子流程异常伪装成 `WAIT_PROVIDER`。对下游可用 TDX 的成功数据，不因其他子域未知而撤销可用状态。
- [ ] 修复/版本化适配真实 `GBBQ` 读取位置（已观察为 `T0002/hq_cache/gbbq`，旧代码错误期待 `vipdoc/cw/gbbq`），分类和 CRC/hash 一致；若需要其他附加表，按真实可取源补齐，而非掩盖缺项。
- [ ] 修复正式 lifecycle 和 special-phase source adapter、旧 Builder Registry `INPUT_DIGEST_MISMATCH`：只签发版本化 successor seal；历史旧 seal、旧 9/30 accepted head、旧 source contract 完全保留。
- [ ] 已有 528/528 只代表“指定窗口 corrected 可计算”，必须验四日含跨除权事件/短上市/停牌的真实 MA5/20/60、ATR、前高/前低、涨幅、RPS、RPS 差分、成交量/金额比、周/月等原产品基础字段，分别输出 known/unknown 和确切原因。不存在足够历史窗口可以合法保留 UNKNOWN，但须证明不是代码未运行或旧缓存错误。

### 2.3 Core/Profile、市场、股票和板块的实际重建

- [ ] 将 `TDX_TYPED_RAW_V2`、调整因子/GBBQ、实际主证券集与 TDX 最新成员冻结 S 纳入**新 corrected version** 的四日 owner 实际重建。旧 `corrected_candidate_rebuilt=false` 不许直接改成 true；真正执行后生成新输入 digest、计算 receipt、逐日数量与抽样复算。
- [ ] 股票基础层必须输出全市场每日 Profile 的实际字段族和状态、非候选股票的缺选理由；股票独立 Base Seed/D0/PREWATCH 若经依赖证明和原逻辑一致，允许精确复用并保留数值校验，不因板块回算无意义重跑所有 20,893 行。
- [ ] TDX 行业/概念板块：每个交易日从同一 S 分别算板块收益/价格推进、强弱、宽度、均线、成员扩散、Base Seed 汇总、重叠、行业/概念主线对比和合法 Rotation 候选；**不能只给 83 个 CSRC 行业或全部 UNKNOWN**。若某项真正依赖此前不存在的历史 episode/首次可见性，则运营回算路径可新增明确 `RECONSTRUCTED_EPISODE_V1`，严格 PIT 路径保持不可用，不得 UNKNOWN 强转 FALSE。
- [ ] 个股 `relative_sector_state` 必须基于 TDX 行业与概念的多成员关系、目标股 LOO 排除、自身与板块比较的明确聚合规则；跟原代码版签名一致，按真实多板块语义逐股计算。禁止再复用 `BAO_CSRC` 结果冒充。
- [ ] 之前 `basic_breakout_state` 全部 UNKNOWN 的问题要查清 Owner、历史起点、是否有实际符合的先验 episode；可确证的值真实计算，不能凭没有前态假定没有突破。输出 expected source/actual input/known count/unknown reason。
- [ ] Market 四轴、事件、涨跌幅限制/一字板／实际触板等如原产品需数据，必须按可观测日 K 和真正可用的日内字段分别计算，不准用日 K 猜历史分时触板；欠缺实际日内源则应明确字段级 `NOT_OBSERVABLE_FROM_DAILY`，但不阻塞日 K/板块等已完成子域。
- [ ] 四日 Focus/Forward 仅以真实可见的历史价格、冻结 Anchor、due/exit/reentry 生命周期开展**事后观察重算**，不得把最新成员 S 的事后主线回算宣称当年 T0 交易信号或盈利预测已验证。`PENDING/RIGHT_CENSORED` 是合法结果，不是工程 BUG。

### 2.4 四日一致性对账硬门

逐日必须提交同一张全量 reconciliation 表（不是四个零散日志）：

| 字段 | 9/28 | 9/29 | 9/30 | 10/08 | 统一要求 |
|---|---|---|---|---|---|
| exchange session / T-1/T-3 | 实际 | 实际 | 实际 | 实际 | 无休市错位 |
| canonical 有效股数/RAW 有 BAR 数 | 实算 | 实算 | 实算 | 实算 | 每个 security-date 有具体状态 |
| TDX typed RAW/bars SHA、BaoStock 请求 | 实算 | 实算 | 实算 | 实算 | 已采源与未达源分开 |
| no-BAR 停牌/缺源/身份未知 | 实算 | 实算 | 实算 | 实算 | 不把停牌算漏 |
| QFQ/GBBQ/MA20/ATR20 & T-1 | 实算 | 实算 | 实算 | 实算 | 真实窗口、跨事件复算 |
| TDX 最新成员 S / industry / concept / 关系条数 | 同一 S | 同一 S | 同一 S | 同一 S | 不准 CSRC 替代 |
| 板块 Native/LOO/宽度/Rotation known vs unknown | 实算 | 实算 | 实算 | 实算 | 非真实缺项不得全 UNKNOWN |
| 股票 Core/Profile/结构/Seed/预警 known vs unknown | 实算 | 实算 | 实算 | 实算 | 字段级原因及原理一致 |
| accepted operational head / API context | 日期 | 日期 | 日期 | 日期 | 最终 cutover 支持 10/08，四日可查询 |

## 3. 版本迁移与正式研究运营准入：不得再因旧全九项 PIT 合同死锁

### 3.1 用户授权的范围与旧合同迁移

用户明确授权对四日**以最新 TDX 成员事后统一回算的研究结果**进入一个标识清晰、来源可追溯的新运营研究版本。应新增例如：

- `V4_DATED_OPERATIONAL_RECONSTRUCTED_OWNER_V1`：可接受真实 TDX RAW、corrected Core/Profile 和 `TDX_LATEST_MEMBER_RETRO_V1` 所产研究面；字段标注 `PROXY/RECONSTRUCTED`；
- `V4_STRICT_HISTORICAL_PIT_V1`：维持原 strict PIT 与 first-available 门，不因用户新授权改变其历史含义；
- `V4_CURRENT_ACCEPTED_READ_V2`：将“当前运营数据能否正常展示”与“历史 T0 是否严格当时可见”拆成两种可查询能力。

这是**新版本合同迁移**，不是对旧 `production_permission=false` 或 `AS_RECORDED=false` 的伪造性覆写。新运行规则需清楚界定可发布的域、保留 `historical_PIT_permission=false`、各个生产模块读哪个版本、对旧 accepted 的安全回退；新开发版本须独立审计，不得用本任务卡直接跳过 QA。

### 3.2 真正发布的先决条件

- 已归档真实完整的四日 source、security identity、复权与 latest-member S；每个子域输出 hash lineage、计算参数与 `source/field_quality`；
- 独立复算不少于 30 个真实多样性样本（至少除权/停牌/上市短窗/不同市场、TDX 多概念、CSRC 冲突、T-1/T-3）；差异容忍须有事先定义的可重复数值精度；所有失败用明细逐行修复；
- 验证同一版 S 的四日板块差分不被真实历史 9/30 frozen snapshot 偷换，且 9/30 旧 accepted 内容和 digest 未变；
- 消费者 namespace 和类型拒绝测试：`BAO_CSRC:` 注入 TDX 主链必须 FAIL；`RECONSTRUCTED_LATEST_MEMBERSHIP` 注入 strict PIT 必须 FAIL；缺合法 TDX 最新成员源不得发布假的代理集合；
- CAS 并发、重复发布、半途故障、坏源、错误 predecessor、回滚都在真实新 successor staging 实测通过；正式 head 切换原子化，并且在旧 9/30 last-good 基线可安全回滚；
- 现行 authority 无法直接发布时，先完成**可执行的独立外审与新发布合同审查**，根据可证明范围签发明确新版本准入，再执行生产切换；**不得把外审缺席解释为永久停止代码修复**。

### 3.3 正式在线 readback

- `/api/v4/context` 必须显示新的 `accepted_trade_date=2026-10-08`、source/snapshot/cutoff/permission、field lineage；最新交易日是 10/08，不能用 10/09 盘中成交凑数。
- 股票、板块、市场、今日变化、Focus/Forward、诊断与可用历史对比，在**同一 context token / same publication ID** 下读到对应的 10/08 版本。缺独立正式源的子域显示真原因，**不能全部模块 UNKNOWN 或全空**；与其历史已接受域不同源版本时必须在字段旁显示明确适用口径。
- 页面至少要展示“板块成员口径：通达信最新成员回算（快照 S，采集 10/09），非历史当日成员”，并允许显式查看 9/30 原已接受快照口径，不能把两者混合为一个历史时间线；不能用新的代理回算数据去回填先前冻结策略表现。
- 保留 9/30 last-good 回滚测试，生产读数真正切成 10/08 之前不得写“CUTOVER_PASS”。

## 4. 验收等级：严禁混淆“完整基础数据修复”与“严格历史 PIT”

以下三层必须在交付页上独立给结论：

1. **`FOUR_SESSION_SOURCE_AND_NUMERIC_PASS`**：四天证券日期、RAW、停牌、来源、GBBQ/QFQ、核心数值真实复算可接受；不代表板块或生产已上线。
2. **`FOUR_SESSION_OPERATIONAL_RECONSTRUCTED_PASS`**：同一通达信最新成员快照 S 已完成四天行业/概念及个股相对板块、Native/Rotation 的实际合法事后回算，Core/Profile/Stock/市场各已支持子域全部有按契约可复核结果，欠缺真实性无法计算的字段仅保留有证据的局部 UNKNOWN；全部消费字段保留 `RECONSTRUCTED` 标志，绝不宣称 strict PIT。**不能把“写了方案/有 JSON 文件”判通过**。
3. **`FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS`**：上一层经独立外审，正式 successor 获批准入并 CAS 上线，API/UI 以 10/08 为最新数据、四日历史可查、last-good 可回滚；此项为进入剩余前端任务的**唯一放行门**。

> `STRICT_HISTORICAL_PIT_NOT_GRANTED` 应与以上第一/第二层结果**并存**，不能被错误当作“运营研究事后回算未通过”，更不能将 proxy 回算宣传成真实历史首见事实。若原产品还要求全部北交所身份或某特定源字段，只有补齐/明确合法的作用范围和消费者降级后才可能签 FULL；不得悄悄缩减产品范围。

**阶段最终状态唯一取值**：
- `FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS`：独立外审和真实生产切换完成，准许进入下一阶段页面验收缺陷修复。
- `EXTERNAL_ACCEPTANCE_BLOCKED`：若原始数据、关键身份、真实 TDX 最新成员、数值验证、发布合同或生产读数任何硬门不满足，则继续修复，不允许把“候选 PASS”当生产 PASS；剩余前端问题暂不启动。

## 5. 工作包与执行顺序（允许不依赖链路并行，不能纸面停工）

| 包 | 优先级 | 交付动作 | 独立验收 |
|---|---|---|---|
| W0 | P0 | 对 Drive/HEAD/AGENTS/所有冻结 source 的指针/任务差异生成 entry ledger | ENTRY_HASH_BASELINE_PASS |
| W1 | P0 | 真正采集/解析并冻结最新 TDX 行业+概念**完整成员 S**，和 9/30 旧快照比对 | TDX_LATEST_SNAPSHOT_SOURCE_PASS |
| W2 | P0 | 复用 typed RAW 及 BaoStock，修复 GBBQ/lifecycle/registry successor、北交所身份范围 | FOUR_DAY_SOURCE_CAPABILITY_PASS |
| W3 | P0 | 四天 Core/Profile + 价格/复权/交易日窗口真实构建/独立复核 | FOUR_DAY_CORE_NUMERIC_PASS |
| W4 | P0 | 四天共享 S 的行业+概念、LOO、Native、Seed aggregate、B0/Rotation、个股 relative sector 真回放 | FOUR_DAY_RETRO_SECTOR_PASS |
| W5 | P0 | 股票七结构/主线消费、市场、Focus/Forward 的**合法范围**接入、依赖审计与未知修复 | ALGORITHM_FIELD_LOCAL_PASS |
| W6 | P0 | 新 operational corrected publication policy、scoped Owner/head、隔离与 CAS 全负例、API 同版验读 | SCOPED_PRODUCTION_SUCCESSOR_READY |
| W7 | P0 | 独立外部审计、按问题修复、正式发布与四天 readback | **FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS** |
| W8 | 后续 | 仅 W7 PASS 后，读取已归档前端 00 总调度 + FP-01～FP-14，并从当前实际状态继续缺陷验收和页面开发 | PAGE_REPAIR_CAN_START |

遇到某一子域真实无法证明，立刻记录具体输入/接口/证券/字段，并继续所有无依赖工作；不允许因 `STRICT_PIT_NOT_GRANTED`、某一 `UNKNOWN`、20 天实际 Forward 尚未成熟而停止 W1～W6。W7 的真实发布门不能被忽略。

## 6. 测试与反例（最低必测，不限于此）

1. 四个目标日期和 T-1/T-3 全通过，9/25 与 10/01～10/07 无假 BAR，10/09 盘中不会生成完整日 K。
2. 冻结一次 TDX S，四天唯一成员 digest；S 的行业+概念、多成员、交叠、编号及名称正确；当日未上市证券从日级 eligible population 排除。
3. 9/30 原 accepted 378/50162 digest 完全保持；9/30 的 retro 新版与原版差异真实输出，不借原版 PIT 身份给新版背书。
4. 故意注入 `BAO_CSRC` 到 TDX 主链、latest-membership 到 strict PIT、错误 source SHA/日期、未识别证券码，必须拒绝。
5. 对四日同版 S 分别执行完整 sector strength/RS/width/LOO/rotation，并与独立算法 oracle 比较；从 S 移动一个测试证券成员，只重算受影响行业/概念及其下游，其他领域 digest 不变。
6. 三日旧 528/35 + 10/08 停牌保留，除权/配股/短历史窗口的当前/T-1 MA20/ATR20 独立样本，缺真实分钟线就不给日内触板事实。
7. TDX 官方增量含原 18 项异类记录仍能完成 A 股 RAW，真正目标股票坏日期/坏 OHLC/复权源冲突仍 fail-closed，不能静默跳过。
8. 证券身份变更、北交所分类/历史别名、跨行情源重叠与确切差异明细；不能只用正则推定证券存在。
9. 日常入口实际调用源端并重用已封存源；`no newly fetched source` 与 `requested but failed`、`already frozen`、`NOT_NEW_SESSION` 必须分别报告。
10. 旧 Builder Digest 不被重写，新版 Registry hash 绑定真实新代码/输入，GBBQ/lifecycle/special-phase 的 corrected 兼容链可重放。
11. 模拟 API “全部 UNKNOWN”回归：具备 RAW、Core、最新成员 S 的正式域应显示有意义值，真正缺的数据逐字段可查原因；不能全站回退空卡。
12. 两次重跑相同 source/parameter 的 digest 一致；另一版 S 必须新 publication；CAS stale、丢源、crash、原子回滚、旧 9/30 读数恢复实测。
13. 独立外部审计须检查实际 Git LFS 源对象与大文件的字节/哈希或真实可执行的封存读取，不能只拿 LFS pointer、开发者自评 PASS 当作独立数值验收。

## 7. 必交 MD/JSON/CSV 证据和 Git/Drive 同步门

证据统一归档到新目录 `docs/evidence/r4_3_four_session_closeout_20261009/`，不得修改 R4.1/R4.2.1 旧证据；如果 Codex 因实际运行日期变化，新目录内部记录真实 execution timestamp 而不覆盖冻结日期：

1. `00_ENTRY_DRIVE_HEAD_AND_PROTECTED_DIGESTS.json`
2. `01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json` + 真正快照 raw files 的 hash/bytes
3. `02_TDX_MEMBER_SNAPSHOT_S_AND_0930_PIT_DIFF.jsonl.gz`
4. `03_FOUR_SESSION_UNIVERSE_BAR_SUSPENSION_BJ_RECONCILIATION.csv`
5. `04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json`
6. `05_FOUR_SESSION_RAW_QFQ_CORE_PROFILE_NUMERIC_ORACLE.json`
7. `06_FOUR_SESSION_RETRO_TDX_SECTOR_NATIVE_ROTATION_LOO.json`
8. `07_FIELD_LINEAGE_AND_UNKNOWN_REASONS_BY_DATE.csv`
9. `08_CANONICAL_IDENTITY_AND_CORRECTED_OWNER_ADMISSION.json`
10. `09_NEW_OPERATIONAL_PUBLICATION_POLICY_AND_OLD_PIT_MIGRATION.md`
11. `10_SUCCESSOR_ATOMIC_CAS_BAD_SOURCE_ROLLBACK_QA.json`
12. `11_FOUR_SESSION_LIVE_API_SAME_CONTEXT_AND_UI_READBACK.json`
13. `12_INDEPENDENT_EXTERNAL_REVIEW_AND_FIX_REGISTER.md`
14. `13_ALL_TEST_COMMANDS_SHA_AND_SCOPE.json`
15. `R4_3_EXTERNAL_AUDIT_HANDOFF.md`：按 W0～W8 单项 `PASS/FAIL/NOT_VERIFIABLE`、实测数量、证据哈希、已知残余、正式数据头、修复完成和**下一阶段页面工作是否获准**。

要求：独立 QA 不以测试条数冒充真实样本；有疑义继续修复，不止写报告。真实源码+测试+数据/证据必须 push 并核对远端 HEAD。**正式产物和最后版本任务卡/验收结论自动归档 Google Drive**；若用户个人 Windows Codex 环境不具有 Drive 写入能力则明确同步失败与可替代的可下载 MD，不伪称已归档。

## 8. Codex 直接执行指令（可整段粘贴）

> 读取本任务卡全文和仓库 `AGENTS.md`，以 `codex/v4-fp14-r2-repair` 当前最新 HEAD 为基线完成 **R4.3 四日数据全闭环**。本轮用户已明确授权：通达信如不存在 2026-09-28、09-29、10-08 历史行业/概念成员快照，**冻结一份最新 TDX 行业+概念成员集合 S，四日统一使用 S 回算**，保留 `RECONSTRUCTED_LATEST_MEMBERSHIP/AS_RECORDED=false/PIT_ELIGIBLE=false`，不得用证监会 83 个行业顶替，不得将事后回算冒充历史 T0 可见。旧 9/30 已接受 378/50162 必须原样冻结，并生成单独 9/30 最新 S 回算视图以保持四日横向可比。W1 必须真实采集和冻结行业+概念（不是只写 policy）；W2-W5 连续把四日 RAW/复权/身份/GBBQ/lifecycle/Core/Profile/板块 Native/LOO/轮动/合法下游算出并数值验收；W6 新建**正式研究运营而非 strict PIT** 的版本化发布合同及 successor；W7 独立外审、修复后合法 CAS 生产切换，10/08 同一 context token 的 API/前端实际可见、9/30 可回滚才叫全链 PASS。旧 528/35 成果不重复浪费；局部真实 UNKNOWN 不允许扩大为全站 UNKNOWN，历史严格 PIT 门也不得被用户新授权强行追认。若某硬门尚未过，继续修其工程实现并如实阻断正式发布，不能只提交 `BLOCKED` 报告就停止。**全部四天数据经外部正式验收并实际上线后，才启动原 Drive 前端 00 总卡及 FP-01～FP-14 的剩余页面审计缺陷修复。**四日截止 10/08，10/09 未完成交易日 K 线不入本轮。全部完成后推送源码/真实证据/结果及唯一验收状态。

## 9. 版本迁移记录

- **R4.2.1 → R4.3 原因**：用户指出历史 TDX 成员快照自然可能缺失，不希望三天的成员有效日证据无限阻塞四日数据修复与实际生产使用，明确授权最新 TDX 成员关系统一回算。
- **新增**：`TDX_LATEST_MEMBER_RETRO_V1`、单一 S 复用、事后成员口径的独立产品展示和正确版本化 operational publication；同一 S 四日计算，结束后再进入前端问题修复。
- **保留**：旧 strict PIT 主张、9/30 frozen accepted、旧 528/35、typed RAW V2、CSRC 与 TDX 隔离、源哈希/独立数值 oracle、CAS 可回滚、北交所身份证据约束、项目安全边界。
- **禁止回溯污染**：新成员代理不可声称 T0 当日有效、不可覆盖用户先前冻结判断、不可作为真实历史绩效/概率证明。运营回算的 `PASS` 不改写严格历史 PIT `NOT_GRANTED`。

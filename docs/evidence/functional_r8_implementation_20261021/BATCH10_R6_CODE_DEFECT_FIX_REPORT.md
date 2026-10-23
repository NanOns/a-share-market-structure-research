# BATCH10-R6 源码缺陷修复报告

日期：2026-10-23（Asia/Shanghai）
分支：`codex/v4-unified-development`
复核基线：`3878768c592d657e0a84ace24fee944ea753eb0a`
源码提交：`f34d89385`（`修复 R6 十项源码缺陷`）
阶段合同：`docs/plans/V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md`（S01–S07）；R6 任务卡为 Google Drive `V4_R5_独立代码复核与R6纯功能实修任务_R2_20261023.md`。

## 结果摘要

- 已提交源码、测试和历史范围合同；针对性回归 **128 项通过**。Python AST、两份前端 JS 语法和 `git diff --check` 均通过。
- R8/D0、ReadIndex R2、R8 发布状态机及已验证的 Lifecycle 行情边界未重复施工。旧 `/api/v4/priority` 已在源码路由到同一 dated PG Priority Owner；Focus Priority 与新 D2 失效判定因无业务裁定/生产合同而局部阻断。
- R6 市场趋势不再恒定拒绝权限链，也不再截断到固定日期；真实 10/21 候选源重算在首个缺失的 10/19 涨跌停 Owner 处按源不足关闭。合成 R8/PG 正负例通过，**真实 PG 趋势正例仍未取得**。
- 10/20 原始 Core/adjusted Owners 中，5,217 条调整价记录与 Core 的旧坐标族及同一 64 位修订 SHA 精确配对；修复后适配器识别该配对。**没有按新源码重建 Priority PG Owner**，所以不能把 5,217 条映射修复写成 5,217 条已新增可排序。
- 10/22 BaoStock 限额重试取得 5,225 行日线和 38 行复权因子，形成 G 盘候选快照；来源合同仍标明原始 OHLC 权限为 `TDX_ONLY`，适配器状态为等待外审，未写规范 SourceIngress、Owner 或 PG。
- 现运行 28766 未重启，仍载入修复前代码。28766 API/PG 读回和三并发耗时仅作基线证据；修复后的浏览器 UI 与新 Priority PG 数值尚未验收。

## BUG-01 至 BUG-10

| 缺陷 | 修复与前态 | 实际证据、变化及未闭环 |
|---|---|---|
| BUG-01 日期默认值 | `corrected_owner_pipeline.py` 默认值改为 `None`，在读取文件前要求显式 `target_date`；仍按版本化 `target_sessions` 与官方日历双重校验。 | 省略 T0 抛 `CORRECTED_TARGET_DATE_REQUIRED`；合同内历史 T0 仍可进入 `core` 阶段；合同外日期抛 `CORRECTED_SESSION_OUTSIDE_VERSIONED_CONTRACT`。**CODE_PASS**。历史 DM01 日期集合未扩展。 |
| BUG-02 趋势权限恒 False、固定日期 | `r6_candidate_market_stress.py` 现在核对 Head/Owner、R8 收据、交易文件、市场参考路径字节、官方交易日、25 日同序列/坐标、PG 发布行和最新 `FINALIZED` 事件；截止时间与三日压力窗均由发布交易日驱动。 | 正向合成全链和 `ABORTED` 负例均通过。用真实 10/21 候选运行修复后的函数，返回 `SOURCE_INCOMPLETE / R7_MARKET_STRESS_LIMIT_OWNER_NOT_UNIQUE_OR_SOURCE_MISMATCH:2026-10-19`；当前不能提供 10/21 真实趋势/PG 正例。**CODE_PASS；REAL_SOURCE_WAIT；PG_WAIT**。 |
| BUG-03 D2 固定截止 | 新增 `R7_FROZEN_INVALIDATION_SCOPE_R1`：保留 R2 至 2026-10-14 的历史范围；后续日期没有冻结价位生产合同就返回 `FROZEN_LEVEL_OR_PRODUCER_CONTRACT_NOT_PROVEN`。不推导 MA20 或短期低点。 | 新日期负例通过，历史范围配置可审计。D2 successor 合同未获裁定，局部 **CONTRACT_BLOCKED**。 |
| BUG-04 页面固定 10/14 | `core-product-r1/app.js` 按 `context.context.trade_date` 取压力事实并动态显示日期；文案改为中性“压力窗口分母”，显示趋势质量。 | 新增行未引入固定交易日；`node --check` 通过。由于禁止重启，修复后的运行 UI 未加载，**UI_WAIT_RUNTIME_RELOAD**。 |
| BUG-05 研究页固定 10/12/“已接受” | `research/app.js` 改为当前选择日期与 `RECONSTRUCTED_NON_PIT`、“非已接受”。该 `/v4/research/` 入口在 R5 的 28766 页面读回中可达，因此按现役页面修复。 | JS 语法通过；修复后页面需用户手动启动服务再验，**CODE_PASS / UI_WAIT_RUNTIME_RELOAD**。 |
| BUG-06 Owner 与消费者/Focus 排序 | `/api/v4/priority` 归一到 `/api/v4/radar/priority`，使用相同 dated PG Owner。Focus Priority API 和页面明确 `CONTRACT_BLOCKED`，提供两种未选方案及影响，不生成排名。 | 本轮 28766 旧进程复现 `/api/v4/priority` HTTP 400 `UNKNOWN_PARAMETER`；正式 `/radar/priority` 读到 R5 PG Owner。Focus 旧进程仍回 `NO_OPERATIONAL_FOCUS_SUBPAGE_OWNER`。源码路由及 Focus 阻断测试通过；新路由未在禁止重启的进程中上线。Focus 方案 A/B 见下文。 |
| BUG-07 10/20 个股 Priority | `core_product_bff_r1.py` 精确适配两个已知 QFQ 坐标族，仅当 adjusted 修订 SHA 与 Core `price_basis_id` 后缀相同时才输出 exact coordinate。 | 原 PG Owner 为 0/5,224、`INVALID_INPUT=5,217`、`MISSING_INPUT=7`。源行审计：10/20 Core 5,226 行、adjusted 5,217 行、5,217 个同修订精确配对；10/21 Core 5,224 行、adjusted 5,216 行、5,216 个 v0.3 精确配对。**源码坐标修复已实测；PG 重算/新 rank 和原因对账未完成，PG_WAIT**。 |
| BUG-08 10/20、10/21 板块 Priority | Lifecycle PG 投影现在保留 `input_digest`、`source_bindings`，并将 `parameter_digest` 映射成消费者合同要求的 `parameter_sha256`；不放宽 maturity/health 规则。 | 10/21 候选 API 重建显示 Lifecycle maturity/health 已知 14/9，板块候选可排序 8/400；同 Token 正式 Priority PG Owner 仍是 0/400。`sector_lifecycle_authority` 不含该 Token，实际 sector detail `INDUSTRY:T0101` 的两个字段仍为 `UNKNOWN / SECTOR_LIFECYCLE_PG_OWNER_UNAVAILABLE`。因此是实际 Owner 来源缺失，不把候选重建当 PG 发布；受影响板块功能局部 **SOURCE_INCOMPLETE / PG_WAIT**。 |
| BUG-09 10/22 来源 | BaoStock 0.9.3 因子头字段适配只允许源代码 SHA 固定的 adapter v2，将 `adjustFacto` 规范为 `adjustFactor`；快照绑定 raw/normalized 行摘要及 adapter 摘要。 | R5 已扫描的配置路径 `D:/new_tdx/vipdoc/{sh,sz}/lday` 有 11,884 个 `.day` 文件，最新末条记录为 10/08，未见 SourceIngress；本轮没有证据确认另一 TDX 安装根。首轮 4 次请求失败后，获准的一次重试使用 6 次；累计 10/10。Smoke `PASS`：日线 5,225 行、因子 38 行；snapshot `sha256-3cc3d9a8…bd53b020`，观测时间 `2026-10-23T13:51:13.221422+08:00`。抓取字段含 OHLC、量额、换手率等，但没有显式自由流通股数；请求预算已满，不再调用来源。快照只在 `G:/codex_tmp`。原始 OHLC 权限仍 `TDX_ONLY`、因子 adapter 等待外审，故规范 10/22 Owner/PG 为 **SOURCE_WAIT**；未回填 10/21。 |
| BUG-10 实现断裂与复核 | 与 BUG-02/03/04 同批处理日期、权限和消费代码；R8/D0 发布和 ReadIndex/Lifecycle 已验证部分保持原样；R8 原行不改写。 | 趋势权限、错误终态、历史范围、固定日期窗口和字段适配共 128 项定向回归通过。没有重发旧 R8/D0，也没有改写 PENDING 行或伪造 FINALIZED。**CODE_PASS；完整业务闭环仍受真实来源/PG Owner 限制**。 |

## 三个实际病例

1. **个股 exact coordinate：**10/20 `SEC-00096141BD5420F5CB3120E687CDA5B9` 的 Core 为 `TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE:a14e…bc038`；adjusted 为同一坐标族、修订 `a14e…bc038`，新映射判为匹配。价格值不在此处重算或补造。
2. **真实排序排除：**10/21 候选重建的 `SEC-000A3F9053A2AA6112AAF248CBBD5912` 仍因 `RELATIVE_STRENGTH_NOT_IMPROVING` 与 `FIVE_SESSION_RETURN_NOT_POSITIVE` 不可排序；这些是规则排除，不应被坐标修复抹掉。
3. **Lifecycle 缺源：**10/21 `INDUSTRY:T0101` 的 sector 来源 SHA 为 `af1b64a4…50c6455`；maturity/health 返回 `SOURCE_INCOMPLETE`，原因 `SECTOR_LIFECYCLE_PG_OWNER_UNAVAILABLE`。候选生命周期统计 14/9 不能替代缺失的 exact-token PG Owner。

## PG、API、页面与性能证据

- R5 的 PG 真实读回证据复用自 `BATCH10_R5_OWNER_PUBLICATION_AND_DAILY_INCREMENT_EVIDENCE.json`。10/20 与 10/21 R8、D0、ReadIndex R2 的 Token 和读回保持不变；10/20 D0 为 TRUE=141/FALSE=5,033/UNKNOWN=52。10/21 Launch 为 TRUE=78/FALSE=5,098/UNKNOWN=48，Recovery 为 TRUE=28/FALSE=5,147/UNKNOWN=49，两个场景分开保留。Priority Owner 分别为 10/20 digest `0bf91603…d157e0`、10/21 digest `762b37bf…f8628ec`。不得把历史 PG PASS 当本轮新代码重算通过。
- 28766 当前服务于 Token `14ee0cf8…0067ad378`。正式 PG Priority API 为个股 936/5,224、板块 0/400；同 Token 候选重建为个股 936/5,224、板块 8/400，二者不是同一个发布状态。六入口只读 GET 均为 HTTP 200：Home READY、Sector 400 行、Stock 5,224 行、候选 Priority READY、Focus 3,975 行、Forward `SOURCE_INCOMPLETE / NO_AUTHORIZED_COHORT_OWNER`。旧 `/api/v4/priority` 为 HTTP 400 `UNKNOWN_PARAMETER`。
- 3 个并发候选 Priority GET 的耗时为 277.077、373.519、374.525 ms；nearest-rank P95=374.525 ms，小于 3 秒。该测量来自**修复前、已热缓存的现运行服务**；分阶段读数包括 ReadIndex 0.040 ms、Lifecycle 31.685 ms、来源 SHA 校验 62.356 ms、排名计算 0 ms（缓存命中）、市场压力 0.017 ms、摘要/分页 15.343 ms。它仅为暖缓存 API 基线，不代表新源码部署或完整日增量性能验收；10/22 无规范来源，因此 `source_wait/ingress/core/profile/sector/market/D0/D2/focus/forward/period/PG` 完整流水线计时为 `REAL_INCREMENT_WAIT`。
- 最后监听核对：28766 PID 52916；PostgreSQL 5432 PID 8640；28765 未监听。没有重启服务、Windows、数据库或生产服务，也未进行生产切换。当前进程无法动态载入本次源码，须由用户手动启动后复验 API/UI。

## 合同阻断与验收结论

Focus Priority 尚无已裁定排序算法，本轮只阻断该子功能：

- **方案 A `FOCUS_PRIORITY_D0_STATE_BUCKETS_R1`**：按已发布 D0 confirmation status 分组，组内按 `entity_id` 稳定排序。影响：显式优先确认状态；TRUE/FALSE/UNKNOWN 分组边界需业务裁定，不引入新权重。
- **方案 B `FOCUS_PRIORITY_EVIDENCE_RECENCY_R1`**：按 Focus Owner 最新可验证事件日期倒序，再按已知证据字段数、`entity_id` 排序。影响：优先近期且证据较完整的对象；不表达 D0 确认强弱，依赖事件日期与完整性口径。

R7 frozen invalidation 的 successor 冻结价位/生成合同也未得到证明，按 `UNKNOWN` 保持局部阻断。Forward 首次正式冻结样本仍为 `WAIT_FIRST_CAPTURE`。

Phase 0 汇总门禁在仓库中未找到，本轮登记 `BLOCKED`；只对本轮变更执行静态通用性审计，未启动业务扫描器。新增/修改生产代码与页面中没有固定日期、证券代码或板块代码字面量；仅新版本化历史 scope 配置保留 `through_trade_date=2026-10-14`。测试中的固定日期和合成身份 `sh.999999` 限于测试夹具。详细机器证据见同目录 `BATCH10_R6_CODE_DEFECT_FIX_EVIDENCE.json`。

本轮结论：**CODE_PASS（针对性范围）；R5 既有 PG_PASS 保留；10/22 补充 REAL_SOURCE_PASS 但规范 SourceIngress 为 SOURCE_WAIT；Focus/D2 为 CONTRACT_BLOCKED；新代码 PG/UI/完整流水线验收待用户手动重启后继续。**

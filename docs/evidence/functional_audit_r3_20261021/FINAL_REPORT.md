# V4 截至 2026-10-14 真实功能独立审计与定点验证（R3）

**日期：** 2026-10-21
**基线：** `codex/v4-unified-development`，起始 HEAD `87cf679fb661733f403feb6b64e334fd939b8970`（起始时与 origin 一致）
**范围：** 仅 2026-10-12、13、14 三个既有候选日；本任务不采集或计算 10-15 及以后行情，也不重放已成功的三日候选链。
**发布状态：** 本报告是独立审计与定向修复记录；不构成生产验收、正式 Head 更新、下一阶段许可或交易建议。

## 阶段合同与前置证据

- 阶段 0 前置状态为 `DEGRADED_PASS`，证据：`docs/V4_PHASE0_FINAL_ACCEPTANCE_R3_1_20260925.md`。本轮没有运行扫描器。
- 进入本轮前查阅最新适用升级文件：`docs/evidence/functional_audit_r2_20261020/FINAL_REPORT.md`。该报告确认基线 HEAD、origin、成功候选链、候选 API 约束以及本轮尚待核验的功能点。
- 三日候选链沿用 R2 已生成的不可变证据，不重新计算：10-14 候选 token 为 `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`。API 上下文显示 5,225 股票、400 板块、3,247 Focus 观察；正式 Head 为 10-09，10-14 为候选预览，`production_accepted=false`、`PIT_ELIGIBLE=false`，成员按 10-09 最新 TDX 快照回算并带有存续偏差风险。
- 原始运行进程：28766 为既有本地开发服务，PG 为 `127.0.0.1:5432/market_research`。本轮未停止或重启服务、未写入数据库。28765 未作为验证服务使用。服务进程在本次 Python 修改前已启动，因此其已导入的后端模块不能作为修复后端的运行时验收；本次 28766 页面验收证明的是当时页面与既有只读数据，后端缓存行为由定向测试证明。

## 定向修复及验收

| 检查项 | 修复 / 证据 | 结果 |
|---|---|---|
| 图表缓存路径 | `core_product_bff_r1.py` 先用 token、交易日、证券、复权口径和 history-index 版本形成缓存键；命中时直接复用已冻结 bars / bindings，跳过 PG history rows 与逐日 RAW Owner 读取。history-index 版本改变会换缓存键。 | 定向单测通过；28766 既有 Python 进程未重载，未把其热缓存响应冒充修复后的运行时测量。 |
| 缺失数据绘制 | `components.js` 保留窗口内所有交易日横坐标；只画 OHLC 完整且 `quality=KNOWN` 的 K 线，UNKNOWN 数据显示有日期与原因的虚线标记；MA 按连续有效区间分段，不跨缺口连接。 | UI 单测覆盖首部、内部、尾部缺口，缺口保留位置及 MA 分段，通过。真实页面组件可见“数据缺口保留交易日位置”说明。 |
| 页面模块解析 | 修正 `static/research/labels.js` 末尾残留的字面量 `\\n`，该内容使脚本无法解析。 | `node --check` 通过；页面正常加载。 |

### 定向测试

- `pytest -q tests/test_v4_candidate_daily_chart.py`：3 passed。覆盖冷 / 热 RAW、QFQ 结果一致性、热缓存不再触发逐日 Owner 与 PG history-row 读取、history-index 版本变更后失效重读。
- `node --test tests/test_core_product_ui_r1.mjs`：8 passed。覆盖 K 线缺失数据位置与 MA 分段。
- `node --check src/workbench_service/static/core-product-r1/components.js`、`node --check src/workbench_service/static/research/labels.js`、`git diff --check`：通过。

## 业务功能独立核验矩阵

| 功能 | 证据和观察 | 判定 |
|---|---|---|
| 板块轮动 | 10-14 上下文列 400 个板块；轮动域为 `VALIDATION_ONGOING`。R2 的 10-14 汇总：轮动态 `NONE=216`、`UNKNOWN=134`、`ROTATION_FAILED=45`、`ROTATION_PULSE=4`、`ROTATION_IN=1`；质量为代理重建 266、未知 134，另有 123 条 `REQUIRED_QUALITY_UNAVAILABLE`。首页净变化 191、持续记录 330、轮动变化 46。页面“煤炭 INDUSTRY:T0101”显示 32/32 成员有行情，RS5 90.476、RS20 80.952、宽度 0.625；均注明为代理重建研究值。 | 有当期事实和迁移线索；正式轮动态仍受来源质量与独立验证门禁限制。轮动变化不能解释成正式可交易信号。 |
| Priority | 当前接口对股票及板块 scope 均返回 `RESEARCH_PRIORITY_BINDING_MISSING`；首页只有 177 条部分事件，范围 `ACCEPTED_FOCUS_CHANGE_EVENTS_WITHOUT_TOP_ROTATION_COVERAGE`，原因 `FORMAL_RADAR_PRIORITY_NOT_PUBLISHED`。authority 中存在旧候选 token `914092…` 的 10/12–14 Priority Owner，但不含当前 R3 token `2e3a…`。旧 token 的 10/14 Owner 有股票 967 条可排序、板块 0 条可排序。28766 页面呈现无效参数错误，是当前 token 下接口缺绑定后的页面结果。 | **当前候选绑定缺失；不是全项目从未实现。** 旧 Owner 不能跨 token 复用；当前 token 没有 Owner，股票列表不可读。旧 Owner 的板块 0 可排序仍需单独做逐字段不可排序原因审计。 |
| D0 / D2 | 只读检查 10-14 `corrected_d2.json.gz`（5,225 行）：D0 CONFIRMED `TRUE=145`、`UNKNOWN=5,080`；PREWATCH `TRUE=397`、`FALSE=4,790`、`UNKNOWN=38`；D2 `FRESH=65`、`STALE=5,160`，最终资格同为 65 TRUE / 5,160 UNKNOWN。5,160 条 stale 均记录 `REQUIRED_FACTS_UNKNOWN_PRESERVE`，且均有必需字段 `frozen_invalidation` 为 `UNKNOWN / NOT_IMPLEMENTED`（producer `V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED`）；其中 5,080 条另有 `CONFIRMED=UNKNOWN`（producer 标为 IMPLEMENTED，但当行没有确定值）。PREWATCH、SEED、core-price-damage、suspended 的少量 UNKNOWN 与上述集合重叠，不能将计数相加。`dq5`、`episode_invalidation_contract_id`、`followup_complete` 在相关合同中为可选 / 未实现输入，不是单独把全部样本打为 stale 的充分原因。输出 cutoff / `system_available_at` 为 2026-10-20，晚于 T0，不能证明当日首次可得。 | **Reducer 的 fail-closed 是合同行为；上游必需输入未实现 / 不确定是数据能力缺口。** Stale 本身不证明 reducer 设计错误，但 D2 不可作为完整、可 PIT 追溯的正式结果。 |
| 历史复权与 K 线 | 28766 真实页面选择 10-14、日线、QFQ、最近 60 根，显示 60/422，末根 10-14 收盘 12.55；详情同时展示 MA5 13.336、MA20 13.124、MA60 13.876。日线页有“逐日 RAW Owner、T0 冻结 TDX GBBQ、精确有理数坐标”说明，并注明非正式发布 / 非严格 PIT。图表 API 既有冷 / 热响应测量来自修复前运行进程缓存，故不作为修复后的性能指标。 | **有限通过。** 证明了指定样本的 QFQ 页面与截止日期；本轮没有独立找到并核对股息除权、停牌缺口、IPO 边界的全套分层样本，也没有运行中的修复后端冷缓存基准。 |
| 行业 / 概念关系 | 10-14 stock detail API 的三一重能（`SH.688349`）`primary_industry=INDUSTRY:T0706`，来源为唯一映射行业叶节点；页面能从主行业跳至对应板块。煤炭样本源成员 32、映射 32、未映射 0、有行情 32。另查 5G 概念 `THEME:880506`：源成员 454、映射 442、未映射 12、有行情 440；返回成员样例中，三安光电 `SH.600703` 的唯一行业为 `INDUSTRY:T1203`，其余 4 个样例也均有唯一行业映射。 | **分层样本关系通过。** 样本直接验证行业叶节点与概念板块成员边；仍有 12 个未映射成员，且当前成员重建不等于历史 PIT 关系，不能由样本外推全量完整。 |
| Focus | 只读页面显示独立关注清单共 3,247 条，明确标记“重建关注轨迹”“非正式前瞻验证样本”“不代表持仓”，并关闭新增 / 自动写入。本页 30 条观察中，3 条真实状态变化、27 条来源不足观察；Focus 详情数据将来源不足与业务变化分开。 | **读域部分通过。** 该池不应被当成个人 watchlist、真实持仓或前瞻胜率样本。 |
| 市场风险 | 10-14 市场候选四轴：趋势 `WEAK`、宽度 `DETERIORATING`、参与度 `THIN`、压力 `UNKNOWN`（stress level 缺失、daily limit coverage 59/5,225≈1.13%）；合成环境 `UNKNOWN`，原因 `REQUIRED_MARKET_AXIS_UNKNOWN`。当前候选根没有 `data/v4/operational_risk_authority_r1.json`，因此完整风险 Owner 无 token/date 绑定。个股结构风险仍可由候选事实计算：5,203/5,225 可比较（`NONE=5,154`、`DAMAGED=49`、`UNKNOWN=22`；变差 42、改善 30、不可比 2）；板块生态 0/400 可评估；市场压力 0/1 可评估。 | **Owner 物化 / 输入覆盖缺口，不是已证实的算法设计缺陷。** 市场压力缺少足够日涨跌停输入，板块生态风险缺接受的 lifecycle health 输入；详细根因见下文。UNKNOWN 不等于无风险。 |

## 缺陷原因与归属

下列“原因”区分已由只读产物或源码证实的直接原因，与仍未定位到更底层生产原因的部分。现有证据不支持把这些项目笼统定性为设计缺陷。

| 当前表现 | 已证实的直接原因 | 缺陷类型 / 边界 |
|---|---|---|
| 图表热缓存命中仍有重复读取 | 基线 `CORE_PRODUCT_BFF_R1._candidate_daily_owner_chart` 先读 history-index 的 PG 行，再遍历日期读取 RAW Owner，之后才查 bars cache；所以缓存仅省掉后续复权 / 聚合计算，没有省掉主要输入读取。修复后把缓存查询前移，并将 history-index 版本纳入缓存身份。 | **实现顺序缺陷 / 缓存覆盖范围不足。** 单测验证热缓存跳过 PG history rows 与逐日 Owner 读取；运行服务未重载，尚无修复后 HTTP 冷 / 热现场计时。 |
| 缺行情点在 K 线中消失、时间轴挤压，均线线段跨缺口 | 基线绘图先 `filter` 掉 UNKNOWN / OHLC 不完整行，再按剩余有效行数量算步长和 x 坐标，因此缺失交易日被压缩；MA 也对有效行提取后 `filter(Boolean)`，把缺失点两侧接成同一条线。 | **绘图实现缺陷。** 修复改为保留完整日期窗口、给未知行保留 slot / 标记，并按连续有效 MA 段拆线；合成缺口单测已覆盖首、中、尾缺口。 |
| `static/research/labels.js` 无法解析 | 基线文件最后多出字面量反斜杠-n（两个字符 `\n`），属于无效 JS 语法。 | **文件内容 / 构建输入缺陷。** 删除尾部残留后 `node --check` 通过；本轮未追溯该字符最初由哪次生成或编辑引入。 |
| Priority API 缺绑定，页面无法列出优先级 | 当前 R3 使用 token `2e3a2dd…`；候选根 `data/v4/research_priority_authority_r1.json` 仅列 `554f702…`（10/12 单日旧 binding）和 `914092…`（10/12–14 另一候选链）。PG 读函数按 `(token,T0)` 查不可变 Owner，不允许拿另一 token 的 Owner 冒用。2026-10-20 候选链修复记录已为 `914092…` 生成三日 Priority Owner，10/14 股票可排序 967、板块可排序 0。R3 的 API 400 正是缺少 `2e3a…/2026-10-14` binding；页面“筛选参数无效”是该接口错误的通用呈现，本轮没有证据证明存在另一个独立路由设计故障。 | **当前候选 materialization / authority 绑定缺口。** Priority 能力此前在另一候选 token 上实现过；当前候选上下文更换 token 后没有对应 Owner。此轮任务是只读审计，没有授权补写 Owner。旧 token 里板块零可排序的逐项字段原因未核清。 |
| 10-14 有 5,160 条 D2 stale、资格 UNKNOWN | D2 归约器在必需事实未知时按 `REQUIRED_FACTS_UNKNOWN_PRESERVE` 保持 stale / UNKNOWN，这是 fail-closed 规则；定向合约向量要求 stale 不得变成 eligible。数据中所有 5,160 stale 行都有必需 `frozen_invalidation` 未实现 / UNKNOWN；5,080 行的 CONFIRMED 也为 UNKNOWN。冻结失效字段生产者明确标为 `V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED`。 | **有意的安全归约 + 上游能力未实现 / 信号未确定。** 不是“把旧行情误算成 stale”的证据。10/20 生成时间造成的是历史首次可得 / PIT 证明不足，不是这 5,160 个 stale 状态的唯一直接原因。CONFIRMED 生产者虽标为 IMPLEMENTED，但 5,080 条为何仍无确定值，本轮没有进一步追到原始必需谓词 / 信号分量，仍是待查原因。 |
| 板块生态风险 0/400 可评估 | `build_sector_family` 只把已接受 lifecycle health 映射为生态风险状态；当前板块行中的 health 是 `UNKNOWN`，页面和来源原因显示 `sector lifecycle pg owner unavailable`。板块 RS、宽度等代理指标存在，但不符合该风险合同要求的 accepted health 输入。候选根同时没有 risk authority；2026-10-20 日更修复记录明确未创建 operational-risk Owner schema。 | **上游 lifecycle Owner 不可用 + 本候选风险 Owner 未物化 / 绑定。** 风险状态 UNKNOWN 是按合同降级；若要判定是否应改用其他输入，需要另行修订风险合同并做独立验证，不能当成本轮已发现的设计错误。 |
| 市场压力风险 0/1 可评估、四轴合成 UNKNOWN | 市场事实源给出的 stress level 为 null，unknown reason 为 `STRESS_INPUT_OR_COVERAGE_UNKNOWN`；10-14 daily price-limit source 仅 59/5,225 条已知（约 1.13%），压力变化的同成员样本也只有 6 条。压力必需轴不可评估，组合状态按 `REQUIRED_MARKET_AXIS_UNKNOWN` 返回 UNKNOWN。当前候选没有 risk authority，正式风险读域也未发布。 | **输入覆盖不足 + 当前候选正式风险 Owner 未物化 / 绑定。** 候选趋势、宽度、参与度轴有事实，不足以替代压力轴；按 UNKNOWN 收口是合同降级行为，不代表“无压力”。 |

根因对照所用实现 / 证据：图表原始逻辑以基线 `87cf679f` 的 `core_product_bff_r1.py`、`components.js`、`labels.js` 为对照；Priority 读取合同见 `src/workbench_db/v4_operational_risk_pg_r1.py`（按 token / T0 读取 priority authority），另一 token 已生成 Owner 的记录见 `docs/evidence/continuous_daily_repair_20261020/README.md`；D2 fail-closed reducer 为 `src/v4/research_state.py`，输入 provenance producer 为 `src/v4/confirmation_d2_candidate_r5.py`；风险 Owner 加载 / 候选族计算分别见 `src/workbench_db/v4_operational_risk_pg_r1.py`、`src/workbench_service/operational_risk_v1.py` 和 `src/workbench_service/core_product_bff_r1.py`。当前候选根 `G:/codex_tmp/v4_daily_candidate_chain_20261020` 中 Priority authority 的 token 列表及 operational-risk authority 缺失状态为本轮只读检查结果；没有对该临时根或数据库写入。

## 28766 页面验收记录

- 页面顶部显示当前处理截止日与研究日期均为 **2026-10-14**；成员提示显示 2026-10-09 TDX 最新成员回算、非严格 PIT 及存续偏差风险。
- 窄屏视口 390×844 实际打开个股详情图表：原生前复权 / 不复权控制、最近 20 / 60 / 120 根控制可读；本轮 UI 验收确认 QFQ、最近 60 根及 10-14 尾值。当前页面图表状态说明缺口保留交易日位置。修复后缺口绘图算法另外由真实模块测试覆盖。
- 板块列表与煤炭详情可读；Focus 页面显示 3,247 总数、观察状态与 Forward 缺源说明；市场页显示正式环境未发布。Priority 页面无法出列表，API 明确缺 Owner。
- 未对运行中的 28766 后端热重载或重启，因此缓存修复的 API 运行时冷 / 热耗时、依赖调用次数仅由目标代码单测验证。页面验收不等同于完整发布门禁。

## 阶段结果与后续

**本阶段结果：** 图表缓存与缺失数据绘制已修复并由定向测试通过；只读核验确认其他目标域的真实可用边界与明确缺项。没有证据支持将 Priority、D2、正式市场风险、Focus 前瞻能力或行业概念历史关系认定为完整通过。现有成功三日候选链保持原样。

**下一阶段：** 只在获得单独阶段授权后，针对 Priority Owner 缺失、轮动未知质量、D2 事后可得与 PIT 缺口、复权事件及行业概念映射的分层证据继续定点核验；并在允许重载 28766 后端的窗口，对修复后的真实冷 / 热图表请求做调用与耗时验收。仍须遵守阶段门禁；本报告和 Git 推送均不构成进入下一阶段的许可。

**明确排除：** 未启动 PG 化、Schema 治理或正式生产切换；未改写数据库、正式 Head、生产服务或外部行情源；未读取或处理 2026-10-15 及之后行情。

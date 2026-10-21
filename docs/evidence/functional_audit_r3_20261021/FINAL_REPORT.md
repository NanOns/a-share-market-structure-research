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
| Priority | `GET /api/v4/radar/priority` 对股票及板块 scope 均返回 `RESEARCH_PRIORITY_BINDING_MISSING`；首页统计为 177 条部分事件，范围 `ACCEPTED_FOCUS_CHANGE_EVENTS_WITHOUT_TOP_ROTATION_COVERAGE`，原因 `FORMAL_RADAR_PRIORITY_NOT_PUBLISHED`。28766 的 `/v4/research/radar/priority` 实页显示筛选参数无效，未呈现可排序列表。 | **缺失 / 未通过。** 没有 Priority Owner，177 不能代替正式 Priority 排序。 |
| D0 / D2 | 只读检查 10-14 `corrected_d2.json.gz`（5,225 行，candidate artifact）；值与 R2 汇总一致：D0 CONFIRMED `TRUE=145`、`UNKNOWN=5,080`；PREWATCH `TRUE=397`、`FALSE=4,790`、`UNKNOWN=38`；D2 `FRESH=65`、`STALE=5,160`，最终资格同为 65 TRUE / 5,160 UNKNOWN。未知样本共性包括 `CONFIRMED` 与 `scenario` 未知；所有行还有 `dq5`、`episode_invalidation_contract_id`、`followup_complete` 可选输入未知。D2 的 cutoff / `system_available_at` 是 2026-10-20，不是 T0 当时可知证据；输出不得按 PIT 解释。 | **实现有输出、历史可信度未证明。** UNKNOWN 按原状态保留；D2 不是正式独立验证结果。 |
| 历史复权与 K 线 | 28766 真实页面选择 10-14、日线、QFQ、最近 60 根，显示 60/422，末根 10-14 收盘 12.55；详情同时展示 MA5 13.336、MA20 13.124、MA60 13.876。日线页有“逐日 RAW Owner、T0 冻结 TDX GBBQ、精确有理数坐标”说明，并注明非正式发布 / 非严格 PIT。图表 API 既有冷 / 热响应测量来自修复前运行进程缓存，故不作为修复后的性能指标。 | **有限通过。** 证明了指定样本的 QFQ 页面与截止日期；本轮没有独立找到并核对股息除权、停牌缺口、IPO 边界的全套分层样本，也没有运行中的修复后端冷缓存基准。 |
| 行业 / 概念关系 | 10-14 stock detail API 的三一重能（`SH.688349`）`primary_industry=INDUSTRY:T0706`，来源为唯一映射行业叶节点；页面能从主行业跳至对应板块。煤炭样本源成员 32、映射 32、未映射 0、有行情 32。另查 5G 概念 `THEME:880506`：源成员 454、映射 442、未映射 12、有行情 440；返回成员样例中，三安光电 `SH.600703` 的唯一行业为 `INDUSTRY:T1203`，其余 4 个样例也均有唯一行业映射。 | **分层样本关系通过。** 样本直接验证行业叶节点与概念板块成员边；仍有 12 个未映射成员，且当前成员重建不等于历史 PIT 关系，不能由样本外推全量完整。 |
| Focus | 只读页面显示独立关注清单共 3,247 条，明确标记“重建关注轨迹”“非正式前瞻验证样本”“不代表持仓”，并关闭新增 / 自动写入。本页 30 条观察中，3 条真实状态变化、27 条来源不足观察；Focus 详情数据将来源不足与业务变化分开。 | **读域部分通过。** 该池不应被当成个人 watchlist、真实持仓或前瞻胜率样本。 |
| 市场风险 | 10-14 市场候选四轴：趋势 `WEAK`、宽度 `DETERIORATING`、参与度 `THIN`、压力 `UNKNOWN`（stress level 缺失、daily limit coverage 59/5,225≈1.13%）；合成环境 `UNKNOWN`，原因 `REQUIRED_MARKET_AXIS_UNKNOWN`。完整风险 Owner 未绑定：个股结构风险 5,203/5,225 可比较（`NONE=5,154`、`DAMAGED=49`、`UNKNOWN=22`；变差 42、改善 30、不可比 2）；板块生态 0/400 可评估；市场压力 0/1 可评估。UI 将市场四轴列为“正式环境尚未发布”，正文显示“未发布”。 | **部分可判。** 结构风险是候选变化事实；环境和板块生态风险不能给出正式结论，UNKNOWN 不等于无风险。 |

## 28766 页面验收记录

- 页面顶部显示当前处理截止日与研究日期均为 **2026-10-14**；成员提示显示 2026-10-09 TDX 最新成员回算、非严格 PIT 及存续偏差风险。
- 窄屏视口 390×844 实际打开个股详情图表：原生前复权 / 不复权控制、最近 20 / 60 / 120 根控制可读；本轮 UI 验收确认 QFQ、最近 60 根及 10-14 尾值。当前页面图表状态说明缺口保留交易日位置。修复后缺口绘图算法另外由真实模块测试覆盖。
- 板块列表与煤炭详情可读；Focus 页面显示 3,247 总数、观察状态与 Forward 缺源说明；市场页显示正式环境未发布。Priority 页面无法出列表，API 明确缺 Owner。
- 未对运行中的 28766 后端热重载或重启，因此缓存修复的 API 运行时冷 / 热耗时、依赖调用次数仅由目标代码单测验证。页面验收不等同于完整发布门禁。

## 阶段结果与后续

**本阶段结果：** 图表缓存与缺失数据绘制已修复并由定向测试通过；只读核验确认其他目标域的真实可用边界与明确缺项。没有证据支持将 Priority、D2、正式市场风险、Focus 前瞻能力或行业概念历史关系认定为完整通过。现有成功三日候选链保持原样。

**下一阶段：** 只在获得单独阶段授权后，针对 Priority Owner 缺失、轮动未知质量、D2 事后可得与 PIT 缺口、复权事件及行业概念映射的分层证据继续定点核验；并在允许重载 28766 后端的窗口，对修复后的真实冷 / 热图表请求做调用与耗时验收。仍须遵守阶段门禁；本报告和 Git 推送均不构成进入下一阶段的许可。

**明确排除：** 未启动 PG 化、Schema 治理或正式生产切换；未改写数据库、正式 Head、生产服务或外部行情源；未读取或处理 2026-10-15 及之后行情。

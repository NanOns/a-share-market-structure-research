# 大A V4｜R4.3 R2 控制面修复 / FP01–FP14 入场｜最新独立审计 R1

- 审计日期：2026-10-09
- 冻结审计分支：`codex/v4-fp14-r2-repair`
- 最新 HEAD：`6f0cf3c5a983eab481283d0436e050d70b77fe29`
- 上次已审 HEAD：`379664cbd97f03efdfe6286c3869415bbc15f666`
- 主产物位置：`docs/evidence/r43_r2_fp_entry_20261009/`
- 最新 Google Drive 归档目录：`1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD`
- 最新执行依据：`V4_R43_R2_FP正式入场与控制面修复任务卡_20261009.md` 与 `V4_全功能正式生产前端_完整任务卡合集_R1_20261008.md`
- 审计对象：实际 GitHub 变更、真实 Drive 交接、代码、测试收据、浏览器截图与归档 ZIP 原始字节。

## 1. 唯一阶段结论

**`R43_R2_CONTROL_REPAIR_ENGINEERING_PASS_SCOPED / FP01_FP14_INGRESS_COMPLETE / FP_FULL_ACCEPTANCE_NOT_GRANTED`**。

已经完成 R4.3 四交易日受限运营数据生产切换，当前可见最新收盘日为 2026-10-08。最新一轮新增了控制面双 namespace 修复、FP 兼容接口缺口的显式分流、真实六入口浏览器探查与后续 14 包续办卡。**本轮没有提供任何 FP 工作包新的完整正式通过结论；不能把 14/14 已产生任务卡理解成 14/14 功能验收通过。**

需要区分：①R4.3 基础运营数据发布成功；②R4.3 R2 控制适配工程自测通过；③FP01–FP14 入场及差距盘点完成；④FP 完整模块建设与独立验收尚待逐项完成；⑤全量 Rotation 独立 oracle 和动态日更后继发布仍欠缺。既有历史 FP 工程事实不因本轮 0 个新增最终 PASS 被否定。

## 2. 新 HEAD 实码与交付核查

- GitHub 相对 `379664c...` 领先 2 个 commit，变更核心包括 `src/workbench_service/v4_control_server_v2.py`、`operational_control_status.py`、`operational_gap_bff_v2.py`、`src/workbench_analysis/operational_next_session_v1.py`、`user_authority_provenance_v2.py`、`run_workbench_service.py`、静态适配 `r43-control-v2/app.js`，测试与正式证据。
- 上述运行入口现在显式使用版本化 V2 控制服务，`config/v4_control_adapter_v2.json` 对关联代码与 JS 绑定 SHA；原 `v4_server.py` / 原 PIT Head / 已冻结 S 与 Owner 不被本轮覆盖。
- 从 Drive 真实取得 `R43_R2_FP_ENTRY_CONTROL_REPAIR_20261009.zip`：**1,387,389 bytes，SHA256 `c19ac630ca86af1656a0891a71479c287ee5cc74fb37ad8d9efc55014e3d9fb5`**；ZIP CRC 通过；79 个 ZIP 条目 = 78 个 manifest 受检对象 + 1 个 manifest，逐项 bytes/SHA 重新核对 **78/78 一致**。不能将“78 个 payload”与“79 个 zip entry”误报为冲突。
- Drive 同目录已归档交接 MD、FP gap matrix、控制面 QA、下一日预检及 ZIP；仓库 `DELIVERY_RECEIPT.json` 声明内容读回成功，与所取得 ZIP 相符。

## 3. 本轮修复及验收等级

| 子任务 | 当前状态 | 可以认定的具体结果 | 仍未满足 |
|---|---|---|---|
| R4.3 四日基础运营上线 | **PASS_SCOPED（继承）** | 10/08 Head 已发布；9/30 历史 Head 不变；最新 TDX S 为回算口径 | 历史严格 PIT、完整 Rotation 外审不在授权范围 |
| P0-A 控制面 V2 | **ENGINEERING_PASS；独立关闭待签** | `operational_context`、`legacy_strict_pit_context` 分离，当前日 10/08 / 旧日 9/30；旧五域 false 保留且说明是旧权限 | 全部下游 consumer 迁移的独立再核查 |
| P0-B 用户授权溯源 | **LOCAL_EVENT_VERIFIED；EXTERNAL_PENDING** | 找到 Codex 原始 `role=user` JSONL、会话 ID、时间和行号；保存源事件 | 独立审查原会话/授权身份与范围；本地摘要不等于外部认证 |
| P0-C 下一交易日预检 | **BLOCKED_EXACT_REASON** | 冻结日历识别 10/09；last-good 仍 10/08；没冒充新数据已到齐 | 新 Source QA、身份/GBBQ、动态日期 successor builder、CAS 与失败回滚均未实现/准入 |
| FP 六入口首轮 | **ENGINEERING_INGRESS_PASS** | 真浏览器确认全部六导航、首页日标、股票与板块列表/详情/成员、Focus、诊断基础可达；浏览器 home 1366/1920 无横向溢出 | Edge 全站与所有交互/断网/数值的 FP13 验收尚未通过 |
| FP01–FP14 正式验收 | **NOT_GRANTED_BY_THIS_RUN** | 最新 Drive 完整合同已读；14 张续办卡和缺口矩阵已生成 | 各包按原合同补 Owner、完整功能与独立验收 |
| 数据/算法独立外审 | **PARTIAL_SCOPED / FULL_NOT_GRANTED** | 原四日 source/数值证据继续冻结；Rotation `VALIDATION_ONGOING` | 全量真实 Owner 与完整递归 Rotation 独立复算 |

开发方报告 **18 项 pytest 回归通过、68 次隔离 HTTP、37 次真实服务 HTTP**。本外审已读取这些提交的代码和封存收据、独立复核 Drive ZIP；没有从当前环境直接连开发电脑 `127.0.0.1:28765` 重新发请求，也没有完整重算数 GB 的生产 Owner，不将开发方 HTTP 收据误称为审计者亲自现场实测。

## 4. 真实页面复核发现的问题（不是“全 UNKNOWN”，但远未完整）

- **FP04/FP09 P0 产品阻塞：市场与事件页面主体整个被一个已知缺口拦截。** 真实截图 `live_browser_market.jpg` 页面在请求 `/api/v4/market/breadth` 后仅展示 `SOURCE_INCOMPLETE | DATED_OPERATIONAL_MARKET_BREADTH_OWNER | FP09` 错误和重试，后续指数、涨跌停、事件内容未渲染。虽然 `/api/v4/market` 四轴在首页有数据，但不可称 FP09 市场中心已完成。应在 FP04 加区块级失败隔离，并在 FP09 接通正式 breadth/indices/limits/ladders Owner。
- **FP08/FP10 P0/P1：关注跟踪上半部实际可用，但 Forward 区块中断。** `live_browser_focus.jpg` 显示 2477 条关注对象，后续 `forward/statistics` 的缺失引发错误提示；不能以 Focus 列表可读判定整个生命周期/Forward 通过。区块失败不应清空已展示的 Focus 数据。
- **FP05：今日首页恢复了真实 5224 个股票画像、400 个可计算板块、市场四轴，但变化、风险、去重净信息没有正式 Owner。** 现场截图均给出具体缺失来源；“风险变动源未知”绝不等于“没有风险变化”。
- **FP06：板块列表有中文行业名、成员数、相对强弱等可用数值；timeline/overlap 尚缺 dated Owner，不能完成板块研究历史功能。** 400 是可计算板块，401 源分组含不可计算 T00；旧 110 叶行业+22 派生父级+1 占位的归类仍须保持。
- **FP07：股票列表与详情已有画像和真实代码搜索，但 `stocks/<id>/chart` 明确 `SOURCE_INCOMPLETE`，日周月 K 线及来源链未接通。** 个股展示中文名/别名、技术结构证据仍须 QA。
- **FP11/FP12：部分诊断源与基础数据存在，诊断子页和 replay/compare 未提供正式 Owner。** `src/workbench_service/static/research/app.js` 首页仍展示 **“PIT 冻结回放”** 入口，但当前运营 Head `PIT_ELIGIBLE=false`；应按当前点击结果和回放 scope 增加明显未授权/来源缺失提示，避免用户误以为四日回算已经证明严格 T0 PIT。
- **FP13：真实 IAB 画面、DOM、首页宽度截图存在，可证明第一轮浏览器探索；不足以替代整站 Edge 1366/1920、交互、路由、性能、回滚、错误隔离与逐字段数值抽样。**

**源码级注意：** `operational_gap_bff_v2.py` 通过 `missing()` 将未接路由返回 HTTP 200 + `status=SOURCE_INCOMPLETE`，前端 `api.js` 会把该状态提升成可见错误。在统计 HTTP 成功率时必须同时断言业务状态和 DOM；否则所有接口 200 看似绿灯，实际整页仍停在错误信息。

## 5. 14 个 FP 的确切进度与下一修补方向

| FP | 当前已见成果 | 本轮正式独立验收 | 主要下一项 |
|---|---|---|---|
| 01 权限/发布语义 | 限定运营授权、原事件本机溯源 | NOT_GRANTED | 原事件独立回读及新权限门 |
| 02 数据总线 | 10/08 Head、5224 画像、5209 BAR | NOT_GRANTED | 动态日期 Source QA + successor builder |
| 03 BFF/字段 | 已知与未知按 Owner 精确提示 | NOT_GRANTED | 各缺失 route 的 producer/schema 与单位校验 |
| 04 六入口 | 六导航真实可达、首页 JS 修复 | NOT_GRANTED | 区块隔离、中文 UI、Edge 全页 |
| 05 首页/四轴 | 市场四轴可读 | NOT_GRANTED | 今日变化/风险/净信息 Owner |
| 06 板块研究 | 400 板块与成员可用 | NOT_GRANTED | dated timeline/overlap，Rotation 另审 |
| 07 个股画像 | 搜索、画像、详情可读 | NOT_GRANTED | 日周月真实 chart、名称/结构 |
| 08 Focus | 2477 Focus 对象与事件 | NOT_GRANTED | Episode/T0/Anchor/Observation/Outcome 完整语义 |
| 09 市场中心 | 主页四轴已有 | NOT_GRANTED | breadth/indices/limits/ladders；市场页被缺口挡住 |
| 10 Forward | 原始 Forward owner/观察读域已接 | NOT_GRANTED | statistics/plans/fep/settlement，成熟度正确表达 |
| 11 诊断 | 当期 sources/基础诊断 | NOT_GRANTED | health、FEP、jobs、规则/源子页 |
| 12 Replay/Compare | 原版 9/30 独立可读 | NOT_GRANTED | 冻结 as_of/权限隔离与实际对比/回放 |
| 13 全站浏览器 | IAB 六入口及首页两宽度截图 | NOT_GRANTED | Edge 全流程、数值、错误隔离与性能 |
| 14 正式全产品发布 | R4.3 受限运营读域已运行 | NOT_GRANTED | 先满足 FP13，再做 UI/read 联合 CAS 与回滚 |

**注：** “本轮正式独立验收 NOT_GRANTED”不是声称这 14 项历史上从未开发或全部未验收；仅表示最新入场轮没有为它们新增完整合同 PASS。有关更早 V4-00～V4-22 各阶段正式状态，必须读取其各自最新 Head/进度卡，不能从这份 FP 首轮入场报告推算“22 阶段全部完成”。

## 6. 下一轮最佳执行顺序

### 第一组：先让已经存在的生产功能能完整显示（前端用户感知 P0）

**FP03 + FP04 + FP09 + FP10**：在保留有效数据的基础上做组件级错误隔离，不因一个子路由 SOURCE_INCOMPLETE 将整个 Market/Focus 页面替换成报错；同时按真实 Owner 接通市场 breadth/indices/limits/ladders 与 Forward 统计/计划/权限/结算，只能读实际源，缺失即状态待补，严禁补假数。同步修 FP05 首页 PIT 文案/未知风险含义。

### 第二组：支撑真正研究工作台的核心业务

**FP05/FP06/FP07/FP08/FP11/FP12** 按原合同并行补齐变化与观察、板块趋势时线、真实个股日周月图表、关注路径证据、数据诊断、冻结/比较权限合同，独立 QA 后再交付。不允许用“卡片能显示”代替因子/血缘核实。

### 独立平行链：FP02 动态日更 + 控制/授权审计

10/09 及后续日期的正式 successor 需要单独的、能复算 Source QA/身份/生命周期/GBBQ/日历/原子 CAS/回滚链。既有四日冻结 Owner 与基准继续保持，待新会话数据真实到齐后再滚动研究 Head；在此之前 last-good 10/08 不退化。这条链不阻塞独立前端 UI 开发，但阻止宣布每日生产流水线完成。

### 最终总门

FP13 全站 Edge/E2E/数值通过后，FP14 联合 UI + 运营 Head 正式发布与回滚；独立 Rotation/来源完整外审继续单独记录，不偷换成全面 PASS。

## 7. 本次审计交付状态

- **审核结论：`FP_ENTRY_AND_CONTROL_REPAIR_SCOPED_PASS; FP_FULL_ACCEPTANCE_NOT_GRANTED; NEXT_SESSION_BLOCKED`。**
- 本报告应同步至 Drive 当前 R4.3/FP 同目录，保留正式历史，不覆盖 Codex 原始开发收据或用户原消息。
- 下次恢复以：本文件、R43 R2 控制入场交接、FP01–FP14 最新合同/缺口矩阵、新 Head SHA、最后一次 Stage Acceptance 为事实依据。


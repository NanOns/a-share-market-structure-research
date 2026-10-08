# V4 页面完整性独立审计｜2026-10-08

- Audit ID: AUD-V4-UI-COMPLETENESS-20261008
- Scope: 当前默认 V4 页面与完整产品设计对照；独立于 P0 生产切换阶段门。
- Contract: UI_DESIGN_COMPARISON_R1；只读检查，不运行 scanner、不刷新接受指针、不授予任何 capability。
- Baseline: 61d3b08；服务 V4_DEFAULT_WORKBENCH READY；accepted_trade_date=2026-09-30。
- Authority: docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md §62A–§68、§81.2；最新切换任务 00/02/03/05 与 docs/upgrade/V4_PRODUCTION_CUTOVER_EXECUTION_20261007.md。
- Evidence: 实际浏览器完整加载后的 AX 页面；src/workbench_service/static/v4-workbench.html、v4-workbench.js；v4_server.py、shadow_server.py、current_v4_context.py。

## 对照结果

| 项目 | 设计要求 | 当前展示 / 实现 | 判定 |
|---|---|---|---|
| 一级导航 §62A | 今日总览、板块研究、个股研究、关注跟踪、市场与事件、数据与诊断 | 当前研究、Shadow、V3、来源健康；单长页七区块 | 缺失产品导航 |
| 市场卡 §62B/63 | Trend/Breadth/Participation/Stress 四轴及环境映射 | 无市场卡、四轴或独立 current 模块 | 缺失 |
| 今日变化 §62B | 轮动、板块、独立股票变化；风险退出；成员预览及分项计数 | summary 33 条，仅首6条；通用事件卡片 | 部分实现，未呈现完整变化结构 |
| 板块研究 §62C/64 | 类型/成熟度/健康/轮动筛选，Why Now、RS、宽度、成员扩散、Timeline、Overlap | 378个板块，仅首6个；编码、名称、成员数；algorithm_state 固定 UNKNOWN；无详情 | 明显缺失，含上游能力缺口 |
| 个股研究 §62D/65 | Daily Profile、周/月背景、F/R/H、Waiting/Invalid、图表、锚点、板块上下文 | 5213行Raw行情与部分状态；仅首6条；无个股详情/图表/Timeline | 明显缺失 |
| 未入选解释 §62E | NOT_ELIGIBLE/UNKNOWN/NOT_IMPLEMENTED/池外区分及原因 | 个别最终资格、状态或折叠缺口；无完整解释面板 | 缺失 |
| 关注跟踪 §62F | 生命周期事件、Episode、Anchor、Observation、Path/Outcome | 无一级入口；Cohort 不等于 Focus | 缺失；写入仍未授权 |
| 市场与事件 §62G | 指数、涨跌停、梯队、题材事件、即时统计 | 当前服务无对应入口；继承路由未提供旧页面 | 缺失 |
| 数据与诊断 §62H | 质量、源/参数合同、技术扫描等分层入口 | health四组件及JSON；Shadow；V3仅退役提示页 | 部分实现 |
| PIT Replay/Compare §66/67 | 选日期as-of回放、跨日/市场/板块比较 | 无日期控件、回放或比较入口 | 缺失 |
| 全量浏览 | 详情完整分页、筛选 | API支持offset；UI固定limit=6，无分页/下一页；summary/cohort无搜索 | 已有数据无法完整浏览 |
| 语言/信息层级 §62A | 后台术语默认下沉 | 主屏大量英文枚举、质量标记、摘要hash；股票通常仅代码；结算标题为长hash | 产品可读性不足 |
| Forward与结算 | 期限成熟度、修订来源清楚 | cohort117条首6条，settlement5条PENDING；无法据此认定完整结算浏览 | 部分实现；成熟结果不得伪造 |

## 验收结论与边界

Acceptance: GAP_CONFIRMED / PRODUCT_UI_COMPLETENESS_NOT_ACCEPTED。本结论不否定原有服务切换或数据读取范围的测试结果，也不证明底层算法全部缺失。当前页面覆盖切换任务列出的最低七区块，但没有完成完整产品设计。

当前 permission 中 ROTATION、SECTOR_RISK_CHANGE、SECTOR_STAGE、STOCK_CORE、STOCK_SECTOR_DEPENDENT 均 false，focus_write=false。修复页面不能将它们改为 true；应区分已接受只读数据、能力未授权、来源缺失与尚未实现，不能以 UNKNOWN 替代缺失页面。WAIT_NEXT_ACCEPTED_INPUT 与未成熟 PENDING 本身不是UI故障。

Next: 按六入口建立逐字段 Feature→Data→API→UI 缺口映射；优先导航/全量浏览/个股与板块详情，再市场卡、Focus只读历史、事件与诊断；真实来源不足处显式显示合同原因。实施须作为另行阶段任务，不由本审计自动进入下一门。验收按每个入口、字段、交互和来源独立留证，不能只用HTTP 200或测试通过代替产品验收。

本轮仅新增独立审计文档，不修改业务代码、接受数据或TDX来源。
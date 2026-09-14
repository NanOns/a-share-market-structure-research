# V3 页面与后台全量复核（2026-09-13）

## 阶段合同

- 审计合同：`V3_FULL_STACK_REAUDIT_V1_0`
- 权威文档：`docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`（当前工作区版本）
- 范围：当前默认 `/v3` 页面、V3 本地研究 API、在线 API、生产 DuckDB 只读数据量、P09/P10/P11 收口记录与回归测试。
- Phase 0 前置：`docs/V3_P00_P04_02_FULL_PASS.md` 已记录 P00–P04-02 `FULL_PASS`，允许进入后续只读核查。
- 安全边界：未修改或访问写入 TDX；生产 DuckDB 仅以 `read_only=True` 查询；未提交研究构建任务；未修改业务代码、配置或数据库。

## 总结论

**BLOCKED（不能接受“V3 已全部完成”的结论）。**

工程路由、主要 API、兼容页面和回归测试大量存在，但“存在代码/接口”与“用户可见、真实数据可用、效果完成”被混为一谈。当前默认发布日 2026-09-10 的四个 V3 核心结果全部为空；在线链路仅部分可用；P10-03 效果仍明确处于观察中；主入口没有把 P09 的完整在线工作台显式暴露出来；首页卡片到详情的上下文联动也未完成。

## 关键发现

| ID | 严重度 | 发现 | 现场证据 | 判定 |
|---|---|---|---|---|
| RA-01 | BLOCKER | V3 四个核心业务结果全部为空 | `/api/v3/home/local` 为 `READY`，但 CURRENT=0、POTENTIAL=0、CURRENT_FOCUS=0、EARLY_FOCUS=0；页面同步显示四个空态 | 不能称为用户功能完成；只能称为计算链已生成空结果 |
| RA-02 | BLOCKER | 算法效果没有完成验收 | `/api/v3/research/evaluation` 返回 `PENDING`；`research_signal_outcomes=0`；P10-03 和 P11 文档均为 `EFFECT_OBSERVATION_PENDING` | V3 升级的“效果”未完成，不得纳入全部完成 |
| RA-03 | HIGH | 生产数据覆盖只有一个 V3 run | `research_runs=1`、`research_sector_states=554`、`research_stock_states=6178`、`research_shortlist=0`、`research_signal_outcomes=0` | 历史/跨日生命周期、提前信号、3/5 日结果无法形成真实产品能力 |
| RA-04 | HIGH | 完整在线功能藏在孤立页面，主入口只露出子集 | `/v3/online` 实现七池、四榜、题材成员、分布等；默认 `/v3` 的“市场与事件”只请求 overview、topics、concept hot plates、5 条 hot topics 和按需 ladder，页面无 `/v3/online` 或 `/v3/events` 明确入口 | 用户“基本看不见在线功能”的反馈成立 |
| RA-05 | HIGH | 当前在线关键链路真实降级 | 现场：overview=`DEGRADED`；ladder=`EVENT_BUNDLE_UNAVAILABLE`、0 行；热榜 40 行但东方财富/同花顺报价均 `UNAVAILABLE:RemoteDisconnected`；topics 13 项可用 | 不能以 P09 工程 `FULL_PASS` 表述为当前在线全可用 |
| RA-06 | HIGH | 首页卡片/个股条目没有携带对象上下文下钻 | `v3-unified.js` 的板块卡只带 `data-v3-page="sectors"`，个股条目只带 `data-v3-page="stocks"`；点击仅切换通用页，没有 sector_id/security_id | 不满足“卡片直接进入该板块理由与成员”和“个股证据弹窗/对象联动”的完整体验 |
| RA-07 | MEDIUM | 在线来源登记与运行事实不一致 | `config/online_source_registry_v3.json` 仍为 `stage_status=STATIC_ONLY`、`enabled=false`、所有 EXT01–EXT11 `NOT_VERIFIED`，而 P09 收口与运行页面已消费多项来源 | 配置不是当前能力真相，审计可追溯性失真 |
| RA-08 | MEDIUM | “旧模块仍存在”需要按 V3 去留表区分 | V3 §2 明确要求保留市场周期、主线、成员历史、五类结构、新高/RPS/MA/量额、本地梯队等，仅改标签/入口；禁止项（每日导出、会员、投资日历、外部软件跳转）在当前主页面未发现入口 | 保留型旧模块存在本身不是缺陷；错误在于入口层级、标签或仍冒充 V3 主结果时才构成缺陷 |
| RA-09 | MEDIUM | 旧能力改造主要是“V2 壳 + V3 覆盖层” | `/v3` 直接复用 `static/v2/index.html`、`app.js`，再加载 `v3-unified.js`；页面标题仍显示 `M7 统一研究工作台`、`M7A · 7A-05` | 用户感知不到 V1/V2 改造有客观原因；版本身份与信息架构没有彻底收口 |
| RA-10 | MEDIUM | P11 “最终验收”原始结论并非全通过 | `docs/V3_P11_01_FINAL_ACCEPTANCE_20260913.md` 的 Overall 为 `DEGRADED_PASS`，当时也明确 0 eligible cards、PIT PARTIAL、效果待观察 | 后续入口切换不能反向改写这些限制为“全部完成” |

## 已确认通过的部分

- 默认入口已切换到 `/v3`，旧 `/view` 回退仍在。
- `/api/v3/research/sectors?track=ALL` 可返回 554 个板块，分页语义存在。
- 板块/个股/联动/市场/数据六个主导航可打开，V1/V2 多项能力仍可读。
- P10-01 的 19 项去留矩阵可通过 API 读取。
- 题材在线数据当前可用：13 个题材；热门板块和热门话题有返回。
- 当前代码回归：`355 passed in 89.76s`（`tests/upgrade_v3 tests/upgrade_m7 tests/upgrade_m14 tests/upgrade_m15`）。
- 热榜请求时直取、不持久化的边界仍成立；生产相关在线持久化表当前均为 0。

## 对“不要的模块还存在”的裁决

当前不能把所有旧模块一概判为应删除。权威 V3 §2 明确写了“不得删除旧五类结构、矩阵、主线、RPS能力；移除的是错误入口/标签，不是用户数据”。因此：

1. 主线、历史代表、全部结构候选、本地梯队、新高/RPS 等应保留，但应降级为历史/工具/本地估算入口，不能占用 V3 主要研究结论的位置。
2. 每日导出、登录会员、投资日历、外部软件跳转明确本版不做，当前主页面未发现这些入口。
3. 龙虎榜/新闻原因明确后置，当前主页面未发现独立模块；来源自带题材原因不等同于该后置模块。
4. 若用户此前另有“不要”清单但未写入当前 V3 主文档，应新建独立产品裁决项，不能依靠口头记忆或旧文档判断。

## 验收结果与下一阶段

- 页面功能完整性：`BLOCKED`
- 后台合同/路由存在性：`FULL_PASS`
- 真实本地数据可用性：`BLOCKED`
- 当前在线可用性：`DEGRADED_PASS`
- V1/V2 兼容能力：`FULL_PASS`（但入口与版本身份需整改）
- 算法效果：`EFFECT_OBSERVATION_PENDING`
- 综合结论：`BLOCKED`

建议下一阶段单独立项 `V3-RA-REMEDIATION`，按以下顺序关闭：

1. 查明四个核心清单全为 0 的数据/阈值/历史覆盖原因，并用至少多个真实交易日做分布验收；禁止用旧候选填充。
2. 将 `/v3/online` 和 `/v3/events` 的完整能力并入或显式链接到主入口，逐数据集显示 AVAILABLE/DEGRADED/UNAVAILABLE 和时间戳。
3. 修复板块卡、个股清单到具体对象详情的上下文传递与证据弹窗。
4. 统一在线 source registry 与运行 capability 真相，消除 `enabled=false/NOT_VERIFIED` 和当前运行状态冲突。
5. 重构 V3 页面版本身份和入口层级，保留型旧能力放入清晰的“历史/工具/本地估算”分区。
6. P10-03 达到 20 个信号日/50 个独立 episode 前，持续显示效果观察中，不宣称 V3 全部完成。


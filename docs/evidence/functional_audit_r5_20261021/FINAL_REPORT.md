# V4 R5 现役功能定点实修审计报告

日期：2026-10-21（Asia/Shanghai）
任务卡：`V4_R4外审_R5真实业务功能定点实修任务_截至1014_20261021.md`
基线：`codex/v4-unified-development` @ `90cbc653cd23559b6a970f0c472c02221a25de9a`
数据截止：2026-10-14。没有使用 2026-10-15 及以后行情。

## 阶段合同、适用文档与范围

本轮依据任务卡及 `AGENTS.md`，并查阅了 `docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`、`docs/operations/V4_R4_SOURCE_POLICY_MIGRATION_20261009.md`、R4 外审最终报告、日涨跌停规则配置和相关生产者代码。阶段合同是：只修复截止 10 月 14 日的现役 V4 真实功能缺陷；以冻结候选输入作可审计、只读、非 PIT 的离线重建；完成定向 API 和浏览器读回；明确区分候选与正式已接受状态；不得修改 TDX 源、生产 PG 数据、正式 Head 或生产服务。

本轮未重复已通过项目，也未做 PG 化、Schema 治理或额外流程门禁改造。结果按“已通过的局部实修”和“仍有功能缺口/需下轮处理”分别记账。

## 执行环境及安全边界

- 分支/基线符合任务卡；本报告形成时待提交的改动仅包括本报告、两处服务代码、一处日涨跌停生产者和定向测试。原有未跟踪目录 `.githooks/`、`config_back/`、`script_back/` 保留，不纳入提交。
- 28766 候选预览已重启加载本轮代码：PID `29752`，入口 `G:\codex_tmp\v4_daily_candidate_chain_20261020\serve_preview_28766.py`。状态 API 为 `READY`，T0 `2026-10-14`，formal Head `2026-10-09`，候选 token `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`，`production_accepted=false`、`formal_head_modified=false`。
- 监听核对：网页开发端口 `127.0.0.1:28766`；生产网页端口 `28765` 未监听；共享 PostgreSQL `127.0.0.1:5432` PID `8640`。本轮没有执行生产 PG 写入、迁移、正式 Head 修改或 28765 部署。
- 28766 仅访问候选数据及现有共享 PG 读取路径；候选数据产物写入 `G:\codex_tmp\v4_daily_candidate_chain_20261020\...`。未写入 `D:\new_tdx` 或其他 TDX 源根目录。

## 分项验收

| 项目 | 结论 | 实际证据与剩余问题 |
|---|---|---|
| 日涨跌停源错配（P0-A） | **PARTIAL** | 修复了生产者将 `core.owners` 与 trace dates 按位置 zip、无条件取 trace 中 baostock 来源的错配。现在按该日期 owner 的精确 RAW 路径查找同一候选目录，核验 `SUCCESSOR_CANDIDATE.json` RAW 绑定、日期、证券代码唯一性，并优先绑定同目录 `sources/daily.json`；缺失/错配时失败关闭。对当前链路 10/12 (`54ed1b92…`)、10/13 (`e137824c…`)、10/14 (`727b8c2e…`) 用新代码分别重算 5,224、5,225、5,225 行。详见下方回放数字。输出是隔离的重建候选，`AS_RECORDED=false`、`PIT_ELIGIBLE=false`；没有回写市场 Owner/API/PG，故端到端正式风险/榜单联动仍未验收。仍有参考价/特殊阶段 UNKNOWN。 |
| Priority 榜单无法读取 | **PARTIAL** | 修复 28766 候选预览读取：当前有效 token 的 `/api/v4/radar/priority?view=candidate` 现场返回 200；股票全量 5,225，排序 967、不可排序 4,258；板块全量 400、排序 0、不可排序 400。浏览器桌面端实际渲染候选标签、股票榜与证据抽屉，板块缺字段明确显示为空且不排序。正式视图仍返回 `RESEARCH_PRIORITY_BINDING_MISSING`，按正式 Owner 语义保留缺源。现用股票来源为 10/14 owner `727b8c2e…` core SHA `021c0e6f…`，候选 payload SHA `c4945baac152000a39c3c330c6019f3488a635a1ce9288268d119c30254be163`；R4 记录的 payload SHA 是 `2662ac3c…`、core SHA 是 `2c1d4751…`，身份不同。未选择旧副本来伪造一致性。窄屏 390×844 本轮没有可控 viewport 验收，故不声称通过。 |
| Priority 真实排序/可解释性 | **PARTIAL** | API 返回首位及理由可读，例如 `SZ.000158 常山北明`，因子包含结构、RPS20 变化、5 日收益、延展度与距前低等；页面显示非 PIT/未接受声明。与 R4 历史榜单不相同，排序来源差异待独立对账；不构成发布或交易权限。 |
| D0/D2 | **PARTIAL** | 复核 10/14 冻结 D2 输入 5,225 行：最终资格 UNKNOWN 5,160、TRUE 65；freshness stale 5,160、fresh 65；confirmed UNKNOWN 5,080、TRUE 145。输出均是重建非 PIT，未发现 false 被强行变真。此处数据缺口主要来自滞后/缺证，不能据此宣称 D0/D2 缺陷修复；D0 业务链路与 Parent episode 关联没有在本轮完成端到端纠正及页面读回。 |
| 板块、市场风险 | **PARTIAL** | 5G 概念 `THEME:880506` API 可读，当前成员 454、映射 442、未映射 12，报价可用 440；板块 lifecycle 明确为 `SOURCE_INCOMPLETE / SECTOR_LIFECYCLE_PG_OWNER_UNAVAILABLE`。候选日涨跌停修复后尚未重建并回读市场 Owner 风险轴；旧市场 Owner 仍绑定错误的旧日涨跌停 SHA，stress 保持 UNKNOWN。不得把本地重算比例当成已接受风险事实。 |
| Focus | **PARTIAL** | 实际 API `/api/v4/focus?limit=1` 返回总数 3,247；与 `focus_status` 的 5,225 证券覆盖表不是同一集合/分母。首页“变化数”与 Focus Owner 风险事件未完成逐行核对和真实页面验收，故原缺陷尚未关闭。 |
| 概念关系、真实页面 | **PARTIAL** | `THEME:880506` 的概念详情 API 与当前成员读回成功，保留 12 个未映射成员；本轮没有修复原始成员身份映射来源，也未完成跨页面概念关系、图表冷/热路径及窄屏验证。桌面 Priority 候选页已实际读取浏览器 DOM/画面；真实浏览器检查覆盖范围仅限 Priority。 |

**综合结论：PARTIAL。** 两个优先缺陷已有可复核的局部修复，但正式 Priority、市场风险/Focus 联动及 D0/D2、概念与全页面验收仍有剩余缺陷。本报告不是发布验收，也不授权进入受门禁约束的下一阶段。

## 日涨跌停回放证据

每个日期均由当日现行 lineage owner 的精确 RAW 绑定解析到其候选 `sources/daily.json`；数据源是候选冻结的 BaoStock 日线捕获，观测时间为 10 月 20 日，因此仅用于候选回建，不属于当时可得 PIT 证据。规则仍按版本化 `config/v4_02_price_limit_rules_r3.json`，日线不能证明盘中触板。

| 交易日 | 新来源 SHA256 | 新状态计数 | UNKNOWN 原因 | 回建文件 SHA256 |
|---|---|---|---|---|
| 2026-10-12 | `97f750e3b3eba8f898ef905ab0c3df0cd6ef0e0f73622bb886f4698d29cc2bc9` | NOT_LIMIT 5,122；UP 47；DOWN 23；SUSPENDED 12；UNKNOWN 20 | reference price unknown 18；special period 2 | `518760542fffbac438b432abaebe17a0bc4d217d5b226a4fadd58353eef2f3a7` |
| 2026-10-13 | `c8b0a5719735a52923bd1cbcfe1e07509d61c44a88e5ee4a17bd3b18c7a052ff` | NOT_LIMIT 5,112；UP 69；DOWN 10；SUSPENDED 13；UNKNOWN 21 | reference price unknown 20；special period 1 | `3ae015150a5d16aca8e1c8da3ab36638627509cc832e77526cc10f5d9b9a7aac` |
| 2026-10-14 | `8f949e7418355e8f60dbd859598e27ad948c4cfdf9bed69b37c5f04d65db755e` | NOT_LIMIT 5,141；UP 37；DOWN 13；SUSPENDED 11；UNKNOWN 23 | reference price unknown 22；special period 1 | `10038767951f38df66fa387eed47f45f38f5b501b3953f4e2590285c7e62c69b` |

10/14 旧链路为 NOT_LIMIT 59、SUSPENDED 5、UNKNOWN 5,161、UP/DOWN 均为 0；新候选回建有 5,138 行状态变化。10/13 旧链路为 NOT_LIMIT 47、SUSPENDED 6、UNKNOWN 5,172、UP/DOWN 均为 0；新候选回建有 5,151 行状态变化。该比较证明源错配导致覆盖严重不足，并不证明新候选完全正确。按对齐收盘参考核对的未匹配记录分别为 10/12 16、10/13 17、10/14 20；均需保留为审计问题。

回放目录：`G:\codex_tmp\v4_daily_candidate_chain_20261020\r5_daily_limit_materialization_8ab7eeecc0a7_54ed_e137_727b\{date}`；每个子目录含 `DAILY_PRICE_LIMIT_REPLAY.json`、`DAILY_PRICE_LIMIT_CONTRACT_V1.json` 与压缩输出。10/14 receipt SHA256：`7fe282ad…`；10/13：`3771869e…`；10/12：`e2de8106…`。

## 代码修改与定向验收

- `src/workbench_analysis/r43_daily_price_limits.py`：按候选 owner/日期绑定当前 BaoStock 日线源，强化 source/date/code 校验，回执携带实际来源绑定，支持隔离输出目录。
- `src/workbench_service/core_product_bff_r1.py`：增加严格限于当前 token/T0 的只读 Priority 候选重建路径，附输入绑定和 payload/producer SHA；正式读取路径不回退候选。
- `src/workbench_service/static/core-product-r1/app.js`：增加正式/候选页签、候选状态提示、不可排序分母、个股因子理由及证据抽屉。
- `tests/test_r43_daily_price_limit_source_r5.py`：覆盖 RAW owner 精确绑定、错日期 fail-closed、候选 RAW 绑定不一致。
- 定向测试：`3 passed`。JS `node --check`（`app.js`、`api.js`）通过；`git diff --check` 通过。临时目录和 Python 缓存均在 `G:\codex_tmp`。单测通过只证明以上局部实现，不替代本报告中标为 PARTIAL 的业务验收。

## 下一步

下一轮独立审计优先核对：① R4 与 R5 Priority 输入 owner/payload 身份差异并决定有效基线；② 将日涨跌停候选回建以明确证据接入隔离市场风险 Owner，重读市场 API，不发布正式 Head；③ D0/D2 parent episode、Focus 总数与首页变化计数逐行核对；④ 5G 未映射成员身份来源与板块 lifecycle；⑤ 图表、概念关系与 390×844 浏览器验收。任何正式 PG 写入、正式 Head 修改或 28765 部署仍需用户单独授权。

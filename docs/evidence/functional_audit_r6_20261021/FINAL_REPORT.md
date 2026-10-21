# V4 R6 功能闭环与根因判定报告

- 日期：2026-10-21
- 基线分支：`codex/v4-unified-development`
- 基线提交：`36f311c3d16be53c4c4815647e833cf15995381a`
- 范围：按《V4_R5外审_设计与实现根因判定及R6功能闭环任务_截至1014_20261021.md》执行。遵守最新适用升级文档 `docs/design/V4_WINDOWS_FULL_PACKAGE_FINAL_R2_1_20261010.md`；阶段门禁依据 `docs/V4_PHASE0_FINAL_ACCEPTANCE_R3_1_20260925.md`。
- 阶段状态：阶段 0 为 `DEGRADED_PASS`；扫描器工作不适用，未推进 V4.05 或后续门禁。
- 行情边界：最后一个纳入行情日为 2026-10-14。没有使用 10 月 15 日及以后的行情作为计算输入。10 月 20 日采集的候选快照仅用于来源证据，并明确标记为晚采集、非 PIT、非当日记录。

## 执行摘要

本轮已将板块生命周期、市场风险（可计算压力轴）、Priority 候选排名及 D0/D2/Focus 真实原因归因接入产品 API 和 28766 页面；板块生命周期另经独立重建 Oracle 校验。所有候选结果标记 `CANDIDATE_RECONSTRUCTED · NOT_ACCEPTED · NON_PIT`，没有改变正式 Head，也没有将候选输出宣称为生产准入结果。

身份映射缺口只修复有充分来源合同支持的内容；本轮 12 个 5G 主题成员无法凭现存截止日前证据确定名称/上市日/稳定身份，因此明确隔离为 `UNMAPPED_QUARANTINED`，不伪造身份。

## 根因判定：严格区分四类

| 类型 | 判定 | 证据与本轮处置 |
|---|---|---|
| 设计缺陷 | 生命周期健康度的未知语义未覆盖“没有已知恶化、但比较所需输入缺失”的状态，容易把未知误报为 NONE。 | 修正为保留 UNKNOWN，并给出 `WEAKENING_COMPARISON_INPUT_MISSING`；合同版本由 1.0.0 升至 1.1.0。生产 Oracle 与候选重建 Oracle 都遵循该三态语义。 |
| 实现 Bug | 独立生命周期审计无法绑定任务指定的显式候选 Owner；板块生命周期/市场压力未进入候选页面；候选 Priority 和 Focus 对 D0/D2 的原因链不完整。 | 独立审计工具增加显式 `--candidate` 输入及来源权威标识；BFF 在板块、Priority、Focus 和个股详情接口中实际计算/提供结果，页面展示数量、排序/原因、来源和 UNKNOWN 细项。缓存键包含来源与参数摘要。 |
| 来源问题 | 5G 主题成员清单中有 12 个代码未匹配身份映射，也没有名称、稳定锚点和可核验上市日期来源。 | 交易/证券身份不具备创建稳定 ID 所需合同字段；保留隔离状态，不推断、不补造。代码为 `BJ.920021`、`BJ.920028`、`BJ.920186`、`BJ.920249`、`BJ.920556`、`BJ.920640`、`BJ.920720`、`BJ.920876`、`BJ.920924`、`BJ.920932`、`BJ.920961`、`SZ.301718`。最后一个代码虽有 2026-09-23 IPO 公告与 10-09 申购记录，但截止日前缺少可验证上市日/成员记录；9 月 30 日同期交易所清单也未列出，证据不足以创建身份映射。 |
| 客观数据/功能限制 | 市场宽度和参与度轴没有足够绑定输入；D2 冻结失效判定仍未实现；若干 D0/D2 可选输入和来源字段未知；部分 5G 身份资料没有来源。 | 对市场宽度、参与度保持 null/UNKNOWN，综合风险值不发布；D2 对 `frozen_invalidation` 返回 `UNKNOWN` / `REQUIRED_INPUT_NOT_IMPLEMENTED`，不伪造 TRUE/FALSE；明确展示其余来源及字段名。 |

## 计算与产品接入结果

### 板块生命周期与独立 Oracle

- 候选：`G:\codex_tmp\v4_daily_candidate_chain_20261020\data\v4\dynamic_daily_owners\2026-10-14\727b8c2e04b1b84d190da7da1bdae5338c3b575f94ebac4ab4f8314e624c1157\SUCCESSOR_CANDIDATE.json`，候选 token：`2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`。正式 Head 仍为 2026-10-09。
- 计算窗口：`2026-10-08, 10-09, 10-12, 10-13, 10-14`，每个会话 400 个板块实体。
- 独立 Oracle：`scripts/audit_sector_lifecycle_reconstructed_r1.py`，显式候选路径；重建与 Oracle 20/20 真实样本通过。生产者 SHA-256：`5242490bf2902b8ec9455fd4c02e17d90770536750c236d40898d977214a7029`；参数 SHA-256：`029410f237091c2aef01093346b23d6eef87ac7dc7c009082e768afe342413c3`；候选摘要：`216ffd50e1c03113ea52a7cd436b96c1b8ea0836c74084fa7504b619073ca315`。
- 成熟度分类：DEVELOPING 22、EARLY 9、MATURE 1、NONE 210、UNKNOWN 158（242/400 可判定）。
- 健康度分类：DAMAGED 113、WATCH 5、WEAKENING 108、NONE 4、UNKNOWN 170（230/400 可判定）。未知比较输入不再被错误归入 NONE。
- BFF `/api/v4/sectors?view=candidate` 返回 400 个板块及生命周期字段；候选 Priority 有 141/400 个板块可排名。

### 市场风险与 Priority 候选恢复

- 市场压力轴按 10/12–10/14 候选涨跌停回放计算，三日均为 `LOW`：
  - 10/12：5192/5224 已知，覆盖 0.993874；输入 SHA `5714e51e30ee5a43247ef901fc567ac38057f8cbf3d7362ee8e6067627f858c9`；输出 SHA `40064370bf88173a52e9eb7f1ae1e05c370c5bb3970c67caeeceeed726bdc27c`。
  - 10/13：5191/5225 已知，覆盖 0.993493，方向 `DECLINING`；输入 SHA `672474973bf3694456674cfc4b05c2aa426fa12ea11a3d0ef5a5d930b89ac677`；输出 SHA `7469538e28fb0d91d2ca736276de242fa04c7dc58bf69e8ec581fdfafba1a1af`。
  - 10/14：5191/5225 已知，覆盖 0.993493，方向 `RISING`；输入 SHA `428606f4de2bef845adb5cc3aa76c355bdbf65dec03eb9cbc078bc09e22bcf5f`；输出 SHA `8a47e118910194682688ff3177fd3ebef70251762bd7d41a5bdb969e5b33397f`。
- 三个压力轴结果来源均为 10/20 的候选回放捕获，属晚采集非 PIT。宽度轴和参与度轴没有已绑定合格数据；复合市场风险因此不可用。10/14 候选涨跌停 Owner SHA `10038767951f38df66fa387eed47f45f38f5b501b3953f4e2590285c7e62c69b`；RAW 来源 SHA `8f949e7418355e8f60dbd859598e27ad948c4cfdf9bed69b37c5f04d65db755e`。
- `/api/v4/radar/priority?view=candidate&scope=sectors` 状态 `READY`：141 个板块可排名、967 只股票可排名。页面标出候选/未接纳/非 PIT，展示压力轴、生命周期覆盖和 Oracle 样本覆盖；股票示例常山北明 `SZ.000158` Priority 11.741，并显示五项可解释理由。

### D0、D2 与 Focus 原因归因

- 2026-10-14 D0 Owner `corrected_d0_prewatch.jsonl.gz` SHA-256：`c267064c94fea087c52e21381de1bdef3076ac21077e47f41f4bf149a28d48c3`。共 5,225 行：确认 TRUE 145、UNKNOWN 5,080；`LAUNCH_CONFIRM` FALSE 5,055 / TRUE 118 / UNKNOWN 52；`RECOVERY_TURN` FALSE 5,138 / TRUE 35 / UNKNOWN 52；`STRONG_PULLBACK`、`TREND_CONTINUE` 各 5,225 行 UNKNOWN；Focus trigger 227。归因输出包含每情景原始检查、失败检查及未知原因。
- D2 Owner `corrected_d2.json.gz` SHA-256：`5e466ef0bcb3fab050fdedea4c94a12943e0503c825c8961e16f2f85cb09a8bc`。
- 与 Focus 3,247 个 episodes 交叉：D0 全部映射，TRUE 145 / UNKNOWN 3,102；D2 全部映射，TRUE 65 / UNKNOWN 3,182。Focus Owner 为 `CORRECTED_FOCUS_FORWARD.json.gz`，3,247 episodes、19,752 events；成员来源截至 10/09，为回溯重建，存在非 PIT/存续偏差风险。
- D2 未知原因包含 `frozen_invalidation:REQUIRED_INPUT_NOT_IMPLEMENTED`（该必需谓词尚未实现），以及 `dq5`、`episode_invalidation_contract_id`、`followup_complete`、`scenario` 等可选字段 UNKNOWN。个股详情示例三一重能 `SEC-00096141BD5420F5CB3120E687CDA5B9`：PREWATCH/SEED 原始判定 FALSE；CONFIRMED 和 `frozen_invalidation` 为 UNKNOWN；Owner 状态 `NOT_IMPLEMENTED` / `V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED`。UI 展示等待条件与证据，不将 UNKNOWN 降格为 FALSE。
- 接入位置：Focus API/页面提供 3,247 条 D0/D2 交叉汇总及来源按钮；个股详情接口和展开式归因区提供 D2 原因；Priority 股票候选包括资格归因。

## 浏览器功能验证

使用 Codex 内置浏览器访问 `http://127.0.0.1:28766`，没有使用本机 Chrome/Edge 等浏览器。验证页面包括 Priority 候选页、Focus 汇总和股票详情页。页面可见：候选非 PIT 状态、10/14 压力轴及覆盖、生命周期与 Oracle 覆盖、Priority 可排名数量和示例原因、Focus 的 D0/D2 交叉计数，以及股票详情的 UNKNOWN 与 `frozen_invalidation` 等等待条件。

## 定向验证

- `tests/test_sector_lifecycle_reconstructed_v1.py`：6 passed（含缺少 T−2 比较输入时 producer 与 Oracle 都返回 UNKNOWN）。
- `tests/test_v4_r6_risk_priority.py tests/test_core_product_focus_r2.py`：7 passed。
- `node --test tests/test_core_product_ui_r1.mjs`：8 passed。
- `node --check`：`app.js`、`stock.js`、`labels.js` 均通过。
- `git diff --check`：通过；仅提示 `app.js` 当前 CRLF 文件在 Git 写入时会规范化为 LF。

## 运行与数据保护边界

- 开发验证使用 `127.0.0.1:28766`，当前服务 PID 48724；生产端口 `127.0.0.1:28765` 未监听。项目 PostgreSQL `127.0.0.1:5432/market_research` 保持既有实例，本轮没有生产 PG 写入、Schema 迁移或后台采集/自动任务。
- 正式 Head、生产 28765 和生产数据写入未改变；没有部署或准入动作。
- 候选 Owner 位于 `G:\codex_tmp`，所有子进程临时目录设置在 G 盘。
- `.githooks/`、`config_back/`、`script_back/` 是既有且与本任务无关的未跟踪目录，未纳入本次提交。

## 验收与下一阶段

R6 的可计算功能已落入产品并完成定向验证；独立生命周期 Oracle 通过；候选市场风险与 Priority 结果恢复；D0/D2/Focus 原因在页面可见；身份缺口按证据边界隔离。外审所需的分类、来源摘要、限制和验收证据均已记录。

下一阶段：将本分支和本报告提交、推送，供下一轮独立外审。等待外审判定；本轮不推进正式 Head、生产数据库写入、28765 或后续阶段门禁。身份缺口需要提供截至交易日可验证的代码—名称—交易所—上市日期来源后再修复。

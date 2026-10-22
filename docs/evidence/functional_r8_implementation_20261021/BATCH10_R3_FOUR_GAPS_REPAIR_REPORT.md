# BATCH10-R3 定点修复执行报告

- 日期：2026-10-22（Asia/Shanghai）
- 合同：`BATCH10-R3-FOUR-GAPS-REPAIR/R1`
- 分支：`codex/v4-unified-development`
- 审计基线：`5cfa4c5e9793538a640749d39cf50dbe39acc8c5`；本次续作执行前 HEAD：`565da5ce1631a40c1abf875057ee51633ac95c9d`（本地与远端一致）
- 阶段 0：`DEGRADED_PASS`（沿用 R2 已封存的阶段 0 证据；不启动扫描器）
- 总结：`BATCH10_R3_PARTIAL_WITH_LANE_H_RECOVERY`

## 结果

本轮延续并保留 API 日期 envelope 修复：产品响应分开返回 snapshot token、snapshot context date、data date 和目标日期 Owner bindings。新增 UI 明确状态 `WAIT_REAL_FIRST_CAPTURE` 的处理：Lane L 计数缺失或为零时不渲染成已发布样本，缺少真实首次捕获时显示 WAIT。相关 ReadIndex/BFF/UI 回归共 46 passed。

延续时在 G 盘候选根 `G:/codex_tmp/v4_daily_candidate_chain_20261020` 对 10/21 候选 `d778e5e…368a5` 执行 ReadIndex 生产入口，为 10/19 构建 authority/member 索引；随后直接 PG ReadIndex page 读回 `READY`、5,224 行。10/21 对同 token 也读回 `READY`、5,224 行；10/20 仍返回 `READ_INDEX_DATE_NOT_PREPARED`。这只解决了该候选 token 的 10/19 authority/member 缺项，尚无按 10/19→10/20→10/21 建立的 successor/predecessor Token 链，不能代替完整 dated Owner 重基。10/20 股票 API 仍是旧 Owner 的 5,224 行。

浏览器可见验收用 in-app browser 打开 28766，Home 与 Forward 页面都加载出实际内容。10/20 Home 可见研究日期和 5,224 行股票；Forward 历史样本页显示 73,115 条，切到在线前瞻页显示 `WAIT_REAL_FIRST_CAPTURE`、采集计划 `WAIT_SOURCE_READY`，没有构造 Lane L 行。页面同时显示最近捕获失败 `SOURCE_EXECUTION_FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED`，因此真实首捕仍不具备。完整日期上下文检查仍未通过：10/20 数据仍来自旧 Owner，日/周/月、详情、搜索、分页与缓存切换尚未完成跨入口对账。

## 四项缺口状态

| 工作项 | 状态 | 本轮证据/剩余工作 |
|---|---|---|
| 10/19 ReadIndex 日期成员及 Identity authority 绑定；重基 10/20、10/21 | `PARTIAL` | 10/19 对候选 token `d778…368a5` 的 PG ReadIndex page `READY`、5,224；10/21 同 token 也 `READY`。10/20 尚未准备。没有按受影响 predecessor 顺序重建 dated Owner token 链。 |
| 10/20 RPS5 delta3 + 5,226 对象 + 正式 D0 聚合进入 Owner 链、PG 发布及读回 | `OPEN` | R3 已验证全量 Core 5,226 行（5,202 exact / 24 UNKNOWN / 0 mismatch）和正式 D0 5,226 行（141 TRUE / 5,033 FALSE / 52 UNKNOWN，独立扫描器 0 mismatch），但仍是 NON_PIT 候选文件。当前 Head/28766 10/20 Owner 仍 5,224 行；尚未将 R3 修订放入正式 successor Owner binding，也未执行新 Token 对应的 R8+D0 PG 发布及 28766 读回。 |
| Forward 历史研究 Lane H；Lane L 首次捕获 | `LANE_H_CANDIDATE_PASS` / `WAIT_REAL_FIRST_CAPTURE` | 从候选 Head 绑定的 13 个日期 raw/core/sector/lifecycle Owners 重建 73,115 条 `RETROSPECTIVE_RESEARCH`，逐日追加到隔离 Forward PG namespace；28766 statistics/API 和可见历史页读回 73,115。输入与输出均明确 NON_PIT。Lane L 的 live count 未出样，采集计划为 `WAIT_SOURCE_READY`，保持 `WAIT_REAL_FIRST_CAPTURE`。 |
| 历史日期 snapshot context、真实日期、dated Owner token 全入口统一 | `PARTIAL` | API 现为三个明确字段：snapshot token、snapshot context date、data date，并返回请求日 Owner bindings；10/20 stocks API 已实读一致。其它详情、搜索、分页、日周月图表、缓存及跨日/跨周/月切换尚未完成端到端对账。当前没有可声明的 dated Owner token 新代。 |
| 浏览器可见页面验收 | `PARTIAL` | Home/Forward 页面实际加载；Forward 历史及 Lane L WAIT 可见。10/20 full owner 重基及跨入口完整日期矩阵未做完，不能整体 PASS。使用可见 in-app browser，未绕过安全检查。 |

## 执行合同、边界和验收

本轮执行前查阅 `docs/plans/V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md`、`docs/evidence/functional_r8_implementation_20261021/S00_S06_P_S05_D_PREPARATION.md`、`docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md` 与项目 `AGENTS.md`。依赖边界继续遵循 R2 S00/S06：阶段 0 为 DEGRADED_PASS；历史来源保持 NON_PIT；不改变正式 Head、不清理历史，不根据缺失记录合成首捕或 D0 值。

开发期 PG 写入仅用于用户授权的候选 Forward Lane H；没有发布正式 Head。网页/API 端口为 `127.0.0.1:28766`，PostgreSQL 为 `127.0.0.1:5432/market_research`，未触碰 `28765`。运行实例为 `scripts/batch10r2_28766_1021_d778.py`，它使用 G 盘候选根；候选 ReadIndex/Forward schema 不代表正式接受状态。

## 下一步

下一步首先将 R3 全量 Core+D0 的精确 bytes、版本和 identity closure 接入新的 10/20 successor Owner，再重基 10/21 并生成全新 dated token；之后才发布 R8+D0 candidate、构建对应日期 ReadIndex 并逐 token 从 PG 与 28766 读回。随后完成日期切换、日周月图表、详情、搜索、分页及缓存上下文矩阵。Lane H 本批已写入候选 Forward schema；Lane L 等待真实 source-ready first capture，不能用历史重建补齐。开发结果不授予正式 Head、生产调度或 28765 权限。

机器可读结果见同目录 `BATCH10_R3_FOUR_GAPS_REPAIR_EVIDENCE.json`。

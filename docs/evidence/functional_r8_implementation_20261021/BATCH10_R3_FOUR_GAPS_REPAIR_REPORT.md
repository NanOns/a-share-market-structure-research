# BATCH10-R3 定点修复执行报告

- 日期：2026-10-22（Asia/Shanghai）
- 合同：`BATCH10-R3-FOUR-GAPS-REPAIR/R1`
- 分支：`codex/v4-unified-development`
- 执行前 HEAD：`5cfa4c5e9793538a640749d39cf50dbe39acc8c5`（与用户审计基线相同；本地/远端一致）
- 阶段 0：`DEGRADED_PASS`（沿用 R2 已封存的阶段 0 证据；不启动扫描器）
- 总结：`BATCH10_R3_PARTIAL`

## 结果

本轮修正了 API 返回缺少“请求数据日期”独立标识的问题。所有带有上下文对象的产品响应现在保留候选快照 token，同时明确返回快照上下文日期、实际数据日期和目标日期的 Owner bindings。新增回归用例证明 10/20 历史行不会被标成 10/21 数据。`tests/test_v4_ux_r2_contract.py` 定向回归为 26 passed，`git diff --check` 通过。

重启唯一开发服务后，28766 的 10/20 股票列表 API 返回 `READY`、5,224 行；响应明确区分快照 token/date（10/21 `d778e5e…368a5`）与 `data_trade_date=2026-10-20`，两行样本均为 10/20，并附有 10/20 Owner bindings。只读 PG ReadIndex reader 检查该 token/day 返回 `READ_INDEX_DATE_NOT_PREPARED`；因此此 HTTP 结果不是新 PG ReadIndex 发布/读回证据。尚未完成“dated Owner token”版本链重建或 10/19→10/20→10/21 的顺序重基。

浏览器可见验收通过安全的 in-app browser 打开 28766 并实际选择 10/20。日期控件/URL 更新为 `trade_date=2026-10-20`，页面头部显示研究日期 10/20；但内容区一直停留在“正在读取研究数据…”，因此 UI 状态为 `PARTIAL`，没有把页面记为通过。未遇到或绕过浏览器安全拒绝。

## 四项缺口状态

| 工作项 | 状态 | 本轮证据/剩余工作 |
|---|---|---|
| 10/19 ReadIndex 日期成员及 Identity authority 绑定；重基 10/20、10/21 | `PARTIAL` | 当前 28766 可读取 10/20 的 5,224 股票行和目标 Owner bindings；日期 envelope 修复已实现。没有生成新的顺序候选 Token，没有补建 10/19 ReadIndex authority/member identity，也没有重基 10/20、10/21 的 ReadIndex。 |
| 10/20 RPS5 delta3 + 5,226 对象 + 正式 D0 聚合进入 Owner 链、PG 发布及读回 | `OPEN` | R2 独立核验只覆盖 5,226 行核心，其中 5,202 exact / 24 UNKNOWN；R2 同时记录正式 D0 仅连接 5,224 个对象，仍缺两名正式 D0/prewatch 行。本轮未能产生完整 5,226 D0 Owner、未执行 PG 发布/reader 读回。不能将旧子集或压缩研究产物代称完整聚合。 |
| Forward 历史研究 Lane H；Lane L 首次捕获 | `WAIT` / `PARTIAL` | 28766 UI/上下文证据仍显示历史与 live Forward 未接入。没有能证明正式历史样本 Owner 及授权绑定的可读候选。Lane H 未接线。Lane L 必须来自真实首次捕获；当前没有符合合同的首次捕获证明，保持 `WAIT_REAL_FIRST_CAPTURE`，未伪造样本。 |
| 历史日期 snapshot context、真实日期、dated Owner token 全入口统一 | `PARTIAL` | API 现为三个明确字段：snapshot token、snapshot context date、data date，并返回请求日 Owner bindings；10/20 stocks API 已实读一致。其它详情、搜索、分页、日周月图表、缓存及跨日/跨周/月切换尚未完成端到端对账。当前没有可声明的 dated Owner token 新代。 |
| 浏览器可见页面验收 | `PARTIAL` | 通过符合工具策略的可见浏览器切换至 10/20；可见日期变更，但页面正文一直等待加载。该阻断如实记录，没有安全策略绕行。 |

## 执行合同、边界和验收

本轮执行前查阅 `docs/plans/V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md`、`docs/evidence/functional_r8_implementation_20261021/S00_S06_P_S05_D_PREPARATION.md`、`docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md` 与项目 `AGENTS.md`。依赖边界继续遵循 R2 S00/S06：阶段 0 为 DEGRADED_PASS；历史来源保持 NON_PIT；不改变正式 Head、不清理历史，不根据缺失记录合成首捕或 D0 值。

开发 PG 写入/发布权限虽已由本轮用户明确授权，但本次证据不足以构建可发布的完整 Owner/D0 与顺序 Token；故没有执行候选 PG 写事务。真实只读 PG ReadIndex 查询确认 10/20 对应索引未准备，未伪报新 PG 读回。网页与 DB listener 检查显示开发网页端口 `127.0.0.1:28766`、PostgreSQL `127.0.0.1:5432`；没有 28765 listener。网页进程重启到当前 checkout 后继续绑定原 R2 候选目录，不创建额外服务或数据库。

## 下一步

先补齐可验证的 10/20 全 5,226 身份/正式 D0 来源闭包，再按 10/19→10/20→10/21 predecessor 顺序生成新的候选 Token、ReadIndex 和 dated Owner authority；每一步完成 PG 发布前置数值/身份守恒核验。独立恢复 Lane H 历史样本源绑定。Lane L 仅在发生真实且及时记录的 first capture 后继续。随后覆盖日/周/月图表、详情、搜索、分页和缓存并修复页面持续加载问题，再完成真实 PG 读回和可见浏览器验收。阶段产物不授予正式 Head、生产调度或 28765 权限。

机器可读结果见同目录 `BATCH10_R3_FOUR_GAPS_REPAIR_EVIDENCE.json`。

# P12 生成期间页面状态修复记录

> 日期：2026-09-23；当前：`IN_PROGRESS / CONTRACT_FROZEN`。

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `P12_DAILY_DATABASE_LOCK_REPAIR_20260917.md` 的 `P12_DAILY_DATABASE_PROCESS_OWNERSHIP_REPAIR_V3`；`P12_DAILY_PAGE_GENERATION_REPAIR_V2` |
| stage_contract | `P12_DAILY_BUILD_BUSY_UI_V1` |
| scope | 生成子进程独占 DuckDB 时，保持生产数据库 API fail-closed；修复任务状态可见性与 UI 对 `503/DATABASE_BUILD_IN_PROGRESS` 的呈现和重试。不得放行并发 DuckDB 查询，不改发布身份、源数据或分析算法。 |
| evidence | 2026-09-23 M3 自动输入回执 `FULL_PASS`，目标日 `20260923`、source bundle 已封存；P12-06/P12-08e 报告绑定 publication `m4-7c36d3cc1593eff8312634e397877777` 和目标日 `2026-09-23`。P12 子进程运行期间，工作台曾返回 `BUSY/SUSPENDED_FOR_BUILD`，`/api/jobs?active=1` 却为空；首页把 503 显示成“版本列表读取失败”“研究包读取失败”。修复后，busy-lock HTTP 回归验证数据库读取仍返回 503、后台任务状态仍可查、活动计数正确；JS 语法检查通过。服务恢复后浏览器重新载入为 `READY`，首页恢复到 `2026-09-22`。当前 `/api/publications` 最新仍是 2026-09-22；P12-06 回执标记 `DEGRADED_PASS`、`production_database_written=false`，因此 9 月 23 日尚无可接受发布版本。`runtime/v2_http_errors.log` 最后修改时间为 2026-09-10，不作为本次故障证据。 |
| acceptance_result | `DEGRADED_PASS`：后端锁隔离与活动任务状态有确定性 HTTP 回归；前端忙碌重试逻辑有断言，锁释放后的页面恢复已通过浏览器验证。未在浏览器中重新制造真实生产锁，也未重放生成任务；当前生产发布仍停在 2026-09-22。 |
| next_stage | `P12_DAILY_POSTGRES_SYNC_REPAIR_20260923.md` 已完成：9 月 23 日 PostgreSQL publication、analysis snapshot head、V3.3 bundle head 已原子同步；页面已加载 2026-09-23。Focus 首个 REAL_FORWARD 进入独立 FOCUS-03 预检。 |

## 验收边界

- 生成期间所有会访问 DuckDB 的页面 API 继续返回可重试 503。
- 任务状态端点仅查内存状态，不访问 DuckDB，并能返回活动日任务。
- 页面将数据库忙碌展示为“生成中/稍后自动恢复”，不能显示为算法或数据生成失败；锁释放后自动恢复发布列表和首页读取。
- 失败/成功终态的任务状态不得被忙碌重试覆盖；重试任务状态不重复提交生成任务。

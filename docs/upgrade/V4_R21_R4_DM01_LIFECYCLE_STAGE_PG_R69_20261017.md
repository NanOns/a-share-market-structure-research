---
stage_id: V4_R21_R4_DM01_LIFECYCLE_STAGE_PG_R69_20261017
branch: codex/v4-workspace-cleanup
status: LIFECYCLE_STAGE_PG_WRITER_LANDED_MAIN_CONSUMER_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# V4 R21-R4 DM-01 lifecycle stage PG R69

日期：2026-10-17（Asia/Shanghai）。本批将 lifecycle manifest 的跨进程产物从本地 report 文件改为 DM-01 stage PG fact。

## 代码变更

- `build_v4_dm01_lifecycle_snapshot.py` 不再创建或读取 `reports/v4_dm01` 生命周期 artifact/receipt。成功时把完整 lifecycle manifest 追加为 `lifecycle_snapshot` PG stage fact；阻断/等待状态也按日期追加为阶段结果。
- CLI 输出只携带短的 PG descriptor binding 和阶段摘要；写入继续要求显式 Writer DSN 与预期数据库身份，未配置时关闭失败。
- `run_v4_dm01_daily_increment.py` 工作区改动已切换为读取精确 PG lifecycle descriptor。主编排器还保留特殊阶段及 source-freeze 等其他 report 读取，整文件不符合仓库准入，消费改动未提交。

## 验证与边界

- 生命周期入口 PG stage 接线及日更 lifecycle 构建回归：**52 passed**。
- 测试以受控 PG 边界替身验证 CLI 行为；没有 live PG 写入、TDX/BaoStock 实际采集或业务生命周期验收。
- `tools/git_repository_policy.py --staged` 对本批脚本和回归文件通过；`git diff --check` 通过。
- 没有执行真实数据库迁移、Head CAS、服务启动或部署。

## 原 266 项核对

本批脚本未匹配原清单的稳定 P1 callsite ID；即使 lifecycle writer 已写为 PG-only 代码路径，也不能据此减少正式计数。原 P1 正式完成 **0/266**，正式剩余 **266/266**；实现状态仍为 **48 项待现场/库存对账、210 OPEN、8 ingress OPEN、22 条未映射 reference edge**。

## 后续

把主编排器读取接入 lifecycle stage binding；继续映射并迁移 special-phase 与 source-freeze 的输入 Owner/PG 关系。主编排器的其余 report-backed 读取仍是准入 blocker，解决真实数据关系前不提交该编排器文件。

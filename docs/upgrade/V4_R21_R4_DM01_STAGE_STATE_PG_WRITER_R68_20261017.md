---
stage_id: V4_R21_R4_DM01_STAGE_STATE_PG_WRITER_R68_20261017
branch: codex/v4-workspace-cleanup
status: PG_STAGE_STATE_WRITER_LANDED_CONSUMER_MIGRATION_IN_PROGRESS
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# V4 R21-R4 DM-01 staged state PG writer R68

日期：2026-10-17（Asia/Shanghai）。本批先为 DM-01 分阶段执行状态建立 PG 事实合同，并接入 GBBQ revision probe 的 PG 追加。该批不代表 DM-01 完整调用链或调度业务验收。

## 实际代码

- 新增 `V4_DM01_STAGE_STATE_PG_R1`：按交易日、阶段与内容摘要追加不可变 stage fact；读取时要求精确 descriptor、阶段、日期、payload 摘要和配置的数据库身份匹配。
- 写入端复用 `ForwardFactStore`，只从显式 `V4_NATIVE_PG_DSN` 取得 writer；写入前必须设置 `V4_PG_EXPECTED_DATABASE_IDENTITY_JSON` 并与实际数据库身份相等。
- 读取端不构造写入型 Forward store；使用 `V4_NATIVE_PG_READER_DSN` 或 `WORKBENCH_PG_DSN`，在只读 repeatable-read 事务中验证数据库身份和 PG payload 摘要。没有本地 report fallback。
- GBBQ probe 现在在返回状态时附带 PG stage binding。主日更编排器读取该事实的工作区接线已完成并由隔离测试验证，但该编排器还存在其他 `reports/v4_*` 业务读取，整文件仍被仓库准入策略拒绝，尚未提交。生命周期、special-phase、source-freeze 的真实 PG 关系与读取迁移仍待完成。

## 验证与边界

- stage-state/DM-01/合同注册表选定回归：**42 passed**。其中 PG 数据边界使用受控替身，验证只读连接参数、精确日期/阶段、数据库身份与摘要处理；没有模拟出真实业务验收。
- 扩展工作区选择加入未提交的主编排器 stage-fact 消费检查后：**43 passed**。该编排器仍有其他 report-backed 读取，未纳入本批提交或本批正式验收。
- 另外直接执行的 `tests/test_operational_daily_jobs_v1.py` 遇到 16 项失败，原因均为现有 PG 调度构造要求显式 `V4_NATIVE_PG_DSN`，本环境没有写连接配置；同次另外 37 项通过。未设置伪造 DSN，未连接或写入数据库。
- 没有 live PG catalog/readback、PG 写入、合同导入、source capture、Head CAS、服务启动或外部业务验收。

## 原 266 项核对

本批新增 DM-01 stage state contract 与 GBBQ probe writer 未匹配原清单中的稳定 callsite ID；主编排器消费接线仍未准入。本批原 P1 正式完成为 **0/266**，正式剩余 **266/266**；矩阵为 **48 项代码级 PG 路径待现场对账、210 OPEN、8 ingress OPEN、22 条未映射 reference edge**。没有用 PG 代码或模拟测试减少正式计数。

## 后续

继续把主编排器与 lifecycle、special-phase、source-freeze 的跨进程状态输入从 report 文件迁移到该 stage authority 或语义等价的既有 PG Owner/源事实关系。完成这些真实读取迁移并通过仓库策略后，再提交编排器批次；随后继续 Owner/Head/BFF 实际消费者、外部 CI 与 Issue #2 / PR #3 证据更新。

---
stage_id: V4_R21R4_DM01_PG_HEARTBEAT_R14_20261017
code_sha: 2b4c4227d
test_scope: DM-01 PG progress persistence and contract registry regression suites
conclusion: heartbeat persistence SQL now includes the real PG column; live state transition remains unverified
approval_status: no PG connection or database write was attempted
---

# V4 R21-R4 R14 综合阶段报告

## 范围与结果

修复 DM-01 原生 PG `update_job_progress` 状态 upsert：`heartbeat_at` 与 `last_progress_at` 同步由数据库时钟赋值；重复阶段 upsert 更新心跳。已有 progress 表由现有 `ADD COLUMN IF NOT EXISTS` 补齐字段。测试捕获 `JobTransaction` 发出的实际 SQL，并校验 INSERT 列、冲突更新子句和参数绑定。

## 验证与计数

- DM-01 PG progress 与合同注册表聚焦测试：**20 passed**；`compileall`、`git diff --check`、矩阵 JSON 校验和暂存区策略检查通过。
- 测试只记录/检查发出的 SQL，没有实际数据库事务。PG 持久化状态、连续日任务、取消/恢复和最终 Head 读回仍未完成验收。
- 原 266 项正式 P1 完成 0、剩余 266；矩阵 OPEN 237、ACTIVE_INGRESS_ADAPTER_OPEN 8、IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION 21；未映射引用边 22。

## 下一阶段

继续实现并核对 DM-01 PG job lifecycle 与其 Head/Owner/source 输入路径，同时接入更多有精确关系映射的业务消费者。实时 PG 读回和写入仍受当前凭据缺失与授权边界阻断。

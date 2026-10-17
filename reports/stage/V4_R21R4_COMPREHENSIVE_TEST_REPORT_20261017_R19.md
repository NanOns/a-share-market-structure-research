---
stage_id: V4_R21R4_CONTRACT_APPROVAL_TIME_PROOF_R19_20261017
code_sha: 9fd3c7b24
test_scope: contract approval event proof through PG publication context and candidate BFF, registry, and membership Owner regressions
conclusion: approval occurrence/recorded times and source digest are carried and checked offline; live lifecycle remains unverified
approval_status: no PG connection or approval-event readback was attempted
---

# V4 R21-R4 R19 综合阶段报告

## 范围与结果

合同注册表读取结果新增 `approval_occurred_at`、数据库侧 `approval_recorded_at` 和 `approval_source_sha256`。PG publication reader 将三项加入 contracts context，因此进入共享 `context_token`。PG candidate BFF 要求 source SHA 等于 contract raw SHA，并验证 approval 时间戳带时区且不晚于 publication `accepted_at`。

## 验证与计数

- Registry、PG publication candidate、candidate BFF 和 membership Owner 聚焦测试：**77 passed**；`compileall`、矩阵 JSON、diff 和暂存区策略通过。
- 覆盖合法时间证据透传和审批记录晚于 accepted_at 时拒绝。测试使用 PG-shaped fake；没有实时 approval event 或业务页面读回。
- 原 266 项正式 P1 完成 0、剩余 266；矩阵 OPEN 237、ACTIVE_INGRESS_ADAPTER_OPEN 8、IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION 21；未映射引用边 22。

## 下一阶段

继续精确 Owner/业务消费和 DM-01 PG 状态/Head 输入链路迁移。实际审批生命周期和 BFF 页面验收待合规只读连接与真实 accepted publication。

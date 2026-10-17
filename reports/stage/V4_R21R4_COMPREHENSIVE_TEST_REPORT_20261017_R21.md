---
stage_id: V4_R21R4_BFF_CONTRACT_ACCEPTED_AT_BINDING_R21_20261017
code_sha: b4874514f
test_scope: contract proof/Head acceptance binding through PG candidate BFF, publication reader and registry suites
conclusion: BFF requires exact contract proof accepted_at to match Head context; live response remains unverified
approval_status: no PG connection or live BFF request was attempted
---

# V4 R21-R4 R21 综合阶段报告

## 范围与结果

PG candidate BFF 除核验审批 occurred/recorded 时间不晚于合同绑定 publication 的 accepted_at 外，还要求合同证明的 accepted_at 与选中 Head context 的 accepted_at 完全一致。这样合同版本/审批证明不能从同日期的另一 publication acceptance 搬用。

## 验证与计数

- BFF candidate、publication reader、registry 聚焦测试：**72 passed**；compile、diff、矩阵 JSON 和暂存区策略通过。
- 新测试覆盖 proof acceptance 时间戳与 Head 时间不一致时拒绝。使用 fixture，无实时 PG/BFF 证据。
- 原 266 项正式 P1 完成 0、剩余 266；矩阵 OPEN 237、ACTIVE_INGRESS_ADAPTER_OPEN 8、IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION 21；未映射引用边 22。

## 下一阶段

继续 DM-01 完整状态与 Head/source 接线以及更多精确 Owner/业务消费者迁移。实时验证依赖正确 Reader 权限和已接受的 publication 数据。

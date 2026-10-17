---
stage_id: V4_R21R4_CONTRACT_PROOF_BFF_EDGE_R18_20261017
code_sha: f7fba6ec6
test_scope: PG candidate BFF contract proof validation, publication reader, registry and membership Owner consumer regressions
conclusion: candidate BFF rejects absent or mismatched contract proof and returns publication-bound proof; live BFF remains unverified
approval_status: no live database request or publication readback was attempted
---

# V4 R21-R4 R18 综合阶段报告

## 范围与结果

在显式 PG candidate `/api/v4/current/*` BFF 边界验证 publication context 中的合同证明：合同集必须非空；每项需有合法 SHA256、版本、schema version、approval identity，并与同一响应的 publication、trade date、namespace 一致。证明缺失或不匹配时 fail closed；合法证明随候选响应返回。

## 验证与计数

- Candidate server、publication reader/contract registry、membership Owner consumer 聚焦测试：**76 passed**；`compileall`、矩阵 JSON、diff 和暂存区策略通过。
- HTTP 使用 adapter fixture，验证合同证明从候选 context 到 BFF 响应并拒绝无证明/错 namespace；没有实时 PG 调用、权限核验或业务页面验收。
- 原 266 项正式 P1 完成 0、剩余 266；矩阵 OPEN 237、ACTIVE_INGRESS_ADAPTER_OPEN 8、IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION 21；未映射引用边 22。

## 下一阶段

继续 DM-01 完整状态/Head 流与剩余精确业务和 Owner consumer。PG BFF 正式验收仍需真实 accepted publication、Reader 权限与页面数据对照证据。

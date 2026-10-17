---
stage_id: V4_R21R4_ACCEPTED_PUBLICATION_CONTRACT_IMMUTABILITY_R17_20261017
code_sha: 5cd3d7ea2
test_scope: accepted publication registry trigger static invariant, contract registry, PG publication candidate and candidate BFF suites
conclusion: historical binding exception is limited to verified NULL-to-binding backfill; live trigger behavior remains unverified
approval_status: no database trigger or migration was executed
---

# V4 R21-R4 R17 综合阶段报告

## 范围与结果

收紧合同注册表 forward migration 中的 accepted publication 更新边界。旧 ACCEPTED 行允许从 `contract_bindings=NULL` 补录经版本、digest、namespace 和审批事件校验的 binding；通过 `to_jsonb(NEW) - 'contract_bindings'` 比较整行，`accepted_at`、status 和其它现有或未来列必须保持不变。已有非空 bindings 的 ACCEPTED 行不能修改或清空 bindings。

## 验证与计数

- 合同注册表、PG publication candidate、candidate BFF 测试：**69 passed**；矩阵 JSON、`git diff --check` 和暂存区准入策略通过。
- 静态测试确认 accepted 行身份保护先于历史 NULL binding 兼容分支。未连接数据库，未执行 trigger、DDL/DML 或真实 accepted publication 更新。
- 原 266 项正式 P1 完成 0、剩余 266；矩阵 OPEN 237、ACTIVE_INGRESS_ADAPTER_OPEN 8、IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION 21；未映射引用边 22。

## 下一阶段

继续实际 Owner、其它业务和 DM-01 PG 调用链迁移。触发器真实兼容性仍需读取部署目录并在授权隔离事务中验证。

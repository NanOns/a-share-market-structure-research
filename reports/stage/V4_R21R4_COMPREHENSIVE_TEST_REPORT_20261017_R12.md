---
stage_id: V4_R21R4_CONTRACT_REGISTRY_COMPATIBILITY_R12_20261017
code_sha: 688698ec9
test_scope: contract registry lifecycle, canonical migration schema compatibility, publication candidate and candidate BFF suites
conclusion: offline compatibility checks pass; live catalog and migration acceptance remain open
approval_status: no authorization for PG DDL/DML, PG write, or Head switch
---

# V4 R21-R4 R12 综合阶段报告

## 范围

修正合同注册表迁移草案的 PostgreSQL SHA-256 依赖，并将其列名假设与规范 V4 PostgreSQL 迁移 001/003 对照；补充审批、撤销事件的历史时间边界和 schema 兼容回归断言。

## 验收结果

- `tests/test_v4_contract_registry_pg_v1.py`、`tests/test_v4_pg_publication_candidate.py`、`tests/test_v4_server_pg_candidate_mode.py`：68 项通过。
- 合同字节校验改为内置 `sha256(bytea)`；规范迁移 023 已使用同一内置函数，草案不再要求扩展安装权限。
- 草案所用 `revision_no`、`model_namespace_id`、`accepted_at` 与命名空间列已对照规范迁移 001/003 源码验证。
- 本轮没有连接 PostgreSQL、读取实时目录、执行 DDL/DML、采集外部数据或切换 Head。当前环境没有 `pglast`，本轮 SQL 解析器检查未运行；以上是仓库迁移链与离线模拟调用测试证据，不代表实际数据库验收。
- 原 266 项正式 P1 完成 0，剩余 266；矩阵状态保持 OPEN 237、ACTIVE_INGRESS_ADAPTER_OPEN 8、IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION 21；未映射引用边 22。没有根据离线测试减少正式计数。

## 下一阶段

继续接通 DM-01 实际 PG 状态与其余精确业务调用点。身份 Owner 的字段映射及独立来源验收仍需对应合同/授权；PG 实际迁移和业务读回仍需合规只读/写入凭据及已批准写入窗口。

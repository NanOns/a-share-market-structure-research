---
stage_id: V4_R21R4_CONTRACT_REGISTRY_PREFLIGHT_R13_20261017
code_sha: 35f3b4d1a
test_scope: read-only registry catalog preflight contract, contract registry lifecycle, publication candidate and candidate BFF suites
conclusion: offline preflight contract passes; no live catalog evidence collected
approval_status: preflight is read-only; no live database operation was authorized or attempted
---

# V4 R21-R4 R13 综合阶段报告

## 范围与结果

新增只读 PostgreSQL 目录预检 SQL，限定在 `REPEATABLE READ READ ONLY` 事务内，通过系统目录检查规范 publication/namespace 列、内置 `sha256(bytea)`、注册表对象和 binding trigger 是否存在；检查 reader 的读写权限，并汇总 publication 状态与 accepted_at 数量。预检不读取合同原文，注册表尚未迁移时能报告对象缺失。

## 验证与计数

- 合同注册表、PG publication candidate、candidate BFF 聚焦测试：**69 passed**；矩阵 JSON 校验和 `git diff --check` 通过；暂存区策略检查通过。
- SQL 只读边界由静态测试验证；当前环境未配置合规 PG Reader DSN，因此没有执行该目录预检或取得实时 schema 证据。
- 原 266 项正式 P1 完成 0、剩余 266；状态 OPEN 237、ACTIVE_INGRESS_ADAPTER_OPEN 8、IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION 21；未映射引用边 22。无基线调用点因此关闭。

## 后续

继续 DM-01 状态迁移、Owner/Head 读取和精确业务消费者源码接线。取得合规只读 DSN 后先执行该预检；实际 PG 写入仍须明确授权和经批准的写入窗口。

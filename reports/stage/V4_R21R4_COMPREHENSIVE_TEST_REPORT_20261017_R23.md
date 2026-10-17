---
stage_id: R21_R4_CONTRACT_REGISTRY_XML_ENCODING_GUARD_R65_20261017
code_sha: 6ab928e10
test_scope: Contract registry readers, SQL compatibility parser and selected V4 PG/consumer workflow suite
conclusion: XML DTD and ENTITY declarations are rejected in byte, UTF-8, UTF-16 and UTF-32 forms
approval_status: No live PG catalog or approval event readback was attempted
---

# V4 R21-R4 R23 综合阶段报告

## 范围与结果

合同注册表两个 Reader 入口原先只搜索 ASCII 字节。UTF-16/UTF-32 内的 NUL 字节可绕过 DTD/ENTITY 检查。本批加入统一检查，先核原始字节，再解码 UTF-8、UTF-16、UTF-32 常见形式并拒绝声明；注册表 SQL、审批排序、publication binding 和数据库状态未改动。

## 验证与计数

- 合同注册表和 SQL 聚焦回归 **25 passed**，覆盖 UTF-8 DTD、UTF-16 DTD、UTF-32 ENTITY。
- 仓库当前选定 V4 PG/消费者回归 **309 passed**。
- 无 live PG catalog/read/write、审批事件读回或业务验收；测试使用受控 Reader fixture。
- 原 266 项完成 **0/266**，剩余 **266/266**；矩阵保持 OPEN **210**、PG 代码待实时核对 **48**、Ingress **8**、Open 或 Ingress **218**、未映射边 **22**。此 Reader 安全修复不关闭基线行。
- R64 修复后 Push/PR CI 已成功：`39024797612`、`39024801715`；R65 CI 待本批推送后记录。

## 下一阶段

在只读 catalog 许可下继续审批状态和 SQL 兼容 reconciliation，同时持续迁移真实 PG 消费者；不得以 SQL parser 或 Reader fake 替代实时数据库验收。

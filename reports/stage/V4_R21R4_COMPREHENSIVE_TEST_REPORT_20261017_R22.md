---
stage_id: V4_R21R4_BAOSTOCK_RUNTIME_ACCEPTANCE_PG_R64_20261017
code_sha: 1b86d06b7
test_scope: Runtime acceptance PG adapter, BaoStock capture wiring, contract registry and daily executor selected V4 PG/consumer workflow suite
scope: Date-bound BaoStock V1 runtime acceptance record and active daily capture reader
conclusion: PG-only-by-default runtime acceptance consumer is wired; full operational daily consumer chain remains incomplete
approval_status: No live PG access or PG write attempted; no business acceptance claimed
---

# V4 R21-R4 R22 综合阶段报告

## 范围与结果

R64 为 BaoStock DailyUpdates 验收清单建立按交易日唯一键的 append-only PG 事实；采集入口默认从只读 PG 连接读取，并校验数据库身份、事实/清单摘要、烟测回执绑定、目标日、SDK 指纹、认证模式和方法集合。生产入口默认不回退本地验收清单。验收生产器仅在显式 `V4_NATIVE_PG_DSN` 下写入，本轮没有连接写库。PG 记录支持 V1 清单以及 V2 零变化证明和逐证券精确空响应。

PG 记录和校验器也支持 V2 零变化证明及逐证券精确空响应。执行器尚未切换到该 PG 事实，仍走本地 runtime manifest/native response、source freeze 和 accepted Head 路径；本批不替代其完整调用链。

## 验证与计数

- 聚焦回归 **9 passed**；仓库 CI 当前选定的 V4 PG/消费者完整回归 **306 passed**，含受控 PG-shaped Reader、身份/摘要拒绝、V1 入口接线、V2 零变化证明和执行器回归。
- 业务源码文件读取审计及校验 PASS：扫描 **1,430** 个调用点，仍有 **176** 个 Owner 文件读取、**238** 个 P1 发现待迁移；审计 JSON 保存在 G 盘临时目录，不进入 Git。
- 无 live PG catalog/read/write、BaoStock 采集、烟测、Head CAS 或端到端业务验收。
- 原 266 项完成 **0/266**，剩余 **266/266**；矩阵计数保持 OPEN **210**、PG 代码待实时核对 **48**、Ingress **8**、Open 或 Ingress **218**、未映射引用边 **22**。本批没有独立匹配的原基线 ID，未据单元测试减少正式计数。
- 前批 R63 Push CI `39023921836`、PR CI `39023924531` 均成功；R64 CI 待推送后记录。

## 下一阶段

把执行器接到按日 PG runtime fact，迁移 source freeze 与实际 accepted Head 并对账 V2 证明链，随后继续剩余 Owner/其他业务读取；逐 ID 对账之前保持所有正式基线项未关闭。

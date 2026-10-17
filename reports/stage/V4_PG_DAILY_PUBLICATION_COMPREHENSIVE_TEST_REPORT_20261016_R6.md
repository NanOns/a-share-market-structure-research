---
stage_id: V4_PG_DAILY_PUBLICATION_R6_20261016
baseline: 2a51b12e096df3213a3fdcac0295bf5f7870524a
code_sha: c62bb2e92
test_scope: core-completeness-readback-candidate-binding-039-runner-compatibility-owner-workspace-page-boundaries
conclusion: CODE_PATHS_VERIFIED_LIVE_PUBLICATION_BLOCKED
approval_status: CODE_ONLY_REPAIR_AUTHORIZED
---

# V4 PG 日发布 R6 阶段报告

## 范围与改动

按 R11 审计结论修复 Core 完整性和 Candidate/Head 状态矛盾。新增版本化规则 `V4_DAILY_COMPLETENESS_R1/1.0.0`；Core 行数必须与 exact TDX package fact/manifest 中固化的正数 `record_count` 相等，并满足价格字段和唯一性规则。PG readback 重算完整性。来源/PIT 证据由 PG Reader 从 publication consumed sources、source revisions、source packages 与 package facts 联接后重建；Core typed readback、完整性 PASS 和相同 publication/source manifest 身份一并作为候选发布资格。Candidate 未持有真实 typed proof 时继续阻断。

修复迁移执行器“遍历整个 SQL 目录但只登记部分 migration”的不兼容；改用显式登记集，并登记 `010 R1` 与 `034–039` 依赖序列。新增 `039` 对新建 TDX package fact 的 record-count/manifest 一致性进行 SQL 门禁。完整合同、页面映射与 PG 迁移前方案见 [R6 design contract](../../docs/design/V4_PG_DAILY_PUBLICATION_REPAIR_R6_20261016.md)。

## 验收

- Core、Candidate、Owner、source-manifest、静态迁移/SQL 兼容、日更 producer bridge、Reader、七路候选 HTTP 等 CI 定向集合：**154 passed**（最终复核通过）。
- 正向测试由 completeness PASS、PG 形状的独立 Source/PIT 证明、typed Core readback 一起构建真实 publishable Candidate 并到达 `INSERT_IF_ABSENT` Head plan；反向测试覆盖缺合同、伪造 mapping、错误摘要、Source/PIT 不符、完整性声明不符和读事务不合规。
- 既有 Reader 12 项、390 文件绑定和七路候选 HTTP 测试包含在本轮集合；代码路径无回退。未运行全仓测试。
- 用 `WORKBENCH_PG_DSN` 只读事务确认身份 `market_research@127.0.0.1:5432`；ledger 12 项。Live `publications`/`heads` 为空，缺 source-package facts、Core snapshot/rows、Owner binding、sector-membership relations；`publications` 缺 source-manifest contract 列。Reader 当前连接角色为超管 `postgres`，按合同拒绝。28765/28766 无监听。
- 因缺失实际 source/PIT authority、Core schema/数据和合规 Reader，真实 PG positive publication 与真实七页读回仍 blocked。迁移没有执行；数据库写入、Head、服务与生产保持未变。

## 范围结论与下一阶段

`CODE_PATHS_VERIFIED_LIVE_PUBLICATION_BLOCKED`。已证明代码可由真实检查结果生成正向资格，也证明伪造/缺证据时失败关闭；fixture 不代表 live PG acceptance。迁移前授权方案已具体记录，但当前状态为 `BLOCKED_PREFLIGHT_RECONCILIATION_AND_LEAST_PRIVILEGE_ROLE`。下一阶段须先解决 catalog/ledger 漂移和迁移角色，再取得可接受的来源/PIT package 与实际 producer→PG 数据；PG migration、accepted Head、28765 发布继续分别授权。

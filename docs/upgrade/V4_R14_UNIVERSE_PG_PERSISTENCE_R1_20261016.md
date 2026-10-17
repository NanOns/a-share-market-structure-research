# V4 R14 — Universe PG 持久化与发布资格绑定 R1

日期：2026-10-16。基于 R13 `V4_MARKET_UNIVERSE_COMPLETENESS_R1` 与新日发布 R3/PIT 合同；不更改交易日时钟或 R2 历史读边界。

## 实施合同

- `v4_universe_pg_r1.build_universe_persistence_plan()` 只接受经现役 R3 接收器验证的 source package、精确原始 JSON bytes、同 T0 `security_universe` fact 和 Core 行。`source_fact_sha256` 必须等于提供的原始文件 SHA-256，fact locator 同时绑定 Universe id/digest/全行数；同一 Core 文件派生的分母不能自证完整。
- `persist_universe_snapshot()` 仅使用调用方事务；要求显式 `V4_NATIVE_PG_DSN`、精确 Writer 角色、匹配 CANDIDATE Publication、同一被消费的 `security_universe` source revision、签名包事实和一致计划摘要。它不连接、不提交、不接受 Head。完全相同身份重放幂等；同身份不同摘要拒绝。
- `read_universe_snapshot()` 必须在 `READ ONLY + REPEATABLE READ` 事务，且 Reader 角色无写权限。它重读同一 Publication/source revision/package fact、签名回执及全部证券/对账行，重算规范 Universe 摘要、分母覆盖及对账摘要；只在完整 PASS 时发出私有令牌 `VerifiedUniverseReadback`。Mapping/status/digest 自报或附件文件不能构造此能力。
- Core `VerifiedDailyCoreResult` 回执现在绑定 Universe digest、完整对账计数、Universe readback receipt digest；缺表/缺读权限/未批准签发者保持 BLOCKED，事实不匹配输出 FAIL。Candidate 和 Head planner 对新 T0 检查该封闭 Core typed proof，不接受伪造 Universe PASS。
- `042_market_universe_persistence_r1.sql` 是 append-only 前向迁移草案，按完整文件名在 `scripts/apply_v4_phase0_schema.py` 注册。记录原始来源绑定、Universe/逐证券行、逐证券 Core reconciliation、行数和摘要，并为 R3 生效日起的 accepted Publication 增加 Universe 存储门。未运行、未做 PG 编译。

## 发布范围

现存 Universe 评价仍要求明确 SSE/SZSE/BSE scope；其完整三市场结果才能成为 publishable PASS。任何缺少可核实覆盖的市场只能保留诊断/研究限制，不能删减母集后称 full-market。停牌、上市、退市/代码迁移和未知身份逐行留痕；未知身份或缺失/多余 Core 行阻断。

## 验收边界

代码及合成/伪造防护测试可证明算法、类型闭合和 fail-closed 分支；不能证明 042 已在 PostgreSQL 编译、实际 writer/readback、真实签名 issuer、真实 T0 Universe 或正式发布资格。具体状态见本批 R14—R18 综合报告。

# Focus Outcome 合同测试漂移审计

> 独立审计项；不并入 FOCUS-05 阶段门。

| 字段 | 记录 |
|---|---|
| audit_id | `FOCUS_OUTCOME_TEST_DRIFT_AUDIT_20260923` |
| scope | FOCUS-00 outcome 分类合同、对应单元测试与 V2.1 §15.3/§17.2 数据缺口终态规则；不改结算 schema 或运行时分类算法 |
| evidence | `python -m pytest tests/upgrade_v3 -q -k focus` 曾得到 55 passed、1 failed。失败测试 `test_outcome_uses_fixed_session_and_audited_gap_statuses` 对 `INFERRED_GAP` 调用未提供 `gap_audit_digest`，却预期 `DATA_GAP`。当前 `FOCUS_ANCHOR_OUTCOME_V2` 只有在 accepted + sealed 且提供 64 位有效 audit digest 后，才把缺 BAR / 中间路径缺口判为终态；无审计摘要返回 `PENDING/TARGET_STATUS_UNRESOLVED`，符合最终设计 §15.3 和 §17.2。 |
| change | 修正该测试，使终态样例提供审计摘要，并明确增加缺少审计摘要时仍为 PENDING 的反例。运行时分类逻辑不变。 |
| acceptance | 定向 FOCUS 测试通过；最终测试明确覆盖有审计与无审计两侧。此接受只代表分类单元合同一致，不代表真实 settlement 数据源一定能生成有效 audit digest。 |
| remaining | FOCUS-04 仍需独立验证 PostgreSQL settlement 输入完整性、gap audit digest 来源和终态写入事务；此项证据独立于 FOCUS-05。 |
| status | `TEST_CONTRACT_ALIGNED / SETTLEMENT_INTEGRATION_AUDIT_OPEN` |

# V4-05 Accepted Head Promotion + V4-06 Entry Authorization

Starting HEAD：`06f1c0fd4a60e4f37e5f93fe729c84a04205c16b`

## 权威结论

V4-05 已完成独立外部终验：

`V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2`

本任务仅做：
1. 创建 V4-05 Accepted Head
2. 更新 Global Accepted Head
3. 独立验证 promotion
4. 授权 V4-06 入场

禁止在本任务里开发 V4-06 业务逻辑。

## 1. 创建正式 Accepted Head

创建：

`data/v4/V4_05_ACCEPTED_HEAD.json`

至少记录：

- stage = `V4-05`
- status = `DATA_FACTOR_REPLAY_DEGRADED_PASS`
- external_acceptance = `EXTERNALLY_ACCEPTED`
- external_acceptance_decision = `V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2`
- accepted candidate = `V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_2`
- target_trade_date = `2026-09-28`

## 2. Capability scope 必须完整

必须保留：

- CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS
- WEEKLY_PERIOD = DEGRADED_PASS
- MONTHLY_PERIOD = DEGRADED_PASS
- PURE_CORE_FACTORS = DEGRADED_PASS
- MARKET_REFERENCE = FULL_PASS
- MARKET_REGIME = DEGRADED_PASS
- CURRENT_FORWARD_STOCK_CORE = DEGRADED_PASS
- HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE

不得把历史 blocker 静默改成 PASS。

## 3. Accepted artifacts

绑定：

Period：
`reports/v4_05/staging/V4_05_R4_1_PERIOD_ASOF.jsonl.gz`
SHA `e54674e8459e1258610639d76fac7a5f7b6093a4013f912b8937fb6fa96c2233`

Factors：
`reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz`
SHA `17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48`

Core Profile：
`reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz`
SHA `9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0`

Core logical digest：
`d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`

Market snapshot id：
`92773afba01ac100c9165190423d0228c2b5f9a42549ef8f4d955eba904c3cdb`

Market Reference values：
- `-0.022314506957301243`
- `-0.03792535346523633`
- `-0.01769091161662751`

Market Regime：
`trend_axis=UNKNOWN`

## 4. Bind R4.2 G08

必须绑定：

`reports/v4_05/V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json`

要求：
- `all_exact_bindings_match=true`
- `old_r4_binding_count=0`

绑定：

`reports/v4_05/V4_05_R4_2_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json`

要求：
- PostgreSQL 18.6
- 12 migrations
- I01-I05 all PASS
- `production_connection_used=false`
- state logical digest = `d1955187...`

## 5. Bind determinism / restore

继续绑定：
- R4.1 canonical hash policy
- R4.1 accepted-head hash validation
- R4.1 clean-clone determinism
- R4.1 published LFS restore
- R4.2 clean checkout runtime

Promotion 时不得重算业务 artifacts。

## 6. 更新 global stage head

更新：

`data/v4/V4_STAGE_ACCEPTED_HEAD.json`

必须变为：

`V4_00_TO_V4_05_ACCEPTED`

并新增：

- `v4_05_status`
- `v4_05_external_acceptance`
- `v4_05_binding`

保留所有 V4-00~04 既有 bindings。

## 7. V4-08 blocker 不得解除

继续保留：

`v4_08_sector_entry = BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION`

V4-05 PASS 不得自动解锁 V4-08。

## 8. V4-06 只授权、不开发

Promotion validator PASS 后允许新增：

`v4_06_entry = AUTHORIZED_SUPPLEMENTAL_ENRICHMENT`

但禁止：
- 创建 V4-06 正式业务 artifact
- 实现 enrichment
- 开始 V4-07
- 开始 V4-08

## 9. 独立 promotion validator

必须独立验证：

1. 外部验收 decision 精确匹配
2. candidate manifest SHA/bytes 匹配
3. accepted artifact SHA 匹配
4. exact binding = true
5. old_r4_binding_count = 0
6. current-forward scope 完整
7. historical blocker 保留
8. V4-08 blocker 保留
9. global head 只前移到 V4-05
10. V4-06 only authorized
11. V4-07/V4-08 未启动
12. LFS remote restore 可用

## 10. Required outputs

至少：

- `data/v4/V4_05_ACCEPTED_HEAD.json`
- `reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json`
- `reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json`
- `docs/evidence/V4_05_ACCEPTED_HEAD_PROMOTION_AND_V4_06_ENTRY_20260929.md`

## 11. Terminal state

成功后：

`V4_05_ACCEPTED_HEAD_PROMOTION_PASS_R1`

并明确：

- V4-05 = EXTERNALLY_ACCEPTED
- DATA_FACTOR_REPLAY_PASS = DEGRADED_PASS(current-forward scope)
- V4-06_ENTRY = AUTHORIZED
- V4-07 = NOT_STARTED
- V4-08 = BLOCKED

完成后停止，等待下一轮外部审计。

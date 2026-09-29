# V4-05 Replay Gate A R4.2
## Exact Candidate PostgreSQL Ledger Binding Closure

**Starting HEAD：** `f1e3d2ee4721e4880c043e8ca949e7c1e47dce41`

## 唯一目标

关闭：

`POSTGRES_LEDGER_TESTED_R4_NOT_R4_1_EXACT_IDENTITY`

禁止重新开发 R4.1 已通过能力。

## 1. PostgreSQL G08 必须读取 R4.1 candidate

正式 baseline source 必须改为：

- `reports/v4_05/V4_05_R4_1_PERIOD_ASOF.json`
- `reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json`
- `reports/v4_05/V4_05_R4_1_FULL_SCOPE_FACTORS_RECEIPT.json`
- `reports/v4_05/V4_05_R4_1_CORE_PROFILE_REPLAY.json`
- `reports/v4_05/V4_05_R4_1_MARKET_REGIME.json`
- `reports/v4_05/V4_05_R4_1_MARKET_SNAPSHOT_IDENTITY.json`

LFS artifact：

- `V4_05_R4_1_PERIOD_ASOF.jsonl.gz`
- `V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz`
- `V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz`

正式 G08 baseline 禁止再绑定 `V4_05_R4_*`。

## 2. Required Exact Identities

Core Profile：

- logical digest = `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`
- artifact SHA = `9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0`

Full Scope Factors：

- logical digest = `0cfe708567935726f0ad51ae4bb47237ec7aee556db3437c12f21f0c623bd0d2`
- artifact SHA = `17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48`

Market Reference 1-session output digest：

`80d8ac5cc69e8ae4d165f89324e45d0cc7e49a81d13339b31ff8fbec5e578554`

## 3. Cross-Binding Assertions

正式断言：

- ledger `CORE_PROFILE` digest == R4.1 artifact SHA
- ledger `FULL_SCOPE_FACTORS` digest == R4.1 artifact SHA
- ledger `PERIOD_ASOF` digest == R4.1 artifact SHA
- ledger `MARKET_REFERENCE` digest == canonical R4.1 market reference identity
- state head logical digest == R4.1 Core Profile logical digest
- publication head state logical digest == R4.1 Core Profile logical digest

任一命中旧 R4 identity：

`FAIL_OLD_R4_IDENTITY_BINDING`

## 4. 保留现有 PostgreSQL 框架

继续使用：

- PostgreSQL 18.6 isolated cluster
- 12 formal V4 migrations
- production_connection_used=false

重新执行：

- I01 identical replay
- I02 changed source revision
- I03 negative guards
- I04 rollback
- I05 prior-state freeze

无需重写测试框架。

## 5. 新增 Candidate Binding Receipt

生成：

`reports/v4_05/V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json`

至少记录：

- candidate manifest path/SHA
- R4.1 core/factor/period/market receipt identities
- actual PostgreSQL consumed-source identities
- actual state logical digest
- exact binding comparisons
- `all_exact_bindings_match=true`
- `old_r4_binding_count=0`

## 6. Regression Guard

新增测试，禁止正式 G08 baseline source 再引用：

- `V4_05_R4_CORE_PROFILE_REPLAY.json`
- `V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json`
- `V4_05_R4_MARKET_REFERENCE.json`
- `V4_05_R4_PERIOD_ASOF.json`

这些旧文件只允许用于历史 diff，不允许进入 baseline publication source manifest。

## 7. B05 不重开

当前以下均视为已通过：

- canonical JSON hash
- historical CRLF compatibility
- clean-clone deterministic rebuild
- published LFS restore

除非新测试发现真实错误，否则禁止重做或改语义。

## 8. Business Freeze

必须继续满足：

- `business_field_changes=0`
- `state_changes=0`
- `unexpected_business_value_drift=0`
- target identities = 5222
- Market Reference 数值不变
- `trend_axis=UNKNOWN`

## 9. Runtime

在 clean checkout/fresh clone 上至少运行：

- exact candidate binding test
- PostgreSQL I01-I05
- full required pytest suite

并披露 skipped test names/reasons。

## 10. Accepted Head Discipline

仍禁止：

- 创建 `data/v4/V4_05_ACCEPTED_HEAD.json`
- 修改 global stage head 为 V4-05 accepted
- 正式启动 V4-06/V4-07

完成后仍：

`external_acceptance=PENDING`

## 11. Expected Terminal State

`V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_2`

保持：

- `CURRENT_FORWARD_STOCK_CORE=DEGRADED_PASS`
- `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE=BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

下一轮如 exact binding、I01-I05、runtime、head discipline 全通过，目标：

`V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2`

随后才执行：

`V4-05 Accepted Head Promotion + V4-06 Entry Authorization`

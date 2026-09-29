# V4-05 Replay Gate A R4.2 独立外部终验

仓库：`NanOns/a-share-market-structure-research`  
分支：`codex/v4-system-reform`  
Reviewed HEAD：`06f1c0fd4a60e4f37e5f93fe729c84a04205c16b`  
审计日期：2026-09-29

## 唯一总状态

`V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2`

V4-05 Replay Gate A 在当前合同 §52B capability-scoped 语义下可以正式外部接受。

正式 scope：

- `CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS`
- `WEEKLY_PERIOD = DEGRADED_PASS`
- `MONTHLY_PERIOD = DEGRADED_PASS`
- `PURE_CORE_FACTORS = DEGRADED_PASS`
- `MARKET_REFERENCE = FULL_PASS`
- `MARKET_REGIME = DEGRADED_PASS`
- `CURRENT_FORWARD_STOCK_CORE = DEGRADED_PASS`
- `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

这里的 `DATA_FACTOR_REPLAY_PASS` 是明确 scope 内的 DEGRADED 成功，不代表历史 AS_RECORDED 已通过。

## R4.2 exact candidate binding

上一轮唯一 blocker：
`POSTGRES_LEDGER_TESTED_R4_NOT_R4_1_EXACT_IDENTITY`

本轮已关闭。

PostgreSQL baseline 已绑定当前 R4.1 candidate：

Core Profile：
- artifact `9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0`
- logical digest `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`

Full Scope Factors：
- artifact `17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48`
- logical digest `0cfe708567935726f0ad51ae4bb47237ec7aee556db3437c12f21f0c623bd0d2`

Period：
- artifact `e54674e8459e1258610639d76fac7a5f7b6093a4013f912b8937fb6fa96c2233`

Market Reference：
- canonical identity `7ba19ea03c8cab1858de98f898463cd0257577d118b227b9c1c3a09271d2bc98`
- 1-session output digest `80d8ac5cc69e8ae4d165f89324e45d0cc7e49a81d13339b31ff8fbec5e578554`

Market Regime：
- canonical identity `f72aad70b030c6de1a81000c11bcf41737585c350f5b27a4664ee59b25de9a9f`

Market Snapshot：
- canonical identity `95fa5b98f232b50abed2488e27c9566af31a3f2c3d9292cbca8450a8ae8f3bca`
- target snapshot id `92773afba01ac100c9165190423d0228c2b5f9a42549ef8f4d955eba904c3cdb`

正式证据：
`reports/v4_05/V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json`

结果：
- `all_exact_bindings_match = true`
- `old_r4_binding_count = 0`

## PostgreSQL G08

环境：
- PostgreSQL 18.6
- isolated temporary cluster/database
- `production_connection_used=false`
- 12 formal V4 migrations

I01-I05：
- identical replay PASS
- changed source revision PASS
- negative guards PASS
- transaction rollback PASS
- prior-state freeze PASS

State/Publicaton Head 均绑定：
`d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`

`G08 = PASS`

## Runtime / clean checkout

Fresh checkout head：
`1a88fcba876e619e45584964cc11fde48b1883f8`

结果：
`428 passed, 2 skipped in 6.69s`

两个 skip 均为 Windows symlink creation unavailable，不是业务/算法/数据库失败。

R4.2 regression test：
`tests/v4_05/test_v4_05_r4_2_exact_candidate_binding.py`
通过，并禁止正式 G08 baseline 回退到旧 R4 artifact identity。

## LFS / accepted chain

R4.2 为 clean checkout 补齐了 accepted-chain LFS 输入。

关键 accepted hashes 与 LFS OID 一致：
- Daily `d8e2202f00909ade115315aefe92c810ba5e96f0520472e799da21390ea0ad90`
- Weekly `8eda09c0ca55b986cbebe0aa32454a22835492a6286c1237473c729ea2af0294`
- Monthly `790ae9dd13bc363c431b2a7d02e3c6db868bc5d0b3d85a8c9a2acbd5dfd90ff3`

V4-03 Final Stage Receipt 被转为 LFS pointer，但 OID：
`678c0a47913820e0ad945da4ece429be7836ba31583986a9e23280e2ec904649`
与 V4-03 Accepted Head 的 frozen SHA 一致。

这是存储形态迁移，不是业务内容改写。

## Business freeze

保持：
- target date `2026-09-28`
- target identities `5222`
- Core Profile rows `5222`
- `business_field_changes=0`
- `state_changes=0`
- `unexpected_business_value_drift=0`

Market Reference：
- 1d `-0.022314506957301243`
- 3d `-0.03792535346523633`
- 5d `-0.01769091161662751`

Market Regime：
`trend_axis=UNKNOWN`

## Replay Gate A 总门

| Gate | 结果 |
|---|---|
| G01 Source identity | PASS |
| G02 Universe boundary | PASS_WITH_SCOPED_HISTORICAL_LIMIT |
| G03 Adjustment reproducibility | PASS_CURRENT_FORWARD / HISTORICAL_BLOCKED |
| G04 Daily deterministic | PASS |
| G05 Weekly/Monthly AS-OF | PASS_WITH_FIELD_LOCAL_UNKNOWN |
| G06 Factor replay/source-date | PASS_WITH_BOOTSTRAP_UNKNOWN |
| G07 Core Profile deterministic | PASS_WITH_FIELD_LOCAL_UNKNOWN |
| G08 Revision idempotency | PASS |

合同 §52B 明确允许：当前 TDX/adjustment 通过但历史不完整时，当前 Core、完整窗口算法和当日起 Forward 可以继续；缺证据历史 adjusted 输出仍禁止。

因此：
`DATA_FACTOR_REPLAY_PASS = DEGRADED_PASS(current-forward scope)`

## Accepted Head discipline

当前：
- `data/v4/V4_05_ACCEPTED_HEAD.json = ABSENT`
- global stage head 仍为 `V4_00_TO_V4_04_ACCEPTED; V4_05_NOT_ACCEPTED`
- V4-06 未正式启动
- V4-07 未正式启动
- V4-08 未正式启动

候选没有越权 promotion。

## 最终结论

`V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2`

允许执行：
`V4-05 Accepted Head Promotion`

Promotion validator PASS 后：
`V4-06 Supplemental Enrichment Entry = AUTHORIZED`

同时必须继续保留：
`V4-08 Sector Entry = BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION`

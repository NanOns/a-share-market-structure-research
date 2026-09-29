# V4-05 Replay Gate A R4 独立外部验收审计

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**Reviewed HEAD：** `e751c9dc63ba6e6325b50daa15e849091e18f5dc`  
**R4 Implementation Commit：** `0e5b7585c5bd1e332ce6d11c6dfd1e4ff6cb6108`  
**R4 Artifact Commit：** `569b55862cd6115bc4456ccfb0ee7e98ee42da42`

## 唯一总状态

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R4`

R4 已经真实关闭上一轮多数问题，但仍有两个工程级阻断：

- `B03-R4`：G08 未在已接受 V4 PostgreSQL publication/revision schema 上执行。
- `B05-R4`：governance text hash 域受 Windows working-tree 字节表示影响，clean-clone cross-environment determinism 未闭环。

这两项都与真实市场样本等待无关，属于当前即可修复的工程验收问题。

## 已通过项

### B01 PERIOD_ASOF：PASS
R4 已恢复 `period_view` 只表达 `CLOSED_ONLY / AS_OF_PARTIAL`。QFQ 不可用时由 `period_status=BLOCKED_BY_ADJUSTMENT` 和 `adjusted_quality=UNKNOWN` 表达，不再出现 R3 的 `period_view=BLOCKED`。

R4 period artifact：
`reports/v4_05/staging/V4_05_R4_PERIOD_ASOF.jsonl.gz`  
SHA256：`e54674e8459e1258610639d76fac7a5f7b6093a4013f912b8937fb6fa96c2233`  
rows：`694692`

### B02 Market identity：PASS
R4 start-universe snapshot identity 已恢复 accepted V4-03 强度，绑定：
`security_id + membership_basis + source_revision_id + eligibility_status`。

Sep-28 target snapshot：
- member_count = `5222`
- snapshot id = `92773afba01ac100c9165190423d0228c2b5f9a42549ef8f4d955eba904c3cdb`

Adjustment basis 已改为实际 evaluable endpoint 的：
`security_id + coordinate_basis + frozen GBBQ + raw package identity`。

1/3/5 session Market Reference 独立复算全部匹配。

### Market Path / Regime：PASS with scoped degradation
R4 正确选择 `OPTION_C_FAIL_CLOSED`，没有强行续接 Sep-24 accepted path。  
`target_path_row_published=false`，`trend_axis=UNKNOWN`。  
25-session current-coordinate path 仅作 diagnostic，不改写 accepted V4-03 path。

### R3→R4 drift：PASS
- R3 rows = 5222
- R4 rows = 5222
- same ID set = true
- `business_field_changes=[]`
- `state_changes=[]`
- `unexpected_business_value_drift=0`

### Independent numeric postcheck：PASS
65 个实体，覆盖四板块与：
`normal_ready / no_T0_bar / adjustment_unknown / short_history / code_change / boundary_like_return_tail`。

独立复算：
`ret1/5/20, ma20/60, atr20, amount_ratio20, rps5/20, rel_market_1`，
并复算代表 state，未发现 mismatch。

### B04 Remote LFS：PASS
8 个 LFS artifacts fresh-clone 恢复：
pointer OID、size、restored bytes、SHA 全部一致。  
verified remote commit：
`569b55862cd6115bc4456ccfb0ee7e98ee42da42`

### Accepted Head discipline：PASS
`data/v4/V4_05_ACCEPTED_HEAD.json` 仍不存在；  
`V4_STAGE_ACCEPTED_HEAD` 仍是 `V4_00_TO_V4_04_ACCEPTED; V4_05_NOT_ACCEPTED`；  
未发现 V4-06/V4-07/V4-08 越级正式执行。

## B03-R4 — G08 仍未在正式 V4 PostgreSQL ledger 上关闭

R4 用 SQLite isolated harness 执行了 I01-I04，这比 R3 的纯 hash simulation 前进很多，但该 harness 不是已接受的 V4 persistence contract。

正式 V4 schema 还包含：
- `publication_lineage_id`
- `revision_no`
- `core_revision`
- `same_day_revision_parent_id`
- `market_calendar_id`
- `prior_session_publication_id`
- `prior_session_state_head`
- `prior_session_state_logical_digest`
- `state_heads`
- head freeze / prior-session guards / single-successor constraints

R4 SQLite harness 缺少这些关键正式语义，而且把：
`publication_id = "PUB-" + computation_hash_prefix`
作为 identity；这与 V4-00C 的 opaque physical publication identity 不一致。

因此当前只能证明“简化 ledger 的 I01-I04 正确”，不能证明 Sep-28 R4 exact replay identity 在正式 V4 PostgreSQL schema 下可幂等、修订、回滚。

**B03-R4 = FAIL / BLOCKING**

## B05-R4 — Working-tree text SHA 污染跨环境 determinism

同一个 Git blob：
`data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json`

从 promotion commit 到当前 HEAD 的 Git blob SHA 一直是：
`22fe06ddf0f42bff7ebf3bdf55c542dd50ae11bf`

Global Accepted Head / promotion 绑定 SHA256：
`83fa37ded40337d69ff0e447a0b6a3bc293d2ca95ea9c8aa009f0f104776c4be`

但 R4 本地 protected-head check 记录：
`613a2e46876aeb3283fa268f717134347f4df236e0d935b47b3a770eb0d1afbf`

业务内容没有变化，最合理解释是 Windows working-tree CRLF/LF 字节差异。

问题在于 `build_v4_05_r4_market_reference.py` 把 `sha(go_forward_head_path)` 直接写入 target snapshot 的 `source_head_sha256`，随后 snapshot artifact SHA 又进入 Market Regime 的 input identity。

因此同一 Git commit / source / contract / parameter，在 fresh clone 或不同平台重跑时可能产生不同 artifact/output digest。

当前 determinism 只证明“同一 working tree 两次相同”，没有证明“clean clone / cross-environment 相同”。

**B05-R4 = FAIL / BLOCKING**

## 外部验收矩阵

| 项目 | 结论 |
|---|---|
| PERIOD_ASOF | PASS |
| Market snapshot / basis identity | PASS |
| Market Reference | PASS |
| Market Path fail-closed | PASS |
| Market Regime | DEGRADED_PASS_ACCEPTABLE |
| Core Profile 5222 rows | PASS |
| R3→R4 business drift | PASS |
| Independent numeric postcheck | PASS |
| Same-working-tree determinism | PASS |
| Remote LFS restore | PASS |
| Actual V4 PostgreSQL G08 | **FAIL** |
| Canonical text hash / clean-clone determinism | **FAIL** |
| Accepted Heads protected | PASS |

## 最终结论

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R4`

建议只做一个 targeted closure：

`V4-05 Replay Gate A R4.1 — PostgreSQL Ledger + Canonical Hash Closure`

R4.1 禁止重做 Sep-28 raw source、GBBQ、Daily、Period formula、Factor formula、Market Reference formula、Core Profile rules。

R4.1 关闭 B03/B05 后，直接重新做 V4-05 外部终验。

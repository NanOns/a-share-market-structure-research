# V4-05 Replay Gate A R4.1
## PostgreSQL Ledger + Canonical Hash Final Closure Task

**Starting HEAD：** `e751c9dc63ba6e6325b50daa15e849091e18f5dc`

## 0. R4 External Audit Result

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R4`

R4.1 只关闭：

- `B03-R4`：actual V4 PostgreSQL revision-ledger replay
- `B05-R4`：canonical governance hash + clean-clone determinism

禁止重做已通过的 source / factor / profile 主链。

## 1. Frozen Business Values

除非 canonical-hash 修复导致 lineage/output digest 重新绑定，以下业务值不得变化：

- target_trade_date = `2026-09-28`
- target identities = `5222`
- Market Reference 1/3/5 数值
- Period 业务值
- Factor 业务值
- Core Profile state 业务值
- Market Regime `trend_axis=UNKNOWN`
- `historical_as_recorded_claim=false`

任何业务值变化必须单独解释并停止 promotion。

## 2. B03 — 必须使用正式 V4 PostgreSQL schema

当前 SQLite harness 可保留为 unit test，但不能继续作为 G08 唯一正式证据。

R4.1 必须：

1. 创建 isolated/disposable PostgreSQL database 或 isolated schema；
2. 应用项目正式 migration：
   `src/workbench_db/migrations/v4_postgres/001...012`
3. 校验 migration version/checksum；
4. 禁止写 production V4 runtime rows；
5. 使用 R4 exact Sep-28 source/computation/logical-output identities。

优先复用已有 migration runner 与 `tests/v4_phase0/test_postgres_schema.py`。

## 3. 正式 Publication Identity

必须实际使用：

- opaque `publication_id`
- `publication_lineage_id`
- `revision_no`
- `core_revision`
- `model_namespace_id`
- `market_calendar_id`
- `same_day_revision_parent_id`
- `prior_session_publication_id`
- `prior_session_state_head`
- `prior_session_state_logical_digest`
- 或正式允许的 `prior_session_gap_reason`

禁止把 `publication_id=computation hash prefix` 当正式 G08 证据。

## 4. G08 I01 — Identical Replay

第一次用 R4 exact inputs 建立 replay publication。

第二次相同 replay：

Expected：
- no new logical revision
- no duplicate publication event
- no head drift
- no duplicate consumed-source rows
- same accepted logical identity

Receipt 必须列：
- before / after-first / after-second counts
- publication IDs
- lineage ID
- revision_no
- core_revision
- publication head
- state head
- consumed-source rows

## 5. G08 I02 — Changed Source Revision

只改变受控 TDX source revision identity。

Expected：
- new opaque publication_id
- same publication_lineage_id
- revision_no + 1
- same-day parent 指向前 revision
- old revision immutable
- new consumed-source manifest
- head 在明确 accept 前不移动
- accept 后再移动

必须通过正式 PostgreSQL trigger/constraint。

## 6. G08 I03 — Negative Guards

至少验证：

- same source_revision_id + different payload -> reject
- same-day parent fork -> reject
- revision_no skip -> reject
- lineage mismatch -> reject
- duplicate core_revision -> reject
- head to non-accepted publication -> reject
- head to wrong state head -> reject

## 7. G08 I04 — Transaction Rollback

在正式 PostgreSQL transaction 中故意在：

- publication inserted
- consumed sources partly inserted
- before accepted head update

注入 failure。

Expected：
- no dangling publication
- no dangling consumed-source row
- no dangling state head
- no changed head
- no partial event

必须查询证明。

## 8. G08 I05 — Prior-State Freeze

实际验证：

当下一 session publication 已绑定 prior accepted state 后，尝试：
- replace prior publication head
- delete prior head
- change prior state head
- change prior logical digest

必须 fail closed。

## 9. PostgreSQL Receipt

生成：

`reports/v4_05/V4_05_R4_1_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json`

至少记录：
- PostgreSQL version
- isolated db/schema identity
- applied migration versions/checksums
- `production_connection_used=false`
- I01-I05
- row counts
- publication/lineage/revision/core identities
- state head / publication head
- consumed sources
- rollback
- cleanup

如写入 production：
`BLOCKED_UNAUTHORIZED_PRODUCTION_WRITE`

## 10. B05 — Canonical Governance Hash

当前同一 Git blob：

`data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json`

promotion/global accepted binding：
`83fa37ded40337d69ff0e447a0b6a3bc293d2ca95ea9c8aa009f0f104776c4be`

R4 Windows working-tree hash：
`613a2e46876aeb3283fa268f717134347f4df236e0d935b47b3a770eb0d1afbf`

Git blob 没有变化，不允许重做 V4-02 accepted business content。

## 11. 冻结 Canonical Hash Rule

对 JSON governance artifact 建议采用：

`CANONICAL_JSON_SHA256_V1`

规则：
- parse JSON
- UTF-8
- sorted keys
- separators=(",",":")
- no platform newline dependency

如果必须延续已有 promotion raw canonical SHA，则使用：
- repository canonical LF bytes
- 或 Accepted Head 中已冻结的 SHA binding

禁止把 OS working-tree `read_bytes()` SHA 作为正式逻辑 identity。

普通文本可登记：
`CANONICAL_TEXT_SHA256_V1`
并统一 CRLF -> LF。

二进制 `.gz/.parquet/.zip/gbbq` 继续使用 raw-byte SHA256。

## 12. Accepted Head Validation

必须证明：

- Git blob unchanged
- canonical recomputed V4-02 go-forward Accepted Head SHA
- 与 `V4_STAGE_ACCEPTED_HEAD` binding 一致

如不能证明与：
`83fa37ded40337d69ff0e447a0b6a3bc293d2ca95ea9c8aa009f0f104776c4be`
一致，则停止，先查 hash-domain 历史。

禁止直接修改 global Accepted Head 去“对齐”。

## 13. Remove Working-Tree Hash From Business Identity

检查并修复 R4 builder 中所有 governance text hash：

尤其：
- `source_head_sha`
- `source_head_sha256`
- target snapshot source identity
- market reference input-source digest
- market regime input-source digest
- protected-head evidence

这些必须使用 canonical identity。

## 14. Clean-Clone Determinism

在 fresh clone：

1. checkout exact R4.1 implementation commit
2. `git lfs fetch`
3. `git lfs checkout`
4. 重新运行至少：
   - period
   - target market snapshot
   - market reference
   - market regime
   - full-scope factors
   - core profile

与 primary build 比较：

- business values
- logical digests
- canonical source digests
- deterministic artifact bytes

必须一致。

如果只有 receipt timestamp 等 volatile metadata 不同，则不得进入 logical digest。

## 15. Newline Negative Test

构造逻辑内容完全一致的 JSON：

- LF
- CRLF

要求：
- raw-byte SHA 可以不同
- canonical governance SHA 必须相同
- downstream logical identity 必须相同

## 16. R4 → R4.1 Diff

如果 canonical hash 修复导致 artifact/source/output digest 变化：

允许。

但必须满足：

- `business_field_changes=0`
- `state_changes=0`
- `unexpected_business_value_drift=0`

生成：

`reports/v4_05/V4_05_R4_1_R4_DIFF.json`

## 17. LFS

如果 R4.1 重建 LFS payload：

必须重新：
- push LFS
- fresh clone
- restore
- rehash

如果 payload 不变，可以引用 R4 restore，但必须证明 pointer unchanged。

## 18. Runtime Tests

新增覆盖：

- actual PostgreSQL R4 replay
- identical replay
- changed-source revision
- fork rejection
- state/head guards
- rollback
- canonical LF/CRLF hash
- clean-clone deterministic rebuild

正式 receipt 必须明确列：
- `tests/v4_phase0/test_postgres_schema.py` 是否实际运行
- isolated PostgreSQL connection identity
- skipped test names/reasons

禁止只写 `2 skipped` 而不说明跳过内容。

## 19. Accepted Head Discipline

R4.1 仍然是 candidate closure。

禁止：
- 创建 `V4_05_ACCEPTED_HEAD`
- 把 `V4_STAGE_ACCEPTED_HEAD` 改成 V4-05 accepted
- 正式启动 V4-06
- 正式启动 V4-07

完成后：
`external_acceptance=PENDING`

等待外部终验。

## 20. Required Evidence

至少：

- `V4_05_R4_1_STAGE_ENTRY.md`
- `V4_05_R4_1_CANONICAL_HASH_POLICY.json`
- `V4_05_R4_1_ACCEPTED_HEAD_HASH_VALIDATION.json`
- `V4_05_R4_1_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json`
- `V4_05_R4_1_CLEAN_CLONE_DETERMINISM.json`
- `V4_05_R4_1_R4_DIFF.json`
- `V4_05_R4_1_RUNTIME_TEST_RECEIPT.json`
- `V4_05_R4_1_INDEPENDENT_POSTCHECK.json`
- `V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json`
- `V4_05_R4_1_CLOSURE.md`

## 21. Expected Terminal State

如果 B03/B05 全部关闭：

`V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_1`

保持：

- `CURRENT_FORWARD_STOCK_CORE=DEGRADED_PASS`
- `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE=BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

这符合 §52B capability-scoped acceptance。

下一轮外部审计目标：

`V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_1`

通过后再单独执行：
`V4-05 Accepted Head Promotion + successor stage authorization`

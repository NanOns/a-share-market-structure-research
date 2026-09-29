# V4-02 Go-Forward PIT Amendment R3 Final External Acceptance

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Audit Date:** 2026-09-29  
**Reviewed HEAD:** `a54154e5e25b149fd35a09935435dcaa40ad8b8b`  
**R3 Implementation Commit:** `f6197db9a73f4584616db1af98bcf9c7e339493e`  
**R3 Runtime/Postcheck Commit:** `288d306341d8c8879b090425677c35d84648176b`

---

## 0. Final Decision

`V4_02_GO_FORWARD_PIT_AMENDMENT_EXTERNAL_ACCEPTANCE_PASS_R3`

Accepted capability:

`GO_FORWARD_PIT_ADJUSTED_PRICE / DELAYED_FORMAL_PUBLICATION`

First accepted target:

`2026-09-28`

Historical capability remains:

`HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

This acceptance does not convert pre-project historical adjusted data into PIT history. It authorizes a separately scoped go-forward PIT input chain for V4-05 Replay Gate A R2.

---

## 1. Accepted source package

Official TDX package:

- target trade date: `2026-09-28`
- SHA256: `70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c`
- bytes: `551001603`
- ZIP/CRC: PASS
- max raw date: `20260928`
- future raw rows: `0`
- target bars: SH `4865`, SZ `4503`, BJ `349`, total `9717`
- `D:/new_tdx` write count: `0`

**PASS**

## 2. Raw overlap

Sep-24 accepted-stock cross-section:

- accepted rows: `5210`
- match: `5210`
- accepted-only: `0`
- mismatch: `0`

**PASS**

## 3. Accepted adjustment source

Frozen pre-T0 GBBQ:

- snapshot: `sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e`
- system available: `2026-09-26T13:07:05Z`
- gbbq SHA256: `f8c6a60e052a3fd7f8c3a043dbc9c53311a7599e1b36bb6cc140058f56269ef1`
- gbbq.map SHA256: `f874e09444c03077b1d9e465a6efe56beb6678c0e71c98d118516ad24efe51c8`

Only the frozen Sep-26 event set with effective date no later than T0 may drive Sep-28 QFQ. Later snapshots remain diagnostic-only.

**PASS**

## 4. U01 closure — new listing / new source key

R3 now builds the target universe from prior accepted identities UNION target-date official A-share bar keys, then resolves all required keys through dated identity records. Valid new listings enter the candidate; unresolved, future-listed, or ambiguous identities fail closed.

Real Sep-28 result:

- accepted security count: `5222`
- candidate security count: `5222`
- target actual bars: `5210`
- new source keys: `[]`
- unresolved target source keys: `[]`
- unexplained dropped keys: `[]`

Synthetic automated tests cover valid new listing inclusion, unresolved key, future-listed key and ambiguous dated identity.

**U01 CLOSED**

## 5. Code-change identity preservation

The known code-change sample remains bound to:

- canonical security_id: `SEC-EDEDE35FE66896ACCA0AC85EEB2F133B`
- current source key: `SZ.302132`
- predecessor: `SZ.300114`

**PASS**

## 6. T01 closure — publication-time semantics

Every R3 row now uses:

`PIT_OBSERVED_AFTER_FORMAL_PUBLICATION`

and records target date, max source date, official raw publication time, project raw availability, adjustment availability and formal publication time.

Example:

- target trade date: `20260928`
- official raw source published: `2026-09-28T07:58:05Z`
- project raw source available: `2026-09-29T06:53:52Z`
- adjustment source available: `2026-09-26T13:07:05Z`
- formal publication: `2026-09-29T06:53:52Z`

All 5,222 rows satisfy source-date and availability ordering. No same-day/intraday availability claim is made.

**T01 CLOSED**

## 7. R3 candidate

Artifact:

`reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz`

SHA256:

`7d87f5164c11f791ad24ad7c05139dca949f1c891523616ece907cd0f28fd8c8`

Logical digest:

`a5600d7f1416434bd54e778c2e7e847e309de1c21d71df5677f92daee1791400`

Rows: `5222`

Quality:

- RAW_READY `5210`
- ADJUSTED_READY `5195`
- ADJUSTED_UNAVAILABLE_NO_T0_RAW `12`
- ADJUSTED_UNAVAILABLE_UNSUPPORTED_OR_UNKNOWN_EVENT `15`

No BaoStock QFQ fallback is used.

**PASS**

## 8. R2 → R3 business diff

- added keys: `0`
- removed keys: `0`
- business changes: `0`

Intentional change only: lineage/timestamp semantics.

**PASS**

## 9. Determinism / no-backdating

Two R3 builds from identical frozen inputs produce identical logical digest and compressed SHA. Later GBBQ is excluded from T0 computation, and negative testing confirms later-only T0-effective price events do not backdate into the frozen T0 result.

**PASS**

## 10. E01 closure — runtime test evidence

Formal receipt:

`reports/v4_02/V4_02_GO_FORWARD_R3_TEST_RECEIPT.json`

Bound implementation commit:

`f6197db9a73f4584616db1af98bcf9c7e339493e`

Result:

- passed: `401`
- failed: `0`
- skipped: `2`

No business implementation change occurs after the bound implementation commit; the following commit only binds test/postcheck evidence.

**E01 CLOSED**

## 11. R01 closure — remote Git LFS recovery

An isolated fresh clone successfully fetched and materialized the authoritative 551,001,603-byte LFS object from origin. Restored SHA256:

`70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c`

**R01 CLOSED**

## 12. Independent postcheck

Independent R3 postcheck confirms package identity, remote-LFS restored SHA, target universe, publication ordering on all rows, frozen GBBQ use, candidate digest, R2→R3 business diff, runtime receipt, unchanged Accepted Heads and zero TDX writes.

**PASS**

## 13. Accepted scope

Accepted:

`GO_FORWARD_PIT_ADJUSTED_PRICE`

Scope:

- first accepted target: `2026-09-28`
- publication mode: `DELAYED_FORMAL_PUBLICATION`
- adjustment basis: frozen pre-publication GBBQ
- raw basis: official TDX package

Still unavailable:

`HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`

Historical reconstructed outputs remain diagnostic unless separately proven PIT.

## 14. Non-blocking lifecycle note

The R3 identity resolver safely fails closed on unresolved/ambiguous future keys. For future real delisting/termination cases, the operational lifecycle updater must eventually support legitimate target-universe removal rather than repeatedly stopping on stale prior membership. This does not block the Sep-28 amendment acceptance.

## 15. Accepted-head implication

Do not overwrite the original V4-02 Accepted Head whose foundation cutoff remains `2026-09-24`.

Promote a separate go-forward amendment accepted head/binding. The global stage head must preserve the V4-02 foundation and add the go-forward binding explicitly.

## 16. Final status

```text
V4_02_GO_FORWARD_PIT_AMENDMENT_EXTERNAL_ACCEPTANCE_PASS_R3

GO_FORWARD_PIT_ADJUSTED_PRICE = EXTERNALLY_ACCEPTED
FIRST_ACCEPTED_TARGET = 2026-09-28
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
V4_05_R2 = AUTHORIZED_AFTER_ACCEPTED_SEAL
```

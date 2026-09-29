# V4-06 Closure / Candidate Submission

Recorded at 2026-09-29T15:03:27+00:00.

## Stage result

**DEGRADED_PASS candidate; external acceptance is PENDING.** The supplemental pipeline, append-only PostgreSQL schema, bounded worker, and TURNOVER_CONTEXT_V1 engine are implemented. The live BaoStock strict-binding capability remains blocked and the dataset stays disabled. `CORE_DEPENDENCY = NONE`.

The V4-05 accepted Core publication is `PUB-3c03e227-c60a-4d8c-86ae-2861507c257b` for 2026-09-28, logical digest `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`. The isolated migration run appended two supplemental revisions against that publication and verified that the publication head was identical before and after. No V4-06 Accepted Head was created, the global accepted head was not advanced, and V4-07/V4-08 were not started.

## Capability results

- `SUPPLEMENTAL_PIPELINE = PASS`: versioned append-only schema, manifest/row identity, immutability guards, rollback, and same-publication revision behavior passed in an isolated PostgreSQL 18.6 cluster.
- `TURNOVER_CONTEXT_ENGINE = PASS`: 33 stage tests passed, including strict-only 5/20/60 windows, the 60-sample boundary, 250-session cap, suspension/missing handling, ratio and delta3 boundaries, and Core isolation fixtures.
- `BAOSTOCK_LIVE_STRICT_BINDING = BLOCKED/DEGRADED`: the bounded probe returned 4 target rows across four representative identities; strict-bound count is 0. The provider responded successfully, but every identity had zero exact close/volume/amount rows across common dates and target fingerprints had amount conflicts. Source-specific tolerances and denominator semantics are not independently accepted.
- `CORE_ISOLATION = PASS_WITH_DISCLOSED_FIXTURE_LIMIT`: the sidecar API cannot write Core digests; A/B/C/D matrix fixtures preserve all six supplied components, and the database test preserved the actual accepted V4-05 publication head. V4-05 does not publish one accepted six-component digest vector, so no synthetic digest is presented as a V4-05 business digest.

## Open audit and external review

Audit `V4-06-BAOSTOCK-BINDING-TOLERANCE-01` remains OPEN and independent from this stage gate. Official BaoStock API documentation was not readable through the web renderer during this stage; this evidence does not infer missing source semantics. The source-specific tolerance contract remains unfrozen, strict binding remains forbidden, and all BaoStock datasets remain disabled.

Submit this candidate and its evidence bundle for independent external acceptance. Do not create an Accepted Head until that review is recorded. V4-07 remains not started; V4-08 remains blocked on its existing PIT membership baseline gate.

## Evidence index

See `V4_06_STAGE_CANDIDATE_MANIFEST.json` for SHA-256 bindings for source files and every stage report. The required clean-checkout receipt is `232f8d83525f322116b2c757cf1db42a41d1a908`.

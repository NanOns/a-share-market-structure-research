# V4-07 Accepted Head Promotion — 2026-09-30

## Stage contract and evidence

- Candidate implementation: `e751070cb5018c76229b87bc0c7ec749a0a36f7a`; evidence seal: `075163fd7bf3d4210004734f849cff9225bc6ecf`.
- External decision: `V4_07_EXTERNAL_ACCEPTANCE_PASS_R2_ENGINEERING_SCOPE` from `V4_07_R2_INDEPENDENT_EXTERNAL_ACCEPTANCE_20260930.md` (SHA-256 `082ebdecc7efd45a643a6b887250436c0bcac796c59178de4a8d19e37191296c`).
- Artifact: `reports/v4_07/staging/V4_07_BASE_SEED_CANDIDATE_R2.jsonl.gz`, SHA-256 `bb9992c581092f91ba69ad8390daf522d3441951f5bc61437ff0e4653ed74e72`, logical digest `28c5f6f71f6568c29bb8b1580f8c6ff22475222c802b4d5317a3f0cbb3b16015`, 5,222 rows.
- Contract SHA-256 `73e686fb3bd15ef8afa893efc804d14cb2339f76975a40b5649d5265d327122f`; parameter-set SHA-256 `241785e1a97dd2283eb8b361eb791f4e5c8f6ca67579a06f2a2d38c0c7586a1a`.
- The earlier `V4_07_R2_FULL_MARKET_CANDIDATE_RECEIPT.json` remains an immutable `PRE_FINAL_GATE_CANDIDATE_SNAPSHOT`; final gates are bound from the receipts listed in the Accepted Head.

### Candidate manifest receipt updates

The R2 manifest has two stage-receipt hashes from before the final evidence refresh. The current files are the later final PASS receipts and are independently bound in this promotion validation:

- `reports/v4_07/V4_07_R2_ISOLATED_FULL_REGRESSION.json`: candidate manifest expected `d02cb5da1b25a4d7375906a76311eb2ebc77f8f1d1587e26441d0c6337dc1270`/4977 bytes; final current receipt `728830d597b7a6f3bfe960ed580759b1d1c2d50d14939a9cdf5cedae273c22ce`/4874 bytes. The original manifest and pre-final candidate receipt remain unchanged; promotion binds this final receipt.
- `reports/v4_07/V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json`: candidate manifest expected `548b8c32aaeb8e30afa74f4e58a79a75dffc55c4d09ee4da381bcab942b0c65e`/723 bytes; final current receipt `9353ca10a9de39bedc68b3ba8342f09b77c9b8412d2cba5588b1b5ecce9373a2`/707 bytes. The original manifest and pre-final candidate receipt remain unchanged; promotion binds this final receipt.

## Acceptance result

`V4_07_ACCEPTED_HEAD_PROMOTION_PASS_R1_ENGINEERING_SCOPE`.

`V4_07_ENGINEERING = EXTERNALLY_ACCEPTED`; `REAL_BASE_SEED_SIGNAL = DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN`. The accepted input `rps5_delta3` remains UNKNOWN for all 5,222 target identities. Prior-RPS audit `V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01` remains OPEN.

Accepted Head SHA-256: `b22117b0d14c35167cba86cb7398d878d7112f9cf17c1a427fa92766e78f880f`. Global accepted range advances through V4-07 only. V4-08 full production remains blocked pending an accepted PIT membership baseline and reconstruction.

## Next stage

Begin `V4_08_PIT_SECTOR_MEMBERSHIP_BASELINE_R1`: freeze the membership contract/schema and diagnostic replay. Do not claim a go-forward PIT baseline unless its source observation, cutoff, availability timestamps, and frozen source identities are evidenced.

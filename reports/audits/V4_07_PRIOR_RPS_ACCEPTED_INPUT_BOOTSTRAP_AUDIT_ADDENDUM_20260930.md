# Prior-RPS Bootstrap Repair Audit Addendum — 2026-09-30

**Audit item:** `V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01`  
**Status:** `OPEN`  
**Assessment evidence:** `reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R1.json`  
**Assessment SHA-256:** `ed02df4eb1e3faf9e809e2a890ea47d1a709130c626ac4443a9c2c1c631e7f57`

## Finding

The accepted V4-05 Full Scope Factors publication for `2026-09-28` contains 5,222 identities. Each of `rps5_delta1`, `rps5_delta3`, and `rps20_delta3` is `UNKNOWN / BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY` for all 5,222 rows, with null values and null output digests. The accepted head binds the factor artifact `reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz` (SHA-256 `17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48`; logical digest `0cfe708567935726f0ad51ae4bb47237ec7aee556db3437c12f21f0c623bd0d2`).

The V4-03 R3 candidate computed prior RPS scores from its stage-owned historical staging artifact (SHA-256 `90d5998ba93b60f8061c759952a0f635e4e44fb0cd12fce73331e40d95ff7041`; source digest `f712a3377afa8f4b797a29e7e8fead41847452b52382d9c8a809e41f8f698177`). Its independent postcheck passed on 5,222 rows, and the full-scope candidate reported 5,023 observed / 199 unknown `rps5_delta3` values. The sample value in the candidate is 9.992463694647483 for its recorded `2026-09-21` to `2026-09-24` window. But the prior artifact status is `STAGING_NOT_STAGE_ACCEPTANCE`, and the full-scope output is `FULL_47_FIELD_CANDIDATE_NOT_STAGE_ACCEPTANCE`. They are candidates, not accepted V4-05 inputs, so those values cannot be copied into the accepted factor lineage.

## Exact repair requirement

REV2 §10.0 defines RPS as a same-session cross-sectional midrank of `retN` over the date's evaluable universe. The delta fields require:

- `rps5_delta1 = rps5[t] - rps5[t-1]`
- `rps5_delta3 = rps5[t] - rps5[t-3]`
- `rps20_delta3 = rps20[t] - rps20[t-3]`

Each prior score must bind its accepted prior artifact digest and universe snapshot identity, plus the market calendar, prior trade date, adjustment basis, and source digest. `src/v4/factors/relative.py` rejects missing prior artifact/universe identities and does not synthesize a prior score from raw history. REV2 says the 300-market-day warm-up is a planning target; each field's actual first-available date must be measured independently.

## Open blocker and next action

There is no new independently accepted PIT prior-RPS chain. Repair remains OPEN until a dated, calendar-bound and universe-bound prior score chain is built, independently recomputed, reconciled for first-available/warm-up behavior, and published through a new accepted factor revision. This addendum does not change V4-07 thresholds, consume the V4-03 R3 staging values, rewrite V4-05, or convert UNKNOWN to FALSE. Real Base Seed capability remains `DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN`.

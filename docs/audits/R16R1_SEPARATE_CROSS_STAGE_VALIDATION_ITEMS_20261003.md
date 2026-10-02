# R16R1 separate cross-stage audit items — 2026-10-03

The 22 expanded-regression failures reproduce on clean detached baseline `92bf5cdefe81da6e809a0dd05dcbd3f651dc35ff`. They do not alter the narrow R16R1 projection repair acceptance.

- R16R1-AUD-DM01-STAGE-BINDING: DM01 publication-history readers pin an earlier Stage Head SHA. Status OPEN; requires a separate owner repair and external acceptance.
- R16R1-AUD-HISTORICAL-STAGE-GATES: historical V4-09/V4-12 promotion and frozen-checkout validators assert older protected state. Status OPEN; computational owner/DAG regressions stay selected.

Exact failing identities, source SHA, original errors and separate acceptance criteria are in `reports/v4_13_runtime_r16r1/separate_cross_stage_audit_items.json`. No protected Head, history reader, owner algorithm or migration is changed by this round.

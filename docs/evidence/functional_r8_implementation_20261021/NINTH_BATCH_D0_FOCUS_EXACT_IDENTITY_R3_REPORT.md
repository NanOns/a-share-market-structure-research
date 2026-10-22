# Ninth Batch Follow-up R3: Full Exact Identity and D0 Recompute

**Status:** `FULL_CORE_AND_D0_FOCUS_RECOMPUTED_CANDIDATE_ONLY_NOT_PUBLISHED`
**Date:** 2026-10-20
**Evidence class:** real frozen sources, reconstructed after the historical session (`AS_RECORDED=false`, `PIT_ELIGIBLE=false`).

## Work completed

The exact date-bound candidate membership and identity rows now drive the owner core, the 10/15 endpoint is computed in the 10/20 target QFQ coordinate, and candidate identity rows are preferred by Focus. The two newly active candidate securities are present in the 5,226-row core and D0 output; neither has been fabricated into a positive D0 result. The full owner core has zero independent numeric oracle mismatches.

The independent row-level RPS5 check found 5,202 exact observed deltas, 24 exact endpoint UNKNOWNs and zero mismatches. The formal D0 owner now covers all 5,226 candidate members: **141 TRUE / 5,033 FALSE / 52 UNKNOWN**. The frozen scanner check reports PASS with zero mismatches. This replaces the R2 subset result (5,224 rows; 72 UNKNOWN), which omitted the newly mapped rows and predated the complete Focus production.

## What remains UNKNOWN

Unknown values remain UNKNOWN where the frozen real source does not support a determination. The remaining 24 RPS5 endpoint rows have no exact endpoint value in the frozen source. The two newly active securities have insufficient observed history for the window-dependent D0 checks. Across the 52 formal D0 UNKNOWN members, the underlying Core has 472 `UNEXPLAINED_DATA_GAP` factor-cell occurrences (21 securities), 180 `CURRENT_BAR_UNAVAILABLE` (9), 152 `INSUFFICIENT_HISTORY` (7), and overlapping endpoint/reference reasons listed in the JSON. These are factor-cell occurrences, not distinct securities. The frozen BaoStock daily-status acquisition stops at 2026-10-08; it contains no date-bound daily status for 10/09–10/20. A missing TDX bar after that cutoff cannot prove suspension, so it remains UNKNOWN until a real status source is captured. No synthetic positive sample, alternative provider login, or mismatched old Owner value was used.

## Current limits

The exact 10/20 frozen acquisition has no same-day CSRC industry-membership receipt. Industry/sector-dependent outputs therefore remain UNKNOWN. The recomputed Core, D0, D2 and Focus/Forward files are candidate-only: no successor R8/D0 publication, Priority acceptance, or 28766 same-token route readback has occurred. 28766 still exposes the previous 10/21 token; 28765 was not touched.

The three copied full outputs are hash-bound in [`NINTH_BATCH_D0_FOCUS_EXACT_IDENTITY_R3_EVIDENCE.json`](NINTH_BATCH_D0_FOCUS_EXACT_IDENTITY_R3_EVIDENCE.json). This evidence supersedes the R2 report's two-missing-member statement and its 5,224-row D0 subset counts.

# S02 breadth semantics proposal R1

- Contract: `S02_BREADTH_SEMANTIC_ADJUDICATION_R1`, version `1.0.0`.
- Status: `BUSINESS_RULING_REQUIRED`; this proposal preserves candidate output and is not authority to revise accepted history or publish V4.03 regime.
- Compatibility behavior: keep the existing `POSITIVE_INDICATOR` result as the candidate compatibility formula until an authorized business owner rules. The new adapter reports it separately from `SIGN`; neither result overwrites the other.

## Recommendation and alternative

Recommend **positive-indicator change in advancing share** for the axis named breadth: `mean(I(r_t > 0) - I(r_t-3 > 0))`, where zero is 0. This measures the change in the share of advancing securities and is consistent with the current recorded candidate producer and its threshold. Keep `SIGN` as a diagnostic sensitivity measure, not a substitute for breadth.

Alternative: choose `mean(SIGN(r_t) - SIGN(r_t-3))` with `SIGN(0)=0`. This weights the direction of each security equally but also represents the change in signed direction balance; its scale and the meaning of the existing ±0.05 threshold differ. The alternative therefore requires a separately versioned axis and threshold review before use.

Both use the same prior-third-session universe, valid QFQ one-session return pairs, no rounding before the mean, and exclusion of pairs without both positive finite closes. The 10/12–14 comparison is NON_PIT; source history cannot prove historical availability.

## Measured candidate impact

| T0 | Evaluable / 5,224 | SIGN | Positive indicator | Difference | Class at ±0.05 |
|---|---:|---:|---:|---:|---|
| 2026-10-12 | 5,204 | -0.491929 | -0.237317 | -0.254612 | both DETERIORATING |
| 2026-10-13 | 5,206 | +0.451978 | +0.221667 | +0.230311 | both IMPROVING |
| 2026-10-14 | 5,206 | -0.802920 | -0.398579 | -0.404341 | both DETERIORATING |

The labels happen to match; the values differ materially. Until the semantic ruling is recorded, `BUSINESS_SEMANTICS_PENDING` remains in code and the public/current composite regime remains `NOT_PUBLISHED_V4_03`.

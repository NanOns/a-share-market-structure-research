# V4-03 Market Regime trend WEAK erratum R1

Status: versioned V4-03 contract amendment. This resolves the ambiguity recorded by `V4_03_EXTERNAL_ACCEPTANCE_R1_20260928.md` B02 while leaving the REV2 source document and V4-00G 1.1.0 immutable.

For finite, known inputs at session `t`:

```text
STRONG = index_close[t] > index_MA20[t]
         AND index_MA20[t] > index_MA20[t-5]

WEAK   = index_close[t] < index_MA20[t]
         AND index_MA20[t] < index_MA20[t-5]

NEUTRAL = NOT STRONG AND NOT WEAK
```

If any required input is missing or nonfinite, the result is `UNKNOWN`. Equality remains NEUTRAL when the other known input does not satisfy STRONG or WEAK. No future offset is permitted. This amendment defines only the trend axis; final `regime_ui` remains outside V4-03 publication.

The adopted machine form is `config/v4_03_market_regime_trend_amendment_v1.json`, contract `MARKET_REGIME_TREND_WEAK_ERRATUM_V1@1.0.0`. The supplied external acceptance document recommended this symmetric weak definition, and the user instructed that future work execute the supplied documents. Positive and negative boundary vectors accompany the implementation. Independent external confirmation is still required before V4-03 final acceptance.

# V4-03 benchmark scope decision V1

REV2 §49A.1 and the V4-03 R2 task define `MARKET_RELATIVE_REFERENCE_V1` as the historical, equal-weight endpoint-return reference for `rel_market_N`. The continuous ret1 chain has a separate `DAILY_REBALANCED_RESEARCH_INDEX` identity. V4-03 may calculate those historical primitives from dates at or before as-of.

REV2 §49A.2 assigns the frozen-T0 forward basket, marked suspension valuation, T+N settlement, and `relative_market_return_marked` to V4-15. Their identity is `FORWARD_MARKET_BENCHMARK_V1`; no V4-03 publication may reuse it.

Decision: **historical price path only**. No future rows, forward outcome, or benchmark settlement are consumed. This closes the scope wording for implementation, while final algorithm and artifact acceptance remain separate gates.

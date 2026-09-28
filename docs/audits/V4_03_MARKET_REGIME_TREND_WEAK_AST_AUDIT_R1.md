# V4-03 market trend WEAK AST audit R1

Scope: `MARKET_REGIME_V1` trend_axis WEAK branch and dependent final regime output only. This is an independent contract audit item; other V4-03 pure factors are not blocked by this issue.

Evidence: REV2 §49A states STRONG as `index C > MA20 AND MA20 > MA20[t-5]`, but says WEAK is “反向” without a unique serialized Boolean AST. The V4-03 R2 task §40 expressly requires `CONTRACT_CONFLICT_MARKET_REGIME_TREND_WEAK_AST` if the machine contract cannot establish the exact inverse rule. No such machine rule was found in `config/` or the REV2 source.

Current behavior: `market_axis_primitives` returns the explicit conflict for `trend_axis`; `regime_ui` remains unpublished. Breadth, participation and stress primitives retain independent values and parameter identities.

Acceptance condition: an authorized versioned machine AST for WEAK, positive and negative boundary vectors, and independent audit of the trend_axis and dependent regime output. Until then this item is **OPEN / CONTRACT_CONFLICT**. No developer interpretation is accepted as a substitute.

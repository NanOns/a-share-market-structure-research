# Stock Strength Sector Association Contract V1

Contract version: `stock-strength-sector-association-v1.0`.

The field is descriptive co-strength evidence and is not a causal, probability, or trading claim. It does not replace or mutate the sealed V1 scanner fields.

Price-behavior names (including strong/weak, limit-up/down, consecutive-board, new-high/low, unusual-move, ranking-list, oscillation, turnover, and activity labels), event labels, and status labels are isolated as tags and can never be selected as the primary strength-associated sector. INDUSTRY, THEME, and non-tag STYLE memberships are normal-attribute candidates; no fixed priority is given to an industry membership.

A candidate must be a valid current membership with coverage at least 70%, published structure CURRENT_STRENGTH or REACCELERATION, at least five other members with finite 20-day return, positive leave-one-stock-out 20-day median return, leave-one-stock-out positive-return breadth at least 60%, and target within-sector 20-day return percentile at least 80%. REACCELERATION additionally requires positive leave-one-out 5-day median return and at least 60% positive-return breadth.

Eligible candidates are ordered deterministically by structure (REACCELERATION first), published 5-day and 20-day sector relative-strength percentiles, leave-one-out breadth, member percentile, coverage, and sector id. One primary and at most two alternatives are exposed. If none qualify, the result is explicitly unavailable and no tag is used as fallback.

# Research Priority Contract V1

Version `research-priority-contract-v1.1-correctness`; rule `research-priority-ruleset-v1.1-correctness`. A+/A/B/C means DAILY CROSS-SECTIONAL RESEARCH PRIORITY inside the same-day Candidate Pool. It is not probability, expected return, win rate, recommendation or trade signal.

Score dimensions and fixed rating boundaries are unchanged. Pattern rank is lexicographic on the existing economic tuple only. Exact economic ties occupy positions p..q and all receive average_rank=(p+q)/2 before percentile conversion. SECURITY_ID_IS_NOT_AN_ECONOMIC_SCORE_INPUT=true. Security ID is used only after scoring for deterministic display. Rename, row-order and duplicate-tuple operations cannot alter economic score or research priority.

Ratings use average-rank score percentile: A+ >=.95; A >=.85; B >=.65; C below .65. Ties are not forced into quotas. NO_LINEAR_HIT_COUNT_SCORING=true; NO_MEMBERSHIP_COUNT_SCORING=true; NO_LEADER_SECTOR_COUNT_SCORING=true.

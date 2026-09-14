# Phase 3 Report

PASS at 20260914. The scanner consumed only 541 Phase 2 sector rows and one market vector row. Phase 2 SHA-256, generation and cutoff were validated before evaluation and immediately before publication.

Published 502 valid sectors. CURRENT_STRENGTH=28, STABILIZATION=6, REACCELERATION=0. Tags: BREADTH_EXPANSION=10, HIGH_CONCENTRATION=169, LOW_COVERAGE=0. Overlap=0. Counts do not affect PASS and no threshold was relaxed.

All hits use fixed hard gates and Boolean conditions. RS5/RS60 percentiles were derived within INDUSTRY/THEME/STYLE separately; Phase 2 RS20 percentile was independently reproduced. Invalid sectors and six excluded themes remain in the audit but are absent from the main 503-row scanner publication. NULL is never zero. No score, optimizer, market-state label, stock candidate, external data or index OHLC was introduced.

Market vector is output context only. Membership remains CURRENT_TDX_MEMBERSHIP, pit=false, historical_backtest_safe=false. REACCELERATION means CROSS_HORIZON_REACCELERATION_PATTERN, not a historical state transition.

QA selected hits (up to 3 per scanner) plus at least two deterministic boundary misses per scanner, with all values/operators/thresholds. Tests: 16 passed, 0 failed. Output is append-by-date with same-date replacement, staged validation/fsync/atomic replacement, and receipt last.

NEXT_ALLOWED_PHASE=PHASE_4_FORMAL_STOCK_SCANNER. Phase 4 was not started.

# Phase 2 Report

PASS, cutoff 20260907. Phase1 generation and both canonical SHA256 values verified before consumption and again before publication. No index OHLC, external data, raw .day scan or adjustment recalculation.

Market vector: one latest row from 5214 NORMAL_UNIVERSE members. Sector factors: 541 current sectors, 502 valid. INDUSTRY/THEME/STYLE rankings are separate; excluded theme roles never ranked. coverage=valid/total unique source members, not tradable/total. Each aggregate carries finite-value counts and ratios to total source membership. NULL not imputed.

TOP3_CONCENTRATION follows baseline section39: top3 positive one-session returns / total positive returns, minimum8 finite RET1 values, zero positive sum -> NULL. Phase1 lacks RET1 and current close, so only two latest master dates and seven columns were queried from normalized Parquet (11860 selected rows); no historical dataframe loaded. Amount activity uses AMOUNT_MA5/AMOUNT_MA20, not the distinct today/20D metric.

No subjective trend-quality threshold, market state, composite score, sector classification or concentration tag was introduced. Market and sector layers each aggregate stock inputs independently. All membership carries CURRENT_TDX_MEMBERSHIP, pit=false, historical_backtest_safe=false. Old years are never backfilled.

QA: independent market breadth/median checks, sector RS equivalence, at least 3 samples per role with raw member inputs and direct recalculations, same-type percentile checks. Tests 15 passed,0 failed. See audit JSON and SECTOR_SAMPLE_CALC.md.

Future latest snapshots append by date and preserve existing older rows. Publication uses staged validation/fsync/replace; receipt last. Consumers validate both output hashes/generation. Phase1 inputs and TDX membership unchanged.

NEXT_ALLOWED_PHASE=PHASE_3_SECTOR_SCANNER. Phase3 not started.

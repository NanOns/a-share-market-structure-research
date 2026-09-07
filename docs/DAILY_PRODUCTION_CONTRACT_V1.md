# Daily Production Contract V1

Version: `daily-production-v1.2`.

The only production entrypoint is `python run_daily.py --date latest`. Arbitrary historical dates are rejected because membership is current, `pit_membership=false`, and `historical_backtest_safe=false`. Latest is resolved by the single `resolve_cutoff()` authority from local audited trading-day evidence plus the prior master calendar; the system date is never used as the cutoff. A broad, all-market new day advances the frozen run calendar; partial updates and small future outliers block.

Before publication the runner checks that the TDX root, calendar, security masters, gbbq, membership sources, and upstream contracts exist. It validates Phase0.2C and the Phase1–5 cutoff, status, generation, and SHA256 chain. TDX is a read-only input. Local data acquisition and launching the TDX client are outside this project.

Stage order is PRECHECK; normalization/adjustment and factor engine; market vector and synthetic sectors; sector scanner; stock scanner; candidate pool and research priority; reporting; end-to-end verification; final receipt. A failure stops downstream work. Canonical Phase1–5 writers retain their own stage/fsync/atomic replace/receipt-last contracts.

Reports are built in immutable `reports/releases/YYYYMMDD/<run_id>/` generations. All files, manifest, receipt, hashes, semantic checks, and readback validation complete before the tiny `reports/current/YYYYMMDD.json` pointer is atomically replaced. Old generations and the old pointer remain unchanged on any validation or pointer failure. Same-date business rows replace the same date and cannot duplicate. A future canonical snapshot blocks publication.

PRECHECK computes `production-source-fingerprint-v1.1-full-content` over the resolved cutoff, master calendar hash, gbbq and map, industry/theme/style membership sources, SH/SZ/BJ TNF masters, and every discovered SH/SZ/BJ `.day` file. The day component hashes a canonical sorted list containing security id, file size, mtime nanoseconds, latest record date, final-record SHA256, and complete-file SHA256. A metadata-preserving change to any historical bar therefore changes source identity. `RUN_CALENDAR_SNAPSHOT` and `RUN_UNIVERSE_SNAPSHOT` are recorded for every build.

The TDX root is resolved from `config/paths.yaml`, then `TDX_ROOT` when no configured value exists, then local discovery. Every resolved TDX directory remains a read-only source.

Canonical multi-date datasets are checked for future rows first, then read through `SnapshotReader` at the cutoff. Universe validation is exact-set based, with no fixed count; duplicate, missing, extra, or wrong-generation identities block. The Phase 2 receipt chain binds market factors, sector factors, and the dated sector-membership snapshot by generation and SHA256.

No-new-data requires the same cutoff, `SOURCE_IDENTITY`, `COMPUTATION_IDENTITY`, and `RENDER_IDENTITY`. Same-cutoff source, computation, and render revisions are distinct events; render revision republishes reporting only, while computation revision conservatively recomputes the deterministic chain. `--verify-only` is read-only. `--dry-run` performs readiness checks without publication. A valid empty Candidate Pool publishes fixed-schema `candidates.csv`, displays `本日无符合当前规则的候选`, and keeps A+/A/B/C at zero.

The entrypoint is single-writer protected by `runtime/locks/daily_production.lock`; active locks reject and demonstrably stale locks may be recovered. Failure records freeze the original exception, stage, traceback, cutoff, run id, timestamp, and exit code. Failure-log write errors are appended without masking the primary failure.

The HTML is static and offline. Market data is an unlabeled factor vector for context only. A+/A/B/C means same-day Candidate Pool research priority and is not probability, expected return, recommendation, or a trade signal. Candidate reporting explicitly separates best sector context from the primary Leader sector; Leader id/name/type/pattern are joined by exact Phase3 sector id. Reports preserve the current-membership limitation and never backfill history.

Exit codes: 0 success or verified no new data; 1 general failure; 2 input not ready; 3 generation/hash mismatch; 4 publication validation failure.

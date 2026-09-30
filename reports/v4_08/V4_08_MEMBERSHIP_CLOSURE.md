# V4-08 PIT Sector Membership Baseline R1 — Candidate Closure

- Stage contract: `V4_08_PIT_SECTOR_MEMBERSHIP_BASELINE_R1`.
- Candidate result: `DIAGNOSTIC_RECONSTRUCTION_PASS; PIT_BASELINE_BLOCKED`.
- Starting branch and accepted range: `V4_00_TO_V4_07_ACCEPTED`; source HEAD at candidate generation: `ae27c3bdd170024eff3841a147fcce257d57b038`.
- Latest accepted market session available from V4-05: `2026-09-28`.
- Source capture is hash-bound and observed at `2026-09-30T00:45:21.889920Z`; candidate ingestion/system availability is `2026-09-30T00:45:22.133876Z`. Provider availability and source membership effective date are unknown.
- Current replay digest: `6b6663cb853be75ae269c4b11629abca72fbb4bac8adeff3439255c5ef2e640e`; row count: `87,937`; raw source facts: `85,038`; derived parent facts: `2,899`.
- Formal sector types and rows: `{"INDUSTRY": 8484, "STYLE": 20223, "THEME": 46591, "UNKNOWN": 12639}`. Unmapped source identities: `497` unique keys / `1,176` facts; they are retained with UNKNOWN identity.
- Sector counts by formal type: `{"INDUSTRY": 133, "STYLE": 152, "THEME": 268, "UNKNOWN": 109}`. Unique mapped security identities: `5,468`. Membership quality distribution: `{"CURRENT_REPLAY_DIAGNOSTIC": 87937}`.
- Derived-parent semantics use `TDX_INDUSTRY_PREFIX_PARENT_MAP_V1`; exact child-to-parent map digest: `b99caa32b2060f440f84f7e450a4852c05770c8696baa250e95d92e57d6c5bda` over `76` child codes. Parent membership remains diagnostic-only.
- The candidate cannot claim PIT for `2026-09-28` or any historical date. No go-forward PIT trade date is assigned because the source provider availability and effective date are not evidenced. The current file system mtimes are metadata only.
- Membership basis for historical replay: `CURRENT_MEMBERSHIP_REPLAY`; `pit_observed=false`; `historical_backtest_safe=false`. Style and unknown types remain diagnostic-only. Parent-industry union remains diagnostic-only pending acceptance.
- V4-07 real Base Seed capability remains `DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN`; dependent fields remain UNKNOWN. The separate audit item remains OPEN.
- PostgreSQL migration evidence: `reports/v4_08/V4_08_MEMBERSHIP_SCHEMA_MIGRATION_RECEIPT.json`.
- Candidate manifest: `reports/v4_08/V4_08_MEMBERSHIP_STAGE_CANDIDATE_MANIFEST.json`; SHA-256 `f967159c16a04d5d292e1b521abab3bdcb70e8b23771e1ad0567f926dd2be088`.
- Acceptance result: `BLOCKED_FOR_INDEPENDENT_PIT_BASELINE_ACCEPTANCE` because there is no source provider-availability/effective-date receipt and the accepted identity map leaves unresolved keys. Diagnostic replay and contract/schema engineering are ready for independent audit; no V4-08 formal production is authorized.
- Next stage: independent external review of this candidate and the open source-time/identity limitations. After external review, obtain a separately evidenced dated source capture before requesting a PIT baseline acceptance.

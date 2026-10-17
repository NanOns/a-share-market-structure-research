# R93: configured TDX path in operational Owner preparation

The operational Owner adapter now resolves the TDX source root from the shared path configuration before archiving executed producer bytes. The exact daily release policy uses the same resolver when freezing its immutable policy copy. Both paths no longer contain a `D:/new_tdx` default.

The isolated exact-core guard now validates the configured isolation root is on G: instead of embedding a machine path.

Verification: **32 focused tests passed** across configured path precedence, TDX output guards, immutable exact-policy binding, and exact-core isolation. No PG connection, write, migration, or business acceptance was performed.

Original 266-callsite accounting remains **0 / 266 formally complete; 266 / 266 remaining**. This batch has no exact stable-row closure; report-backed DM-01 inputs and the local Head path remain open.

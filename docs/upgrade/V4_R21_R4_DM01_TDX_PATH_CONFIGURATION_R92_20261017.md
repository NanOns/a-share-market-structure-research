# R92: configured TDX roots in the daily increment path

The active daily increment builder, independent daily increment postcheck, and DM-01 component artifact writer now resolve the read-only TDX root through `common.paths.resolve_tdx_root`. Their default code paths no longer embed `D:/new_tdx`; explicit roots remain available for controlled callers. The artifact writer continues to guard every output against the resolved source root.

Verification: **69 focused tests passed** across TDX/BaoStock path configuration and official daily source increment checks. No PG connection, write, migration, or business acceptance was performed.

Original 266-callsite accounting: **0 / 266 formally complete; 266 / 266 remain**. The mapped `V4-BCA-R2-636d6fc678f581bc984c` callsite in `dm01_incremental_component_builders.py` remains open because it is a local Data Head read; this batch changed only source-root resolution and does not claim a PG Head migration. The remaining market-source ingress and Owner migrations are also open.

Next: migrate the exact DM-01 Head read and continue the mapped non-market consumer batches.

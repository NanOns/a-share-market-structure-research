# Input Snapshot Contract V1

Version: `input-snapshot-v1.0`  
Baseline: `V0.3_FINAL_IMPLEMENTATION_BASELINE`

## Purpose

Every newly built formal production release binds its result to one immutable input identity. The manifest proves what the run observed; it does not copy the TDX source tree.

## Required manifest

`INPUT_SNAPSHOT_MANIFEST.json` is stored inside the immutable release generation and copied into the same-cutoff revision archive. It contains:

```text
contract_version
run_id
cutoff_date
observed_at
source_revision_id
source_identity_version
source_identity
day_source_summary
gbbq_sha256
gbbq_map_sha256
membership_hashes
security_master_hashes
calendar_sha256
run_universe_generation
run_universe_sha256
run_universe_count
adjustment_identity
price_basis
computation_identity
render_identity
snapshot_manifest_sha256
```

`snapshot_manifest_sha256` is SHA-256 over the canonical JSON payload excluding that field itself. An existing manifest may be read again only when byte-equivalent in meaning; a different payload at the same path is rejected.

## Source revision archive

Same-cutoff source revisions are stored at:

```text
reports/revisions/<cutoff>/revision-000001/
reports/revisions/<cutoff>/revision-000002/
...
```

Revision identity is determined by material `SOURCE_IDENTITY.sha256`, not by run count. The same source identity reuses its revision number; a changed material source identity gets the next number. Existing revision directories and records are never overwritten or deleted.

Each revision records the input manifest, source/computation/render identity, run ID, release ID, observation time and changed source components.

## Stability gate

Production computes the full source identity at precheck and again after Phase1–5 and reporting, before manifest/receipt/archive/pointer publication:

```text
source_identity_before == source_identity_after
```

Mismatch raises `SOURCE_CHANGED_DURING_RUN` and blocks publication. Phase1 full-file source integrity remains in addition to the lightweight `.day` freshness identity.

## Safety

- `D:/new_tdx` and configured TDX roots are read-only.
- No external data or adjustment service is permitted.
- Future/cutoff validation precedes canonical staging and replacement.
- Runtime writes are limited to data products, reports, receipts, input snapshots, revision archives, pointers, current status and logs.

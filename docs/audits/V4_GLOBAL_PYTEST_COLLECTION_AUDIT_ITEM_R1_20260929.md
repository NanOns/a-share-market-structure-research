# Cross-cutting audit item: global pytest collection

- Scope: repository-wide test collection and unrelated M14 failures. This item is independent of the V4-04 stage gate.
- Evidence: `python -m pytest -q` fails during collection because `tests/upgrade_m14/test_online_batches.py` imports `_commit_raw_and_batch` from `workbench_online.collector`, where that symbol does not exist. `git grep HEAD` confirms this mismatch exists at the V4-04 input HEAD `ca906884526e41a8cc8d4a47eabba3d5329f0a10`. An exploratory run excluding that file showed additional failures in other areas and was interrupted; no global pass is claimed.
- V4-04 focused regression: `python -m pytest tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_joint tests/v4_phase0 -q` yielded 354 passed, 2 skipped. The skips are existing platform symlink limitations.
- Acceptance: `OPEN / NOT_ACCEPTED`. The global suite is not a V4-04 accepted release test. Resolve the M14 import mismatch and classify the other global failures under this audit item before claiming repository-wide green status.
- Next stage for this audit item: isolate each global failure against its own module baseline, repair or explicitly disposition it, then rerun the global suite. This work does not authorize V4-05 or alter accepted V4-00 through V4-03 artifacts.

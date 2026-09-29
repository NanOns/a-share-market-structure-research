from __future__ import annotations

from scripts.record_v4_00_01_02_03_joint_test_receipt import (
    parse_skip_details,
    parse_terminal_summary,
)


def test_pytest_short_summary_header_does_not_replace_test_counts() -> None:
    output = """\
=========================== short test summary info ===========================
SKIPPED [1] tests/v4_phase0/test_tdx_snapshot.py:101: symlink creation is unavailable on this runner
272 passed, 2 skipped in 3.12s
"""
    assert parse_terminal_summary(output) == "272 passed, 2 skipped in 3.12s"
    skips = parse_skip_details(output)
    assert skips["count"] == 1
    assert skips["unexplained_skip_count"] == 0
    assert skips["required_scope_skip_count"] == 0


def test_required_scope_skip_is_marked_as_blocking() -> None:
    output = "SKIPPED [1] tests/v4_01/test_required_scope_gate.py:10: fixture unavailable"
    skips = parse_skip_details(output)
    assert skips["required_scope_skip_count"] == 1
    assert skips["items"][0]["scope_disposition"] == "BLOCKED_REQUIRED_SCOPE_SKIP"

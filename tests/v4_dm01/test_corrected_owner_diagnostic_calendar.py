from pathlib import Path
from types import SimpleNamespace

import pytest

from workbench_analysis.market_source_acquisition import (
    bind_dm01_calendar_for_diagnostic_candidate,
    diagnostic_session_authority,
    official_sessions,
)


def snapshot(sessions=None):
    return {
        "status": "DM01_ACCEPTED_BASE_PLUS_R4_CALENDAR_DIAGNOSTIC_CANDIDATE",
        "source_bindings": [
            {"role": "accepted_data_head", "path": "data/v4/V4_DATA_ACCEPTED_HEAD.json",
             "sha256": "a" * 64, "bytes": 128},
            {"role": "r4_calendar", "path": "data/v4/DM01_R4_CALENDAR_HEAD_V1.json",
             "sha256": "b" * 64, "bytes": 256},
        ],
        "payload_digest": "c" * 64,
        "production_admission": False,
        "session_dates": sessions or ["2026-10-08", "2026-10-09"],
    }


def test_diagnostic_calendar_is_scoped_and_does_not_replace_default_reader():
    root = Path.cwd()
    fallback = SimpleNamespace(sessions=lambda: ["2026-09-30"])

    assert official_sessions(root, pg_reader=fallback) == ["2026-09-30"]
    with bind_dm01_calendar_for_diagnostic_candidate(root, snapshot()) as authority:
        assert official_sessions(root, pg_reader=fallback, source_mode="PG") == [
            "2026-10-08", "2026-10-09"]
        assert authority["contract_id"] == "V4_DM01_CALENDAR_COMPOSITE_DIAGNOSTIC_CANDIDATE_R1"
        assert diagnostic_session_authority() == authority
    assert diagnostic_session_authority() is None
    assert official_sessions(root, pg_reader=fallback) == ["2026-09-30"]


def test_diagnostic_calendar_rejects_unordered_sessions_and_workspace_mismatch():
    with pytest.raises(ValueError, match="DM01_DIAGNOSTIC_CALENDAR_AUTHORITY_INVALID"):
        with bind_dm01_calendar_for_diagnostic_candidate(
                Path.cwd(), snapshot(["2026-10-09", "2026-10-08"])):
            pass

    with bind_dm01_calendar_for_diagnostic_candidate(Path.cwd(), snapshot()):
        with pytest.raises(ValueError, match="DIAGNOSTIC_CALENDAR_WORKSPACE_MISMATCH"):
            official_sessions(Path("G:/other-v4-workspace"), source_mode="PG")

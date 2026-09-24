from datetime import date, datetime, timezone

from src.focus_tracker.contracts import SOURCE_AUTHORITY_CONTRACT
from src.focus_tracker.read_api import FocusTrackerReadAPI


class _Cursor:
    def __init__(self, row):
        self.row = row

    def execute(self, _query, _params):
        pass

    def fetchone(self):
        return self.row


def test_explicit_trade_date_matches_postgres_date_value():
    run_id = "focus-run-test"
    row = (
        run_id, date(2026, 9, 23), 1, "publication-1", SOURCE_AUTHORITY_CONTRACT,
        ["V3_SHORTLIST_STOCK"], {"V3_SHORTLIST_STOCK": "COMPLETE"},
        "FOCUS_PATH_STATE_V1", "PARAMS_V1", "REAL_FORWARD", "ACTIVATED",
        "PENDING", datetime(2026, 9, 23, tzinfo=timezone.utc), "VALID", True,
    )

    resolved = FocusTrackerReadAPI(dsn="unused")._resolve_run(
        _Cursor(row), None, "2026-09-23")

    assert resolved is not None
    assert resolved["focus_run_id"] == run_id
    assert resolved["trade_date"] == "2026-09-23"

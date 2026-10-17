from datetime import date, datetime, timezone
import hashlib
import json

import pytest

from workbench_analysis.market_source_acquisition import official_sessions
from workbench_db.v4_market_calendar_reader_r1 import (
    MarketCalendarReadError,
    PgMarketCalendarReader,
    from_environment,
)


IDENTITY = {"database": "market_research", "database_oid": 16384, "host": "127.0.0.1", "port": 5432}
ACCEPTED_AT = datetime(2026, 10, 16, 16, 0, tzinfo=timezone.utc)
CALENDAR_CONTRACT = {
    "contract_id": "V4_OFFICIAL_MARKET_CALENDAR_V1", "version": "1.0.0",
    "agreement": True, "exchanges": ["SSE", "SZSE"],
    "session_relation": "v4.market_calendar_sessions",
    "session_numbering": "CONTIGUOUS_STARTING_AT_ONE",
    "calendar_digest_semantics": "ONE_SHA256_FOR_COMPLETE_ORDERED_SESSION_SET",
    "historical_PIT_permission": False, "automated_trading_permission": False,
}
CONTRACT_BYTES = json.dumps(CALENDAR_CONTRACT, sort_keys=True, separators=(",", ":")).encode()
CONTRACT_SHA = hashlib.sha256(CONTRACT_BYTES).hexdigest()


class Cursor:
    def __init__(self, one=None, rows=None):
        self.one = one
        self.rows = rows or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.rows


class FakePg:
    def __init__(self, *, sessions=None, identity=IDENTITY):
        self.sessions = sessions or [
            (1, date(2026, 10, 15), "a" * 64),
            (2, date(2026, 10, 16), "a" * 64),
        ]
        self.identity = tuple(identity[k] for k in ("database", "database_oid", "host", "port"))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        if sql.startswith("SET "):
            return Cursor()
        if "inet_server_addr()" in sql:
            return Cursor(one=self.identity)
        if "FROM pg_roles r" in sql:
            return Cursor(one=("v4_reader",) + (False,) * 13)
        if "FROM v4.publication_heads" in sql:
            return Cursor(one=("pub-20261016-r1", 1, date(2026, 10, 16), ACCEPTED_AT,
                              "calendar-r1", {"V4_OFFICIAL_MARKET_CALENDAR_V1": {"version": "1.0.0", "raw_sha256": CONTRACT_SHA}}))
        if "current_setting('transaction_isolation')" in sql:
            if "current_database()" in sql:
                return Cursor(one=("market_research", "v4_reader", "repeatable read", "on"))
            return Cursor(one=("repeatable read", "on"))
        if ("FROM v4.publications p" in sql and "p.revision_no=%s" in sql
                and "JOIN v4.model_namespaces" not in sql):
            return Cursor(one=({"V4_OFFICIAL_MARKET_CALENDAR_V1": {"version": "1.0.0", "raw_sha256": CONTRACT_SHA}},))
        if "JOIN v4.model_namespaces" in sql and "contract_bindings" in sql:
            return Cursor(one=({"V4_OFFICIAL_MARKET_CALENDAR_V1": {"version": "1.0.0", "raw_sha256": CONTRACT_SHA}},
                               "v4-main", "ACCEPTED", ACCEPTED_AT, date(2026, 10, 16)))
        if "FROM v4.contract_versions c" in sql:
            return Cursor(one=(CONTRACT_BYTES, CONTRACT_SHA, "JSON", "1", "v4-main", "source-r1",
                               "APPROVED", "approver", "approval-r1", ACCEPTED_AT,
                               "approval-source-r1", CONTRACT_SHA, ACCEPTED_AT))
        if "FROM v4.market_calendar_sessions" in sql:
            return Cursor(rows=self.sessions)
        raise AssertionError(f"unexpected query: {sql}")


def factory(pg):
    class Context:
        def __enter__(self):
            return pg

        def __exit__(self, *_):
            return False
    return lambda: Context()


def test_pg_market_calendar_reader_uses_accepted_head_contract_and_ordered_sessions():
    reader = PgMarketCalendarReader(
        namespace_id="v4-main", expected_database_identity=IDENTITY,
        connection_factory=factory(FakePg()),
    )
    assert reader.sessions() == ["2026-10-15", "2026-10-16"]


def test_pg_calendar_exposes_verified_metadata_for_daily_gap_planning():
    reader = PgMarketCalendarReader(
        namespace_id="v4-main", expected_database_identity=IDENTITY,
        connection_factory=factory(FakePg()),
    )
    calendar = reader.calendar()
    assert calendar["agreement"] is True
    assert calendar["exchanges"] == ["SSE", "SZSE"]
    assert calendar["accepted_trade_date"] == "2026-10-16"
    assert calendar["coverage_start"] == "2026-10-15"
    assert calendar["binding"]["market_calendar_id"] == "calendar-r1"


def test_market_source_acquisition_calendar_entry_can_be_pinned_to_pg():
    reader = PgMarketCalendarReader(
        namespace_id="v4-main", expected_database_identity=IDENTITY,
        connection_factory=factory(FakePg()),
    )
    assert official_sessions("unused", pg_reader=reader, source_mode="PG") == ["2026-10-15", "2026-10-16"]


def test_official_session_consumers_select_pg_calendar_from_runtime_mode(monkeypatch):
    class Reader:
        def sessions(self):
            return ["2026-10-15", "2026-10-16"]

    monkeypatch.setenv("V4_MARKET_CALENDAR_SOURCE", "PG")
    monkeypatch.setattr("workbench_db.v4_market_calendar_reader_r1.from_environment", lambda: Reader())
    assert official_sessions("no-file-head-here") == ["2026-10-15", "2026-10-16"]


def test_pg_calendar_configuration_is_required_and_does_not_fall_back():
    with pytest.raises(MarketCalendarReadError, match="PG_MARKET_CALENDAR_IDENTITY_REQUIRED"):
        from_environment({})


@pytest.mark.parametrize("sessions", [
    [(1, date(2026, 10, 15), "a" * 64), (3, date(2026, 10, 16), "a" * 64)],
    [(1, date(2026, 10, 16), "a" * 64), (2, date(2026, 10, 15), "a" * 64)],
    [(1, date(2026, 10, 15), "a" * 64), (2, date(2026, 10, 16), "b" * 64)],
])
def test_pg_calendar_rejects_sequence_date_or_digest_mismatch(sessions):
    reader = PgMarketCalendarReader(
        namespace_id="v4-main", expected_database_identity=IDENTITY,
        connection_factory=factory(FakePg(sessions=sessions)),
    )
    with pytest.raises(MarketCalendarReadError, match="MARKET_CALENDAR_SEQUENCE_OR_DIGEST_INVALID"):
        reader.sessions()

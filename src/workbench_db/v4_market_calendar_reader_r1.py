"""Read the current accepted market calendar from its PG publication Head."""
from __future__ import annotations

import json
import os
import re
from datetime import date
from typing import Any, Callable, Mapping

from workbench_analysis.contract_registry_pg_v1 import (
    ContractRegistryError,
    load_publication_contracts,
)
from .v4_publication_reader import PgPublicationReader, readonly_connection


CONTRACT_ID = "V4_PG_MARKET_CALENDAR_READER_R1"
CALENDAR_CONTRACT_ID = "V4_OFFICIAL_MARKET_CALENDAR_V1"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class MarketCalendarReadError(ValueError):
    pass


def from_environment(environ: Mapping[str, str] | None = None) -> "PgMarketCalendarReader":
    env = os.environ if environ is None else environ
    raw_identity = env.get("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON")
    namespace_id = env.get("V4_PG_MODEL_NAMESPACE_ID")
    if not raw_identity or not namespace_id:
        raise MarketCalendarReadError("PG_MARKET_CALENDAR_IDENTITY_REQUIRED")
    try:
        identity = json.loads(raw_identity)
    except (TypeError, ValueError) as exc:
        raise MarketCalendarReadError("PG_MARKET_CALENDAR_IDENTITY_INVALID") from exc
    if (not isinstance(identity, dict)
            or set(identity) != {"database", "database_oid", "host", "port"}
            or not isinstance(identity.get("database"), str)
            or isinstance(identity.get("database_oid"), bool)
            or not isinstance(identity.get("database_oid"), int)
            or not isinstance(identity.get("host"), str)
            or isinstance(identity.get("port"), bool)
            or not isinstance(identity.get("port"), int)):
        raise MarketCalendarReadError("PG_MARKET_CALENDAR_IDENTITY_INVALID")
    return PgMarketCalendarReader(namespace_id=namespace_id, expected_database_identity=identity)


class PgMarketCalendarReader:
    def __init__(
        self,
        *,
        namespace_id: str,
        expected_database_identity: Mapping[str, Any],
        connection_factory: Callable[[], Any] = readonly_connection,
    ):
        if not isinstance(namespace_id, str) or not namespace_id.strip():
            raise MarketCalendarReadError("PG_MARKET_CALENDAR_NAMESPACE_REQUIRED")
        if set(expected_database_identity) != {"database", "database_oid", "host", "port"}:
            raise MarketCalendarReadError("PG_MARKET_CALENDAR_IDENTITY_REQUIRED")
        self.namespace_id = namespace_id
        self.expected_database_identity = dict(expected_database_identity)
        self.connection_factory = connection_factory

    def sessions(self) -> list[str]:
        with self.connection_factory() as pg:
            try:
                pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                pg.execute("SET LOCAL statement_timeout='15s'")
                pg.execute("SET LOCAL lock_timeout='5s'")
                identity_row = pg.execute(
                    """SELECT current_database(),
                              (SELECT oid FROM pg_database WHERE datname=current_database()),
                              inet_server_addr()::text, inet_server_port()"""
                ).fetchone()
                identity = dict(zip(("database", "database_oid", "host", "port"), identity_row, strict=True))
                if identity != self.expected_database_identity:
                    raise MarketCalendarReadError("PG_DATABASE_IDENTITY_MISMATCH")
                PgPublicationReader._attest_read_role(pg)
                head = pg.execute(
                    """SELECT p.publication_id, p.revision_no, p.trade_date,
                              p.accepted_at, p.market_calendar_id, p.contract_bindings
                         FROM v4.publication_heads h
                         JOIN v4.publications p ON p.publication_id=h.publication_id
                        WHERE h.model_namespace_id=%s AND p.status='ACCEPTED'
                        ORDER BY h.trade_date DESC LIMIT 1""",
                    (self.namespace_id,),
                ).fetchone()
                if not head:
                    raise MarketCalendarReadError("NO_ACCEPTED_PUBLICATION_HEAD")
                publication_id, revision_no, trade_date, accepted_at, calendar_id, contract_bindings = head
                if (not publication_id or not calendar_id or not accepted_at
                        or not isinstance(revision_no, int) or isinstance(revision_no, bool)
                        or revision_no < 1):
                    raise MarketCalendarReadError("PUBLICATION_CALENDAR_BINDING_INVALID")
                try:
                    registered_contracts=load_publication_contracts(pg, publication_id, revision_no, contract_bindings)
                except ContractRegistryError as exc:
                    raise MarketCalendarReadError(str(exc)) from exc
                rows = pg.execute(
                    """SELECT session_no, trade_date, calendar_digest
                         FROM v4.market_calendar_sessions
                        WHERE market_calendar_id=%s ORDER BY session_no""",
                    (calendar_id,),
                ).fetchall()
            except MarketCalendarReadError:
                raise
            except Exception as exc:
                code = getattr(exc, "sqlstate", None)
                if code == "42501":
                    raise MarketCalendarReadError("PG_READ_PERMISSION_DENIED") from exc
                if code in {"42P01", "42703"}:
                    raise MarketCalendarReadError("PG_MARKET_CALENDAR_SCHEMA_UNAVAILABLE") from exc
                if isinstance(exc, ContractRegistryError):
                    raise MarketCalendarReadError(str(exc)) from exc
                raise MarketCalendarReadError("PG_MARKET_CALENDAR_READ_FAILED") from exc
        if not rows:
            raise MarketCalendarReadError("MARKET_CALENDAR_EMPTY")
        sessions = []
        digest = None
        prior_no = None
        prior_date = None
        for session_no, trade_day, calendar_digest in rows:
            try:
                normalized = trade_day.isoformat() if isinstance(trade_day, date) else date.fromisoformat(str(trade_day)).isoformat()
            except (TypeError, ValueError) as exc:
                raise MarketCalendarReadError("MARKET_CALENDAR_DATE_INVALID") from exc
            current_digest = str(calendar_digest).strip().lower()
            if (not isinstance(session_no, int) or isinstance(session_no, bool)
                    or (prior_no is not None and session_no != prior_no + 1)
                    or (prior_date is not None and normalized <= prior_date)
                    or not _DIGEST.fullmatch(current_digest)
                    or (digest is not None and digest != current_digest)):
                raise MarketCalendarReadError("MARKET_CALENDAR_SEQUENCE_OR_DIGEST_INVALID")
            digest = current_digest
            prior_no, prior_date = session_no, normalized
            sessions.append(normalized)
        selected_date = trade_date.isoformat() if isinstance(trade_date, date) else str(trade_date)
        if selected_date not in sessions:
            raise MarketCalendarReadError("HEAD_TRADE_DATE_OUTSIDE_MARKET_CALENDAR")
        self._last_read=dict(publication_id=publication_id,publication_revision=revision_no,
            accepted_trade_date=selected_date,market_calendar_id=calendar_id,
            calendar_digest=digest,session_dates=sessions,contracts=registered_contracts)
        return sessions

    def calendar(self) -> dict[str, Any]:
        sessions=self.sessions()
        read=getattr(self,"_last_read",{})
        contract=read.get("contracts",{}).get(CALENDAR_CONTRACT_ID)
        metadata=contract.parsed_json if contract is not None else None
        if (not isinstance(metadata,dict)
                or metadata.get("contract_id")!=CALENDAR_CONTRACT_ID
                or metadata.get("version")!="1.0.0"
                or metadata.get("agreement") is not True
                or metadata.get("exchanges")!=["SSE","SZSE"]
                or metadata.get("session_relation")!="v4.market_calendar_sessions"
                or metadata.get("session_numbering")!="CONTIGUOUS_STARTING_AT_ONE"
                or metadata.get("calendar_digest_semantics")!="ONE_SHA256_FOR_COMPLETE_ORDERED_SESSION_SET"
                or metadata.get("historical_PIT_permission") is not False
                or metadata.get("automated_trading_permission") is not False):
            raise MarketCalendarReadError("OFFICIAL_MARKET_CALENDAR_CONTRACT_INVALID")
        binding=dict(publication_id=read["publication_id"],
            publication_revision=read["publication_revision"],
            market_calendar_id=read["market_calendar_id"],
            calendar_digest=read["calendar_digest"],
            contract_id=contract.contract_id,contract_version=contract.version,
            contract_sha256=contract.raw_sha256)
        return dict(contract_id=CALENDAR_CONTRACT_ID,status="ACCEPTED",agreement=True,
            exchanges=["SSE","SZSE"],coverage_start=sessions[0],coverage_end=sessions[-1],
            accepted_trade_date=read["accepted_trade_date"],session_dates=sessions,
            binding=binding,source="PG_ACCEPTED_PUBLICATION_HEAD")

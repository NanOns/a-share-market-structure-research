"""Versioned PostgreSQL writers for M14 online evidence and quotes."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from psycopg import sql

from .postgres_repository import PostgresRepository


def _utc_timestamp(value: datetime | str | None, *, required: bool, code: str) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ValueError(code + "_MISSING")
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(code + "_OFFSET_REQUIRED")
    return parsed


class PostgresOnlineRepository:
    """External evidence/quote persistence with explicit UTC instant contracts."""

    CONTRACT_VERSION = "PG_ONLINE_TIME_CONTRACT_V1"

    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def _connection(self):
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        return self.repository.connection

    def insert_evidence(self, item: Mapping[str, Any]) -> None:
        required = {"evidence_id", "source_id", "evidence_type", "security_id", "first_seen_at", "text_hash", "raw_ref"}
        if not required.issubset(item) or any(not str(item.get(key) or "").strip() for key in required if key not in {"first_seen_at"}):
            raise ValueError("ONLINE_EVIDENCE_SCHEMA_INVALID")
        first_seen = _utc_timestamp(item.get("first_seen_at"), required=True, code="FIRST_SEEN_AT")
        event_time = _utc_timestamp(item.get("event_time"), required=False, code="EVENT_TIME")
        published_at = _utc_timestamp(item.get("published_at"), required=False, code="PUBLISHED_AT")
        query = sql.SQL(
            "insert into {schema}.online_evidence "
            "(evidence_id,source_id,evidence_type,security_id,source_code,trade_date,event_time,published_at,first_seen_at,title,summary,text_hash,raw_ref,source_url,personal_research_only) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict(evidence_id) do nothing"
        ).format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (
                str(item["evidence_id"]), str(item["source_id"]), str(item["evidence_type"]), str(item["security_id"]),
                item.get("source_code"), item.get("trade_date"), event_time, published_at, first_seen,
                item.get("title"), item.get("summary"), str(item["text_hash"]), str(item["raw_ref"]), item.get("source_url"),
                bool(item.get("personal_research_only", True)),
            ))

    def insert_quote(self, item: Mapping[str, Any]) -> None:
        required = {"batch_id", "security_id", "quote_time", "quote_state", "source_code", "price_unit", "amount_unit", "volume_unit"}
        if not required.issubset(item) or any(not str(item.get(key) or "").strip() for key in required if key != "quote_time"):
            raise ValueError("ONLINE_QUOTE_SCHEMA_INVALID")
        quote_time = _utc_timestamp(item.get("quote_time"), required=True, code="QUOTE_TIME")
        query = sql.SQL(
            "insert into {schema}.online_quote_entries "
            "(batch_id,security_id,quote_time,price,ret1,amount,volume,quote_state,source_code,price_unit,amount_unit,volume_unit,extra,personal_research_only) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s) on conflict(batch_id,security_id) do nothing"
        ).format(schema=sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (
                str(item["batch_id"]), str(item["security_id"]), quote_time, item.get("price"), item.get("ret1"), item.get("amount"), item.get("volume"),
                str(item["quote_state"]), str(item["source_code"]), str(item["price_unit"]), str(item["amount_unit"]), str(item["volume_unit"]),
                json.dumps(item.get("extra") or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), bool(item.get("personal_research_only", True)),
            ))


__all__ = ["PostgresOnlineRepository"]

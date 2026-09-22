"""Transactional PostgreSQL research-run writer boundary.

The service is not wired to this class yet.  A caller owns the surrounding
``PostgresRepository.transaction()`` so a run and all of its result rows share
one commit/rollback boundary.
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

from psycopg import sql

from .postgres_repository import PostgresRepository
from workbench_service.research_runs import JOB_TYPE, validate_research_job


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _canonical(value: Any) -> str:
    return json.dumps(_clean(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)


def _input_key(request: Mapping[str, Any]) -> str:
    identity = {
        "publication_id": str(request["publication_id"]),
        "trade_date": str(request["trade_date"]),
        "snapshot_id": str(request["snapshot_id"]),
        "membership_snapshot_id": str(request["membership_snapshot_id"]),
        "algorithm_version": str(request["algorithm_version"]),
        "parameter_hash": str(request["parameter_hash"]),
        "dependency_bindings": request.get("dependency_bindings") or {},
    }
    return hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()


class PostgresResearchRepository:
    """Research run/state writer with stable input identity and idempotency."""

    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def _connection(self):
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        return self.repository.connection

    def start(self, body: Mapping[str, Any]) -> dict[str, Any]:
        request = validate_research_job(dict(body))
        key = _input_key(request)
        with self._connection().cursor() as cur:
            cur.execute(sql.SQL("select run_id,status from {schema}.research_runs where input_key=%s").format(schema=sql.Identifier(self.repository.schema)), (key,))
            existing = cur.fetchone()
            if existing:
                if existing[1] == "FAILED":
                    cur.execute(sql.SQL("update {schema}.research_runs set status='BUILDING',error_code=null where run_id=%s and status='FAILED'").format(schema=sql.Identifier(self.repository.schema)), (existing[0],))
                    return {"run_id": str(existing[0]), "status": "BUILDING", "reused": True, "input_key": key}
                return {"run_id": str(existing[0]), "status": str(existing[1]), "reused": True, "input_key": key}
            run_id = "research-" + uuid.uuid4().hex
            cur.execute(
                sql.SQL(
                    "insert into {schema}.research_runs "
                    "(run_id,input_key,trade_date,publication_id,snapshot_id,membership_snapshot_id,algorithm_version,parameter_hash,dependency_bindings,history_basis,status,created_at) "
                    "values (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)"
                ).format(schema=sql.Identifier(self.repository.schema)),
                (run_id, key, request["trade_date"], request["publication_id"], request["snapshot_id"], request["membership_snapshot_id"], request["algorithm_version"], request["parameter_hash"], _canonical(request["dependency_bindings"]), "LOCAL_CLOSE_ONLY", "BUILDING", datetime.now(timezone.utc)),
            )
        return {"run_id": run_id, "status": "BUILDING", "reused": False, "input_key": key, "job_type": JOB_TYPE}

    def complete(self, run_id: str, *, sector_states: Iterable[Mapping[str, Any]] = (), member_roles: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
        with self._connection().cursor() as cur:
            cur.execute(sql.SQL("select status from {schema}.research_runs where run_id=%s").format(schema=sql.Identifier(self.repository.schema)), (run_id,))
            current = cur.fetchone()
            if not current:
                raise ValueError("RESEARCH_RUN_NOT_FOUND")
            if current[0] == "COMPLETE":
                return {"run_id": run_id, "status": "COMPLETE", "reused": True}
            if current[0] != "BUILDING":
                raise ValueError("RESEARCH_RUN_NOT_BUILDING")
            state_query = sql.SQL(
                "insert into {schema}.research_sector_states "
                "(run_id,sector_id,current_eligible,potential_eligible,potential_branch,potential_branches,current_rank,potential_rank,m1,b1,rel1,p1,q5,q20,dq5_3,b_delta3,ma20_width,ma20_delta3,early_width,amount_a,top1_positive_share,member_count,quote_valid_count,feature_valid_count,early_count,positive_count,quote_coverage,feature_coverage,risk_coverage,quality,reason_codes,evidence,input_members_hash,rank_universe_hash) "
                "values (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)"
            ).format(schema=sql.Identifier(self.repository.schema))
            for row in sector_states:
                cur.execute(state_query, (run_id, row["sector_id"], row.get("current_eligible"), row.get("potential_eligible"), row.get("potential_branch"), _canonical(row.get("potential_branches", {})), row.get("current_rank"), row.get("potential_rank"), row.get("m1"), row.get("b1"), row.get("rel1"), row.get("p1"), row.get("q5"), row.get("q20"), row.get("dq5_3"), row.get("b_delta3"), row.get("ma20_width"), row.get("ma20_delta3"), row.get("early_width"), row.get("amount_a"), row.get("top1_positive_share"), row.get("member_count"), row.get("quote_valid_count"), row.get("feature_valid_count"), row.get("early_count"), row.get("positive_count"), row.get("quote_coverage"), row.get("feature_coverage"), row.get("risk_coverage"), row.get("quality", "UNKNOWN"), _canonical(row.get("reason_codes", [])), _canonical(row.get("evidence", {})), row.get("input_members_hash"), row.get("rank_universe_hash")))
            role_query = sql.SQL(
                "insert into {schema}.research_sector_member_roles "
                "(run_id,sector_id,security_id,role,role_rank,today_rank,role_reason_codes,evidence) "
                "values (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)"
            ).format(schema=sql.Identifier(self.repository.schema))
            for row in member_roles:
                cur.execute(role_query, (run_id, row["sector_id"], row["security_id"], row["role"], row["role_rank"], row.get("today_rank"), _canonical(row.get("role_reason_codes", [])), _canonical(row.get("evidence", {}))))
            cur.execute(sql.SQL("update {schema}.research_runs set status='COMPLETE',completed_at=%s where run_id=%s").format(schema=sql.Identifier(self.repository.schema)), (datetime.now(timezone.utc), run_id))
        return {"run_id": run_id, "status": "COMPLETE", "reused": False}

    def fail(self, run_id: str, error_code: str) -> None:
        with self._connection().cursor() as cur:
            cur.execute(sql.SQL("update {schema}.research_runs set status='FAILED',error_code=%s where run_id=%s and status='BUILDING'").format(schema=sql.Identifier(self.repository.schema)), (str(error_code), run_id))

    def visible(self, run_id: str) -> dict[str, Any]:
        with self._connection().cursor() as cur:
            cur.execute(sql.SQL("select run_id,input_key,trade_date,publication_id,status,completed_at from {schema}.research_runs where run_id=%s and status='COMPLETE'").format(schema=sql.Identifier(self.repository.schema)), (run_id,))
            row = cur.fetchone()
        if not row:
            raise ValueError("RESEARCH_RUN_NOT_VISIBLE")
        return dict(zip(("run_id", "input_key", "trade_date", "publication_id", "status", "completed_at"), row))


__all__ = ["PostgresResearchRepository"]

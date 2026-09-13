"""Transactional P07-03 research-run storage boundary."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import uuid
from typing import Any, Iterable

import duckdb

from pathlib import Path


CONTRACT_ID = "RESEARCH_RUN_PREVIEW_1"
JOB_TYPE = "BUILD_RESEARCH_V3"
VISIBLE_STATUS = "COMPLETE"


class ResearchRunError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def research_input_key(*, publication_id: str, trade_date: Any, snapshot_id: str, membership_snapshot_id: str, algorithm_version: str, parameter_hash: str, dependency_bindings: dict[str, Any]) -> str:
    payload = {
        "publication_id": str(publication_id), "trade_date": str(trade_date), "snapshot_id": str(snapshot_id),
        "membership_snapshot_id": str(membership_snapshot_id), "algorithm_version": str(algorithm_version),
        "parameter_hash": str(parameter_hash), "dependency_bindings": dependency_bindings,
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def validate_research_job(body: dict[str, Any]) -> dict[str, Any]:
    allowed = {"job_type", "publication_id", "trade_date", "algorithm_version", "parameter_hash", "snapshot_id", "membership_snapshot_id", "dependency_bindings"}
    unknown = sorted(set(body).difference(allowed))
    if unknown:
        raise ResearchRunError("RESEARCH_JOB_UNKNOWN_FIELD:" + ",".join(unknown))
    if str(body.get("job_type", JOB_TYPE)) != JOB_TYPE:
        raise ResearchRunError("RESEARCH_JOB_TYPE_INVALID")
    required = ("publication_id", "trade_date", "algorithm_version", "parameter_hash", "snapshot_id", "membership_snapshot_id")
    missing = [name for name in required if not str(body.get(name) or "").strip()]
    if missing:
        raise ResearchRunError("RESEARCH_JOB_FIELD_REQUIRED:" + ",".join(missing))
    try:
        normalized_date = date.fromisoformat(str(body["trade_date"])).isoformat()
    except ValueError as exc:
        raise ResearchRunError("RESEARCH_JOB_TRADE_DATE_INVALID") from exc
    return {**body, "job_type": JOB_TYPE, "trade_date": normalized_date, "dependency_bindings": body.get("dependency_bindings") or {}}


class ResearchRunStore:
    """The only writer for a run: BUILDING rows are never query-visible."""

    def __init__(self, connection: duckdb.DuckDBPyConnection):
        self.connection = connection
        schema_path = Path(__file__).resolve().parents[1] / "workbench_db" / "research_runs_schema.sql"
        self.connection.execute(schema_path.read_text(encoding="utf-8"))

    def start(self, body: dict[str, Any]) -> dict[str, Any]:
        request = validate_research_job(body)
        key = research_input_key(
            publication_id=request["publication_id"], trade_date=request["trade_date"], snapshot_id=request["snapshot_id"],
            membership_snapshot_id=request["membership_snapshot_id"], algorithm_version=request["algorithm_version"],
            parameter_hash=request["parameter_hash"], dependency_bindings=request["dependency_bindings"],
        )
        existing = self.connection.execute("SELECT run_id,status FROM research_runs WHERE input_key=?", [key]).fetchone()
        if existing:
            return {"run_id": existing[0], "status": existing[1], "reused": True, "input_key": key}
        run_id = "research-" + uuid.uuid4().hex
        self.connection.execute(
            """INSERT INTO research_runs
               (run_id,input_key,trade_date,publication_id,snapshot_id,membership_snapshot_id,
                algorithm_version,parameter_hash,dependency_bindings,history_basis,status,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [run_id, key, request["trade_date"], request["publication_id"], request["snapshot_id"], request["membership_snapshot_id"], request["algorithm_version"], request["parameter_hash"], _canonical(request["dependency_bindings"]), "LOCAL_CLOSE_ONLY", "BUILDING", datetime.now(timezone.utc)],
        )
        return {"run_id": run_id, "status": "BUILDING", "reused": False, "input_key": key}

    def complete(self, run_id: str, *, stock_states: Iterable[dict[str, Any]] = (), sector_states: Iterable[dict[str, Any]] = (), signal_states: Iterable[dict[str, Any]] = (), member_roles: Iterable[dict[str, Any]] = (), shortlists: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
        current = self.connection.execute("SELECT status FROM research_runs WHERE run_id=?", [run_id]).fetchone()
        if not current:
            raise ResearchRunError("RESEARCH_RUN_NOT_FOUND")
        if current[0] == "COMPLETE":
            return {"run_id": run_id, "status": "COMPLETE", "reused": True}
        if current[0] != "BUILDING":
            raise ResearchRunError("RESEARCH_RUN_NOT_BUILDING")
        try:
            self.connection.execute("BEGIN TRANSACTION")
            for row in stock_states:
                self.connection.execute("""INSERT INTO research_stock_states VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", [run_id, row["security_id"], row.get("setup"), row.get("breakout"), row.get("recovery"), row.get("trend_background"), row.get("structure_break"), row.get("quality", "UNKNOWN"), row.get("bias20"), row.get("sigma20"), row.get("extension_z20"), row.get("dist_high20"), row.get("range5"), row.get("range20"), row.get("rps5_delta3"), row.get("liquidity20_amount"), _canonical(row.get("risk_codes", [])), _canonical(row.get("reason_codes", [])), _canonical(row.get("evidence", {}))])
            for row in sector_states:
                self.connection.execute("""INSERT INTO research_sector_states VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", [run_id, row["sector_id"], row.get("current_eligible"), row.get("potential_eligible"), row.get("potential_branch"), _canonical(row.get("potential_branches", {})), row.get("current_rank"), row.get("potential_rank"), row.get("m1"), row.get("b1"), row.get("rel1"), row.get("p1"), row.get("q5"), row.get("q20"), row.get("dq5_3"), row.get("b_delta3"), row.get("ma20_width"), row.get("ma20_delta3"), row.get("early_width"), row.get("amount_a"), row.get("top1_positive_share"), row.get("member_count"), row.get("quote_valid_count"), row.get("feature_valid_count"), row.get("early_count"), row.get("positive_count"), row.get("quote_coverage"), row.get("feature_coverage"), row.get("risk_coverage"), row.get("quality", "UNKNOWN"), _canonical(row.get("reason_codes", [])), _canonical(row.get("evidence", {})), row.get("input_members_hash"), row.get("rank_universe_hash")])
            for row in signal_states:
                self.connection.execute("""INSERT INTO research_sector_signal_state VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", [run_id, row["sector_id"], row.get("episode_id"), row.get("first_seen_date"), row.get("last_qualified_date"), row.get("end_date"), row.get("age_sessions"), row.get("miss_sessions"), row.get("reset_sessions"), row.get("lifecycle"), row.get("end_reason"), row.get("prior_run_id"), bool(row.get("history_complete", False))])
            for row in member_roles:
                self.connection.execute("""INSERT INTO research_sector_member_roles VALUES (?,?,?,?,?,?,?,?)""", [run_id, row["sector_id"], row["security_id"], row["role"], row["role_rank"], row.get("today_rank"), _canonical(row.get("role_reason_codes", [])), _canonical(row.get("evidence", {}))])
            for row in shortlists:
                self.connection.execute("""INSERT INTO research_shortlist VALUES (?,?,?,?,?,?,?,?,?,?,?)""", [run_id, row["list_type"], row["security_id"], row["rank"], row.get("primary_sector_id"), _canonical(row.get("alternative_sector_ids", [])), _canonical(row.get("selection_reason", [])), _canonical(row.get("waiting_for", [])), _canonical(row.get("invalid_if", [])), row.get("previous_state"), row.get("change_reason")])
            self.connection.execute("UPDATE research_runs SET status='COMPLETE',completed_at=? WHERE run_id=?", [datetime.now(timezone.utc), run_id])
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        return {"run_id": run_id, "status": "COMPLETE", "reused": False}

    def fail(self, run_id: str, error_code: str) -> None:
        self.connection.execute("UPDATE research_runs SET status='FAILED',error_code=? WHERE run_id=? AND status='BUILDING'", [str(error_code), run_id])

    def visible(self, run_id: str) -> dict[str, Any]:
        row = self.connection.execute("SELECT run_id,input_key,trade_date,publication_id,status,completed_at FROM research_runs WHERE run_id=? AND status='COMPLETE'", [run_id]).fetchone()
        if not row:
            raise ResearchRunError("RESEARCH_RUN_NOT_VISIBLE")
        return dict(zip(("run_id", "input_key", "trade_date", "publication_id", "status", "completed_at"), row))


__all__ = ["CONTRACT_ID", "JOB_TYPE", "ResearchRunError", "ResearchRunStore", "research_input_key", "validate_research_job"]

"""P12-11 verified registration of immutable V3.3 research bundles."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

import duckdb

from workbench_service.research_bundle_v3_3 import read_active


CONTRACT_ID = "TODAY_RESEARCH_V3_3_DATABASE_REGISTRY_01"
SUPPORTED_BUNDLE_CONTRACTS = {
    "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_02",
    "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO",
}


class ResearchRegistryV33Error(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ResearchRegistryV33Error("V3_3_NON_FINITE_NUMBER")
    return number


def _load(pointer: Path) -> tuple[dict[str, Any], Path, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    active = read_active(pointer)
    if not active:
        raise ResearchRegistryV33Error("V3_3_ACTIVE_BUNDLE_MISSING")
    bundle_path = Path(active["bundle_path"]).resolve()
    manifest = json.loads((bundle_path / "bundle.json").read_text(encoding="utf-8"))
    results = json.loads((bundle_path / "results.json").read_text(encoding="utf-8"))
    contracts = json.loads((bundle_path / "contracts.json").read_text(encoding="utf-8"))
    if manifest.get("contract_id") not in SUPPORTED_BUNDLE_CONTRACTS:
        raise ResearchRegistryV33Error("V3_3_BUNDLE_CONTRACT_UNSUPPORTED")
    identity = manifest.get("identity") or {}
    required_identity = (
        "research_run_id", "trade_date", "publication_id", "snapshot_id",
        "membership_snapshot_id", "parameter_hash", "dependency_lock_hash", "history_basis",
    )
    if any(not str(identity.get(key) or "").strip() for key in required_identity):
        raise ResearchRegistryV33Error("V3_3_IDENTITY_INCOMPLETE")
    try:
        target_date = date.fromisoformat(str(identity["trade_date"])).isoformat()
    except ValueError as exc:
        raise ResearchRegistryV33Error("V3_3_TRADE_DATE_INVALID") from exc
    if not isinstance(results, list):
        raise ResearchRegistryV33Error("V3_3_RESULTS_NOT_LIST")
    seen: set[str] = set()
    for row in results:
        security_id = str(row.get("security_id") or "").strip()
        if not security_id or security_id in seen:
            raise ResearchRegistryV33Error("V3_3_SECURITY_ID_MISSING_OR_DUPLICATE")
        seen.add(security_id)
        row_date = row.get("trade_date")
        if row_date is not None and str(row_date) != target_date:
            raise ResearchRegistryV33Error("V3_3_RESULT_DATE_MISMATCH")
        if not isinstance(row.get("factor_evidence"), dict) or not isinstance(row.get("scanner_evidence"), dict):
            raise ResearchRegistryV33Error("V3_3_RESULT_EVIDENCE_MISSING")
        _canonical(row)
    return active, bundle_path, manifest, results, contracts


def register_active_bundle(connection: duckdb.DuckDBPyConnection, pointer: str | Path) -> dict[str, Any]:
    active, bundle_path, manifest, results, contracts = _load(Path(pointer))
    digest = str(manifest["output_digest"])
    identity = manifest["identity"]
    existing = connection.execute(
        "SELECT result_count,status FROM research_runs_v3_3 WHERE bundle_digest=?", [digest]
    ).fetchone()
    if existing:
        actual = connection.execute(
            "SELECT count(*) FROM research_candidates_v3_3 WHERE bundle_digest=?", [digest]
        ).fetchone()[0]
        if existing[1] != "COMPLETE" or existing[0] != len(results) or actual != len(results):
            raise ResearchRegistryV33Error("V3_3_EXISTING_REGISTRY_INCONSISTENT")
        return {"contract_id": CONTRACT_ID, "bundle_digest": digest, "result_count": len(results), "status": "COMPLETE", "reused": True}
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute(
            """INSERT INTO research_runs_v3_3 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [digest, identity["research_run_id"], identity["trade_date"], identity["publication_id"],
             identity["snapshot_id"], identity["membership_snapshot_id"], manifest["contract_id"],
             identity["parameter_hash"], identity["dependency_lock_hash"], identity["history_basis"],
             len(results), str(bundle_path), _canonical(contracts), "COMPLETE", datetime.now(timezone.utc)],
        )
        for row in results:
            connection.execute(
                """INSERT INTO research_candidates_v3_3 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [digest, row["security_id"], identity["trade_date"], row.get("security_name"),
                 row.get("primary_category"), _canonical(row.get("matched_categories", [])),
                 row.get("category_rank"), _finite_or_none(row.get("category_score")),
                 str(row.get("rank_status") or "UNKNOWN"), row.get("selection_mode"),
                 row.get("sector_support_status"), _canonical(row.get("risk_codes", [])),
                 _canonical(row["factor_evidence"]), _canonical(row["scanner_evidence"]), _canonical(row)],
            )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return {"contract_id": CONTRACT_ID, "bundle_digest": digest, "result_count": len(results), "status": "COMPLETE", "reused": False, "active_digest": active["output_digest"]}


__all__ = ["CONTRACT_ID", "ResearchRegistryV33Error", "register_active_bundle"]

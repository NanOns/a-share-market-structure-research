"""Export verified producer-format technical rows from accepted PostgreSQL data."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import psycopg
from psycopg import sql

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.contracts import canonical_bytes
from src.focus_tracker.technical_identity import CONTRACT_ID, canonical_technical_identity
from workbench_analysis.technical import TECHNICAL_RESULT_COLUMNS, _technical_hash


ROOT = Path(__file__).resolve().parents[1]
OBJECT_ID = "result-obj-26d6c569b3493670830a8cedbd177419"


def export(*, object_id: str = OBJECT_ID) -> dict[str, object]:
    if not re.fullmatch(r"result-obj-[0-9a-f]{32}", object_id):
        raise ValueError("invalid technical result object id")
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select exists(select 1 from workbench.analysis_snapshot_heads h "
                        "join workbench.publication_heads p on p.trade_date=h.trade_date "
                        "and p.publication_id=h.publication_id "
                        "join workbench.analysis_snapshots s on s.snapshot_id=h.snapshot_id "
                        "join workbench.analysis_snapshot_entries e on e.snapshot_id=h.snapshot_id "
                        "and e.domain='technical' and e.trade_date=h.trade_date "
                        "join workbench.analysis_slice_result_bindings b on b.slice_id=e.slice_id "
                        "where b.result_object_id=%s and h.domain in "
                        "('LOCAL_OBSERVED','LOCAL_RECONSTRUCTED') "
                        "and s.status='SUCCESS' and s.cutoff_date=h.trade_date)", (object_id,))
            if not cur.fetchone()[0]:
                raise ValueError("technical object lacks exact accepted publication binding")
            cur.execute("select value_hash,row_count,semantic_contract from "
                        "workbench.analysis_result_objects where result_object_id=%s", (object_id,))
            registered = cur.fetchone()
            if registered is None or registered[2] != "TECHNICAL_RESULT_V3":
                raise ValueError("technical result registration unavailable")
            cur.execute(sql.SQL("select {} from workbench.technical_result_rows "
                                "where result_object_id=%s order by security_id,trade_date")
                        .format(sql.SQL(",").join(map(sql.Identifier, TECHNICAL_RESULT_COLUMNS))),
                        (object_id,))
            rows = [dict(zip(TECHNICAL_RESULT_COLUMNS, row)) for row in cur.fetchall()]
        connection.rollback()
    canonical_hash, canonical_logical, canonical_count = canonical_technical_identity(rows)
    for row in rows:
        row["quality_codes"] = json.dumps(row["quality_codes"], ensure_ascii=False)
        row["basis_json"] = json.dumps(row["basis_json"], ensure_ascii=False, sort_keys=True)
    legacy_hash, legacy_count, _ = _technical_hash(rows)
    if (legacy_hash != registered[0] or
            legacy_count != canonical_count or legacy_count != registered[1]):
        raise ValueError("producer-format technical reconstruction mismatch")
    payload = b"".join(canonical_bytes(row) + b"\n" for row in rows)
    evidence_sha = hashlib.sha256(payload).hexdigest()
    target = ROOT / "runtime/focus_evidence" / f"technical-legacy-{object_id}-{evidence_sha}.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != payload:
            raise ValueError("technical evidence file identity conflict")
    else:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".technical-legacy-", suffix=".tmp",
                                                       dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, target)
        finally:
            Path(temporary_name).unlink(missing_ok=True)
    return {"contract_id": CONTRACT_ID, "status": "PRODUCER_FORMAT_RECONCILED",
            "source_object_id": object_id, "legacy_hash": legacy_hash,
            "canonical_hash": canonical_hash, "canonical_logical_hash": canonical_logical,
            "row_count": legacy_count, "backup_sha256": evidence_sha,
            "evidence_path": str(target),
            "migration_reason": "PG_JSONB_RECONSTRUCTED_WITH_ORIGINAL_PRODUCER_JSON_SERIALIZER"}


if __name__ == "__main__":
    print(json.dumps(export(), ensure_ascii=False, sort_keys=True))

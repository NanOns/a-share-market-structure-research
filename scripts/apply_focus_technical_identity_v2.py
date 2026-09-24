"""Register a reconciled technical identity without changing accepted rows.

Default mode rolls back the schema and receipt. --apply commits both atomically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.export_focus_technical_legacy_evidence import OBJECT_ID as FORWARD_OBJECT
from scripts.export_focus_technical_legacy_evidence import export as export_forward_evidence
from scripts.probe_focus_technical_identity_v2 import DEFAULT_BACKUP, DEFAULT_OBJECT, run
from src.focus_tracker.technical_identity import CONTRACT_ID


DDL_PATH = Path(__file__).resolve().parents[1] / "src/workbench_db/focus_technical_identity_v2.sql"
EXPECTED_EVIDENCE_SHA256 = {
    DEFAULT_OBJECT: "793dae0682a79aaf7b21366baad39ab899a5b043e9cde06e14fdeb1e92650cac",
    FORWARD_OBJECT: "ce101e6869493fac53c324d63b92508e65539d0e446bb9d597d36cd35577de39",
}
VERSION = "FOCUS_TECHNICAL_IDENTITY_MIGRATION_V2"
COLUMNS = ("source_object_id", "legacy_hash", "canonical_hash", "canonical_logical_hash",
           "row_count", "backup_sha256", "migration_reason", "migration_contract_id")


def install(*, apply: bool, object_id: str = DEFAULT_OBJECT) -> dict[str, object]:
    evidence = (run(backup=DEFAULT_BACKUP, object_id=object_id)
                if object_id == DEFAULT_OBJECT else export_forward_evidence(object_id=object_id))
    if (object_id in EXPECTED_EVIDENCE_SHA256 and
            evidence["backup_sha256"] != EXPECTED_EVIDENCE_SHA256[object_id]):
        raise ValueError("technical identity backup evidence changed")
    ddl = DDL_PATH.read_text("utf-8")
    checksum = hashlib.sha256(ddl.encode("utf-8")).hexdigest()
    expected = (evidence["source_object_id"], evidence["legacy_hash"],
                evidence["canonical_hash"], evidence["canonical_logical_hash"],
                evidence["row_count"], evidence["backup_sha256"],
                evidence["migration_reason"], CONTRACT_ID)
    with psycopg.connect(_dsn()) as connection:
        try:
            with connection.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))", (VERSION,))
                cur.execute("select checksum,status from workbench_meta.schema_migrations "
                            "where version=%s", (VERSION,))
                old = cur.fetchone()
                if old and old != (checksum, "COMPLETE"):
                    raise ValueError("technical identity schema ledger conflict")
                cur.execute(ddl)
                cur.execute("insert into workbench.focus_technical_identity_migrations "
                            "(source_object_id,legacy_hash,canonical_hash,canonical_logical_hash,"
                            "row_count,backup_sha256,migration_reason,migration_contract_id) "
                            "values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing", expected)
                cur.execute("select source_object_id,legacy_hash,canonical_hash,"
                            "canonical_logical_hash,row_count,backup_sha256,"
                            "migration_reason,migration_contract_id "
                            "from workbench.focus_technical_identity_migrations "
                            "where source_object_id=%s", (evidence["source_object_id"],))
                stored = cur.fetchone()
                if stored != expected:
                    raise ValueError("technical identity immutable receipt conflict")
                if apply and not old:
                    cur.execute("insert into workbench_meta.schema_migrations "
                                "(version,checksum,applied_at,status) "
                                "values (%s,%s,now(),'COMPLETE')", (VERSION, checksum))
            if apply:
                connection.commit()
            else:
                connection.rollback()
        except Exception:
            connection.rollback()
            raise
    return {**evidence, "schema_version": VERSION, "schema_checksum": checksum,
            "mode": "APPLIED" if apply else "ROLLBACK_REHEARSAL"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--result-object-id", default=DEFAULT_OBJECT)
    options = parser.parse_args()
    print(json.dumps(install(apply=options.apply, object_id=options.result_object_id),
                     ensure_ascii=False, sort_keys=True))

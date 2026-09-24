"""Register exact-publication technical identity after accepted PG synchronization."""
from __future__ import annotations

import argparse
import json
from datetime import date

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.apply_focus_technical_identity_v2 import install


CONTRACT_ID = "FOCUS_TECHNICAL_IDENTITY_REGISTRATION_V1"


def accepted_object(*, trade_date: date, publication_id: str) -> str:
    with psycopg.connect(_dsn()) as connection:
        with connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select b.result_object_id from workbench.publication_heads p "
                        "join workbench.analysis_snapshot_heads h "
                        "on h.trade_date=p.trade_date and h.publication_id=p.publication_id "
                        "join workbench.analysis_snapshots s on s.snapshot_id=h.snapshot_id "
                        "join workbench.analysis_snapshot_entries e on e.snapshot_id=h.snapshot_id "
                        "and e.domain='technical' and e.trade_date=h.trade_date "
                        "join workbench.analysis_slice_result_bindings b on b.slice_id=e.slice_id "
                        "where p.trade_date=%s and p.publication_id=%s "
                        "and h.domain in ('LOCAL_OBSERVED','LOCAL_RECONSTRUCTED') "
                        "and s.status='SUCCESS' and s.cutoff_date=%s",
                        (trade_date, publication_id, trade_date))
            objects = {row[0] for row in cur.fetchall()}
        connection.rollback()
    if len(objects) != 1:
        raise ValueError("exact accepted publication technical object unavailable or ambiguous")
    return next(iter(objects))


def register(*, trade_date: date, publication_id: str, apply: bool) -> dict[str, object]:
    object_id = accepted_object(trade_date=trade_date, publication_id=publication_id)
    result = install(apply=apply, object_id=object_id)
    return {"contract_id": CONTRACT_ID,
            "status": "ACCEPTED" if apply else "ROLLBACK_READY",
            "trade_date": trade_date.isoformat(), "publication_id": publication_id,
            "source_object_id": object_id,
            "legacy_hash": result["legacy_hash"],
            "canonical_hash": result["canonical_hash"],
            "evidence_sha256": result["backup_sha256"],
            "row_count": result["row_count"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-date", required=True, type=date.fromisoformat)
    parser.add_argument("--publication-id", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        report = register(trade_date=args.trade_date,
                          publication_id=args.publication_id, apply=args.apply)
    except (ValueError, RuntimeError, psycopg.Error, OSError) as exc:
        report = {"contract_id": CONTRACT_ID, "status": "BLOCKED",
                  "trade_date": args.trade_date.isoformat(),
                  "publication_id": args.publication_id,
                  "reason": str(exc)}
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        raise SystemExit(2)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))

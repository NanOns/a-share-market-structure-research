"""Verify and register one accepted publication's missing package SHA-256."""
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.contracts import digest
from src.workbench_input.pipeline import verify_source_bundle_membership_identity


CONTRACT_ID = "FOCUS_PUBLICATION_SOURCE_IDENTITY_MIGRATION_V1"
ROOT = Path(__file__).resolve().parents[1]
DDL = ROOT / "src/workbench_db/focus_publication_identity_migrations_v1.sql"


def _verified_candidate(cur, target_date: date) -> dict[str, object]:
    cur.execute("""select h.publication_id,p.status,p.source_identity_sha256,p.source_path
        from workbench.publication_heads h join workbench.publications p using(publication_id)
        where h.trade_date=%s""", (target_date,))
    rows = cur.fetchall()
    if len(rows) != 1:
        raise ValueError("SOURCE_IDENTITY_EXPECTED_ONE_ACCEPTED_PUBLICATION")
    publication_id, status, native_sha, source_path = rows[0]
    if status != "SUCCESS":
        raise ValueError("SOURCE_IDENTITY_PUBLICATION_NOT_SUCCESS")
    if not source_path:
        raise ValueError("SOURCE_IDENTITY_PUBLICATION_PATH_MISSING")
    bundle_path = Path(str(source_path))
    if not bundle_path.is_absolute():
        bundle_path = ROOT / bundle_path
    bundle_path = bundle_path.resolve(strict=True)
    catalog = (ROOT / "data/source_bundles").resolve(strict=True)
    if catalog not in bundle_path.parents:
        raise ValueError("SOURCE_IDENTITY_BUNDLE_OUTSIDE_CATALOG")
    identity = verify_source_bundle_membership_identity(bundle_path / "source_bundle.json")
    if date.fromisoformat(str(identity["target_trade_date"])) != target_date:
        raise ValueError("SOURCE_IDENTITY_BUNDLE_TRADE_DATE_MISMATCH")
    bundle_id = str(identity["source_bundle_id"])
    if bundle_path.name != bundle_id:
        raise ValueError("SOURCE_IDENTITY_BUNDLE_ID_PATH_MISMATCH")
    package_sha = str(identity["package_sha256"])
    if native_sha and str(native_sha).strip() != package_sha:
        raise ValueError("SOURCE_IDENTITY_NATIVE_SHA_CONFLICT")
    cur.execute("""select source_identity_sha256,source_bundle_id,
        source_bundle_manifest_sha256,target_trade_date,evidence_digest
        from workbench.publication_source_identity_migrations where publication_id=%s""",
        (publication_id,))
    existing = cur.fetchone()
    payload = {"contract_id": CONTRACT_ID, "publication_id": str(publication_id),
               "target_trade_date": target_date,
               "source_bundle_id": bundle_id,
               "source_bundle_manifest_sha256": str(identity["manifest_sha256"]),
               "source_identity_sha256": package_sha}
    evidence_digest = digest(payload)
    expected = (package_sha, bundle_id, str(identity["manifest_sha256"]),
                target_date, evidence_digest)
    if existing and tuple(str(value) for value in existing) != tuple(str(value) for value in expected):
        raise ValueError("SOURCE_IDENTITY_EXISTING_MIGRATION_CONFLICT")
    return {**payload, "evidence_digest": evidence_digest,
            "existing": existing is not None,
            "native_identity_present": bool(native_sha)}


def migrate(*, target_date: date, apply: bool = False) -> dict[str, object]:
    checked_at = datetime.now(timezone.utc)
    with psycopg.connect(_dsn()) as con:
        try:
            with con.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))",
                            (CONTRACT_ID + ":" + target_date.isoformat(),))
                cur.execute(DDL.read_text("utf-8"))
                candidate = _verified_candidate(cur, target_date)
                inserted = False
                if not candidate["native_identity_present"] and not candidate["existing"]:
                    cur.execute("""insert into workbench.publication_source_identity_migrations
                        (publication_id,source_identity_sha256,source_bundle_id,
                         source_bundle_manifest_sha256,target_trade_date,contract_id,
                         verified_at_utc,evidence_digest,verifier_id)
                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (candidate["publication_id"], candidate["source_identity_sha256"],
                         candidate["source_bundle_id"],
                         candidate["source_bundle_manifest_sha256"], target_date,
                         CONTRACT_ID, checked_at, candidate["evidence_digest"], CONTRACT_ID))
                    inserted = True
                cur.execute("""select source_identity_sha256,source_bundle_id,
                    source_bundle_manifest_sha256,target_trade_date,evidence_digest
                    from workbench.publication_source_identity_migrations where publication_id=%s""",
                    (candidate["publication_id"],))
                stored = cur.fetchone()
                if inserted and stored is None:
                    raise RuntimeError("SOURCE_IDENTITY_MIGRATION_READBACK_FAILED")
                if apply:
                    con.commit()
                else:
                    con.rollback()
        except Exception:
            con.rollback()
            raise
    report = {"contract_id": CONTRACT_ID,
              "mode": "APPLIED" if apply else "ROLLBACK_REHEARSAL",
              "status": "PASS", "checked_at_utc": checked_at.isoformat(),
              "migration": candidate, "inserted": inserted,
              "publication_row_mutated": False,
              "readback": list(stored) if stored else None}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-date", required=True, type=date.fromisoformat)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        result = migrate(target_date=args.trade_date, apply=args.apply)
    except (RuntimeError, ValueError, psycopg.Error) as exc:
        result = {"contract_id": CONTRACT_ID, "mode": "APPLY" if args.apply else "PREVIEW",
                  "status": "BLOCKED", "reason": str(exc)}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

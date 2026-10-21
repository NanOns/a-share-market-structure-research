"""R8 candidate-only PG publication ledger and recoverable Head CAS bridge.

This version uses a pending PG row, a finalized transaction file, an append-only
PG state event, and independent post-commit readback. It grants no production
or PIT permission.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from psycopg.types.json import Jsonb

from .v4_native import connection, create_schema, workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore

CONTRACT = "V4_R8_REAL_APPEND_PG_RECEIPT_R2"
FOLDER = "data/v4/r8_publication_bridge_v1"
DDL = """
CREATE TABLE IF NOT EXISTS r8_publications(
    candidate_token text PRIMARY KEY CHECK (candidate_token ~ '^[0-9a-f]{64}$'),
    trade_date date NOT NULL,
    predecessor_head_sha256 text NOT NULL CHECK (predecessor_head_sha256 ~ '^[0-9a-f]{64}$'),
    candidate_head_sha256 text NOT NULL CHECK (candidate_head_sha256 ~ '^[0-9a-f]{64}$'),
    owner_authority_sha256 text NOT NULL CHECK (owner_authority_sha256 ~ '^[0-9a-f]{64}$'),
    source_freeze_sha256 text NOT NULL CHECK (source_freeze_sha256 ~ '^[0-9a-f]{64}$'),
    readback jsonb NOT NULL,
    inserted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE OR REPLACE FUNCTION reject_r8_publication_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'R8_PUBLICATION_LEDGER_APPEND_ONLY'; END $$;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='r8_publications'::regclass AND tgname='r8_publications_append_only') THEN
  CREATE TRIGGER r8_publications_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON r8_publications
  FOR EACH STATEMENT EXECUTE FUNCTION reject_r8_publication_mutation();
 END IF;
END $$;
CREATE TABLE IF NOT EXISTS r8_publication_events(
    event_id bigserial PRIMARY KEY,
    candidate_token text NOT NULL,
    event_type text NOT NULL CHECK (event_type IN ('FINALIZED','ABORTED','CORRECTION_NO_PRODUCTION_ACCEPTANCE')),
    row_sha256 text NOT NULL CHECK (row_sha256 ~ '^[0-9a-f]{64}$'),
    evidence jsonb NOT NULL,
    inserted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS r8_publication_events_token_idx ON r8_publication_events(candidate_token,event_id);
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='r8_publication_events'::regclass AND tgname='r8_publication_events_append_only') THEN
  CREATE TRIGGER r8_publication_events_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON r8_publication_events
  FOR EACH STATEMENT EXECUTE FUNCTION reject_r8_publication_mutation();
 END IF;
END $$;
"""


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare_schema(root):
    root = Path(root).resolve()
    if root.drive.upper() != "G:" or not root.is_relative_to(Path("G:/codex_tmp").resolve()):
        raise ValueError("R8_CANDIDATE_G_DRIVE_ROOT_REQUIRED")
    folder = root / FOLDER
    schema = workspace_schema(folder, "r8pub")
    with connection(schema) as pg:
        create_schema(pg, schema)
        pg.execute(DDL)
        identity = ForwardFactStore._database_identity(pg)
    return schema, identity


def recover_candidate_publications(root):
    """Reconcile file CAS and PG append rows after a process restart.

    Recovery only changes a candidate below G:/codex_tmp. It never mutates a
    publication row: it appends FINALIZED or ABORTED events and restores the
    exact archived predecessor when the HTTP readback had not completed.
    """
    import os
    from workbench_analysis.operational_daily_storage_v1 import atomic_json, exclusive_lock
    from workbench_analysis.r43_owner_replay import checked
    from workbench_analysis.tdx_official_daily_source import sha256_file, _atomic_write
    root = Path(root).resolve()
    if os.environ.get("R4_NATIVE_ISOLATION") != "1" or root.drive.upper() != "G:" or not root.is_relative_to(Path("G:/codex_tmp").resolve()):
        raise ValueError("R8_CANDIDATE_ISOLATION_REQUIRED")
    schema, identity = prepare_schema(root)
    tx_dir = root / "runtime/dynamic_daily/publication_transactions"
    head = root / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json"
    recovered = []
    if not tx_dir.exists():
        return {"contract_id":"V4_R8_PUBLICATION_RECOVERY_R1","status":"NO_PENDING_TRANSACTIONS","items":[]}
    with exclusive_lock(root, root / "runtime/dynamic_daily/publisher.lock"):
        for path in sorted(tx_dir.glob("*.json")):
            record = json.loads(path.read_bytes())
            if record.get("r8_publication_contract") != CONTRACT or record.get("state") not in ("CAS_COMPLETE_READBACK_PENDING", "COMMITTED"):
                continue
            token = record.get("candidate_token")
            if not isinstance(token, str) or path.stem != token:
                raise ValueError("R8_RECOVERY_TRANSACTION_TOKEN_INVALID")
            with connection(schema) as pg:
                current_identity = ForwardFactStore._database_identity(pg)
                row = pg.execute("SELECT candidate_token,trade_date::text,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback FROM r8_publications WHERE candidate_token=%s", (token,)).fetchone()
                events = pg.execute("SELECT event_type FROM r8_publication_events WHERE candidate_token=%s ORDER BY event_id DESC LIMIT 1", (token,)).fetchone()
            if current_identity != identity:
                raise ValueError("R8_RECOVERY_PG_IDENTITY_MISMATCH")
            if row is None:
                if record.get("state") != "CAS_COMPLETE_READBACK_PENDING":
                    raise ValueError("R8_RECOVERY_FINALIZED_PG_ROW_MISSING")
                archive_ref = record.get("predecessor")
                before = checked(root, archive_ref).read_bytes()
                if sha256_file(head) != record.get("head_sha256"):
                    raise ValueError("R8_RECOVERY_HEAD_MOVED_FAIL_CLOSED")
                _atomic_write(head, before, tdx_root=Path("D:/new_tdx"))
                atomic_json(root, path, {"state":"ROLLED_BACK","candidate_token":token,
                    "predecessor":archive_ref,"recovery":"FAILED_BEFORE_PG_INSERT"})
                recovered.append({"candidate_token":token,"event_type":"ROLLED_BACK_NO_PG_ROW"})
                continue
            if events and events[0] in ("FINALIZED", "ABORTED", "CORRECTION_NO_PRODUCTION_ACCEPTANCE"):
                continue
            actual_head = sha256_file(head)
            if record.get("state") == "CAS_COMPLETE_READBACK_PENDING":
                archive_ref = record.get("predecessor")
                before = checked(root, archive_ref).read_bytes()
                if actual_head != record.get("head_sha256"):
                    raise ValueError("R8_RECOVERY_HEAD_MOVED_FAIL_CLOSED")
                _atomic_write(head, before, tdx_root=Path("D:/new_tdx"))
                atomic_json(root, path, {"state":"ROLLED_BACK","candidate_token":token,
                    "predecessor":archive_ref,"recovery":"PG_COMMITTED_BEFORE_READBACK"})
                event_type = "ABORTED"
                event_evidence = {"reason":"RESTART_BEFORE_FINALIZE_READBACK","restored_head_sha256":sha256_file(head)}
            else:
                if actual_head != record.get("head_sha256") or row[6].get("status") != "PENDING":
                    raise ValueError("R8_RECOVERY_FINALIZED_HEAD_OR_ROW_MISMATCH")
                readback = record.get("readback")
                if not isinstance(readback,dict) or readback.get("context_token") != token or readback.get("production_accepted") is not False:
                    archive_ref = record.get("predecessor")
                    before = checked(root, archive_ref).read_bytes()
                    _atomic_write(head, before, tdx_root=Path("D:/new_tdx"))
                    atomic_json(root, path, {"state":"ROLLED_BACK","candidate_token":token,
                        "predecessor":archive_ref,"recovery":"RESTART_BEFORE_HTTP_READBACK"})
                    event_type = "ABORTED"
                    event_evidence = {"reason":"RESTART_BEFORE_HTTP_READBACK","restored_head_sha256":sha256_file(head)}
                else:
                    event_type = "FINALIZED"
                    event_evidence = {"transaction_sha256":_sha(path.read_bytes()),"readback":readback,
                        "recovered_after_restart":True}
            row_sha = _sha(_canonical([*row[:6], row[6]]))
            with connection(schema) as pg:
                pg.execute("INSERT INTO r8_publication_events(candidate_token,event_type,row_sha256,evidence) VALUES(%s,%s,%s,%s)",
                    (token,event_type,row_sha,Jsonb(event_evidence)))
            recovered.append({"candidate_token":token,"event_type":event_type,"row_sha256":row_sha})
    return {"contract_id":"V4_R8_PUBLICATION_RECOVERY_R1","status":"PASS","database_identity":identity,
        "schema":schema,"recovered":recovered}




def publish_candidate(root, candidate, *, append_evidence_binding, rollback_evidence_binding, readback):
    """CAS one isolated candidate through a recoverable, append-only protocol.

    The PG pending row commits before the HTTP readback. A finalization event is
    appended only after the transaction file is durable and G4 independently
    verifies the PG row, Head, transaction, and same-token readback.
    """
    import os

    from workbench_analysis.operational_daily_storage_v1 import atomic_json, exclusive_lock
    from workbench_analysis.r43_owner_replay import checked, ref
    from workbench_analysis.operational_successor_v1 import validate, digest
    from workbench_analysis.operational_successor_release_v1 import _commit_pointers
    from workbench_analysis.operational_daily_exact_policy_v2 import verify, KERNEL
    from workbench_analysis.tdx_official_daily_source import sha256_file, _atomic_write

    root = Path(root).resolve()
    if os.environ.get("R4_NATIVE_ISOLATION") != "1" or root.drive.upper() != "G:" or not root.is_relative_to(Path("G:/codex_tmp").resolve()):
        raise ValueError("R8_CANDIDATE_ISOLATION_REQUIRED")
    recover_candidate_publications(root)
    validate(root, candidate)
    policy, _ = verify(root, candidate["release_policy"], candidate_only=True)
    if candidate.get("accepted_algorithm_bindings") != policy.get("accepted_algorithm_bindings"):
        raise ValueError("R8_CANDIDATE_POLICY_BINDING_MISMATCH")
    if candidate.get("exact_daily_adjustment_contract") != KERNEL:
        raise ValueError("R8_EXACT_DAILY_ADJUSTMENT_BINDING_REQUIRED")

    evidence = json.loads(checked(root, append_evidence_binding).read_bytes())
    if (evidence.get("contract_id") != "V4_R8_APPEND_G123_EVIDENCE_R1"
            or evidence.get("candidate_token") != digest(candidate)
            or evidence.get("target_session") != candidate["accepted_trade_date"]):
        raise ValueError("R8_G123_EVIDENCE_CANDIDATE_BINDING_REQUIRED")
    from workbench_analysis.r8_candidate_append_comparator import compare_candidate_append
    comparison = compare_candidate_append(**evidence["comparator_input"])
    if comparison["G1"] != "PASS" or comparison["G2"] != "PASS" or comparison["G3"] != "PASS":
        raise ValueError("R8_G123_INDEPENDENT_EVIDENCE_REQUIRED:" + ",".join(comparison["errors"]))
    rollback = json.loads(checked(root, rollback_evidence_binding).read_bytes())
    if (rollback.get("contract_id") != "V4_R8_CAS_ROLLBACK_DRILL_R1"
            or rollback.get("status") != "PASS" or rollback.get("candidate_token") != digest(candidate)
            or rollback.get("head_restored_exactly") is not True
            or rollback.get("last_good_head_sha256") != candidate["predecessor"]["sha256"]
            or rollback.get("publication_rows_after_failure") != 0):
        raise ValueError("R8_CAS_ROLLBACK_EVIDENCE_REQUIRED")

    token = digest(candidate)
    day = candidate["accepted_trade_date"]
    head = root / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json"
    joint = root / "config/v4_current_native_joint_authority_v3.json"
    # Preserve one immutable transaction receipt per candidate token. A later
    # corrected candidate on the same T0 must not overwrite the audit bytes
    # referenced by an earlier append receipt.
    transaction = root / "runtime/dynamic_daily/publication_transactions" / (digest(candidate) + ".json")
    schema, database_identity = prepare_schema(root)
    expected = candidate["predecessor"]["sha256"]
    # The R8 candidate-only policy does not authorize the separate full
    # current-joint admission contract. Keep that pointer byte-identical.
    joint_before = joint.read_bytes() if joint.is_file() else None
    joint_binding = None
    joint_bytes = None
    joint_previous = None

    day_receipt = json.loads(checked(root, candidate["day_receipt"]).read_bytes())
    owner_authority = candidate.get("native_pg_owner_authority")
    source_freeze = day_receipt.get("source_freeze")
    if not isinstance(owner_authority, dict) or not isinstance(source_freeze, dict):
        raise ValueError("R8_OWNER_AND_SOURCE_PROVENANCE_REQUIRED")

    with exclusive_lock(root, root / "runtime/dynamic_daily/publisher.lock"):
        if sha256_file(head) != expected or candidate["predecessor"]["sha256"] != expected:
            raise ValueError("STALE_OPERATIONAL_HEAD_CAS")
        before = head.read_bytes()
        archive = head.parent / "predecessors" / (expected + ".json")
        _atomic_write(archive, before, tdx_root=Path("D:/new_tdx"))
        coordination = dict(current_joint=joint_binding, current_joint_predecessor=joint_previous,
            r8_publication_contract=CONTRACT)

        def verified_readback(current_candidate):
            candidate_head_sha = sha256_file(head)
            with connection(schema) as pg:
                if ForwardFactStore._database_identity(pg) != database_identity:
                    raise ValueError("R8_PUBLICATION_DATABASE_IDENTITY_CHANGED")
                pending_readback = {"status":"PENDING", "context_token":token, "accepted_trade_date":day,
                    "production_accepted":False, "read_scope":"DEVELOPMENT_CANDIDATE_PREVIEW"}
                pg.execute("INSERT INTO r8_publications(candidate_token,trade_date,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (candidate_token) DO NOTHING",
                    (token, day, expected, candidate_head_sha, owner_authority["sha256"], source_freeze["sha256"], Jsonb(pending_readback)))
                row = pg.execute("SELECT candidate_token,trade_date::text,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback FROM r8_publications WHERE candidate_token=%s", (token,)).fetchone()
                if row is None or row[:6] != (token, day, expected, candidate_head_sha, owner_authority["sha256"], source_freeze["sha256"]) or row[6] != pending_readback:
                    raise ValueError("R8_PUBLICATION_PG_READBACK_MISMATCH")
            # PG is committed before the externally observable readback. The
            # file is still CAS_PENDING, so a restart can distinguish this
            # crash window and recover idempotently.
            atomic_json(root, transaction, dict(state="COMMITTED", predecessor=ref(root, archive),
                head_sha256=candidate_head_sha, pg_schema=schema, candidate_token=token, **coordination))
            observed = readback(current_candidate)
            if (observed.get("status") != "PASS" or observed.get("context_token") != token
                    or observed.get("accepted_trade_date") != day
                    or observed.get("production_accepted") is not False
                    or observed.get("read_scope") != "DEVELOPMENT_CANDIDATE_PREVIEW"):
                raise ValueError("R8_HTTP_SAME_TOKEN_READBACK_FAILED")
            return observed

        try:
            result = _commit_pointers(root, head, joint, transaction, candidate, before, archive,
                                      coordination, joint_before, joint_bytes, verified_readback)
        except BaseException:
            (root / FOLDER / "receipts" / (token + ".json")).unlink(missing_ok=True)
            # Append-only compensation preserves the original row and records
            # why this token must remain invisible to accepted consumers.
            try:
                with connection(schema) as pg:
                    row = pg.execute("SELECT candidate_token,trade_date::text,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback FROM r8_publications WHERE candidate_token=%s", (token,)).fetchone()
                    if row and not pg.execute("SELECT 1 FROM r8_publication_events WHERE candidate_token=%s AND event_type='FINALIZED'",(token,)).fetchone():
                        row_sha = _sha(_canonical([*row[:6], row[6]]))
                        pg.execute("INSERT INTO r8_publication_events(candidate_token,event_type,row_sha256,evidence) VALUES(%s,'ABORTED',%s,%s)",
                            (token,row_sha,Jsonb({"reason":"PUBLISH_CALLBACK_FAILED","candidate_head_sha256":row[3]})))
            except Exception:
                pass
            raise
        # _commit_pointers has now durably finalized the transaction file.
        # Only now append the PG finalization event and invoke the independent
        # G4 reader. This ordering makes a crash before this point fail closed.
        finalized_tx = json.loads(transaction.read_bytes())
        finalized_readback = finalized_tx.get("readback")
        if finalized_tx.get("state") != "COMMITTED" or finalized_tx.get("candidate_token") != token:
            raise ValueError("R8_PUBLICATION_TRANSACTION_FINALIZE_MISMATCH")
        with connection(schema) as pg:
            row = pg.execute("SELECT candidate_token,trade_date::text,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback FROM r8_publications WHERE candidate_token=%s", (token,)).fetchone()
            if row is None:
                raise ValueError("R8_PUBLICATION_PG_ROW_MISSING_AFTER_FINALIZE")
            row_sha = _sha(_canonical([*row[:6], row[6]]))
            existing = pg.execute("SELECT event_type,row_sha256 FROM r8_publication_events WHERE candidate_token=%s ORDER BY event_id DESC LIMIT 1", (token,)).fetchone()
            if existing is None:
                pg.execute("INSERT INTO r8_publication_events(candidate_token,event_type,row_sha256,evidence) VALUES(%s,'FINALIZED',%s,%s)",
                    (token,row_sha,Jsonb({"transaction_sha256": _sha(transaction.read_bytes()), "readback": finalized_readback})))
            elif existing != ("FINALIZED", row_sha):
                raise ValueError("R8_PUBLICATION_FINALIZATION_CONFLICT")
        receipt_path = root / FOLDER / "receipts" / (token + ".json")
        receipt = dict(contract_id=CONTRACT, version="2.0.0", status="PASS", trade_date=day,
            compute_sessions=[day], candidate_only=True, formal_head_modified=False, production_accepted=False,
            pg_database_identity=database_identity, pg_schema=schema, candidate_token=token,
            predecessor_head_sha256=expected, candidate_head_sha256=candidate_head_sha,
            pg_row_sha256=row_sha, owner_authority=owner_authority, source_freeze=source_freeze,
            publication_transaction=ref(root, transaction), readback=finalized_readback,
            pg_readback_match=True, cas_result="APPLIED", write_count=1, duplicate_write_count=0,
            last_good_preserved_on_failure=True, rollback_drill=rollback_evidence_binding)
        atomic_json(root, receipt_path, receipt)
        final_comparison = compare_candidate_append(**dict(evidence["comparator_input"],
            pg_receipt_binding=ref(root, receipt_path), pg_schema=schema, pg_database_identity=database_identity))
        if final_comparison.get("status") != "PASS":
            with connection(schema) as pg:
                pg.execute("INSERT INTO r8_publication_events(candidate_token,event_type,row_sha256,evidence) VALUES(%s,'ABORTED',%s,%s)",
                    (token,row_sha,Jsonb({"reason":"INDEPENDENT_G4_REJECTED","errors":final_comparison.get("errors",[])})))
            if sha256_file(head) != candidate_head_sha:
                raise ValueError("R8_G4_REJECTED_BUT_HEAD_MOVED_FAIL_CLOSED")
            _atomic_write(head, before, tdx_root=Path("D:/new_tdx"))
            atomic_json(root, transaction, {"state":"ABORTED","candidate_token":token,
                "predecessor":ref(root,archive),"reason":"INDEPENDENT_G4_REJECTED"})
            receipt_path.unlink(missing_ok=True)
            raise ValueError("R8_G1234_INDEPENDENT_EVIDENCE_REQUIRED:" + ",".join(final_comparison["errors"]))
        receipt["append_comparator"] = final_comparison
        atomic_json(root, receipt_path, receipt)

    receipt_path = root / FOLDER / "receipts" / (token + ".json")
    return dict(result, receipt=ref(root, receipt_path), pg_database_identity=database_identity,
                pg_schema=schema, formal_head_modified=False, production_accepted=False)

"""R8 candidate-only PG publication ledger and isolated Head CAS bridge.

This bridge is deliberately limited to a candidate root under G:/codex_tmp.
It records no formal publication and grants no production/PIT permission.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from psycopg.types.json import Jsonb

from .v4_native import connection, create_schema, workspace_schema
from .v4_forward_pg_r1 import ForwardFactStore

CONTRACT = "V4_R8_REAL_APPEND_PG_RECEIPT_R1"
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


def publish_candidate(root, candidate, *, append_evidence_binding, rollback_evidence_binding, readback):
    """CAS one isolated candidate and commit an append-only PG publication row.

    The PG insert runs only after exact-token HTTP readback succeeds. Any
    exception rolls back the filesystem Head in the shared CAS helper and the
    PG transaction. Existing accepted Owners remain immutable.
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
    transaction = root / "runtime/dynamic_daily/publication_transaction.json"
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
        coordination = dict(current_joint=joint_binding, current_joint_predecessor=joint_previous)

        def verified_readback(current_candidate):
            observed = readback(current_candidate)
            if (observed.get("status") != "PASS" or observed.get("context_token") != token
                    or observed.get("accepted_trade_date") != day):
                raise ValueError("R8_HTTP_SAME_TOKEN_READBACK_FAILED")
            candidate_head_sha = sha256_file(head)
            payload = dict(contract_id=CONTRACT, candidate_token=token, trade_date=day,
                predecessor_head_sha256=expected, candidate_head_sha256=candidate_head_sha,
                owner_authority_sha256=owner_authority["sha256"], source_freeze_sha256=source_freeze["sha256"],
                readback=observed, production_accepted=False, formal_head_modified=False)
            receipt_path = root / FOLDER / "receipts" / (token + ".json")
            receipt = dict(contract_id=CONTRACT, version="1.0.0", status="PASS", trade_date=day,
                compute_sessions=[day], candidate_only=True, formal_head_modified=False, production_accepted=False,
                pg_database_identity=database_identity, pg_schema=schema, candidate_token=token,
                predecessor_head_sha256=expected, candidate_head_sha256=candidate_head_sha,
                owner_authority=owner_authority, source_freeze=source_freeze,
                publication_transaction=ref(root, transaction), readback=observed,
                pg_readback_match=True, cas_result="APPLIED", write_count=1, duplicate_write_count=0,
                last_good_preserved_on_failure=True, rollback_drill=rollback_evidence_binding)
            atomic_json(root, receipt_path, receipt)
            receipt_binding = ref(root, receipt_path)
            final_comparison = compare_candidate_append(**dict(evidence["comparator_input"], pg_receipt_binding=receipt_binding))
            if final_comparison.get("status") != "PASS":
                receipt_path.unlink(missing_ok=True)
                raise ValueError("R8_G1234_INDEPENDENT_EVIDENCE_REQUIRED:" + ",".join(final_comparison["errors"]))
            receipt["append_comparator"] = final_comparison
            atomic_json(root, receipt_path, receipt)
            with connection(schema) as pg:
                if ForwardFactStore._database_identity(pg) != database_identity:
                    raise ValueError("R8_PUBLICATION_DATABASE_IDENTITY_CHANGED")
                pg.execute("INSERT INTO r8_publications(candidate_token,trade_date,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (token, day, expected, candidate_head_sha, owner_authority["sha256"], source_freeze["sha256"], Jsonb(observed)))
                row = pg.execute("SELECT candidate_token,trade_date::text,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback FROM r8_publications WHERE candidate_token=%s", (token,)).fetchone()
                if row != (token, day, expected, candidate_head_sha, owner_authority["sha256"], source_freeze["sha256"], observed):
                    raise ValueError("R8_PUBLICATION_PG_READBACK_MISMATCH")
            return observed

        try:
            result = _commit_pointers(root, head, joint, transaction, candidate, before, archive,
                                      coordination, joint_before, joint_bytes, verified_readback)
        except BaseException:
            (root / FOLDER / "receipts" / (token + ".json")).unlink(missing_ok=True)
            raise

    receipt_path = root / FOLDER / "receipts" / (token + ".json")
    return dict(result, receipt=ref(root, receipt_path), pg_database_identity=database_identity,
                pg_schema=schema, formal_head_modified=False, production_accepted=False)

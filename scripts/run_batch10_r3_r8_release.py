"""Candidate-only R8 and D0 publication for a BATCH10-R3 successor.

This command binds the candidate's actual dated Owners and sources into G123,
performs a real isolated Head rollback drill, publishes through the R8 PG CAS,
reads the exact token over 28766, then publishes and reads back D0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "src")]

from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import digest, validate
from workbench_analysis.r8_candidate_append_comparator import _digest, compare_candidate_append
from workbench_analysis.operational_successor_release_v1 import _commit_pointers
from workbench_db.v4_native import connection
from workbench_db.v4_r8_publication_bridge_v1 import prepare_schema, publish_candidate
from workbench_analysis.d0_source_seal_r2 import independent_pg_readback as d0_pg_readback
from workbench_analysis.d0_source_seal_r2 import publish_candidate as publish_d0_candidate
from workbench_analysis.r43_owner_replay import checked, ref
from workbench_analysis.tdx_official_daily_source import _atomic_write


def _local_dsn(root: Path) -> None:
    env_file = root / "config/.env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() in ("WORKBENCH_PG_DSN", "V4_NATIVE_PG_DSN", "V4_NATIVE_PG_READER_DSN") and value.strip():
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    if not os.environ.get("V4_NATIVE_PG_DSN") and os.environ.get("WORKBENCH_PG_DSN"):
        os.environ["V4_NATIVE_PG_DSN"] = os.environ["WORKBENCH_PG_DSN"]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _binding(root: Path, owner: str, value: dict) -> dict:
    path = checked(root, value)
    raw = path.read_bytes()
    return {"owner": owner, "path": value["path"], "bytes": len(raw), "sha256": _sha(raw)}


def make_g123(root: Path, candidate: dict, candidate_path: Path, baseline_path: Path) -> dict:
    baseline = json.loads(baseline_path.read_bytes())
    baseline_ci = baseline["comparator_input"]
    day = candidate["accepted_trade_date"]
    predecessor = candidate["predecessor"]
    source_bindings = []
    for owner, value in candidate["owners"][day].items():
        source_bindings.append(_binding(root, "owner:" + owner, value))
    for owner, value in candidate["source_registry"][day].items():
        source_bindings.append(_binding(root, "source:" + owner, value))
    for owner, value in (("day_receipt", candidate["day_receipt"]),
                         ("native_pg_owner_authority", candidate["native_pg_owner_authority"]),
                         ("membership_snapshot", candidate["membership_snapshot"])):
        source_bindings.append(_binding(root, "candidate:" + owner, value))
    parameters = {"accepted_algorithm_bindings": candidate["accepted_algorithm_bindings"],
                  "exact_daily_adjustment_contract": candidate["exact_daily_adjustment_contract"],
                  "release_policy": candidate["release_policy"], "contract_id": candidate["contract_id"]}
    window = {"target_session": day, "compute_sessions": [day],
              "published_sessions": candidate["published_sessions"]}
    previous_ref = predecessor
    expected = _digest({"source_bindings": source_bindings, "parameters": parameters,
                        "window": window, "previous_ref": previous_ref})
    # R8's historical G1 comparison covers the immutable accepted business
    # snapshot; target-day bytes are independently bound in G3 above.
    ci = dict(formal_predecessor=baseline_ci["formal_predecessor"],
              candidate_predecessor={"accepted": False, "evidence_class": "NON_PIT",
                                     "head_sha256": predecessor["sha256"]},
              reference_snapshot=baseline_ci["reference_snapshot"],
              candidate_snapshot=baseline_ci["candidate_snapshot"], target_session=day,
              compute_sessions=[day], source_bindings=source_bindings, root=str(root),
              parameters=parameters, window=window, previous_ref=previous_ref,
              expected_g3_digest=expected)
    compared = compare_candidate_append(**ci)
    if (compared["G1"], compared["G2"], compared["G3"]) != ("PASS", "PASS", "PASS"):
        raise ValueError("BATCH10_R3_G123_PRECAS_FAILED:" + repr(compared["errors"]))
    value = {"contract_id": "V4_R8_APPEND_G123_EVIDENCE_R1", "version": "1.0.0",
             "target_session": day, "candidate_token": digest(candidate),
             "comparator_input": ci, "production_admission": False,
             "formal_predecessor_binding": baseline["formal_predecessor_binding"],
             "repair_contract": "BATCH10_R3_EXACT_OWNER_APPEND_R1"}
    path = candidate_path.parent / "R8_G123_EVIDENCE_R3.json"
    if path.exists():
        existing = json.loads(path.read_bytes())
        if existing != value:
            raise ValueError("PRESERVE_EXISTING_R8_G123_EVIDENCE")
    else:
        atomic_json(root, path, value)
    return ref(root, path)


def rollback_drill(root: Path, candidate: dict, candidate_path: Path, schema: str) -> dict:
    token = digest(candidate)
    day = candidate["accepted_trade_date"]
    head = root / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json"
    joint = root / "config/v4_current_native_joint_authority_v3.json"
    predecessor_path = checked(root, candidate["predecessor"])
    before = head.read_bytes()
    predecessor_bytes = predecessor_path.read_bytes()
    if _sha(predecessor_bytes) != candidate["predecessor"]["sha256"]:
        raise ValueError("R8_ROLLBACK_PREDECESSOR_BYTES_MISMATCH")
    if _sha(before) != candidate["predecessor"]["sha256"]:
        _atomic_write(head, predecessor_bytes, tdx_root=Path("D:/new_tdx"))
        before = head.read_bytes()
    if before != predecessor_bytes:
        raise ValueError("R8_ROLLBACK_HEAD_NOT_EXACT_PREDECESSOR")
    joint_before = joint.read_bytes() if joint.is_file() else None
    with connection(schema) as pg:
        rows_before = pg.execute("SELECT count(*) FROM r8_publications WHERE candidate_token=%s", (token,)).fetchone()[0]
    transaction = candidate_path.parent / ("ROLLBACK_DRILL_TRANSACTION.json" if rows_before == 0 else
        f"ROLLBACK_DRILL_TRANSACTION_RETRY_{rows_before}.json")
    try:
        _commit_pointers(root, head, joint, transaction, candidate, before, predecessor_path,
                         {"r8_publication_contract": "V4_R8_REAL_APPEND_PG_RECEIPT_R2"},
                         joint_before, None,
                         lambda _: (_ for _ in ()).throw(RuntimeError("intentional candidate-only CAS rollback drill")))
    except RuntimeError as exc:
        if "intentional candidate-only" not in str(exc):
            raise
    else:
        raise ValueError("R8_ROLLBACK_DRILL_FAILURE_CALLBACK_DID_NOT_FAIL")
    restored = head.read_bytes() == before
    joint_restored = (joint.read_bytes() if joint.is_file() else None) == joint_before
    with connection(schema) as pg:
        rows_after = pg.execute("SELECT count(*) FROM r8_publications WHERE candidate_token=%s", (token,)).fetchone()[0]
    if not restored or not joint_restored or rows_after != rows_before:
        raise ValueError("R8_REAL_CANDIDATE_ROLLBACK_DRILL_FAILED")
    value = {"contract_id": "V4_R8_CAS_ROLLBACK_DRILL_R1", "version": "1.0.0",
             "candidate_token": token, "status": "PASS", "transaction_state": "ROLLED_BACK",
             "head_restored_exactly": True, "joint_restored_exactly": True,
             "last_good_head_sha256": candidate["predecessor"]["sha256"],
             "publication_rows_before_failure": rows_before,
             "publication_rows_after_failure": rows_after,
             "formal_head_modified": False, "production_accepted": False,
             "candidate_only": True, "failed_callback_is_deliberate_test_fault": True,
             "failed_transaction_sha256": _sha(transaction.read_bytes())}
    path = candidate_path.parent / ("R8_CAS_ROLLBACK_DRILL_R1.json" if rows_before == 0 else
        f"R8_CAS_ROLLBACK_DRILL_R1_RETRY_{rows_before}.json")
    if path.exists():
        if json.loads(path.read_bytes()) != value:
            raise ValueError("PRESERVE_EXISTING_R8_ROLLBACK_EVIDENCE")
    else:
        atomic_json(root, path, value)
    return ref(root, path)


def http_readback(candidate: dict) -> dict:
    day = candidate["accepted_trade_date"]
    token = digest(candidate)
    query = urllib.parse.urlencode({"trade_date": day, "context_token": token})
    request = urllib.request.Request("http://127.0.0.1:28766/api/v4/context?" + query,
                                     headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        payload = json.loads(raw)
        context = payload.get("context") or {}
        actual_day = context.get("trade_date") or context.get("accepted_trade_date")
        if response.status != 200 or payload.get("context_token") != token or actual_day != day:
            raise ValueError("R8_28766_SAME_TOKEN_CONTEXT_MISMATCH")
        return {"status": "PASS", "context_token": token, "accepted_trade_date": day,
                "production_accepted": False, "read_scope": "DEVELOPMENT_CANDIDATE_PREVIEW",
                "http_status": response.status, "response_sha256": _sha(raw)}


def run(root: Path, candidate_path: Path, baseline_path: Path) -> dict:
    root = root.resolve(strict=True)
    candidate_path = candidate_path.resolve(strict=True)
    candidate = json.loads(candidate_path.read_bytes())
    validate(root, candidate)
    schema, identity = prepare_schema(root)
    g123 = make_g123(root, candidate, candidate_path, baseline_path)
    rollback = rollback_drill(root, candidate, candidate_path, schema)
    os.environ["R4_NATIVE_ISOLATION"] = "1"
    publication = publish_candidate(root, candidate, append_evidence_binding=g123,
                                    rollback_evidence_binding=rollback, readback=http_readback)
    if candidate.get("AS_RECORDED") is not False or candidate.get("PIT_ELIGIBLE") is not False:
        raise ValueError("BATCH10_R3_D0_HISTORICAL_FLAGS_MUST_REMAIN_NON_PIT")
    existing_d0 = d0_pg_readback(candidate["accepted_trade_date"], digest(candidate))
    if existing_d0.get("status") == "PG_BINDING_PRESENT":
        d0_publication = {"status": "ALREADY_PRESENT"}
        d0_readback = existing_d0
    else:
        d0_publication = publish_d0_candidate(repository_root=REPO, candidate_root=root,
            candidate=candidate, trade_date=candidate["accepted_trade_date"],
            candidate_token=digest(candidate))
        d0_readback = d0_pg_readback(candidate["accepted_trade_date"], digest(candidate))
    if d0_readback.get("status") != "PG_BINDING_PRESENT":
        raise ValueError("BATCH10_R3_D0_RESTRICTED_PG_READBACK_FAILED:" + str(d0_readback.get("status")))
    return {"candidate_token": digest(candidate), "trade_date": candidate["accepted_trade_date"],
            "pg_schema": schema, "pg_database_identity": identity,
            "r8_publication": publication,
            "d0_publication": d0_publication,
            "d0_readback": {"status": d0_readback.get("status"),
                "fact_rows": d0_readback.get("fact_rows"),
                "fact_digest_readback": d0_readback.get("fact_digest_readback"),
                "production_admission": False, "as_recorded": False,
                "pit_eligible": False},
            "production_accepted": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--baseline-g123", required=True, type=Path)
    args = parser.parse_args()
    _local_dsn(args.input_root)
    print(json.dumps(run(args.input_root, args.candidate, args.baseline_g123), ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

"""Run bounded, isolated P0-4 candidate validation and CAS/rollback injections."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.fp01_evidence import write, ref
from workbench_service.current_v4_context import SourceInvalid, digest
from workbench_service.joint_release import AUTHORITY, activate, validate
from workbench_service.production_v4 import POINTER
from scripts.build_fp06_sector_v2 import width_facts

EVIDENCE = ROOT / "docs/evidence/three_day_repair_r2_20261008/p04c"
CANDIDATE_PATH = EVIDENCE / "R2_P0_4_RELEASE_CANDIDATE.json"
SOURCE_SANDBOX = Path(r"E:\codex_tmp\r2_available_fields_preview")
PREVIEW_SANDBOX = Path(r"E:\codex_tmp\three_day_r2_p04_preview")
TX_SANDBOX = Path(r"E:\codex_tmp\three_day_r2_p04_tx_preview")


def atomic_write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".r2tmp")
    if temp.exists():
        raise RuntimeError("SANDBOX_TEMP_EXISTS:" + str(temp))
    temp.write_bytes(raw)
    os.replace(temp, path)


def collect_bindings(obj, output):
    if isinstance(obj, dict):
        if "path" in obj and "sha256" in obj:
            output.add(obj["path"])
        for value in obj.values():
            collect_bindings(value, output)
    elif isinstance(obj, list):
        for value in obj:
            collect_bindings(value, output)


def sync_candidate_files(candidate, predecessor, sandbox):
    manifest = json.loads((ROOT / candidate["snapshot"]["manifest"]["path"]).read_text(encoding="utf-8"))
    refs = set()
    collect_bindings(candidate, refs)
    collect_bindings(manifest, refs)
    predecessor_manifest = json.loads((ROOT / predecessor["snapshot"]["manifest"]["path"]).read_text(encoding="utf-8"))
    collect_bindings(predecessor, refs)
    collect_bindings(predecessor_manifest, refs)
    for relative in sorted(refs):
        src = ROOT / relative
        dst = sandbox / relative
        if not src.is_file():
            raise RuntimeError("SOURCE_BINDING_MISSING:" + relative)
        expected = hashlib.sha256(src.read_bytes()).hexdigest()
        if dst.is_file() and hashlib.sha256(dst.read_bytes()).hexdigest() == expected:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        temp = dst.with_name(dst.name + ".r2tmp")
        if temp.exists():
            raise RuntimeError("SANDBOX_TEMP_EXISTS:" + str(temp))
        shutil.copy2(src, temp)
        os.replace(temp, dst)
    return len(refs)


def clone_sandbox(target):
    if target.exists():
        raise RuntimeError("SANDBOX_ALREADY_EXISTS:" + str(target))
    def link_or_copy(src, dst):
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    shutil.copytree(SOURCE_SANDBOX, target, copy_function=link_or_copy, symlinks=False)


def expect_source_invalid(label, action, expected_prefix):
    try:
        action()
    except SourceInvalid as error:
        result = str(error)
        if not result.startswith(expected_prefix):
            raise AssertionError(f"{label}:unexpected:{result}")
        return {"result": "PASS_REJECTED", "reason": result}
    raise AssertionError(label + ":NOT_REJECTED")


def main():
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    predecessor_raw = (ROOT / AUTHORITY).read_bytes()
    predecessor = json.loads(predecessor_raw)
    live_digest = digest(predecessor_raw)
    validate(ROOT, candidate)
    cases = {"candidate": "PASS_VALIDATED_NOT_ACTIVATED"}

    wrong_date = dict(candidate, trade_date="2026-09-29")
    cases["wrong_date"] = expect_source_invalid("wrong date", lambda: validate(ROOT, wrong_date), "JOINT_DATE_MISMATCH")
    bad_hash = json.loads(json.dumps(candidate))
    bad_hash["snapshot"]["manifest"]["sha256"] = "0" * 64
    cases["source_hash"] = expect_source_invalid("source hash", lambda: validate(ROOT, bad_hash), "JOINT_SOURCE_DIGEST_MISMATCH")

    target = candidate["trade_date"]
    deps = {key: {"value": value, "quality": "ACCEPTED", "max_source_date": target}
            for key, value in (("close", 101.0), ("ma20", 100.0))}
    correct = width_facts({"S1": {"trade_date": target, "price_basis_id": "EXPECTED",
                                   "fields": deps}}, target, "EXPECTED")["S1"]["fields"]["close_minus_ma20"]
    incorrect = width_facts({"S1": {"trade_date": target, "price_basis_id": "WRONG",
                                     "fields": deps}}, target, "EXPECTED")["S1"]["fields"]["close_minus_ma20"]
    assert correct["quality"] == "ACCEPTED" and correct["value"] == 1.0
    assert incorrect["quality"] == "UNKNOWN" and incorrect["value"] is None and incorrect["reason"] == "PRICE_BASIS_ID_MISMATCH"
    cases["wrong_price_basis"] = {"result": "PASS_FAIL_CLOSED", "correct_basis": correct,
                                  "wrong_basis": incorrect, "field_scope": "ma20_width_only"}
    cases["stale_live_cas"] = expect_source_invalid("stale CAS", lambda: activate(ROOT, candidate, "0" * 64, lambda _: {"pass": True}), "JOINT_CAS_CONFLICT")
    assert (ROOT / AUTHORITY).read_bytes() == predecessor_raw

    # Build an isolated transaction root; its two pointers and all referenced
    # bindings are copied or hard-linked from the earlier preview environment.
    clone_sandbox(TX_SANDBOX)
    refs = sync_candidate_files(candidate, predecessor, TX_SANDBOX)
    tx_authority = TX_SANDBOX / AUTHORITY
    atomic_write(tx_authority, predecessor_raw)
    validate(TX_SANDBOX, predecessor)
    rollback = expect_source_invalid("rollback injection", lambda: activate(
        TX_SANDBOX, candidate, live_digest, lambda _: {"pass": False, "reason": "INJECTED_HEALTH_FAILURE"}), "JOINT_HEALTH_FAILED")
    assert tx_authority.read_bytes() == predecessor_raw
    cases["rollback"] = {**rollback, "exact_predecessor_restore": True,
                          "restored_sha256": hashlib.sha256(tx_authority.read_bytes()).hexdigest()}
    receipt = activate(TX_SANDBOX, candidate, live_digest, lambda _: {"pass": True, "candidate_readback": True})
    assert receipt["result"] == "SCOPED_OPERATIONAL_RELEASE_PASS"
    cases["isolated_first_cas"] = receipt
    cases["parallel_stale_writer"] = expect_source_invalid("parallel CAS", lambda: activate(
        TX_SANDBOX, predecessor, live_digest, lambda _: {"pass": True}), "JOINT_CAS_CONFLICT")
    assert tx_authority.read_bytes() == json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    # Candidate-serving sandbox for IAB smoke; never points at the live project.
    if not PREVIEW_SANDBOX.exists():
        clone_sandbox(PREVIEW_SANDBOX)
    preview_refs = sync_candidate_files(candidate, predecessor, PREVIEW_SANDBOX)
    candidate_raw = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    atomic_write(PREVIEW_SANDBOX / AUTHORITY, candidate_raw)
    validate(PREVIEW_SANDBOX, candidate)
    assert (ROOT / AUTHORITY).read_bytes() == predecessor_raw
    entry = {"contract_id": "R2_P0_4_RELEASE_GATE_SMOKE_V1", "result": "PASS_ISOLATED_GATES_CANDIDATE_NOT_LIVE",
             "candidate": ref(CANDIDATE_PATH), "predecessor_joint_authority_sha256": live_digest,
             "live_joint_authority_unchanged": True, "cases": cases,
             "sandbox": {"transaction_root": str(TX_SANDBOX), "transaction_bindings": refs,
                         "preview_root": str(PREVIEW_SANDBOX), "preview_bindings": preview_refs},
             "activation_performed": False,
             "next_stage": "IAB_MINIMAL_FIELD_SMOKE_THEN_PRODUCTION_CAS_AND_READBACK"}
    write(EVIDENCE / "R2_P0_4_RELEASE_GATE_SMOKE.json", entry)
    print(json.dumps({"result": entry["result"], "cases": list(cases), "activation_performed": False,
                      "preview": str(PREVIEW_SANDBOX)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Atomically freeze R3B contracts, source capability evidence and negative tests."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.confirmation_input_closure_r3b import (
    CONTRACT_ID, DIAGNOSTIC_FIELDS, EPISODE_PARAMETERS, EPISODE_PRODUCER,
    SAFETY_BINDINGS, scenario_capability_matrix,
)
from src.v4.state_identity import digest

OUT = ROOT / "reports/v4_11_r3b"
AUTH = ROOT / "docs/evidence/next_round_r3"


def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def read(path):
    return json.loads(Path(path).read_bytes())


def atomic(path, value):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise RuntimeError("R3B_OUTPUT_OUTSIDE_WORKSPACE")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".r3b-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    captured = datetime.now(timezone.utc).isoformat()
    protected = {name: ref(ROOT / "data/v4" / name) for name in (
        "V4_DATA_ACCEPTED_HEAD.json", "V4_STAGE_ACCEPTED_HEAD.json", "V4_10_ACCEPTED_HEAD.json")}
    authorities = {key: ref(AUTH / name) for key, name in {
        "task": "V4_11_R3B_EPISODE_SAFETY_LOO_INPUT_CLOSURE_TASK_20261002.md",
        "master": "V4_NEXT_ROUND_EXECUTION_MASTER_R3_20261002.md",
        "external_audit": "V4_R2_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R2_20261002.md",
    }.items()}
    legacy = {name: ref(ROOT / path) for name, path in {
        "scanner": "src/workbench_analysis/today_research_scanner_v3_3.py",
        "stock_attention": "src/workbench_analysis/stock_attention.py",
        "factor": "src/workbench_analysis/today_research_factors_v3_3.py",
        "episode": "src/workbench_analysis/pullback_episode_v1.py",
        "loo": "src/workbench_analysis/full_loo_v3_3.py",
        "sector_current": "src/workbench_analysis/sector_attention.py",
        "legacy_parameters": "config/research_attention_v3.yaml",
        "frozen_manifest": "config/v4_11_legacy_extraction_manifest_r2.json",
        "executable_authority": "docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md",
    }.items()}
    cfg = read(ROOT / "config/research_attention_v3.yaml")
    parameters = {"contract_id": EPISODE_PARAMETERS, "version": "1.0.0",
        "legacy_episode_source": legacy["episode"],
        "values": {"max_event_sessions": 20, "max_pullback_sessions": 10},
        "common_safety_parameters": {"stock_signals": {
            key: cfg["thresholds"]["stock_signals"][key] for key in ("STRUCTURE_BREAK", "risk")},
            "first_day_damage_close_to_ma20_lt": .97,
            "severe_drop": {"drop_floor_pct": .04, "drop_cap_pct": .08, "drop_z": 2.0}},
        "changes_legacy_parameters": False}
    parameter_path = ROOT / "config/v4_11_r3b_episode_safety_parameters_v1.json"
    atomic(parameter_path, parameters)
    contract = {"contract_id": CONTRACT_ID, "version": "1.0.0", "authorities": authorities,
        "legacy_bindings": legacy, "parameter_set": ref(parameter_path),
        "safety_predicate_bindings": SAFETY_BINDINGS,
        "safety_wrapper": "Exact legacy individual NOT_* predicates; missing Boolean remains UNKNOWN",
        "safety_publication_owner": "R3A sealed target-date producer set; four original fields retained individually",
        "episode_producer_contract_id": EPISODE_PRODUCER,
        "episode_required_metadata": ["episode_id", "security_id", "episode_start", "prior_session_status",
            "prior_session_trade_date", "prior_session_publication_id", "producer_contract_id", "parameter_set_id",
            "origin_publication_id", "publication_id", "source_publication_ids", "system_available_at", "knowledge_cutoff"],
        "episode_required_upstream": ["master calendar", "same-cutoff adjusted OHLC", "amount", "MA20",
            "frozen per-session strong_seed", "frozen per-session structure_break", "prior slope20/r2_20",
            "CLV", "reclaim_ma5/touch_reclaim10", "intraday_reject_high20"],
        "diagnostic_fields": DIAGNOSTIC_FIELDS,
        "scenario_capability_matrix_before_R3A_seal": scenario_capability_matrix(),
        "scenario_capability_matrix_when_bound_to_R3A_seal": scenario_capability_matrix(r3a_sealed=True),
        "formal_D0_scope": ["LAUNCH_CONFIRM", "RECOVERY_TURN"],
        "historical_PIT_equivalent": False, "AS_RECORDED": False,
        "permissions": {"production": False, "shadow": False, "focus": False, "global_mandatory_adoption": False},
        "stage_head": "KEEP", "data_head": "KEEP", "external_acceptance": False}
    contract_path = ROOT / "config/v4_11_r3b_input_closure_contract_v1.json"
    atomic(contract_path, contract)
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/v4_11_r3b", "-q"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf8")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    inventory = []
    for path in sorted((ROOT / "data/v4").glob("*ACCEPTED*HEAD*.json")):
        head = read(path)
        inventory.append({"binding": ref(path), "contract_id": head.get("contract_id", head.get("head_id")),
            "accepted_trade_date": head.get("accepted_trade_date", head.get("first_accepted_trade_date")),
            "capabilities": head.get("capabilities", {}),
            "declares_exact_legacy_episode_producer": EPISODE_PRODUCER in json.dumps(head, ensure_ascii=False)})
    if any(item["declares_exact_legacy_episode_producer"] for item in inventory):
        raise RuntimeError("EPISODE_CAPABILITY_CHANGED_REVIEW_REQUIRED")
    legacy_graph = {
        "nodes": {"RAW_QUOTES": "Accepted target raw + native adjustment -> R3A ret1 facts",
            "MEMBERSHIP": "V4_08 PIT membership accepted 2026-09-30",
            "SECTOR_METADATA": "Immutable accepted membership metadata / versioned semantic registry",
            "PARAMETERS": legacy["legacy_parameters"],
            "LOO": legacy["loo"], "CURRENT": legacy["sector_current"]},
        "edges": [["LOO", "CURRENT"], ["LOO", "MEMBERSHIP"], ["CURRENT", "RAW_QUOTES"],
            ["CURRENT", "SECTOR_METADATA"], ["CURRENT", "PARAMETERS"]],
        "callable_algorithm_is_pure_upstream": True,
        "algorithm_consumes_V4_11_D0": False, "algorithm_consumes_V4_10_D2_current": False,
        "algorithm_consumes_Focus": False, "algorithm_same_day_feedback": False,
        "proof_scope": "Bound source-code dependency graph, not an admitted target-date LOO publication",
        "target_day_knowledge_cutoff_proven_for_LOO_publication": False,
        "target_day_LOO_publication_sealed": False,
        "formal_candidate_admission": False,
        "frozen_input_time_role": read(ROOT / legacy["frozen_manifest"]["path"])["input_time_roles"]["current_with_loo_breadth_support"],
        "reason": DIAGNOSTIC_FIELDS["current_with_loo_breadth_support"],
        "does_not_depend_on_Amount_A_warmup": True,
        "note": "CURRENT selects quote/breadth/rank predicates only; Amount-A is not a CURRENT eligibility predicate."}
    # Auditable source proof that the LOO callable calls only the pure CURRENT
    # builder and does not import a confirmation/reducer/Focus consumer.
    tree = ast.parse((ROOT / legacy["loo"]["path"]).read_text(encoding="utf8"))
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    if any(module and any(token in module.lower() for token in ("confirmation", "focus", "state_reducer")) for module in imports):
        raise RuntimeError("LOO_SOURCE_GRAPH_CHANGED")
    legacy_graph["source_imports"] = imports
    report = {"stage_contract": authorities["task"], "captured_at_utc": captured,
        "acceptance_result": "V4_11_R3B_EPISODE_SAFETY_LOO_CANDIDATE_READY",
        "contract": ref(contract_path), "parameters": ref(parameter_path),
        "source_inventory": inventory,
        "episode_capability_evidence": {"accepted_legacy_episode_head_count": 0,
            "accepted_prior_session_frozen_seed_episode_publication": None,
            "existing_trace_scope": "P12-02 bounded diagnostic candidate requiring caller-supplied frozen per-day strong_seed/structure_break",
            "result": "STRONG_PULLBACK_DIAGNOSTIC_ONLY", "reason": DIAGNOSTIC_FIELDS["pullback_episode_confirmed"],
            "same_day_final_state_used": False, "compatible_value_fabricated": False},
        "loo_dependency_graph": legacy_graph,
        "safety_predicate_bindings": SAFETY_BINDINGS,
        "scenario_capability_matrix_before_R3A_seal": scenario_capability_matrix(),
        "scenario_capability_matrix_when_bound_to_R3A_seal": scenario_capability_matrix(r3a_sealed=True),
        "negative_test_receipt": {"command": [sys.executable, "-m", "pytest", "tests/v4_11_r3b", "-q"],
            "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
            "required_cases": ["same-day D2 feedback rejected", "Focus input rejected", "future episode rejected",
                "same-day revision cannot become prior-session episode", "fake episode id rejected", "wrong producer rejected",
                "wrong parameter set rejected", "LOO circular dependency detected", "diagnostic-only cannot enter formal D0"]},
        "protected_heads_before": protected,
        "protected_heads_after": {name: ref(ROOT / "data/v4" / name) for name in protected},
        "external_acceptance": False, "next_stage": "WAIT_R3A_SEALED_PRODUCER_SET_THEN_R3C_REAL_DAG",
        "permissions": contract["permissions"]}
    if report["protected_heads_before"] != report["protected_heads_after"]:
        raise RuntimeError("PROTECTED_HEAD_MUTATION")
    report_path = OUT / "R3B_EPISODE_SAFETY_LOO_CLOSURE_RECEIPT.json"
    atomic(report_path, report)
    bindings = [ref(path) for path in (contract_path, parameter_path, report_path,
        ROOT / "src/v4/confirmation_input_closure_r3b.py", ROOT / "tests/v4_11_r3b/test_input_closure.py",
        ROOT / "scripts/seal_v4_11_r3b_input_closure.py")]
    sealed = {"contract_id": "V4_11_R3B_SEALED_PRODUCER_SET_V1", "sealed_at_utc": captured,
        "status": "V4_11_R3B_EPISODE_SAFETY_LOO_CANDIDATE_READY", "bindings": bindings,
        "producer_set_digest": digest(bindings), "scenario_capability_matrix_when_bound_to_R3A_seal": scenario_capability_matrix(r3a_sealed=True),
        "required_external_acceptance": True, "formal_stage_head_created": False,
        "data_head_advanced": False, "stage_head_advanced": False, "permissions": contract["permissions"]}
    atomic(OUT / "R3B_SEALED_PRODUCER_SET.json", sealed)
    print(json.dumps({"status": sealed["status"], "producer_set_digest": sealed["producer_set_digest"],
        "sealed_file": "reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json", "test_output": result.stdout}, ensure_ascii=False))


if __name__ == "__main__":
    main()

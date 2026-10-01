"""Formalize only externally authorized R3 scoped/amendment acceptance."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from workbench_analysis.forward_pit_ledger_r2 import atomic, bound, canonical, reference
from v4.scoped_promotions_r3 import CONTRACT, HEADS, PERMISSIONS, publish, require_authority
from scripts.next_round_execution_r3 import verify_protected

OUTPUT = "reports/audits/next_round_r3/scoped_promotions/"


def save(name, value):
    path = ROOT / OUTPUT / name
    atomic(path, canonical(value), immutable=True)
    return reference(ROOT, path)


def ref(path):
    return reference(ROOT, ROOT / path)


def read(path):
    return json.loads((ROOT / path).read_bytes())


def main():
    entry = verify_protected()
    require_authority(ROOT, entry["authority"])
    proof_path = OUTPUT + "INDEPENDENT_SOURCE_READBACK_R1.json"
    proof = read(proof_path)
    if proof["status"] != "PASS" or proof["A04"]["formal_consumer_enabled"] is not False:
        raise ValueError("FRESH_INDEPENDENT_SOURCE_READBACK_REQUIRED")
    common = dict(contract_id=CONTRACT, external_authority=entry["authority"],
                  audited_implementation="d119c0526e44a819f85b4917159d3eeb5daadf2a",
                  master=entry["master"], stage_entry=ref("reports/next_round_r3/BATCH_STAGE_ENTRY_R1.json"),
                  independent_readback=ref(proof_path), protected_heads=entry["protected_heads"],
                  permissions=PERMISSIONS, main_stage_promotion=False,
                  next_stage="STOP_AFTER_UNIFIED_COMMIT_PUSH_WAIT_INDEPENDENT_EXTERNAL_ACCEPTANCE")
    tasks = {Path(b["path"]).name: b for b in entry["task_bindings"]}
    heads = {}
    report_path = "reports/audits/next_round_r2/A02_DOWNSTREAM_AMENDMENT_REPLAY_R1.json"
    replay = read(report_path)
    for stage in ("V4_05", "V4_07", "V4_09"):
        receipt = json.loads(bound(ROOT, replay["amendments"][stage]))
        value = dict(common, scope_key=stage,
                     status="A02_DOWNSTREAM_AMENDMENTS_PROMOTED_SCOPED",
                     acceptance_result="PASS_RECONSTRUCTED_CORRECTED_SCOPE",
                     task=tasks["V4_A02_DOWNSTREAM_AMENDMENT_PROMOTION_TASK_20261002.md"],
                     trade_date=receipt["trade_date"], knowledge_lineage="RECONSTRUCTED_CORRECTED",
                     AS_RECORDED=False, historical_first_availability_proven=False,
                     accepted_rps_head=replay["accepted_rps_head"], full_old_new_replay=ref(report_path),
                     business_diff=replay["full_business_diff"], accepted_candidate=replay["amendments"][stage],
                     old_accepted_head=receipt["old_accepted_head"], artifact=receipt["artifact"],
                     algorithm_parameter_bindings=receipt["unchanged_algorithms_parameters"],
                     row_count=receipt["row_count"], rows_changed=receipt["rows_changed"],
                     reader_modes=["ORIGINAL_ACCEPTED", "RECONSTRUCTED_CORRECTED_AMENDMENT"], silent_fallback=False)
        if stage == "V4_05":
            value["factor_artifact"] = receipt["factor_artifact"]
        if stage == "V4_09":
            value["exact_seed_binding"] = replay["new_stock_context"]["source_bindings"]["seed_artifact"]
        heads[stage] = publish(ROOT, stage, value)
    a05_path = "reports/audits/next_round_r2/V4_08_ACCEPTED_HEAD_B2_CAPABILITY_AMENDMENT_CANDIDATE_R3.json"
    a05 = read(a05_path)
    heads["A05"] = publish(ROOT, "A05", dict(common, scope_key="A05",
        status="V4_08_B2_CURRENT_SNAPSHOT_SCOPED_AMENDMENT_PROMOTED",
        acceptance_result="PASS_CURRENT_SNAPSHOT_ONLY",
        task=tasks["V4_A05_V4_08_B2_SCOPED_AMENDMENT_PROMOTION_TASK_20261002.md"],
        trade_date="2026-09-24", scope="CURRENT_SNAPSHOT_ONLY", AS_RECORDED=False,
        historical_PIT_equivalent=False, accepted_candidate=ref(a05_path),
        acceptance_record=a05["A05_acceptance_record"], artifact=a05["current_snapshot_replay"],
        full_541_sector_diff=a05["full_accepted_artifact_diff"], zero_member_sector_rows=10,
        normal_quote_universe=5464, sector_rows=541, states=a05["new_snapshot_states"],
        algorithm_parameter_bindings=a05["unchanged_algorithm_parameters"],
        rotation_context_readback=a05["rotation_context_readback"],
        reader_mode="CURRENT_SNAPSHOT_20260924", later_date_injection=False,
        amount_a_warm_branch_enabled=False, old_accepted_head=a05["old_accepted_head"]))
    a04_path = "reports/audits/a04_r3/A04_R3_1_EXTERNAL_REAUDIT_HANDOFF_R1.json"
    a04 = read(a04_path)
    heads["A04"] = publish(ROOT, "A04", dict(common, scope_key="A04",
        status="A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTED", accumulation="ACCUMULATION_CONTINUES",
        acceptance_result="PASS_ENGINEERING_GO_FORWARD_SCOPE",
        task=tasks["V4_A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTANCE_TASK_20261002.md"],
        producer_accepted=True, formal_consumer_enabled=False, historical_reconstruction_accepted=False,
        H21_warmup_required=True, sector_rows=378, known_amount_a=0, warmup_UNKNOWN=378,
        accepted_sessions=1, missing_H21=20, historical_formal_capability="BLOCKED",
        producer_bindings=[a04["producer_contract"], a04["source_admission_contract"], a04["namespace_contract"],
                           a04["scoped_real_proof"], a04["h21_membership_scope"], *a04["runtime_bindings"]],
        audited_engineering_handoff=ref(a04_path),
        observation_bindings=proof["A04"]["observations"], candidate=proof["A04"]["candidate"],
        accumulation_contract="ACCEPTED_MEMBERSHIP_PLUS_ACCEPTED_AMOUNT_SOURCE_TO_APPEND_ONLY_OBSERVATION",
        accumulation_command="python scripts/run_a04_go_forward_r3_1.py",
        historical_first_availability_backfill=False, stock_amr20_dependency=False,
        formal_value_before_H21="UNKNOWN", consumer_auto_activation_after_H21=False,
        consumer_external_acceptance_requires=["H21_COMPLETENESS", "SOURCE_CONSISTENCY", "ARITHMETIC_ORACLE", "CONSUMER_SPECIFIC_EXTERNAL_ACCEPTANCE"],
        reader_mode="GO_FORWARD_PRODUCER_ENGINEERING_ONLY"))
    verify_protected()
    receipt = dict(contract_id=CONTRACT, statuses={
        "A02": "A02_DOWNSTREAM_AMENDMENTS_PROMOTED_SCOPED",
        "A05": "V4_08_B2_CURRENT_SNAPSHOT_SCOPED_AMENDMENT_PROMOTED",
        "A04": "A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTED", "A04_accumulation": "ACCUMULATION_CONTINUES"},
        scoped_heads=heads, independent_source_readback=ref(proof_path), external_authority=entry["authority"],
        protected_heads_unchanged=True, permissions=PERMISSIONS,
        next_stage="ROOT_BATCH_UNIFIED_COMMIT_PUSH_THEN_STOP_WAIT_EXTERNAL_ACCEPTANCE")
    save("PROMOTION_RECEIPT_R1.json", receipt)
    print(json.dumps(receipt["statuses"]))


if __name__ == "__main__":
    main()

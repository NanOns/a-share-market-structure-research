"""R3 archaeology and true accepted-membership scope; no formal consumer activation."""
from datetime import datetime,timezone
import gzip
import json
from pathlib import Path
import re
import subprocess
from workbench_analysis.forward_pit_ledger_r2 import atomic,bound,canonical,digest,reference
from workbench_analysis.amount_a_go_forward_r3 import compute_ledger_candidate,read_verified_observations

ROOT=Path(__file__).resolve().parents[1]
BASE="66ef2e342dd339cc9795c2d1fd774b8edec4c345"


def save(path,value):
    atomic(ROOT/path,canonical(value),immutable=True)
    return reference(ROOT,ROOT/path)


def durable(path):
    raw=(ROOT/path).read_bytes()
    try:g=subprocess.check_output(["git","show",BASE+":"+path],cwd=ROOT,stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:g=raw
    if g.startswith(b"version https://git-lfs.github.com/spec/v1") or digest(g)==digest(raw):return reference(ROOT,ROOT/path)
    archive="data/v4/source_evidence/a04_r3/observed_authority_original_bytes/"+digest(raw)+".bin"
    atomic(ROOT/archive,raw,immutable=True)
    return dict(reference(ROOT,ROOT/archive),observed_original_path=path,git_representation_sha256=digest(g))


def cites(path,pattern):
    lines=(ROOT/path).read_text(encoding="utf8").splitlines()
    return {"binding":durable(path),"evidence_lines":[{"line":i,"text":line} for i,line in enumerate(lines,1) if re.search(pattern,line)]}


def threshold_archaeology():
    records=[
        {"authority_scope":"PREVIEW_AMOUNT_A_ENGINEERING_QUALITY_PARAMETER_NOT_EXTERNAL_UNIVERSAL_AUTHORITY",
         "source":cites("docs/M10_AMOUNT_A_DESIGN_DECISION_V1.md",r"状态|2.2|预览质量参数|min_comparable|不是已证实|外审通过"),
         "fields":["min_comparable_members","min_comparable_coverage"],"values":[5,"0.80"],"formal_reuse_this_batch":False},
        {"authority_scope":"M10_LOCAL_PREVIEW_CONSUMER_SCOPED_QUALITY_GATE",
         "source":cites("docs/M10_MAINLINE_STATE_CONTRACT_V2_4_PREVIEW.md",r"preview|默认质量门|质量门|v2.4"),
         "fields":["amount_comparable_member_count","amount_comparable_coverage","amount_window_coverage"],"values":[5,"0.80"],"formal_reuse_this_batch":False},
        {"authority_scope":"IMPLEMENTATION_CONVENIENCE_DEFAULT_OF_FROZEN_PREVIEW_PARAMETER",
         "source":cites("src/workbench_analysis/sector_amount.py",r"DEFAULT_MIN|LOW_MEMBER_COUNT|LOW_COVERAGE"),
         "fields":["DEFAULT_MIN_COMPARABLE_MEMBERS","DEFAULT_MIN_COMPARABLE_COVERAGE"],"values":[5,"0.80"],"formal_reuse_this_batch":False},
        {"authority_scope":"CORE_SECTOR_SAFETY_MEMBERS_AND_QUOTE_COVERAGE; DIFFERENT_DENOMINATOR_FROM_AMOUNT_A",
         "source":cites("docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md",r"Core sector最低|sector_safety=|amount_a_value / amount_a_quality|amount_ratioN=|AMOUNT_VOLUME_STATE_V1"),
         "fields":["member_count","quote_coverage"],"values":[5,"0.8"],"formal_reuse_for_amount_a":False},
        {"authority_scope":"V4_08_CANDIDATE_CORE_SECTOR_PARAMETERS_BOUND_TO_REV2_15_NOT_AMOUNT_A_PARAMETERS",
         "source":cites("config/v4_08_algorithm_parameter_set_r5.json",r"claims|MIN_MEMBERS|MIN_QUOTE_COVERAGE|FROZEN_CANDIDATE|formal_consumer_enabled"),
         "fields":["V4_08_SECTOR_MIN_MEMBERS","V4_08_SECTOR_MIN_QUOTE_COVERAGE"],"values":[5,"0.8"],"formal_reuse_for_amount_a":False}]
    return save("reports/audits/a04_r3/A04_R3_THRESHOLD_AUTHORITY_ARCHAEOLOGY_R1.json",{
        "namespace":"SECTOR.amount_a_value","baseline":BASE,"records":records,
        "determination":"5_AND_0_80_HAVE_VERIFIABLE_LOCAL_PREVIEW_AND_CORE_SAFETY_SCOPES; NO_UNIVERSAL_EXTERNALLY_ACCEPTED_AMOUNT_A_THRESHOLD",
        "universal_threshold":None,"missing_global_threshold_is_arithmetic_blocker":False,
        "consumer_activation":"REQUIRES_SEPARATE_CONSUMER_SPECIFIC_ACCEPTED_GATE", "new_external_acceptance":None})


def membership_scope(observation):
    head=json.loads((ROOT/"data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json").read_text(encoding="utf8"))
    facts=[json.loads(line) for line in gzip.decompress(bound(ROOT,head["facts"])).decode("utf8").splitlines()]
    accepted_dates=sorted({r["membership_asof_date"] for r in facts})
    prior=json.loads(bound(ROOT,observation))["calendar_binding"]
    calendar=json.loads(bound(ROOT,prior))["session_dates"];target="2026-09-30";window=calendar[calendar.index(target)-20:calendar.index(target)+1]
    paths=subprocess.check_output(["git","ls-tree","-r","--name-only",BASE,"data/v4","reports/v4_08"],cwd=ROOT).decode("utf8").splitlines()
    inventory=[]
    for path in paths:
        lower=path.lower()
        if "membership" not in lower or not path.endswith((".json",".jsonl.gz")):continue
        item={"binding":durable(path),"scope":"HISTORICAL_SOURCE_OR_CANDIDATE_NOT_ACCEPTED_H21"}
        if path=="data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json":
            item["scope"]="EXTERNALLY_ACCEPTED_FORWARD_PIT_MEMBERSHIP_FROM_20260930_ONLY"
        elif path==head["facts"]["path"]:
            item["scope"]="HASH_BOUND_ACTUAL_ACCEPTED_FACTS_SINGLE_20260930_DATE"
        elif "current" in lower or "interval" in lower:
            item["scope"]="IDENTITY_OR_CURRENT_RECONSTRUCTED_MEMBERSHIP_NOT_HISTORICAL_SECTOR_PIT_AUTHORITY"
        inventory.append(item)
    return save("reports/audits/a04_r3/A04_R3_H21_ACCEPTED_MEMBERSHIP_SCOPE_R1.json",{
        "baseline":BASE,"inventory":inventory,"accepted_membership_head":reference(ROOT,ROOT/"data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json"),
        "accepted_facts":head["facts"],"actual_accepted_dates":accepted_dates,"actual_fact_count":len(facts),
        "accepted_first_trade_date":head["first_accepted_trade_date"],"required_h21":window,
        "missing_accepted_h21_dates":sorted(set(window)-set(accepted_dates)),"proved_sessions":len(set(window)&set(accepted_dates)),
        "historical_capability":"PRE_BASELINE_HISTORICAL_AMOUNT_A_NOT_FORMALLY_RECONSTRUCTABLE",
        "current_snapshot_backfill_permitted":False,"go_forward":"APPEND_ACTUAL_ACCEPTED_DATED_OBSERVATIONS; WARMUP_UNKNOWN_UNTIL_H21",
        "historical_formal_amount_a":"BLOCKED","wait_for_future_days":False})


def consumer_gates():
    ast=json.loads((ROOT/"config/v4_08_b2_machine_ast_r5.json").read_text(encoding="utf8"))
    affected=[]
    for rule,body in ast["rules"].items():
        if '"amount_A"' in json.dumps(body,ensure_ascii=False):affected.append({"rule":rule,"exact_ast":body})
    records=[
      {"consumer":"V4_08_LEGACY_B2_AMOUNT_A_RULES","source_bindings":[durable("src/sector/legacy_b2_r5.py"),durable("config/v4_08_b2_machine_ast_r5.json")],
       "current_gate":"DIAGNOSTIC_ONLY_UNKNOWN_AMOUNT_A_AUDIT_OPEN","future_scoped_use":"GO_FORWARD_H21_ACCEPTED_INPUT_PLUS_SEPARATELY_ACCEPTED_B2_AMENDMENT",
       "specific_quality_gate":{"membership":"H21_ACTUAL_ACCEPTED_PIT","amount":"KNOWN_SOURCE_BOUND_COMMON_MEMBER_ARITHMETIC","other_facts":"EXACT_B2_AST_OTHER_REQUIRED_INPUTS","coverage":"REQUIRES_SEPARATE_B2_ACCEPTED_POLICY_NOT_DEFAULT_CORE_QUOTE_COVERAGE"},
       "amount_rules":affected,"formal_consumer_enabled":False},
      {"consumer":"M10_MAINLINE_NEW_REACCELERATING","source_bindings":[durable("src/workbench_analysis/mainline.py"),durable("docs/M10_MAINLINE_STATE_CONTRACT_V2_4_PREVIEW.md")],
       "current_gate":"LEGACY_PREVIEW_UNCHANGED; NEW_R3_CANDIDATE_NOT_INJECTED","future_scoped_use":"ACCEPTED_GO_FORWARD_A_U_T_AND_VERSIONED_CONSUMER_AMENDMENT",
       "specific_quality_gate":{"required_sessions":21,"local_preview_min_members":5,"local_preview_coverage":"0.80","external_acceptance_of_reuse":None,"amount_thresholds":"EXACT_EXISTING_CONSUMER_PARAMETER_SOURCE; NOT_THIS_PRODUCER"},"formal_consumer_enabled":False},
      {"consumer":"M10_MAINLINE_FADING_FIXED_COMMON_COMPARISON","source_bindings":[durable("src/workbench_analysis/mainline.py"),durable("docs/M10_AMOUNT_A_DESIGN_DECISION_V1.md")],
       "current_gate":"DIAGNOSTIC_PREVIEW; R3_SINGLE_A_NOT_SUFFICIENT_FOR_FADING","future_scoped_use":"SEPARATE_24_SESSION_COMMON_SET_COMPARISON_AND_ACCEPTED_CONSUMER_GATE",
       "specific_quality_gate":{"required_sessions":24,"same_members_both_endpoints":True,"unknown_delta_no_fallback":True},"formal_consumer_enabled":False},
      {"consumer":"RESEARCH_SECTOR_POTENTIAL_AMOUNT_A","source_bindings":[durable("src/workbench_analysis/sector_attention.py"),durable("src/workbench_service/research_builder.py")],
       "current_gate":"RESEARCH_DIAGNOSTIC_UNCHANGED_NO_R3_AUTHORITY_ADOPTION","future_scoped_use":"SEPARATE_EXACT_RESEARCH_CONSUMER_GATE_VERSION_AFTER_PRODUCER_ACCEPTANCE",
       "specific_quality_gate":{"amount_namespace":"SECTOR.amount_a_value","source_membership":"H21_ACCEPTED","other_research_safety":"EXACT_OLD_CONSUMER_GATE_NOT_UNIVERSAL_PRODUCER_THRESHOLD"},"formal_consumer_enabled":False},
      {"consumer":"UI_API_AMOUNT_A_FIELD_DISPLAY","source_bindings":[durable("src/workbench_service/catalog.py"),durable("src/workbench_service/research_queries.py"),durable("src/workbench_service/app.py")],
       "current_gate":"DIAGNOSTIC_LABEL_QUALITY_AND_LINEAGE_ONLY","future_scoped_use":"DISPLAY_KNOWN_ARITHMETIC_WITH_SCOPE_AND_INACTIVE_CONSUMER_PERMISSIONS",
       "specific_quality_gate":{"unknown_no_fallback":True,"diagnostic_not_eligibility":True},"formal_consumer_enabled":False},
      {"consumer":"V4_11_STOCK_CONFIRMATION","current_gate":"OUTSIDE_AMOUNT_A_NAMESPACE_NO_A04_GATE_ALLOWED",
       "future_scoped_use":"NONE; STOCK_AMR20_INDEPENDENT_ACCEPTED_STOCK_CONTRACT",
       "specific_quality_gate":{"a04_status_must_not_affect_stock_confirmation":True,"stock_amr20_not_sector_amount_a":True},"formal_consumer_enabled":False}]
    return save("reports/audits/a04_r3/A04_R3_CONSUMER_SPECIFIC_GATE_INVENTORY_R1.json",{
        "namespace":"SECTOR.amount_a_value","records":records,"universal_producer_quality_threshold":None,
        "global_formal_adoption":False,"source_inventory_prior":reference(ROOT,ROOT/"reports/audits/A04_AMOUNT_A_R2_REPO_CONSUMER_INVENTORY_DURABLE_R1.json")})


def main():
    source_bindings=[reference(ROOT,path) for path in sorted((ROOT/"data/v4/a04_go_forward_r3/observations").glob("*.json"))]
    observations=read_verified_observations(ROOT,source_bindings)
    candidate=compute_ledger_candidate(ROOT,source_bindings,target="2026-09-30")
    target=ROOT/"reports/audits/a04_r3/candidates"/(candidate["publication_id"].split(":")[1]+".json")
    if target.read_bytes()!=canonical(candidate):raise ValueError("REAL_CANDIDATE_REPLAY_MISMATCH")
    threshold=threshold_archaeology();membership=membership_scope(source_bindings[0]);consumers=consumer_gates()
    proof={"status":"A04_R3_GO_FORWARD_FORMAL_AUTHORITY_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT","baseline":BASE,
           "engineering_status":"CANDIDATE_READY_FOR_EXTERNAL_REAUDIT","real_observation":source_bindings,
           "candidate":reference(ROOT,target),"real_sector_rows":len(candidate["rows"]),"real_known_arithmetic_rows":sum(r["arithmetic_status"]=="KNOWN" for r in candidate["rows"]),
           "real_unknown_warmup_rows":sum(r["arithmetic_status"]=="UNKNOWN" for r in candidate["rows"]),"accepted_membership_observation_sessions":len(observations),
           "historical_capability":"PRE_BASELINE_HISTORICAL_AMOUNT_A_NOT_FORMALLY_RECONSTRUCTABLE","historical_formal_amount_a":"BLOCKED",
           "threshold_authority_archaeology":threshold,"h21_membership_scope":membership,"consumer_gates":consumers,
           "namespace_contract":reference(ROOT,ROOT/"config/a04_amount_a_namespace_r3.json"),"producer_contract":reference(ROOT,ROOT/"config/a04_amount_a_go_forward_r3.json"),
           "task":reference(ROOT,ROOT/"docs/evidence/next_round_r2/V4_A04_R3_AMOUNT_A_FORMAL_AUTHORITY_CLOSURE_TASK_20261001.md"),
           "master":reference(ROOT,ROOT/"docs/evidence/next_round_r2/V4_NEXT_ROUND_EXECUTION_MASTER_R2_20261001.md"),
           "scope_external_audit":reference(ROOT,ROOT/"docs/evidence/next_round_r2/V4_NEXT_ROUND_10_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md"),
           "stage_entry":reference(ROOT,ROOT/"reports/next_round_r2/BATCH_STAGE_ENTRY_R1.json"),
           "data_head":reference(ROOT,ROOT/"data/v4/V4_DATA_ACCEPTED_HEAD.json"),"stage_head":reference(ROOT,ROOT/"data/v4/V4_STAGE_ACCEPTED_HEAD.json"),
           "runtime_bindings":[reference(ROOT,ROOT/path) for path in ["src/workbench_analysis/amount_a_go_forward_r3.py","scripts/run_a04_go_forward_r3.py","scripts/seal_a04_go_forward_r3.py"]],
           "real_source_replay":"PASS_EXACT_MEMBERS_AMOUNT_STATUS_CALENDAR_IDENTITY","formal_consumer_enabled":False,"accepted_owner_registered":False,
           "stock_confirmation_dependency":False,"new_external_acceptance":None,"head_moved":False,
           "permissions":{"production":False,"shadow":False,"focus":False,"global_mandatory_adoption":False},
           "next_stage":"INDEPENDENT_EXTERNAL_REAUDIT_ONLY; STOP_AFTER_BATCH_COMMIT_PUSH"}
    result=save("reports/audits/a04_r3/A04_R3_REAL_SCOPED_CANDIDATE_PROOF_R1.json",proof)
    print(canonical(result).decode("utf8"))

if __name__=="__main__":main()

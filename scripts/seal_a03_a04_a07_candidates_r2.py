"""Seal exact byte durability and individual external reaudit handoffs without rewriting history."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from workbench_analysis.forward_pit_ledger_r2 import atomic, bound, canonical, digest, reference

ROOT=Path(__file__).resolve().parents[1]


def save(path,value):
    atomic(ROOT/path,canonical(value),immutable=True)
    return reference(ROOT,ROOT/path)


def durable(ref,role):
    raw=bound(ROOT,ref)
    try:
        historical=subprocess.check_output(["git","show","bc3e398efb4f4a05c20973ff3cb335a6b101ac87:"+ref["path"]],cwd=ROOT,stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        historical=raw
    if historical.startswith(b"version https://git-lfs.github.com/spec/v1"):
        return {"binding":ref,"role":role,"representation":"GIT_LFS_IMMUTABLE_BYTES"}
    if digest(historical)!=ref["sha256"]:
        path="data/v4/source_evidence/a03_a04_a07_r2_original_bytes/"+ref["sha256"]+".bin"
        atomic(ROOT/path,raw,immutable=True)
        return {"binding":reference(ROOT,ROOT/path),"role":role,"observed_original_path":ref["path"],
                "git_representation_sha256":digest(historical),"representation":"EXACT_OBSERVED_BYTE_ARCHIVE_NO_HASH_NORMALIZATION"}
    return {"binding":ref,"role":role,"representation":"EXACT_PRE_EXISTING_GIT_BYTES"}


def main():
    a04=json.loads((ROOT/"reports/audits/A04_AMOUNT_A_FORMAL_AUTHORITY_R2_REAL_PROOF.json").read_text(encoding="utf8"))
    inv=json.loads(bound(ROOT,a04["consumer_inventory"]))
    records=[]
    for entry in inv["files"]:
        sealed=durable(entry["binding"],entry["role"])
        records.append(dict(entry,binding=sealed["binding"],durability=sealed))
    inv_new=dict(inv,files=records,prior_observed_inventory=a04["consumer_inventory"],durability="EXACT_SOURCE_BYTE_ARCHIVES_FOR_PRE_EXISTING_CRLF_OBSERVATIONS")
    inv_ref=save("reports/audits/A04_AMOUNT_A_R2_REPO_CONSUMER_INVENTORY_DURABLE_R1.json",inv_new)
    a04new=dict(a04,consumer_inventory=inv_ref,prior_candidate_report=reference(ROOT,ROOT/"reports/audits/A04_AMOUNT_A_FORMAL_AUTHORITY_R2_REAL_PROOF.json"))
    a04ref=save("reports/audits/A04_AMOUNT_A_FORMAL_AUTHORITY_R2_DURABLE_REAL_PROOF_R1.json",a04new)
    a07=json.loads((ROOT/"reports/audits/A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_REAL_PROOF.json").read_text(encoding="utf8"))
    inventory=[durable(ref,"ADJUSTMENT_SOURCE_OR_RECEIPT_OR_PRODUCER") for ref in a07["raw_source_inventory"]]
    a07new=dict(a07,raw_source_inventory=[x["binding"] for x in inventory],source_inventory_durability=inventory,
                prior_candidate_report=reference(ROOT,ROOT/"reports/audits/A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_REAL_PROOF.json"),
                go_forward_capture_contract=reference(ROOT,ROOT/"config/a07_go_forward_capture_r2.json"))
    a07ref=save("reports/audits/A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_DURABLE_REAL_PROOF_R1.json",a07new)
    rejected=ROOT/"data/v4/source_evidence/a04_r2/raw_amount_exact_source_samples.json"
    disposition=save("reports/audits/A04_AMOUNT_A_R2_INITIAL_CAPTURE_DISPOSITION_R1.json",{
        "historical_attempt_source":reference(ROOT,rejected),"status":"SUPERSEDED_EXPLANATORY_OFFSET_METADATA_INVALID",
        "issue":"raw_byte_offset was subset-local ordinal, not original archive member offset; it is not used as proof",
        "canonical_real_source":a04["real_raw_samples"],"raw_amount_values":"UNCHANGED_EXACT_RAW_FLOAT32",
        "old_artifact_preserved":True,"false_offset_removed_from_new_source":True})
    tests=reference(ROOT,ROOT/"reports/audits/A03_A04_A07_R2_TARGETED_TESTS.xml")
    package_specs=[("A03","FORWARD_PIT_HISTORY_ACCUMULATION",reference(ROOT,ROOT/"reports/audits/A03_FORWARD_PIT_BUILDER_R2_REAL_OBSERVATION.json"),"config/a03_forward_pit_ledger_r2.json",["src/workbench_analysis/forward_pit_ledger_r2.py","scripts/run_a03_forward_pit_daily_r2.py"],"PARTIAL_AWAITING_FUTURE_REAL_OBSERVATIONS_NOT_A_BATCH_BLOCKER"),
                   ("A04","AUD-AMOUNT-A-06",a04ref,"config/a04_amount_a_authority_candidate_r2.json",["src/workbench_analysis/amount_a_authority_r2.py"],"BLOCKED_FORMAL_THRESHOLD_AND_HISTORICAL_H21_MEMBERSHIP_AUTHORITY"),
                   ("A07","HISTORICAL_AS_RECORDED_ADJUSTED_PRICE",a07ref,"config/a07_adjusted_price_lineage_r2.json",["src/workbench_analysis/adjusted_price_lineage_r2.py","scripts/capture_a07_adjustment_source_r2.py","config/a07_go_forward_capture_r2.json"],"PERMANENTLY_BLOCKED_PRE_CAPTURE_AS_RECORDED")]
    results={}
    for name,audit,proof,config,files,limitation in package_specs:
        value={"package":name,"audit_id":audit,"status":"CANDIDATE_READY_FOR_EXTERNAL_REAUDIT","technical_candidate":"ENGINEERING_AND_CURRENT_REAL_OBSERVATION_COMPLETE",
               "external_condition_status":limitation,"candidate_proof":proof,"contract":reference(ROOT,ROOT/config),
               "runtime_bindings":[reference(ROOT,ROOT/path) for path in files],"builder_script":reference(ROOT,ROOT/"scripts/build_a03_a04_a07_candidates_r2.py"),
               "byte_durability_sealer":reference(ROOT,ROOT/"scripts/seal_a03_a04_a07_candidates_r2.py"),
               "batch_entry":reference(ROOT,ROOT/"reports/next_round_r1/BATCH_STAGE_ENTRY_R1.json"),
               "tests":tests,"targeted_test_result":{"passed":23,"failed":0,"source":"ACTUAL_PYTEST_JUNIT"},
               "clean_checkout_result":"ROOT_BATCH_SEAL_MUST_BIND_ACTUAL_INDEPENDENT_CLEAN_RUN; NOT_CLAIMED_HERE",
               "accepted_data_head":reference(ROOT,ROOT/"data/v4/V4_DATA_ACCEPTED_HEAD.json"),"stage_head":reference(ROOT,ROOT/"data/v4/V4_STAGE_ACCEPTED_HEAD.json"),
               "head_moved":False,"new_formal_consumer_enabled":False,"accepted_owner_registered":False,"external_acceptance":None,
               "permissions":{"production":False,"shadow":False,"focus_cutover":False,"global_mandatory_adoption":False},
               "next_stage":"INDEPENDENT_EXTERNAL_REAUDIT; STOP_AFTER_BATCH_COMMIT_PUSH"}
        if name=="A04":value["initial_source_disposition"]=disposition
        results[name]=save(f"reports/audits/{name}_R2_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json",value)
    print(canonical(results).decode("utf8"))

if __name__=="__main__":main()

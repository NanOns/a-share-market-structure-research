"""Itemize the R19 352/92 reference inventory findings against an R20 scan."""
from __future__ import annotations
import argparse, collections, hashlib, json
from pathlib import Path

def key(row):
    return (row.get("caller_path"), row.get("symbol"), row.get("literal_or_resolved_target"), row.get("expected_sha256"), row.get("expected_bytes"))

def classify(row, restorations):
    caller=row.get("caller_path",""); target=row.get("literal_or_resolved_target","") or ""; symbol=row.get("symbol","")
    if row.get("risk_type")=="KNOWN_VALID_CURRENT_REFERENCE" and target in restorations:
        restored=restorations[target]
        return {"classification":"RESTORED_FROM_EXACT_GIT_BLOB","review_priority":"INFO","disposition":"ARCHIVE_IDENTITY_REPAIRED_EXACTLY","reason":"The archived byte file was restored atomically from a reachable Git blob whose SHA-256 and byte count exactly match the accepted folder identity; policy/Head contents were not changed.","repair_source_commit":restored["source_commit"],"repair_source_git_path":restored["source_git_path"],"repair_sha256":restored["sha256"],"repair_bytes":restored["bytes"]}
    if row.get("risk_type")=="HISTORICAL_ARCHIVE_VALID_CURRENT_CHANGED":
        return {"classification":"HISTORICAL_REFERENCE_ARCHIVE_VERIFIED","review_priority":"INFO","disposition":"KEEP_FROZEN_IDENTITY_AND_USE_VERIFIED_ARCHIVE","reason":"The historical registry maps this exact original path/SHA to an archive. R20 independently verified archived SHA/bytes and the source commit Git blob; current namespace evolution is expected."}
    if row.get("risk_type")=="ACTUAL_MISMATCH" and caller in {"config/operational_daily_exact_release_policy_v2.json","config/read_only_operational_daily_release_policy_v1_1.json","config/v4_continuous_daily_admission_v10.json"}:
        return {"classification":"ACTIVE_POLICY_FAIL_CLOSED_STALE_IDENTITY","review_priority":"P1","disposition":"BLOCKED_NO_SAFE_REBINDING_EVIDENCE","reason":"A verified V4 runtime chain reads this policy/admission and exact-checks the binding. The referenced source identity differs from current bytes. The verifier fails closed. No exact replacement source evidence is present, so changing the accepted policy or Head would weaken authority."}
    if row.get("risk_type")=="ACTUAL_MISMATCH":
        return {"classification":"FROZEN_BINDING_BYTES_DIFFER_FROM_CURRENT_TARGET","review_priority":"P2","disposition":"RETAIN_AND_REPORT_STALE_BINDING","reason":"The old expected SHA/byte count and independently measured current target were checked for this exact edge. Other source-path literals are recorded as candidate links only; no verified active runtime loader chain for this config was established."}
    if "SYNTHETIC_ENGINEERING_ONLY" in target:
        return {"classification":"INTENTIONAL_SYNTHETIC_NEGATIVE_FIXTURE","review_priority":"P2","disposition":"RETAIN_NEGATIVE_CASE","reason":"The fixture namespace and all-zero SHA are explicit negative-test input; missing payload is the expected rejection case."}
    if "source_path" in symbol and any(ch.isspace() for ch in target):
        return {"classification":"PROSE_NOT_A_FILE_REFERENCE","review_priority":"INFO","disposition":"REMOVE_FROM_FILE_REFERENCE_EDGES","reason":"The source_path field contains explanatory prose with slash-separated words, not a filesystem path; R20 path-token validation reclassifies it."}
    if caller=="config/automatic_input.yaml":
        return {"classification":"EXTERNAL_TDX_DATASET_LOCATOR","review_priority":"P2","disposition":"KEEP_EXTERNAL_LOCATOR_UNRESOLVED_LOCALLY","reason":"The path is a configured external TDX data root/zip locator and is not expected inside this repository."}
    if caller=="config/operational_daily_exact_release_policy_v2.json":
        return {"classification":"ACTIVE_POLICY_FAIL_CLOSED_MISSING_SOURCE","review_priority":"P1","disposition":"BLOCKED_NO_SAFE_REBINDING_EVIDENCE","reason":"This runtime policy binding is absent locally, so its verifier fails closed. No replacement accepted source bytes are available."}
    return {"classification":"MISSING_TARGET_REQUIRES_OWNER_REVIEW","review_priority":"P2","disposition":"NO_AUTOMATIC_REPAIR","reason":"Target is absent from this checkout; an external-root or frozen-history contract must establish whether it should be locally present."}

def build_review(baseline,current,restorations=None):
    restorations=restorations or {}
    old=baseline.get("reference_edges",[]); new=current.get("reference_edges",[])
    queues=collections.defaultdict(collections.deque)
    for row in new: queues[key(row)].append(row)
    selected=[x for x in old if x.get("risk_type") in {"ACTUAL_MISMATCH","MISSING_FILE"}]
    items=[]; unmatched=[]
    for row in selected:
        candidates=queues.get(key(row)); now=candidates.popleft() if candidates else None
        c=classify(now or row,restorations)
        chain_id=now.get("reachability_chain_id") if now else None
        items.append({"reference_id":row.get("reference_id"),"baseline_reference_id":row.get("reference_id"),"baseline_risk_type":row.get("risk_type"),"baseline_priority":row.get("priority"),"caller_path":row.get("caller_path"),"entrypoint":now.get("entrypoint") if now else row.get("entrypoint"),"json_pointer_or_line":row.get("symbol"),"target":row.get("literal_or_resolved_target"),"resolved_path":now.get("resolved_path") if now else None,"expected_sha256":row.get("expected_sha256"),"expected_bytes":row.get("expected_bytes"),"baseline_actual_sha256":row.get("actual_sha256"),"baseline_actual_bytes":row.get("actual_bytes"),"r20_reference_id":now.get("reference_id") if now else None,"r20_risk_type":now.get("risk_type") if now else None,"r20_priority":now.get("priority") if now else None,"r20_actual_sha256":now.get("actual_sha256") if now else None,"r20_actual_bytes":now.get("actual_bytes") if now else None,"r20_expected_bytes":now.get("expected_bytes") if now else None,"historical_or_current":now.get("historical_or_current") if now else row.get("historical_or_current"),"origin_commit":now.get("origin_commit") if now else None,"archive_path":now.get("archive_path") if now else None,"archive_sha256":now.get("archive_sha256") if now else None,"archive_hash_verified":now.get("archive_hash_verified") if now else False,"t0":now.get("T0") if now else row.get("T0"),"publication_id":now.get("publication_id") if now else row.get("publication_id"),"namespace":now.get("namespace") if now else row.get("namespace"),"exists":now.get("exists") if now else None,"reachability_class":now.get("reachability_class") if now else None,"reachability_chain_id":chain_id,"reachability_chain":current.get("reachability_chains",{}).get(chain_id,[]) if chain_id else [],"runtime_traced":bool(now and now.get("proof",{}).get("runtime_trace") is True),"path_expression":now.get("path_expression") if now else None,"dynamic_resolution_steps":now.get("dynamic_resolution_steps") if now else [],"evidence":now.get("proof") if now else None,"candidate_invoked_by":now.get("candidate_invoked_by",[]) if now else [],"status":c["disposition"],**c})
        if now is None and c["classification"]!="PROSE_NOT_A_FILE_REFERENCE": unmatched.append(row.get("reference_id"))
    return {"contract_id":"V4_R20_R19_352_92_ITEM_REVIEW_R1","baseline_git_head":baseline.get("git_head"),"r20_git_head":current.get("git_head"),"baseline_selected_count":len(selected),"baseline_mismatch_count":sum(x.get("risk_type")=="ACTUAL_MISMATCH" for x in selected),"baseline_missing_count":sum(x.get("risk_type")=="MISSING_FILE" for x in selected),"matched_current_edge_count":sum(1 for x in items if x["r20_reference_id"] is not None),"reclassified_not_file_reference_count":sum(x["classification"]=="PROSE_NOT_A_FILE_REFERENCE" for x in items),"unmatched_baseline_reference_ids":unmatched,"review_priority_counts":dict(collections.Counter(x["review_priority"] for x in items)),"classification_counts":dict(collections.Counter(x["classification"] for x in items)),"items":items}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--baseline",required=True);ap.add_argument("--current",required=True);ap.add_argument("--output",required=True);ap.add_argument("--restorations");a=ap.parse_args()
    baseline=json.loads(Path(a.baseline).read_text(encoding="utf-8"));current=json.loads(Path(a.current).read_text(encoding="utf-8"));restorations={}
    if a.restorations:
        data=json.loads(Path(a.restorations).read_text(encoding="utf-8"));restorations={x["path"]:x for x in data["restored"]}
    review=build_review(baseline,current,restorations)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_name("."+out.name+".tmp");tmp.write_text(json.dumps(review,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(out)
    print(json.dumps({k:review[k] for k in ("baseline_selected_count","baseline_mismatch_count","baseline_missing_count","matched_current_edge_count","unmatched_baseline_reference_ids","review_priority_counts","classification_counts")}))
    return 0 if not review["unmatched_baseline_reference_ids"] else 1
if __name__=="__main__":raise SystemExit(main())

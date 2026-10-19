"""CI assertions for complete R20 file-reference inventory coverage."""
from __future__ import annotations
import argparse,collections,json,subprocess
from pathlib import Path
SOURCE_EXTS={".py", ".sh", ".ps1", ".bat", ".cmd", ".sql", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".css"}

def validate(root:Path, inventory:dict):
    tracked=[x.decode("utf-8","surrogateescape").replace("\\","/") for x in subprocess.check_output(["git","-C",str(root),"ls-files","-z"]).split(b"\0") if x]
    edges=inventory.get("reference_edges") or []
    risk=collections.Counter(x.get("risk_type") for x in edges);priority=collections.Counter(x.get("priority") for x in edges)
    docs_sources=[x for x in edges if x.get("caller_path","").startswith(("reports/","docs/"))]
    docs_targets=[x for x in edges if (x.get("literal_or_resolved_target") or "").replace("\\","/").lower().startswith(("reports/","docs/"))]
    closure=set(inventory.get("authority_dependency_closure_files",[]))
    dynamic_edges=[x for x in edges if x.get("static_or_dynamic")=="DYNAMIC"]
    expected_source_count=sum(Path(p).suffix.lower() in SOURCE_EXTS for p in tracked)
    checks={
      "head_matches_worktree":inventory.get("git_head")==subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip(),
      "tracked_file_count_matches_git":inventory.get("tracked_file_count")==len(tracked),
      "module_coverage_covers_all_tracked":sum(inventory.get("module_coverage",{}).values())==len(tracked),
      "source_file_count_matches_extensions":inventory.get("source_file_count")==expected_source_count,
      "edge_count_matches_rows":inventory.get("reference_edges_total")==len(edges),
      "reports_docs_sources_bounded_by_authority_closure":all(x.get("caller_path") in closure and x.get("reachability_class")=="CONFIRMED_AUTHORITY_CLOSURE" for x in docs_sources),
      "authority_closure_count_matches_files":inventory.get("authority_dependency_closure_count")==len(closure),
      "reports_docs_reference_targets_present_in_inventory":len(docs_targets)>0,
      "dynamic_rows_have_expression_and_resolution_steps":all(bool(x.get("path_expression")) and bool(x.get("dynamic_resolution_steps")) for x in dynamic_edges),
      "reachability_class_present_on_all_edges":all(x.get("reachability_class") in {"CONFIRMED_STATIC_CHAIN","CONFIRMED_AUTHORITY_CLOSURE","POSSIBLE_CURRENT_SCOPE","DETERMINED_RETIRED_OR_FIXTURE","OUTSIDE_V4_SCOPE"} for x in edges),
      "dynamic_unresolved_count_matches":inventory.get("dynamic_unresolved_count")==risk.get("DYNAMIC_UNRESOLVED",0),
      "historical_count_matches":inventory.get("historical_frozen_reference_count")==sum(x.get("historical_or_current")=="HISTORICAL" for x in edges),
      "p0_count_matches":inventory.get("p0_open")==priority.get("P0",0),
      "p1_count_matches":inventory.get("p1_open")==priority.get("P1",0),
      "lfs_pointer_count_matches":inventory.get("lfs_pointer_only_count")==risk.get("GIT_LFS_POINTER_ONLY",0),
      "lfs_verified_count_matches":inventory.get("lfs_object_verified_count")==sum(x.get("lfs_object_hash_verified") is True for x in edges),
      "no_unknown_dynamic_resolution_pass":not any(x.get("risk_type")=="DYNAMIC_UNRESOLVED" and not x.get("dynamic_resolution_steps") for x in edges),
    }
    return {"contract_id":"V4_R20_REFERENCE_INVENTORY_CI_ASSERTIONS_R2","checks":checks,"tracked_file_count":len(tracked),"source_file_count":expected_source_count,"reference_edges_total":len(edges),"authority_dependency_closure_count":len(closure),"reports_docs_reference_source_count":len(docs_sources),"reports_docs_reference_target_count":len(docs_targets),"dynamic_unresolved_count":risk.get("DYNAMIC_UNRESOLVED",0),"risk_counts":dict(risk),"priority_counts":dict(priority)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));ap.add_argument("--inventory",required=True);a=ap.parse_args();r=validate(Path(a.root).resolve(),json.loads(Path(a.inventory).read_text(encoding="utf-8")));print(json.dumps(r,ensure_ascii=False,sort_keys=True));return 0 if all(r["checks"].values()) else 1
if __name__=="__main__":raise SystemExit(main())

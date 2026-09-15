"""Verify the isolated P12-06 bundle pointer and production-write boundary."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from production.release import atomic_write_json
from workbench_service.research_bundle_v3_3 import read_active,validate_bundle
DB=ROOT/'data/database/market_research.duckdb';OUT=ROOT/'reports/p12_06/p12_06_stage_gate.json';POINTER=ROOT/'data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json'
def sha(p):h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def main():
 before=(DB.stat().st_size,DB.stat().st_mtime_ns);first=read_active(POINTER);digest=first['output_digest'];subprocess.run([sys.executable,str(ROOT/'scripts/build_p12_06_candidate_bundle.py')],cwd=ROOT,check=True,capture_output=True);second=read_active(POINTER);after=(DB.stat().st_size,DB.stat().st_mtime_ns);manifest=validate_bundle(Path(second['bundle_path']));receipt=json.loads((ROOT/'reports/p12_06/candidate_bundle_receipt.json').read_text(encoding='utf-8'))
 checks={'p12_05_accepted':json.loads((ROOT/'reports/p12_05/p12_05_stage_gate.json').read_text(encoding='utf-8'))['acceptance_result']=='DEGRADED_PASS','complete_bundle_readable':len(manifest['files'])==2 and receipt['result_rows']==113,'same_input_digest_idempotent':digest==second['output_digest'] and receipt['bundle']['reused'] is True,'production_database_unchanged':before==after,'pointer_identity_complete':all(second['identity'].get(k) for k in ('publication_id','snapshot_id','membership_snapshot_id','research_run_id','parameter_hash','dependency_lock_hash','trade_date')),'ui_not_switched_in_p12_06':receipt['ui_consumes_pointer'] is False}
 result={'stage_contract':'P12-06_BUNDLE_V3_3_ACCEPTANCE_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'pointer':str(POINTER),'bundle_path':second['bundle_path'],'output_digest':digest,'input_identity':second['identity'],'checks':checks,'failure_probes':'tests/upgrade_v3/test_p12_06_bundle.py','acceptance_result':'DEGRADED_PASS' if all(checks.values()) else 'BLOCKED','acceptance_scope':'Immutable file bundle, complete identity, atomic isolated pointer, hash validation, retry and failure preservation; UI consumption deferred','next_stage':'P12-07_UI_V3_3' if all(checks.values()) else 'P12-06_REPAIR'}
 atomic_write_json(OUT,result)
 if result['acceptance_result']=='BLOCKED':raise RuntimeError('P12-06 blocked')
 print(OUT)
if __name__=='__main__':main()

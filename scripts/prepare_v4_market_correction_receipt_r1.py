"""Prepare bounded Market receipt only; never overwrite a candidate/Head."""
import argparse,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_market_context_correction_r1 import KEY,CONTRACT,driver_scope

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--original',required=True);p.add_argument('--result-g3',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.out).resolve()
    if root.drive.upper()!='G:' or not out.is_relative_to(root/'data/v4'):raise ValueError('ADDITIVE_MARKET_OUTPUT_REQUIRED')
    original_binding=ref(root,Path(a.original));result_binding=ref(root,Path(a.result_g3))
    original=json.loads(checked(root,original_binding).read_bytes());result=json.loads(checked(root,result_binding).read_bytes())
    if result.get('acceptance')!='PASS' or result.get('G3',{}).get('status')!='PASS':raise ValueError('MARKET_ACTUAL_G3_REQUIRED')
    adapter_path=ROOT/'src/workbench_analysis/operational_owner_adapter_v1.py';raw=adapter_path.read_bytes()
    archived=out.parent/'driver_sources'/hashlib.sha256(raw).hexdigest()/'operational_owner_adapter_v1.py'
    if not archived.exists():
        from workbench_analysis.tdx_official_daily_source import _atomic_write
        _atomic_write(archived,raw,tdx_root=Path('D:/new_tdx'))
    old=json.loads(checked(root,original['release_policy']).read_bytes());maps={b.get('module_path',b['path']):b for b in old['accepted_algorithm_bindings']}
    drivers={'src/workbench_analysis/r43_market_replay.py':result['G3']['producer'],'src/workbench_analysis/operational_owner_adapter_v1.py':ref(root,archived)}
    for name,function in [('src/workbench_analysis/r43_market_replay.py','materialize_market'),('src/workbench_analysis/operational_owner_adapter_v1.py','replay')]:driver_scope(checked(root,maps[name]).read_text(encoding='utf-8'),checked(root,drivers[name]).read_text(encoding='utf-8'),function)
    receipt=dict(contract_id=CONTRACT,generation_candidate=original_binding,patch_result=result_binding,driver_bindings=drivers)
    if out.exists() and json.loads(out.read_bytes())!=receipt:raise ValueError('MARKET_RECEIPT_IMMUTABLE_CONFLICT')
    if not out.exists():atomic_json(root,out,receipt)
    print(json.dumps(dict(key=KEY,binding=ref(root,out),status='PREPARATION_ONLY_CANDIDATE_VERIFICATION_REQUIRED')))
if __name__=='__main__':main()

"""Real four-session typed delta V2, independent target BAR reconciliation."""
import csv
import gzip
import io
import json
import struct
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.tdx_snapshot_delta_v2 import build_typed_delta,file_sha,digest
from workbench_analysis.tdx_official_daily_source import _atomic_write
from workbench_analysis.dm01_sources_r4 import parent_tdx_package

OUT=ROOT/'docs/evidence/r4_2_1_20261009'
DATES=['2026-09-28','2026-09-29','2026-09-30','2026-10-08']


def load(p):return json.loads(Path(p).read_bytes())


def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)


def write(p,v):
    _atomic_write(p,(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode(),tdx_root=Path('D:/new_tdx'))


def inputs():
    head=load(ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json')
    ib=head['component_artifacts']['IDENTITY_UNIVERSE'];ip=ROOT/ib['path']
    if file_sha(ip)!=ib['sha256']:raise ValueError('IDENTITY_DIGEST_MISMATCH')
    ids={r['source_security_key'].upper():r for r in load(ip)['rows']
         if r['security_type']=='A_STOCK' and r['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT')}
    pb=parent_tdx_package(ROOT)
    current=load(ROOT/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/CORE_REPLAY.json')['owners'][0]['sources']['package']
    acq=load(ROOT/'docs/evidence/source_acquisition_r4_20261009/capture/acquisition.json')
    members={}; roster_bindings=[]
    for q in acq['queries']:
        if q.get('path') and q['method']=='query_all_stock' and q['params'].get('day') in DATES:
            day=q['params']['day'];p=Path(q['path']);payload=load(p)
            members[day]={r['code'].upper() for r in payload['rows']}
            roster_bindings.append(dict(trade_date=day,**ref(p)))
    if set(members)!=set(DATES):raise ValueError('FOUR_DATED_ROSTERS_REQUIRED')
    return head,ids,dict(ib,dated_rosters=roster_bindings),pb,current,members


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    head,ids,ib,pb,cb,members=inputs()
    protected={p:file_sha(ROOT/p) for p in ('data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_joint_release_authority_v1.json')}
    policy=ROOT/'config/tdx_a_stock_delta_scope_policy_v2.json'
    entry=OUT/'ENTRY_SOURCE_AND_RELEASE_HEAD.json'
    if not entry.exists():
        write(entry,dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
            stage_contract='R4.2.1',phase0='DEGRADED_PASS',observed_at=datetime.now(timezone.utc).isoformat(),
            production_protected=protected,parent_package=pb,current_package=cb,
            consulted_upgrade='R4_2_1_TASK_CONTRACT.md',acceptance='IN_PROGRESS',next_stage='TYPED_DELTA_AND_TAXONOMY_ISOLATION'))
    result=build_typed_delta(parent_zip=ROOT/pb['path'],current_zip=ROOT/cb['path'],target_dates=DATES,
        identities=ids,identity_binding=ib,policy_binding=ref(policy),parent_sha256=pb['sha256'],current_sha256=cb['sha256'],dated_members=members)
    for day,value in result['targets'].items():
        write(OUT/'typed_delta'/day/'delta_v2.json',dict(value,contract_id=result['contract_id'],target_date=day,
              source_scope_policy=ref(policy),AS_RECORDED=False,production_permission=False,
              parent_package_sha256=pb['sha256'],current_package_sha256=cb['sha256'],delta_sha256=result['delta_sha256']))
    # Re-read actual records with independent direct struct decoding, no typed parser.
    independent={d:[] for d in DATES};errors=[]
    with zipfile.ZipFile(ROOT/cb['path']) as z:
        for name in z.namelist():
            leaf=name.lower().replace('\\','/').split('/')[-1]
            if not leaf.endswith('.day') or len(leaf)!=12:continue
            key=leaf[:2].upper()+'.'+leaf[2:8]
            if key not in ids:continue
            for b in struct.iter_unpack('<IIIIIfII',z.read(name)):
                s=str(b[0]);day=s[:4]+'-'+s[4:6]+'-'+s[6:]
                if day not in DATES or key not in members[day] or b[6]==0:continue
                i=ids[key];start=i.get('list_date');end=i.get('delist_date')
                if not start or day<start or (end and day>end):continue
                independent[day].append(dict(trade_date=b[0],open=b[1]/100,high=b[2]/100,low=b[3]/100,close=b[4]/100,
                    amount=b[5],volume=b[6],security_id=i['security_id'],source_security_key=key))
    for day,rs in independent.items():
        rs.sort(key=lambda r:r['security_id'])
        if rs!=result['targets'][day]['target_bars']:errors.append(day+':TARGET_ROWS_MISMATCH')
    manifest=result.pop('entry_manifest')
    _atomic_write(OUT/'TYPED_ENTRY_MANIFEST.jsonl.gz',gzip.compress(b''.join((json.dumps(r,sort_keys=True)+'\n').encode() for r in manifest),mtime=0),tdx_root=Path('D:/new_tdx'))
    existing=load(ROOT/'docs/evidence/r4_1_audit_repair_r1_20261009/OFFICIAL_PACKAGE_STRICT_DELTA_BLOCKERS.json')
    bad={r['path'].lower() for r in existing['entries']}
    sample=[r for r in manifest if r['path'] in bad]+[r for r in manifest if r.get('inferred_type')=='A_STOCK_CANONICAL'][:10]
    text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=sorted(set(k for r in sample for k in r)));writer.writeheader()
    writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in sample)
    _atomic_write(OUT/'OFFICIAL_ZIP_TYPED_ENTRY_VALIDATION.csv',text.getvalue().encode('utf-8-sig'),tdx_root=Path('D:/new_tdx'))
    for day,v in result['targets'].items():
        v.pop('target_bars')
        v['binding']=ref(OUT/'typed_delta'/day/'delta_v2.json')
    result.update(parent_package=pb,current_package=cb,independent_target_counts={d:len(r) for d,r in independent.items()},
        independent_target_errors=errors,manifest=ref(OUT/'TYPED_ENTRY_MANIFEST.jsonl.gz'),
        prior_18_anomalies_accounted=sum(r['path'] in bad for r in manifest),
        protected_unchanged=all(file_sha(ROOT/p)==h for p,h in protected.items()),
        request_count_this_run=0,cache_use='HASH_VERIFIED_FROZEN_OFFICIAL_SOURCE',
        producer_bindings=[ref(ROOT/'src/workbench_analysis/tdx_snapshot_delta_v2.py'),ref(ROOT/'scripts/execute_r4_2_typed_delta.py')],
        acceptance='PASS_TYPED_A_STOCK_SCOPE' if not errors and result['status']=='READY' else 'FAIL')
    write(OUT/'TDX_A_STOCK_DELTA_V2_RUNTIME_RECEIPT.json',result)
    print(json.dumps({k:result[k] for k in ('status','targets','independent_target_counts','prior_18_anomalies_accounted','acceptance')}),flush=True)
    return 0 if result['acceptance']=='PASS_TYPED_A_STOCK_SCOPE' else 2


if __name__=='__main__':raise SystemExit(main())

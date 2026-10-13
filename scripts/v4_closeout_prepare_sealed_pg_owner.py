"""Prepare native facts for an already sealed candidate without recomputation."""
import argparse,json,os,hashlib
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_operational_owner_authority_v2 import prepare_successor

ROOT=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label.isalnum():raise ValueError('VERSIONED_PREPARATION_REQUIRED')
    report=OUT/('SEALED_NATIVE_OWNER_'+a.label+'.json')
    if report.exists():raise ValueError('PRESERVE_PRIOR_PREPARATION')
    runpath=Path(a.run).resolve()
    if not runpath.is_relative_to(OUT):raise ValueError('RUN_SCOPE_REQUIRED')
    run=json.loads(runpath.read_bytes())
    if run['status']!='CANDIDATE_SEALED_NOT_PUBLISHED':raise ValueError('SEALED_CANDIDATE_REQUIRED')
    candidate=json.loads(checked(ROOT,run['candidate']).read_bytes())
    heads={name:(ROOT/'data/v4'/name).read_bytes() for name in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json')}
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[1]]
    receipt=prepare_successor(ROOT,candidate)
    raw=json.dumps(candidate,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    path=ROOT/'data/v4/prepared_daily_candidates_v2'/hashlib.sha256(raw).hexdigest()/'CANDIDATE.json'
    if path.exists():
        if json.loads(path.read_bytes())!=candidate:raise ValueError('IMMUTABLE_CANDIDATE_CONFLICT')
    else:atomic_json(ROOT,path,candidate)
    if any((ROOT/'data/v4'/name).read_bytes()!=before for name,before in heads.items()):raise ValueError('HEAD_MOVED_DURING_PREPARATION')
    result=dict(contract_id='V4_SEALED_DAILY_NATIVE_OWNER_PREPARATION_R1',source_candidate=run['candidate'],candidate=ref(ROOT,path),receipt=receipt,
        acceptance='PASS_NATIVE_OWNER_PAYLOAD_ONLY',numerical_recomputed=False,publication=False,
        heads_unchanged={name:hashlib.sha256(value).hexdigest() for name,value in heads.items()})
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],counts=receipt['counts'],candidate=result['candidate'])),flush=True)

if __name__=='__main__':main()

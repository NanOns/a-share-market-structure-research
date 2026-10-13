"""Attach independent period proof and read new dated facts as formal reader."""
import argparse,json,os,hashlib
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label.isalnum():raise ValueError('VERSIONED_READBACK_REQUIRED')
    out=OUT/('SEALED_READER_'+a.label+'.json')
    if out.exists():raise ValueError('PRESERVE_PRIOR_READBACK')
    preparation=json.loads((OUT/('SEALED_NATIVE_OWNER_'+a.label+'.json')).read_bytes())
    candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes())
    period=json.loads((OUT/('DAILY_PERIOD_ORACLE_'+a.label+'.json')).read_bytes())
    day=candidate['accepted_trade_date']
    if period['acceptance']!='PASS' or period['errors'] or period['target_session']!=day or period['owners']!={k:candidate['owners'][day][k] for k in ('period_raw','period_adjusted')}:
        raise ValueError('EXACT_PERIOD_ACCEPTANCE_REQUIRED')
    verifier=Path(__file__).with_name('v4_closeout_daily_period_oracle.py');raw=verifier.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=period['verifier']['sha256']:raise ValueError('PRESERVE_EXECUTED_ORACLE_SOURCE')
    archive=ROOT/'data/v4/independent_verifiers'/hashlib.sha256(raw).hexdigest()/verifier.name
    archive.parent.mkdir(parents=True,exist_ok=True)
    if archive.exists():
        if archive.read_bytes()!=raw:raise ValueError('IMMUTABLE_ORACLE_CONFLICT')
    else:
        from workbench_analysis.tdx_official_daily_source import _atomic_write
        _atomic_write(archive,raw,tdx_root=Path('D:/new_tdx'))
    period['verifier']=ref(ROOT,archive)
    folder=ROOT/'data/v4/prepared_daily_candidates_v2'/preparation['candidate']['sha256']
    receipt=folder/'PERIOD_NUMERIC_ORACLE.json';atomic_json(ROOT,receipt,period)
    candidate['period_numeric_oracle']=ref(ROOT,receipt)
    path=folder/'CANDIDATE_WITH_PERIOD.json';atomic_json(ROOT,path,candidate)
    heads={n:(ROOT/'data/v4'/n).read_bytes() for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    api=OperationalSuccessorReaderV1(ROOT,candidate)
    records=[]
    for domain in candidate['owners'][day]:
        response=api.read(domain,day,api.token)
        if response['context_token']!=api.token or response['trade_date']!=day or response['status']!='READY':raise ValueError('SAME_DATE_TOKEN_OWNER_READ_REQUIRED')
        records.append(dict(domain=domain,T0=day,context_token=api.token,rows=len(response['rows']),container=type(response['rows']).__name__))
    try:api.read('raw',day,'0'*64)
    except ValueError as error:
        if str(error)!='CONTEXT_TOKEN_MISMATCH':raise
    else:raise ValueError('WRONG_REQUEST_TOKEN_ACCEPTED')
    if any((ROOT/'data/v4'/n).read_bytes()!=before for n,before in heads.items()):raise ValueError('HEAD_CHANGED_DURING_READBACK')
    result=dict(contract_id='V4_SEALED_CANDIDATE_FORMAL_READER_READBACK_R1',acceptance='PASS_READER_IO_ONLY',candidate=ref(ROOT,path),
        T0=day,context_token=api.token,records=records,reader_role=ROLES[0],full_admission='PENDING_HISTORY_FIELDS_AND_56_SCOPE',
        numerical_recomputed=False,publication=False,heads_unchanged={n:hashlib.sha256(raw).hexdigest() for n,raw in heads.items()})
    atomic_json(OUT,out,result);print(json.dumps(dict(acceptance=result['acceptance'],domains=len(records),T0=day,context_token=api.token)),flush=True)

if __name__=='__main__':main()

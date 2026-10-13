"""Migrate the actual current membership reference, with no Head publication."""
import json,os
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_membership_reference_pg_v1 import prepare,read

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    report=OUT/'NATIVE_MEMBERSHIP_PREPARATION_R6.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_MEMBERSHIP_PREPARATION')
    previous=json.loads((OUT/'SEALED_PRODUCT_CATALOG_R6.json').read_bytes())
    candidate=json.loads(checked(ROOT,previous['candidate']).read_bytes());credentials=load_credentials(ROOT/'config/native_pg_roles.dpapi')
    heads={name:(ROOT/'data/v4'/name).read_bytes() for name in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[1]];receipt=prepare(ROOT,candidate)
    path=ROOT/'data/v4/prepared_daily_candidates_v2'/previous['candidate']['sha256']/'CANDIDATE_WITH_NATIVE_MEMBERSHIP.json';atomic_json(ROOT,path,candidate)
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[0]];actual=read(ROOT,candidate)
    if len(actual)!=receipt['rows']:raise ValueError('FORMAL_MEMBERSHIP_READER_ROW_DENOMINATOR')
    if any((ROOT/'data/v4'/name).read_bytes()!=raw for name,raw in heads.items()):raise ValueError('HEAD_CHANGED_DURING_REFERENCE_PREPARATION')
    result=dict(contract_id='V4_NATIVE_MEMBERSHIP_REFERENCE_PREPARATION_R1',acceptance='PASS_REFERENCE_PAYLOAD_ONLY',candidate=ref(ROOT,path),receipt=receipt,
        reader_role=ROLES[0],publication=False,full_consumer_acceptance='REQUIRES_UPDATED_CURRENT_MEMBER_PROJECTION')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],rows=len(actual),publication=False)),flush=True)

if __name__=='__main__':main()

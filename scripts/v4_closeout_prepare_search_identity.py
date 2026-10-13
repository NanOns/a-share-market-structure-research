"""Close only the observed remaining complete identity search JSON consumer."""
import json,os
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from scripts.v4_closeout_sealed_bff_readback import NoLegacyFacts
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_db.v4_membership_reference_pg_v1 import prepare_search_identity,KEY
from workbench_service.core_product_bff_r1 import CoreProductBFFR1

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    report=OUT/'NATIVE_SEARCH_IDENTITY_PREPARATION_R6.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_SEARCH_IDENTITY_RECEIPT')
    previous=json.loads((OUT/'NATIVE_IDENTITY_PREPARATION_R6.json').read_bytes());candidate=json.loads(checked(ROOT,previous['candidate']).read_bytes())
    before=json.loads(checked(ROOT,candidate[KEY]).read_bytes());heads={n:(ROOT/'data/v4'/n).read_bytes() for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    credentials=load_credentials(ROOT/'config/native_pg_roles.dpapi');os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[1]]
    receipt=prepare_search_identity(ROOT,candidate);after=json.loads(checked(ROOT,candidate[KEY]).read_bytes())
    if any(after[k]!=v for k,v in before.items()):raise ValueError('PRIOR_REFERENCE_FACT_CHANGED')
    path=ROOT/'data/v4/prepared_daily_candidates_v2'/previous['candidate']['sha256']/'CANDIDATE_WITH_SEARCH_IDENTITY.json';atomic_json(ROOT,path,candidate)
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[0]]
    bff=CoreProductBFFR1(OperationalSuccessorReaderV1(ROOT,candidate),NoLegacyFacts())
    source=after['search_identity']['source'];expected=json.loads(checked(ROOT,source).read_bytes())['records']
    actual,binding=bff.identity_records()
    if actual!=expected or binding!=source:raise ValueError('SEARCH_IDENTITY_NATIVE_READ_DIFFERENCE')
    bff.api.cache.pop(('product-identity',))
    from workbench_service import core_product_bff_r1
    original=core_product_bff_r1.checked
    def forbidden(*args):raise RuntimeError('SEARCH_IDENTITY_BUSINESS_JSON_READ_FORBIDDEN')
    core_product_bff_r1.checked=forbidden
    try:
        if bff.identity_records()!=(expected,source):raise ValueError('SEARCH_IDENTITY_NO_FALLBACK_DIFFERENCE')
    finally:core_product_bff_r1.checked=original
    if any((ROOT/'data/v4'/n).read_bytes()!=raw for n,raw in heads.items()):raise ValueError('HEAD_CHANGED_DURING_SEARCH_REFERENCE_PREPARATION')
    result=dict(contract_id='V4_NATIVE_SEARCH_IDENTITY_PREPARATION_R1',acceptance='PASS_CHANGED_CONSUMER_ONLY',candidate=ref(ROOT,path),receipt=receipt,
        reader_role=ROLES[0],business_json_consumer_forbidden=True,complete_source_rows_equal=True,prior_reference_facts_preserved=True,publication=False)
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],rows=len(actual),publication=False)),flush=True)

if __name__=='__main__':main()

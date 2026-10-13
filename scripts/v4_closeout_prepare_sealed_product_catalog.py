"""Prepare current PG read pack and immutable dated catalogue; never publish."""
import argparse,json,os,hashlib
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_product_pack_v3 import prepare

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label.isalnum():raise ValueError('VERSIONED_CATALOG_PREPARATION_REQUIRED')
    report=OUT/('SEALED_PRODUCT_CATALOG_'+a.label+'.json')
    if report.exists():raise ValueError('PRESERVE_PRIOR_CATALOG')
    previous=json.loads((OUT/('SEALED_READER_'+a.label+'.json')).read_bytes())
    candidate=json.loads(checked(ROOT,previous['candidate']).read_bytes())
    correction=json.loads((OUT/('HISTORY_CORRECTIONS_'+a.label+'.json')).read_bytes())
    if correction['acceptance']!='PASS_PREPARATION_ONLY':raise ValueError('HISTORICAL_CORRECTIONS_PREPARATION_REQUIRED')
    run=json.loads((OUT/('exact_daily_candidate_20261013_'+a.label+'.json')).read_bytes())
    folder=checked(ROOT,run['candidate']).parent;replay=json.loads((folder/'owner_v3/CORE_REPLAY.json').read_bytes())
    owner=next(row for row in replay['owners'] if row['trade_date']==candidate['accepted_trade_date'])
    heads={n:(ROOT/'data/v4'/n).read_bytes() for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[1]]
    receipt=prepare(ROOT,candidate,owner,historical_indices=correction['indices'])
    path=ROOT/'data/v4/prepared_daily_candidates_v2'/previous['candidate']['sha256']/'CANDIDATE_WITH_PRODUCT_CATALOG.json';atomic_json(ROOT,path,candidate)
    if any((ROOT/'data/v4'/n).read_bytes()!=before for n,before in heads.items()):raise ValueError('HEAD_CHANGED_DURING_CATALOG_PREPARATION')
    result=dict(contract_id='V4_SEALED_CANDIDATE_PRODUCT_CATALOG_PREPARATION_R1',candidate=ref(ROOT,path),receipt=receipt,acceptance='PASS_PREPARATION_ONLY',
        publication=False,numerical_producer_recomputed=False,heads_unchanged={n:hashlib.sha256(raw).hexdigest() for n,raw in heads.items()})
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],receipt=receipt)),flush=True)

if __name__=='__main__':main()

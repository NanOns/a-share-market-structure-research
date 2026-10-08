"""Stage the native owner -> Focus -> research chain without changing live authority."""
import copy,gzip,json,os,sqlite3,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from focus_tracker.v4_native_core_daily_driver import advance
from focus_tracker.v4_path_adapter import checked
from workbench_service.production_v4 import ProductionV4ResearchReader,build_snapshot,frozen_current_reader
from workbench_service.current_v4_context import SourceInvalid
from workbench_service.joint_release import AUTHORITY

OWNERS={'market':(5,'v4_market_operational_authority_v1.json'),
        'sector':(6,'v4_sector_operational_authority_v1.json'),
        'stocks':(7,'v4_stock_operational_authority_v1.json'),
        'market_center':(9,'v4_market_center_authority_v1.json'),
        'forward':(10,'v4_forward_operational_authority_v1.json')}
MODULES={5:'build_fp05_market',6:'build_fp06_sector_v2',7:'build_fp07_stock',9:'build_fp09_market_center',10:'build_fp10_forward_v2'}

def prepare(*,rebuild_owners=False,replay_namespace=False):
    live_before=(ROOT/AUTHORITY).read_bytes();live=ProductionV4ResearchReader(ROOT)
    live_joint=json.loads(live_before)
    current,_=frozen_current_reader(ROOT);context=current.load_context()['context'];day=context['accepted_trade_date']
    run=day+'_'+uuid.uuid4().hex
    directory=ROOT/'data/v4/r2_daily_candidates'/run
    evidence=ROOT/'docs/evidence/r2_daily_runs'/run
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT),
             R2_DAILY_AUTHORITY_DIR=str(directory),R2_DAILY_EVIDENCE_DIR=str(evidence),
             TEMP='E:/codex_tmp',TMP='E:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
    overrides={};stages=[]
    for key,(stage,name) in OWNERS.items():
        cached=live_joint.get('daily_owner_authorities',{}).get(key) or json.loads((ROOT/'config'/name).read_bytes())
        reusable=cached['trade_date']==day and cached['input_data_head']['sha256']==context['data_head_digest']
        if rebuild_owners or not reusable:
            process=subprocess.run([sys.executable,'-B','-m','scripts.'+MODULES[stage]],cwd=ROOT,env=env,
                capture_output=True,text=True,encoding='utf8',timeout=1200)
            write(evidence/('fp%02d_process.json'%stage),dict(exit_code=process.returncode,stdout=process.stdout,stderr=process.stderr))
            if process.returncode:raise SourceInvalid('DAILY_OWNER_FAILED_FP%02d'%stage)
            authority=json.loads((directory/name).read_bytes())
        else:authority=cached
        if authority['trade_date']!=day or authority['input_data_head']['sha256']!=context['data_head_digest']:
            raise SourceInvalid('DAILY_OWNER_CONTEXT_MISMATCH_'+key)
        overrides[key]=authority
        stages.append(dict(owner=key,trade_date=day,result='REBUILT' if rebuild_owners or not reusable else 'EXACT_ACCEPTED_OWNER_REUSED'))
    manifest=copy.deepcopy(live.manifest);contract,_=current._contract()
    manifest['context']=context;manifest['sources']['states']=contract['sources']['states']
    manifest['sources']['market_operational']=overrides['market']['market']
    manifest['sources']['stock_series']=overrides['stocks']['series']
    previous=live.manifest['sources']['focus_journal']
    with sqlite3.connect(checked(ROOT,previous).as_uri()+'?mode=ro',uri=True) as db:
        expected=db.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]
    first=None
    if replay_namespace:
        states=json.load(gzip.open(checked(ROOT,manifest['sources']['states']),'rt',encoding='utf8'))
        prior=states['prior_binding'];prior_states=json.load(gzip.open(checked(ROOT,prior),'rt',encoding='utf8'))
        earlier=copy.deepcopy(manifest);earlier['context']['accepted_trade_date']=prior_states['rows'][0]['trade_date'];earlier['sources']['states']=prior
        first=advance(ROOT,earlier)
        focus=advance(ROOT,manifest,previous_journal=first['journal'],previous_publication=first['publication'],expected_head=first['head'])
    else:
        focus=advance(ROOT,manifest,previous_journal=previous,
            previous_publication=live.manifest['sources']['focus_operational'],expected_head=expected)
    # Replay coverage is separate; a stale replay must neither masquerade as current nor block local daily staging.
    replay=json.loads((ROOT/'config/v4_replay_compare_authority_v1.json').read_bytes())
    overrides['replay']=replay if replay['trade_date']==day and replay['input_data_head']['sha256']==context['data_head_digest'] else None
    snapshot=build_snapshot(ROOT,publish=False,focus_override=dict(trade_date=day,input_data_head=overrides['market']['input_data_head'],publication=focus['publication'],journal=focus['journal']),authority_overrides=overrides)
    candidate=ProductionV4ResearchReader(ROOT,snapshot_authority=snapshot['pointer'])
    assert candidate.context['accepted_trade_date']==day
    assert (ROOT/AUTHORITY).read_bytes()==live_before
    result=dict(status='STAGED_OWNER_FOCUS_SNAPSHOT_PASS',trade_date=day,stages=stages,focus=focus,snapshot=snapshot,owner_authorities=overrides,
        first_day=first,live_authority_preserved=True,automatic_production_write_admitted=False,full_daily_e2e_pass=False,
        next_stage='EXACT_CANDIDATE_UI_OWNER_QA_AND_JOINT_CAS')
    write(evidence/'CANDIDATE.json',result)
    write(ROOT/'runtime/research_daily/OWNER_CHAIN_STAGING_LATEST.json',dict(receipt=ref(evidence/'CANDIDATE.json'),**result))
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--rebuild-owners',action='store_true');parser.add_argument('--replay-namespace',action='store_true');args=parser.parse_args()
    result=prepare(rebuild_owners=args.rebuild_owners,replay_namespace=args.replay_namespace)
    print(json.dumps(dict(status=result['status'],trade_date=result['trade_date'],full_daily_e2e_pass=False)))

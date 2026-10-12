"""Resume actual R13 Focus from immutable five-day D2 and verified native Series."""
import gzip,hashlib,json,os,sys,time,traceback
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
workspace=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
generation='f12dba29cbad0cf13c4ab1645d237d90217fdbba39197d39a206b3ec8b76de82'
folder=workspace/'data/v4/dynamic_daily_owners/2026-10-09'/generation
owner_out=folder/'owner_v3'
run=sys.argv[1]
if not run.startswith('FOCUS_RESUME_R') or not run.replace('_','').isalnum():raise ValueError('VERSIONED_FOCUS_RESUME_REQUIRED')
audit=ROOT/'docs/audits/r4_r3_consumers_20261011'/run;audit.mkdir(exist_ok=False)
destination=folder/run;destination.mkdir(exist_ok=False)
from scripts.r4_readonly_source_guard import install
install(['G:/codex work/大A交易','D:/new_tdx',str(owner_out),str(folder/'sector_v3')])
os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
os.environ['R4_CONNECTION_LEDGER']=str(audit/'ACTUAL_CONNECTIONS.jsonl')
from tests import v4_native_isolation_plugin_r4 as guard
config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='ACTUAL_R13_FOCUS_RESUME_VERIFIED_PG_PROJECTION'
from scripts.r4_r3_consumer_trace import ConsumerTrace
trace=ConsumerTrace(audit/'ACTUAL_56_TRACE.json','Actual R13 persisted five-day D2 -> real native Focus/Forward consumers');trace.start()
from workbench_analysis.r43_owner_replay import ref,checked,gzrows,load
from workbench_db.v4_series_pg_r1 import verified_series_scope
from focus_tracker.v4_native_core_adapter import AcceptedPaths,enriched_project
protected=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_joint_release_authority_v1.json']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before={p:sha(workspace/p) for p in protected}
inputs={};sources=load(owner_out/'SOURCE_BINDINGS.json')['sources'];profiles=load(owner_out/'PROFILE_STRUCTURE_REPLAY.json');sectors=load(folder/'sector_v3/SECTOR_REPLAY.json')
freeze=load(ROOT/'docs/audits/r4_r3_consumers_20261011/SOURCE_DERIVATION_R13/ENGINEERING_SOURCE_FREEZE.json')
for name,expected in freeze['engineering_exact_adjustment_candidate']['executed_sources'].items():
    if sha(ROOT/name)!=expected:raise ValueError('R13_EXECUTED_MATH_SOURCE_MOVED')
days={};status={};native={};contexts={};receipts=[];metadata=None
keys=('membership_mode','taxonomy','membership_snapshot_id','membership_observed_at','member_set_asof','knowledge_lineage','AS_RECORDED','PIT_ELIGIBLE','HISTORICAL_FIRST_AVAILABLE_PROVEN','production_eligible_scope','survivorship_bias_risk')
series=ref(workspace,owner_out/'focus_actual_bars.pg.json')
for item in profiles['owners']:
    owner=item['owner'];day=owner['trade_date'];base=owner_out/'owners'/day
    path=base/'corrected_d2.json.gz'
    with gzip.open(path,'rt',encoding='utf8') as stream:publication=json.load(stream)
    current={k:publication[k] for k in keys}
    if metadata is None:metadata=current
    if metadata!=current or publication.get('accepted') is not False:raise ValueError('R13_FOCUS_MEMBERSHIP_OR_ACCEPTANCE_DRIFT')
    days[day]=publication['rows']
    if len(days[day])!=owner['rows'] or any(r['trade_date']!=day for r in days[day]):raise ValueError('R13_FULL_D2_ROWS_OR_DATE_DRIFT')
    calculations=gzrows(base/'corrected_d0_prewatch.jsonl.gz')
    contexts[day]={r['security_id']:r.get('research_mainline_context') for r in calculations}
    status[day]=ref(workspace,base/'focus_status.json')
    native[day]=dict(contract_id='R2_V4_FOCUS_NATIVE_CORE_FACTS_V1',trade_date=day,price_basis='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',factors=owner['core'],profiles=owner['profiles'],series=series)
    for p in (path,base/'corrected_d0_prewatch.jsonl.gz',base/'corrected_state_input_facts.jsonl.gz',base/'focus_status.json'):inputs[str(p)]=sha(p)
    for binding in (owner['core'],owner['profiles']):checked(workspace,binding)
    receipts.append(dict(trade_date=day,rows=len(days[day]),D0=dict(Counter(r['confirmation']['confirmation_status'] for r in calculations)),PREWATCH=dict(Counter(r['prewatch']['raw_qualification'] for r in calculations)),D2_freshness=dict(Counter(r['state_freshness'] for r in days[day])),D2=ref(workspace,path),facts=ref(workspace,base/'corrected_state_input_facts.jsonl.gz'),calculations=ref(workspace,base/'corrected_d0_prewatch.jsonl.gz')))
bindings=dict(series=series,calendar=ref(workspace,owner_out/'FOCUS_CALENDAR.json'),gbbq=sources['gbbq'],classification=ref(workspace,workspace/'config/v4_02_gbbq_price_impact_classification_v1.json'),status=status,native_core=native)
start=time.monotonic();result=None
try:
    with verified_series_scope():projection=enriched_project(days,AcceptedPaths(workspace,bindings))
    for episode in projection['episodes']:
        episode.update(metadata);episode['research_mainline_context']=contexts.get(episode['start_date'],{}).get(episode['entity_id'])
        for name in ('observations','outcomes'):
            for row in episode[name]:row.update(metadata);row['research_mainline_context']=contexts.get(row['trade_date'],{}).get(episode['entity_id'])
        for anchor in episode['anchors']:anchor.update(metadata)
    projection['research_mainline_source_bindings']=[s['relative_sector'] for s in sectors['owners']]
    projection.update(**metadata,contract_id='V4_R4_CORRECTED_FOCUS_FORWARD_CANDIDATE_V1',source_bindings=bindings,production_admission=False)
    path=destination/'CORRECTED_FOCUS_FORWARD.json.gz'
    with path.open('xb') as stream:stream.write(gzip.compress(json.dumps(projection,ensure_ascii=False,sort_keys=True).encode(),mtime=0))
    result=dict(status='ENGINEERING_FOCUS_PROJECTED',owners=receipts,focus=ref(workspace,path),episodes=len(projection['episodes']),events=len(projection['events']),outcomes=dict(Counter(o['outcome_status'] for e in projection['episodes'] for o in e['outcomes'])),production_admission=False,next_stage='INDEPENDENT_NUMERICAL_QA_AND_CANDIDATE_SEAL')
    (destination/'FOCUS_FORWARD_REPLAY.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
except BaseException as exc:result=dict(status='ENGINEERING_FAILED',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
finally:trace.close();guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)
after={p:sha(workspace/p) for p in protected}
unchanged=all(sha(p)==expected for p,expected in inputs.items())
if before!=after or not unchanged:raise ValueError('R13_IMMUTABLE_INPUT_OR_PROTECTED_HEAD_MOVED')
record=dict(contract='R4_R3_FOCUS_PERSISTED_CHECKPOINT_RESUME_V1',result=result,seconds=time.monotonic()-start,inputs=inputs,inputs_unchanged=unchanged,protected_before=before,protected_after=after,production_changed=False,source_bindings={p:sha(ROOT/p) for p in ('scripts/resume_r4_r3_focus_projection.py','src/workbench_db/v4_series_pg_r1.py','src/focus_tracker/v4_native_core_adapter.py','src/focus_tracker/v4_path_adapter.py')},all_56_numerical_acceptance='OPEN')
(audit/'RESULT.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(status=result['status'],seconds=record['seconds'],episodes=result.get('episodes'))));sys.exit(0 if result['status']=='ENGINEERING_FOCUS_PROJECTED' else 1)

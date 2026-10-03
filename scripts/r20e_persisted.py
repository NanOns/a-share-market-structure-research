"""Process-separated engineering replay. Every boundary is an exact persisted ref."""
import json,os,subprocess,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
from scripts.r20_io import ROOT,atomic,ref,read
NAMESPACE='reports/v4_15_runtime_r20/e2e_r2'
OUT='reports/r20e'
sys.path.insert(0,str(ROOT/'src'))

def now():return datetime.now(timezone.utc).isoformat()
def dh(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def components():
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    from workbench_analysis.v4_15_persistence import Store
    from workbench_analysis.v4_15_radar_cohort import RadarCohortRuntime
    from workbench_analysis.v4_15_settlement import SettlementRuntime
    a=CurrentStageAuthority(ROOT);s=Store(ROOT,NAMESPACE)
    return a,s,RadarCohortRuntime(a,s),SettlementRuntime(a,s)

def producer():
    start=now();a,s,c,d=components();t0='2026-08-31';nextdate=a.sessions[a.sessions.index(t0)+1]
    universe=[]
    for i,sid in enumerate(['S','CNF','INV','A','B','C','X']):
        universe.append(dict(security_id=sid,close=10,adjustment_identity='VECTOR_AFFINE_IDENTITY',hard_safety=True,research_eligible=True,prewatch_final_eligible=sid in ['S','CNF','INV'],delta3=7-i,prior20_mean_amount=100+i,vol20=.1+i/100,RPS20=50+i,primary_industry='J' if sid=='X' else 'I'))
    def owner(sid,event=None,maturity='PREWATCH',date=t0):
        return dict(entity_type='STOCK',entity_id=sid,episode_id='EP_'+sid,maturity=maturity,final_eligibility='FALSE' if event=='INVALIDATION' else 'TRUE',model_contract_id='RESEARCH_STATE_V1',state_lineage_id='E2E_ENGINEERING_LINEAGE',radar_owner_events=[event] if event else [],comparison_reference=10,signal_reference=10,adjustment_identity='VECTOR_AFFINE_IDENTITY',cutoff=date,parameter_set_id='ACCEPTED_VECTOR_PARAMETERS',primary_industry='I',transition_reasons=[],matched_predicates=['ACCEPTED_OWNER_EVENT'] if event else [])
    publications=[]
    for suffix,metadata in [('r1',{}),('r2',{}),('correction',{'observation_state':'CORRECTED','source_correction':True})]:
        rows=[owner(sid,'FIRST_PREWATCH') for sid in ['S','CNF','INV']]
        rows.append(owner('W','UPGRADE_TO_WARM','WARM'))
        fixture=dict(authority=a.head_ref,evidence_class='ENGINEERING_SYNTHETIC',trade_date=t0,publication_id='E2E_T0_'+suffix,rows=rows,observation_metadata=metadata)
        f=s.append('fixtures','T0_'+suffix,fixture);publications.append(c.engineering_fixture(f))
    # Later state changes cannot remove enrollment or stop forward settlement.
    later=dict(authority=a.head_ref,evidence_class='ENGINEERING_SYNTHETIC',trade_date=nextdate,publication_id='E2E_LATER',rows=[owner('S',None,date=nextdate),owner('CNF','NEW_CONFIRMED','CONFIRMED',nextdate),owner('INV','INVALIDATION','PREWATCH',nextdate)])
    later_ref=s.append('fixtures','LATER',later);publications.append(c.engineering_fixture(later_ref))
    manifest=s.read(publications[0]);snapshot=s.append('t0_snapshots','E2E_T0',dict(trade_date=t0,source_asof=t0,available_at=t0,evidence_class='ENGINEERING_SYNTHETIC',universe=universe,logical_event_refs=manifest['logical_events']))
    first_enrollments=manifest['enrollments'];freezes=[d.freeze_t0(e,snapshot) for e in first_enrollments]
    competing=[]
    for f in freezes:
        sid=s.read(f)['signal_id'];ev=[]
        if sid in ('CNF','INV'):ev=[dict(trade_date=nextdate,event='CONFIRMED' if sid=='CNF' else 'INVALIDATED',publication=publications[-1])]
        competing.append(d.competing_outcome(f,ev,nextdate))
    crossed=d.crossed_control(freezes[0],'A',nextdate,publications[-1])
    # Real publication is current V4-14 sealed evidence, never a fabricated owner row.
    realbinding=next(b for b in a.allowed_publications if '/real/' in b['path'])
    realpub=c.project(realbinding);realm=s.read(realpub);real_freezes=[]
    adjusted=json.loads(a.read(a.data['component_artifacts']['ADJUSTED_DAILY']))
    prices={r['security_id']:r for r in adjusted['rows'] if r.get('adjustment_readiness')=='READY'}
    eligible={s.read(r)['entity_id'] for r in realm['daily_ledger'] if s.read(r)['eligibility_state']=='TRUE'}
    real_universe=[dict(security_id=sid,close=float(p['close']),adjustment_identity=p['adjustment_source_revision'],hard_safety=False,research_eligible=None,prewatch_final_eligible=sid in eligible,delta3=None,prior20_mean_amount=None,vol20=None,RPS20=None,primary_industry=None) for sid,p in prices.items()]
    # Missing accepted matching features remain UNKNOWN, never invented to obtain controls.
    real_snapshot=s.append('t0_snapshots','REAL_ACCEPTED_T0',dict(trade_date='2026-09-30',source_asof='2026-09-30',available_at=a.data['promoted_at_utc'],evidence_class='RECONSTRUCTED_ASOF',research_universe_quality='UNKNOWN_ACCEPTED_RESEARCH_ELIGIBILITY_NOT_PROJECTED',hard_safety_quality='UNKNOWN_ACCEPTED_HARD_SAFETY_NOT_PROJECTED',universe=real_universe,source=a.data['component_artifacts']['ADJUSTED_DAILY'],logical_event_refs=realm['logical_events']))
    realenrollment=next((e for e in realm['enrollments'] if s.read(e)['entity_id'] in prices and s.read(e)['comparison_reference'] is not None),None)
    if realenrollment is None:raise ValueError('REAL_ACCEPTED_REFERENCE_ENROLLMENT_REQUIRED')
    real_freezes.append(d.freeze_t0(realenrollment,real_snapshot))
    frozen_refs=first_enrollments+freezes+[snapshot,realenrollment,real_snapshot]+real_freezes
    receipt=dict(process='PRODUCER',pid=os.getpid(),start=start,end=now(),authority=a.bindings(),portability_receipts=a.portability_receipts,publications=publications,first_enrollments=first_enrollments,freezes=freezes,real_publication=realpub,real_freezes=real_freezes,real_enrollment=realenrollment,competing=competing,crossed=crossed,frozen_refs=frozen_refs,T0_FROZEN_BEFORE_FUTURE_SOURCE_READ=True,future_source_reads=[],input_channels=['CURRENT_V4_14_ACCEPTED_AUTHORITY','SEALED_OWNER_PUBLICATION','EXPLICIT_ENGINEERING_VECTOR'],forbidden_feedback=[])
    atomic(OUT+'/PRODUCER_RECEIPT.json',receipt);print(json.dumps({'pid':os.getpid(),'receipt':OUT+'/PRODUCER_RECEIPT.json'}))

def settlement():
    from workbench_analysis.v4_15_settlement import VectorPriceSource,AcceptedPriceSource
    start=now();a,s,c,d=components();p=read(OUT+'/PRODUCER_RECEIPT.json')
    # Exact disk readback precedes constructing or opening any future source.
    for b in p['frozen_refs']:s.read(b)
    readback_at=now();t0='2026-08-31';dates=a.sessions[a.sessions.index(t0)+1:];dates=[date for date in dates if date<='2026-09-30']
    prices={}
    for sid in ['S','CNF','INV','A','C']:
        prices[sid]={date:dict(close=10+[1,2,-1,3,4][i%5],high=11+[1,2,-1,3,4][i%5],low=9+[1,2,-1,3,4][i%5],verified_identity=True,verified_adjustment=True,T0_basis_verified=True,T0_transform_coefficients={'alpha':1,'beta':0},transform_coefficients={'alpha':1,'beta':0},adjustment_identity='VECTOR_AFFINE_IDENTITY',source_asof=date,available_at=date,status='ACTUAL_TRADED') for i,date in enumerate(dates)}
    future_inputs=[];outcomes=[];trace=[];corrected_refs=[]
    empty=s.append('price_sources','PENDING_SOURCE',dict(evidence_class='ENGINEERING_VECTOR',rows={}))
    pending=VectorPriceSource({},empty)
    for f in p['freezes']:outcomes.extend(d.settle(f,pending,t0))
    first_future_open_at=now()
    v1=s.append('price_sources','SOURCE_R1',dict(evidence_class='ENGINEERING_VECTOR',rows=prices));future_inputs.append(v1)
    source=VectorPriceSource(s.read(v1)['rows'],v1)
    for f in p['freezes']:outcomes.extend(d.settle(f,source,'2026-09-30'))
    count_before=len(s.refs('outcomes'))
    for f in p['freezes']:d.settle(f,source,'2026-09-30')
    count_after=len(s.refs('outcomes'));trace.extend(source.read_log)
    correction=json.loads(json.dumps(prices));correction['S'][dates[0]]['close']=11.5;correction['S'][dates[0]]['high']=12.5
    v2=s.append('price_sources','SOURCE_R2',dict(evidence_class='ENGINEERING_VECTOR',rows=correction));future_inputs.append(v2)
    corrected=VectorPriceSource(s.read(v2)['rows'],v2)
    main=next(f for f in p['freezes'] if s.read(f)['signal_id']=='S')
    corrected_refs=d.settle(main,corrected,'2026-09-30');outcomes+=corrected_refs;trace.extend(corrected.read_log)
    realbinding=a.data['component_artifacts']['ADJUSTED_DAILY'];real=AcceptedPriceSource(a,realbinding)
    realout=[]
    for f in p['real_freezes']:realout.extend(d.settle(f,real,'2026-09-30'))
    outcomes+=realout;trace.extend(real.read_log)
    views=[s.append('readbacks',dh([f,'FINAL_READBACK']),d.readback(f,'2026-09-30')) for f in p['freezes']+p['real_freezes']]
    receipt=dict(process='SETTLEMENT',pid=os.getpid(),start=start,freeze_exact_readback_at=readback_at,first_future_source_open_at=first_future_open_at,end=now(),producer_receipt=ref(OUT+'/PRODUCER_RECEIPT.json'),future_sources=future_inputs,real_source=realbinding,outcomes=outcomes,corrected_outcomes=corrected_refs,real_outcomes=realout,readbacks=views,source_read_log=trace,same_source_counts={'before':count_before,'after':count_after},authority=a.bindings(),portability_receipts=a.portability_receipts,frozen_refs_after=[ref(b['path']) for b in p['frozen_refs']],HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',REAL_ACCEPTED_SOURCE_V4_15='PASS_CAPABILITY_SCOPED',real_scope='CURRENT_AUTHORITY_RADAR_ENROLLMENT_T0_FREEZE_ACCEPTED_PRICE_READBACK_PENDING_DUE_TO_DATA_HEAD',forbidden_feedback=[],raw_provider_fallback=False)
    atomic(OUT+'/SETTLEMENT_RECEIPT.json',receipt);print(json.dumps({'pid':os.getpid(),'receipt':OUT+'/SETTLEMENT_RECEIPT.json'}))

def run():
    gates=[('reports/r20a/CURRENT_AUTHORITY_GATE.json','R20A_CURRENT_STAGE_AUTHORITY'),('reports/r20b/stage_gate.json','R20B_BYTE_IDENTITY_PORTABILITY'),('reports/r20c/INDEPENDENT_RADAR_COHORT_GATE.json','R20C_V4_15_RADAR_COHORT_RUNTIME'),('reports/r20d/SETTLEMENT_GATE.json','R20D_V4_15_SETTLEMENT_RUNTIME')]
    for path,key in gates:
        value=read(path)
        if value.get(key)!='PASS_LOCAL':raise ValueError('R20E_ENTRY_GATE_'+key)
    for phase in ['producer','settlement']:
        result=subprocess.run([sys.executable,'-m','scripts.r20e_persisted',phase],cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace')
        atomic(OUT+'/'+phase+'_process.log',(result.stdout+result.stderr).encode(),raw=True)
        if result.returncode:raise ValueError(phase+':'+result.stderr[-4000:])
    from scripts.validate_r20e_oracle import validate
    result=validate();atomic(OUT+'/INDEPENDENT_E2E_GATE.json',result);print(json.dumps(result))
if __name__=='__main__':{'producer':producer,'settlement':settlement,'run':run}[sys.argv[1] if len(sys.argv)>1 else 'run']()

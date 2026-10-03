"""Independent exact-artifact debt oracle; derives prices/coverage without writers."""
import json,subprocess,hashlib
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from scripts.r20r1r1_io import ROOT,ref,exact
def demand(ok,reason):
    if not ok:raise ValueError(reason)
REQUIRED=[1,3,5,10,20]
DENIED='NOT_GRANTED_PENDING_MATURITY_EVIDENCE'
def packet_oracle(packet,root):
    root=Path(root);registry=json.loads((root/'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json').read_bytes())
    h=exact(registry['accepted_head'],root);seal=exact(h['bindings']['runtime_seal'],root)
    demand(packet['accepted_head']==registry['accepted_head']==ref('data/v4/V4_14_ACCEPTED_HEAD.json',root),'ORACLE_CURRENT_OWNER_HEAD')
    demand(packet['owner_publication']==registry['owner_publication'] and packet['owner_publication'] in seal['replay_publications'],'ORACLE_SEALED_OWNER')
    owner=exact(packet['owner_publication'],root);en=exact(packet['enrollment'],root);freeze=exact(packet['freeze'],root)
    demand(owner['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' and packet['enrollment']==registry['enrollment'] and packet['freeze']==registry['freeze'],'ORACLE_REAL_T0_EXACT_ANCHORS')
    demand(en['cohort_namespace']=='RECONSTRUCTED_ASOF' and en['source_publication']==packet['owner_publication'] and freeze['enrollment']==packet['enrollment'] and en['T0']==freeze['T0']==owner['trade_date'],'ORACLE_RECONSTRUCTED_LINEAGE')
    prod=exact(registry['producer_receipt'],root);log=exact(packet['endpoint_read_receipt'],root)
    demand(packet['freeze_completed_at']==prod['end'] and packet['freeze'] in prod['real_freezes'] and prod['real_enrollment']==packet['enrollment'],'ORACLE_PERSISTED_FREEZE_TIME')
    demand(log['freeze']==packet['freeze'] and log['accepted_endpoints']==packet['accepted_endpoints'] and log['first_future_endpoint_open_at']==packet['first_future_endpoint_open_at'],'ORACLE_REAL_FUTURE_READ_BINDING')
    demand(datetime.fromisoformat(prod['end'])<datetime.fromisoformat(log['first_future_endpoint_open_at']) and log['raw_provider_fallback'] is False,'ORACLE_T0_BEFORE_FUTURE')
    demand(packet['raw_provider_fallback'] is False and packet['historical_prices_only'] is False and packet['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' and packet['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED','ORACLE_NO_PROVIDER_PRICE_ONLY_PIT_REALTIME_UPGRADE')
    current=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json',root);anchors=[];seen=set()
    while True:
        demand(current['sha256'] not in seen,'ORACLE_ANCESTRY_CYCLE');seen.add(current['sha256']);node=exact(current,root);anchors.append(current)
        demand(node['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2','ORACLE_DATA_HEAD_CONTRACT')
        if current['sha256']==registry['T0_data_archive']['sha256']:break
        parent=node['parent_archive'];demand(exact(parent,root)['accepted_trade_date']<=node['accepted_trade_date'],'ORACLE_MONOTONE_CUTOFF');current=parent
    demand(any((b['sha256'],b['bytes'])==(packet['data_head']['sha256'],packet['data_head']['bytes']) for b in anchors),'ORACLE_ACCEPTED_DATA_ANCESTRY')
    demand(all(h['bindings']['data_head'][k]==registry['T0_data_archive'][k] for k in ['sha256','bytes']),'ORACLE_EXACT_T0_DATA_ARCHIVE')
    data=exact(packet['data_head'],root);calendar=exact(data['calendar'],root);ss=[s['trade_date'] if isinstance(s,dict) else s for s in calendar['session_dates']]
    old=exact(h['bindings']['calendar'],root);past=[s['trade_date'] if isinstance(s,dict) else s for s in old['session_dates']]
    demand(ss[:len(past)]==past and ss==sorted(set(ss)),'ORACLE_FROZEN_CALENDAR_PREFIX')
    n=packet['horizon'];demand(type(n) is int and n in REQUIRED,'ORACLE_FROZEN_HORIZON');i=ss.index(en['T0']);days=ss[i+1:i+n+1]
    demand(len(days)==n and days[-1]<=data['accepted_trade_date'],'ORACLE_ACCEPTED_DUE')
    todo=[data['component_artifacts']];allowed=[]
    while todo:
        v=todo.pop()
        if isinstance(v,dict):
            if {'path','sha256','bytes'}<=v.keys():allowed.append(v)
            else:todo.extend(v.values())
        elif isinstance(v,list):todo.extend(v)
    demand(len(packet['accepted_endpoints'])==n,'ORACLE_COMPLETE_PATH');prices=[]
    for day,b in zip(days,packet['accepted_endpoints']):
        demand(b in allowed,'ORACLE_EXACT_ACCEPTED_ENDPOINT');source=exact(b,root);demand(source['contract_id']=='DM01_ADJUSTED_DAILY_ARTIFACT_R3_3','ORACLE_ACCEPTED_SOURCE_CONTRACT')
        row=[r for r in source['rows'] if r['trade_date']==day and r['security_id']==freeze['signal_id']];demand(len(row)==1,'ORACLE_DATED_IDENTITY');r=row[0]
        demand(r['source_authority']=='TDX_OFFICIAL_PACKAGE' and r['evaluation_basis_date']==days[-1] and r['verified_identity'] is True and r['verified_adjustment'] is True and r['T0_basis_verified'] is True and r.get('status','ACTUAL')=='ACTUAL','ORACLE_COMMON_OBSERVED_BASIS');prices.append(r)
    outcome=exact(packet['outcome'],root);demand(outcome['price_path']==prices and outcome['frozen_t0']==packet['freeze'] and outcome['enrollment_id']==en['enrollment_id'] and outcome['outcome_status']=='OBSERVED' and outcome['due_date']==days[-1] and outcome['horizon']==n,'ORACLE_BOUND_OUTCOME')
    demand(outcome['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' and all(x['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' for x in [en,freeze,outcome]),'ORACLE_PIT_STAYS_DENIED')
    d=lambda v:Decimal(str(v));t=prices[-1]['T0_transform_coefficients'];base=d(t['alpha'])*d(freeze['comparison_reference'])+d(t['beta'])
    demand(all(not isinstance(c[k],bool) and d(c[k]).is_finite() for r in prices for c in [r['transform_coefficients'],r['T0_transform_coefficients']] for k in ['alpha','beta']) and all(d(c['alpha'])>0 for r in prices for c in [r['transform_coefficients'],r['T0_transform_coefficients']]),'ORACLE_VALID_AFFINE_COEFFICIENTS')
    demand(all(not isinstance(r[k],bool) and d(r[k]).is_finite() and d(r[k])>0 for r in prices for k in ['close','high','low']),'ORACLE_VALID_PRICE_VALUES')
    demand(base>0 and all(r['T0_transform_coefficients']==t for r in prices),'ORACLE_ONE_T0_TRANSFORM')
    val=lambda r,k:d(r['transform_coefficients']['alpha'])*d(r[k])+d(r['transform_coefficients']['beta'])
    peak=base;dd=Decimal(0)
    for r in prices:c=val(r,'close');peak=max(peak,c);dd=min(dd,c/peak-1)
    expected={'R_N':val(prices[-1],'close')/base-1,'MFE_N':max([base]+[val(r,'high') for r in prices])/base-1,'MAE_N':min([base]+[val(r,'low') for r in prices])/base-1,'PATH_MDD_CLOSE_N':dd}
    demand(all(d(outcome[k]).is_finite() and abs(d(outcome[k])-v)<Decimal('1e-10') for k,v in expected.items()),'ORACLE_NUMERICAL_EXPECTATION')
    return n
def state_oracle(root,state=None):
    root=Path(root);view=state if state is not None else json.loads((root/'reports/r20r1r1/MATURITY_DEBT_READBACK.json').read_bytes())
    coverage=set()
    for key,v in view['proofs_by_enrollment_horizon'].items():
        demand(v['FIRST_OBSERVED']==v['receipt_history'][0] and v['LATEST_VALIDATED']==v['receipt_history'][-1],'ORACLE_APPEND_ONLY_FIRST_LATEST')
        previous=None
        for b in v['receipt_history']:
            proof=exact(b,root);n=packet_oracle(proof['packet'],root);coverage.add(n)
            identity=[proof['enrollment_id'],proof['horizon'],proof['due_date']]
            demand(key==hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest() and all(v[k]==proof[k] for k in ['enrollment_id','horizon','due_date']),'ORACLE_EXACT_COVERAGE_IDENTITY')
            if previous:
                new=exact(proof['packet']['outcome'],root);old=exact(previous['packet']['outcome'],root)
                demand(new['supersedes']==previous['packet']['outcome'] and new['revision_sequence']==old['revision_sequence']+1 and proof['packet']['accepted_endpoints']!=previous['packet']['accepted_endpoints'],'ORACLE_CORRECTION_REVISION_NOT_OVERWRITE')
            previous=proof
    proved=sorted(coverage);unproved=[n for n in REQUIRED if n not in coverage]
    expected='OPEN' if not proved else 'PARTIAL_MATURITY_EVIDENCE' if unproved else 'FULL_REQUIRED_HORIZONS_PROVEN'
    demand(view['required_horizons']==REQUIRED and view['proved_horizons']==proved and view['unproved_horizons']==unproved and view['aggregate_state']==view['status']==expected,'ORACLE_HORIZON_COVERAGE_AGGREGATE')
    demand(view['capability_by_horizon']=={str(n):'PASS_CAPABILITY_SCOPED' if n in coverage else DENIED for n in REQUIRED},'ORACLE_CAPABILITY_BY_HORIZON')
    blocked=bool(unproved) or root.resolve()!=ROOT.resolve()
    demand(view['blocks_unqualified_matured_real_claims'] is blocked and view['blocks_matured_real_claims'] is blocked,'ORACLE_NO_PARTIAL_OR_FIXTURE_GLOBAL_UNBLOCK')
    demand(view['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']==(DENIED if blocked else 'PASS_CAPABILITY_SCOPED'),'ORACLE_UNQUALIFIED_RUNTIME_CAPABILITY')
    demand(view['HISTORICAL_PIT_EFFECTIVENESS']==view['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED' and view['T0_OBSERVATION_SCOPE']=='RECONSTRUCTED_ASOF' and view['stage_promotion_authorized'] is False and view['blocks_unrelated_development'] is False,'ORACLE_NO_PIT_REALTIME_STAGE_UPGRADE')
    return dict(status='PASS',aggregate_state=expected,proved_horizons=proved,unproved_horizons=unproved)
def validate():
    from scripts.validate_r20r1_oracle import validate as previous_scope
    previous_scope();current=state_oracle(ROOT)
    demand(current['proved_horizons']==[],'CURRENT_REAL_MATURITY_MUST_REMAIN_NONE')
    report=json.loads((ROOT/'reports/r20r1r1/ENGINEERING_REACHABILITY.json').read_bytes());transitions=[]
    for step in report['transitions']:
        directory=(ROOT/step['fixture_directory']).resolve();demand(directory.is_relative_to(ROOT/'reports/r20r1r1/engineering_fixtures'),'ISOLATED_FIXTURE_REQUIRED')
        state=exact(step['readback'],ROOT);result=state_oracle(directory,state);demand(result['proved_horizons']==step['proved_horizons'],'INDEPENDENT_POSITIVE_TRANSITION');transitions.append(result)
    demand([x['aggregate_state'] for x in transitions]==['OPEN','PARTIAL_MATURITY_EVIDENCE','PARTIAL_MATURITY_EVIDENCE','FULL_REQUIRED_HORIZONS_PROVEN'],'ALL_COVERAGE_STATES_PROVEN')
    stage=json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes());data=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    demand(stage['accepted_stage_range']=='V4_00_TO_V4_14_ACCEPTED' and data['accepted_trade_date']=='2026-09-30' and not (ROOT/'data/v4/V4_15_ACCEPTED_HEAD.json').exists(),'PROTECTED_STAGE_DATA_HEAD')
    for b in json.loads((ROOT/'reports/r20r1r1/FROZEN_BASELINE_BINDINGS.json').read_bytes())['bindings']:exact(b,ROOT)
    demand(subprocess.check_output(['git','diff','555409d79c58517761472531404f0ee5cccd81af','--name-only','--','src','data','reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/v4_15_runtime_r20','reports/r20r1'],cwd=ROOT)==b'','IMMUTABLE_R20_R20R1_SUCCESS_EVIDENCE')
    return dict(R20R1R1_INDEPENDENT_ORACLE='PASS_LOCAL',R20R1R1_FORWARD_MATURITY_REACHABILITY='PASS_LOCAL',CURRENT_REAL_MATURITY_EVIDENCE='NONE',REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME=DENIED,PROVED_HORIZONS=[],UNPROVED_HORIZONS=REQUIRED,FUTURE_POSITIVE_PATH_ENGINEERING_REACHABILITY='PASS',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED',transitions=transitions,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
if __name__=='__main__':print(json.dumps(validate(),indent=2))

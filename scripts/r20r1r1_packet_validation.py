"""Exact forward settlement-runtime maturity; no runtime evaluator imports."""
import json,math
from datetime import datetime
from pathlib import Path
from scripts.r20r1r1_io import ROOT,ref,exact
HORIZONS=(1,3,5,10,20)
def require(ok,message):
    if not ok:raise ValueError(message)
def stamp(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'));require(result.tzinfo is not None,'EXPLICIT_TIMEZONE_REQUIRED');return result
def sessions(calendar):return [x['trade_date'] if isinstance(x,dict) else x for x in calendar['session_dates']]
def data_chain(root,registry):
    current=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json',root);chain=[];seen=set();b=current
    while True:
        require(b['sha256'] not in seen,'ACCEPTED_DATA_ANCESTRY_CYCLE');seen.add(b['sha256']);d=exact(b,root)
        require(d['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2','ACCEPTED_DATA_CONTRACT_REQUIRED');chain.append((b,d))
        if b['sha256']==registry['T0_data_archive']['sha256']:
            require(b['bytes']==registry['T0_data_archive']['bytes'],'EXACT_T0_DATA_ANCHOR');break
        parent=d.get('parent_archive');require(isinstance(parent,dict),'ACCEPTED_DATA_ANCESTRY_MUST_REACH_T0')
        old=exact(parent,root);require(old['accepted_trade_date']<=d['accepted_trade_date'],'MONOTONE_ACCEPTED_DATA_INCREMENT');b=parent
    return chain
def validate_packet(packet,root=ROOT):
    root=Path(root);registry=json.loads((root/'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json').read_bytes())
    head_ref=ref('data/v4/V4_14_ACCEPTED_HEAD.json',root)
    require(head_ref==registry['accepted_head']==packet['accepted_head'],'EXACT_FROZEN_HEAD')
    head=exact(head_ref,root);seal=exact(head['bindings']['runtime_seal'],root)
    require(packet['owner_publication'] in seal['replay_publications'] and packet['owner_publication']==registry['owner_publication'],'EXACT_REGISTERED_SEALED_REAL_OWNER')
    owner=exact(packet['owner_publication'],root)
    require(owner['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','SYNTHETIC_OWNER_NOT_REAL')
    require(packet['enrollment']==registry['enrollment'] and packet['freeze']==registry['freeze'],'EXACT_REGISTERED_T0_ENROLLMENT_FREEZE')
    enrollment=exact(packet['enrollment'],root);freeze=exact(packet['freeze'],root)
    require(enrollment['source_publication']==packet['owner_publication'] and freeze['enrollment']==packet['enrollment'],'OWNER_ENROLLMENT_FREEZE_LINEAGE')
    require(freeze['T0']==enrollment['T0']==owner['trade_date']==registry['T0'],'IMMUTABLE_T0')
    require(enrollment['cohort_namespace']=='RECONSTRUCTED_ASOF' and enrollment['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','REGISTERED_RECONSTRUCTED_REAL_T0_ONLY')
    require(all(x.get('HISTORICAL_PIT_EFFECTIVENESS')=='NOT_GRANTED' for x in [enrollment,freeze]),'NO_PIT_UPGRADE')
    require(packet.get('HISTORICAL_PIT_EFFECTIVENESS')=='NOT_GRANTED' and packet.get('REALTIME_ACCEPTED_COHORT_MATURITY')=='NOT_GRANTED','NO_PIT_OR_REALTIME_UPGRADE')
    producer=exact(registry['producer_receipt'],root)
    require(packet['freeze_completed_at']==producer['end'] and packet['freeze'] in producer['real_freezes'] and producer['real_enrollment']==packet['enrollment'],'FREEZE_TIMESTAMP_BOUND_TO_PERSISTED_PRODUCER')
    log=exact(packet['endpoint_read_receipt'],root)
    require(log['freeze']==packet['freeze'] and log['accepted_endpoints']==packet['accepted_endpoints'] and log['raw_provider_fallback'] is False,'EXACT_FUTURE_READ_RECEIPT')
    require(packet['first_future_endpoint_open_at']==log['first_future_endpoint_open_at'] and stamp(producer['end'])<stamp(log['first_future_endpoint_open_at']),'ENDPOINT_AFTER_FREEZE')
    require(packet.get('raw_provider_fallback') is False and packet.get('historical_prices_only') is False,'NO_PROVIDER_OR_PRICE_ONLY_PACKET')
    chain=data_chain(root,registry);data=exact(packet['data_head'],root)
    require(any(b['sha256']==packet['data_head']['sha256'] and b['bytes']==packet['data_head']['bytes'] for b,_ in chain),'ACCEPTED_DATA_SNAPSHOT_MUST_BE_IN_CURRENT_ANCESTRY')
    # Explicit exact-byte T0 archive preserves the frozen head's historical binding.
    require({k:head['bindings']['data_head'][k] for k in ['sha256','bytes']}=={k:registry['T0_data_archive'][k] for k in ['sha256','bytes']},'ARCHIVE_IS_EXACT_T0_DATA_HEAD')
    calendar=exact(data['calendar'],root);dates=sessions(calendar);old_dates=sessions(exact(head['bindings']['calendar'],root))
    require(dates[:len(old_dates)]==old_dates and dates==sorted(set(dates)),'FROZEN_CALENDAR_PREFIX')
    n=packet['horizon'];require(type(n) is int and n in HORIZONS,'FROZEN_HORIZON')
    index=dates.index(freeze['T0']);require(index+n<len(dates),'NO_ACCEPTED_DUE_SESSION');future=dates[index+1:index+n+1];due=future[-1]
    require(due<=data['accepted_trade_date'] and data['accepted_trade_date']<=chain[0][1]['accepted_trade_date'],'DUE_INSIDE_ACCEPTED_CUTOFF')
    admitted=[]
    def walk(v):
        if isinstance(v,dict):
            if {'path','sha256','bytes'}<=v.keys():admitted.append(v)
            else:
                for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    walk(data['component_artifacts'])
    require(len(packet['accepted_endpoints'])==n,'COMPLETE_FORWARD_PATH')
    rows=[]
    for day,b in zip(future,packet['accepted_endpoints']):
        require(b in admitted,'ENDPOINT_NOT_BOUND_BY_ACCEPTED_DATA_AUTHORITY');source=exact(b,root)
        require(source['contract_id']=='DM01_ADJUSTED_DAILY_ARTIFACT_R3_3','ACCEPTED_ADJUSTED_PRICE_CONTRACT')
        matches=[r for r in source['rows'] if r['trade_date']==day and r['security_id']==freeze['signal_id']]
        require(len(matches)==1,'EXACT_ACCEPTED_SIGNAL_DATE_ROW');row=matches[0]
        require(row['source_authority']=='TDX_OFFICIAL_PACKAGE' and row['evaluation_basis_date']==due and row['verified_identity'] is True and row['verified_adjustment'] is True,'EXACT_ONE_EVALUATION_BASIS')
        require(row.get('status','ACTUAL')=='ACTUAL' and row['T0_basis_verified'] is True,'OBSERVED_PATH_NOT_MISSING_OR_SUSPENDED')
        for coeff in [row['transform_coefficients'],row['T0_transform_coefficients']]:
            require(all(isinstance(coeff[k],(int,float)) and not isinstance(coeff[k],bool) and math.isfinite(coeff[k]) for k in ['alpha','beta']) and coeff['alpha']>0,'VALID_ACCEPTED_AFFINE_BASIS')
        require(all(math.isfinite(float(row[k])) and float(row[k])>0 for k in ['close','high','low']),'NO_MISSING_ZERO_OR_NONFINITE_PRICE');rows.append(row)
    outcome=exact(packet['outcome'],root)
    require(outcome['frozen_t0']==packet['freeze'] and outcome['enrollment_id']==enrollment['enrollment_id'] and outcome['horizon']==n and outcome['due_date']==due and outcome['outcome_status']=='OBSERVED','BOUND_OBSERVED_OUTCOME')
    require(outcome['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' and outcome['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','NO_OUTCOME_SCOPE_UPGRADE')
    require(outcome['price_path']==rows,'EXACT_SOURCE_PATH_NO_T0_OR_CORRECTED_OVERWRITE')
    t0=rows[-1]['T0_transform_coefficients'];p0=t0['alpha']*float(freeze['comparison_reference'])+t0['beta'];require(p0>0,'POSITIVE_EVALUATION_REFERENCE')
    require(all(r['T0_transform_coefficients']==t0 for r in rows),'ONE_T0_EVALUATION_TRANSFORM')
    values=lambda r,k:r['transform_coefficients']['alpha']*float(r[k])+r['transform_coefficients']['beta']
    peak=p0;mdd=0
    for r in rows:close=values(r,'close');peak=max(peak,close);mdd=min(mdd,close/peak-1)
    expected={'R_N':values(rows[-1],'close')/p0-1,'MFE_N':max([p0]+[values(r,'high') for r in rows])/p0-1,'MAE_N':min([p0]+[values(r,'low') for r in rows])/p0-1,'PATH_MDD_CLOSE_N':mdd}
    require(all(isinstance(outcome[k],(int,float)) and not isinstance(outcome[k],bool) and math.isfinite(outcome[k]) and abs(outcome[k]-v)<1e-10 for k,v in expected.items()),'INDEPENDENT_RECOMPUTATION_FAILED')
    return dict(enrollment_id=enrollment['enrollment_id'],horizon=n,due_date=due,accepted_future_endpoint_read_count=n,T0_OBSERVATION_SCOPE='RECONSTRUCTED_ASOF',REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',packet=packet,validation_environment='CURRENT_ACCEPTED_AUTHORITY' if root.resolve()==ROOT.resolve() else 'ISOLATED_ENGINEERING_REACHABILITY_ONLY')

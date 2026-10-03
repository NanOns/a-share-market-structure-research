"""Incremental evidence debt, independent of stage promotion and runtime evaluators.

Accepted-session ingestion may call refresh with exact proof packets. Append-only
receipts close only the explicitly evidenced maturity debt, never grant PIT or a stage.
"""
import hashlib,json,math
from datetime import datetime
from scripts.validate_r20r1_feasibility import ROOT,exact,descriptor,require,HORIZONS
from scripts.r20r1_io import atomic
def validate_packet(packet,root=ROOT):
    head_ref=descriptor('data/v4/V4_14_ACCEPTED_HEAD.json',root);data_ref=descriptor('data/v4/V4_DATA_ACCEPTED_HEAD.json',root)
    require(packet['accepted_head']==head_ref and packet['data_head']==data_ref,'EXACT_CURRENT_AUTHORITY_REQUIRED')
    head=exact(head_ref,root);data=exact(data_ref,root);seal=exact(head['bindings']['runtime_seal'],root)
    require(packet['owner_publication'] in seal['replay_publications'],'EXACT_SEALED_OWNER_LINEAGE_REQUIRED')
    owner=exact(packet['owner_publication'],root);enrollment=exact(packet['enrollment'],root);freeze=exact(packet['freeze'],root)
    require(owner.get('evidence_class')=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','ENGINEERING_OWNER_NOT_REAL')
    require(enrollment['cohort_namespace']=='REALTIME_ACCEPTED' and enrollment['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','RECONSTRUCTED_NOT_REAL_MATURITY')
    require(enrollment['source_publication']==packet['owner_publication'] and freeze['enrollment']==packet['enrollment'] and freeze['T0']==enrollment['T0']==owner.get('trade_date'),'BOUND_T0_LINEAGE')
    calendar=exact(head['bindings']['calendar'],root);sessions=[x['trade_date'] if isinstance(x,dict) else x for x in calendar['session_dates']]
    horizon=packet['horizon'];require(horizon in HORIZONS,'FROZEN_HORIZON_NAMESPACE')
    index=sessions.index(enrollment['T0']);require(index+horizon<len(sessions),'NO_ACCEPTED_DUE_SESSION')
    dates=sessions[index+1:index+horizon+1];due=dates[-1];require(due<=data['accepted_trade_date'],'DUE_BEYOND_ACCEPTED_CUTOFF')
    require(packet['raw_provider_fallback'] is False and packet['historical_prices_only'] is False,'NO_FALLBACK_OR_PRICE_ONLY_PROOF')
    require(datetime.fromisoformat(packet['freeze_completed_at'])<datetime.fromisoformat(packet['first_future_endpoint_open_at']),'T0_BEFORE_FUTURE_ENDPOINT')
    # Only direct/indirect exact Data Head authority targets can admit future rows.
    authorized={};pending=[data]
    while pending:
        value=pending.pop()
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and 'sha256' in value and ('bytes' in value or 'byte_count' in value):
                key=(value['path'],value['sha256'])
                if key not in authorized:
                    authorized[key]=value
                    if value['path'].endswith('.json'):pending.append(exact(value,root))
            else:pending.extend(value.values())
        elif isinstance(value,list):pending.extend(value)
    require(len(packet['accepted_endpoints'])==len(dates),'COMPLETE_ACCEPTED_FUTURE_PATH')
    rows=[]
    for date,b in zip(dates,packet['accepted_endpoints']):
        require((b['path'],b['sha256']) in authorized and authorized[(b['path'],b['sha256'])]==b,'UNACCEPTED_FUTURE_ENDPOINT')
        source=exact(b,root);found=[x for x in source.get('rows',[]) if x.get('security_id')==freeze['signal_id'] and x.get('trade_date')==date]
        require(len(found)==1 and found[0].get('source_authority')=='TDX_OFFICIAL_PACKAGE','EXACT_ACCEPTED_PRICE_ROW')
        row=found[0];require(row.get('evaluation_basis_date')==due,'ONE_ACCEPTED_EVALUATION_BASIS_REQUIRED');rows.append(row)
    outcome=exact(packet['outcome'],root)
    require(outcome['frozen_t0']==packet['freeze'] and outcome['outcome_status']=='OBSERVED' and outcome['horizon']==horizon and outcome['due_date']==due,'REAL_OBSERVED_BOUND_OUTCOME')
    require(outcome['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' and outcome['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','NO_EVIDENCE_CLASS_OR_PIT_UPGRADE')
    require([x['trade_date'] for x in outcome['price_path']]==dates,'EXACT_FUTURE_DATES_EXCLUDE_T0')
    reference=float(freeze['comparison_reference']);closes=[float(x['close']) for x in rows];peak=reference;mdd=0
    for close in closes:peak=max(peak,close);mdd=min(mdd,close/peak-1)
    expected={'R_N':closes[-1]/reference-1,'MFE_N':max(float(x['high']) for x in rows)/reference-1,'MAE_N':min(float(x['low']) for x in rows)/reference-1,'PATH_MDD_CLOSE_N':mdd}
    require(all(math.isfinite(float(outcome[k])) and abs(float(outcome[k])-v)<1e-10 for k,v in expected.items()),'INDEPENDENT_NUMERICAL_PROOF')
    return dict(enrollment_id=enrollment['enrollment_id'],horizon=horizon,due_date=due,accepted_future_endpoint_read_count=len(rows),packet=packet,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED')
def refresh(packets=(),root=ROOT):
    from pathlib import Path
    readback_path=Path(root)/'reports/r20r1/MATURITY_DEBT_READBACK.json'
    inherited=[]
    if readback_path.exists():
        previous=json.loads(readback_path.read_bytes())
        inherited=exact(previous['LATEST_VALIDATED'],root)['verified_maturity_receipts']
    # A prior assertion is never trusted alone: revalidate each inherited packet
    # against the accepted authority on every accepted-session increment.
    proofs=[validate_packet(p,root) for p in [x['packet'] for x in inherited]+list(packets)]
    proofs=list({(p['enrollment_id'],p['horizon'],p['due_date']):p for p in proofs}.values())
    proofs.sort(key=lambda p:(p['enrollment_id'],p['horizon'],p['due_date']))
    payload=dict(contract_id='R20R1_MATURITY_DEBT_INCREMENT_V1',initial_debt=descriptor('reports/r20r1/OPEN_VALIDATION_DEBT.json',root),accepted_head=descriptor('data/v4/V4_14_ACCEPTED_HEAD.json',root),data_head=descriptor('data/v4/V4_DATA_ACCEPTED_HEAD.json',root),verified_maturity_receipts=proofs,matured_real_horizons=sorted({p['horizon'] for p in proofs}),status='CLOSED_LOCAL_MATURITY_EVIDENCE' if proofs else 'OPEN',blocks_unrelated_development=False,blocks_matured_real_claims=not bool(proofs),HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',stage_promotion_authorized=False,unproved_horizons_remain_restricted=True)
    key=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest();path='reports/r20r1/maturity_debt_revisions/'+key+'.json'
    if (Path(root)/path).exists():require(exact(descriptor(path,root),root)==payload,'APPEND_ONLY_DEBT_REVISION')
    atomic(path,payload,root=root)
    binding=descriptor(path,root)
    readback=dict(FIRST_OBSERVED=previous['FIRST_OBSERVED'] if readback_path.exists() else binding,LATEST_VALIDATED=binding,status=payload['status'],matured_real_horizons=payload['matured_real_horizons'],HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',stage_promotion_authorized=False)
    atomic('reports/r20r1/MATURITY_DEBT_READBACK.json',readback,root=root)
    return binding
if __name__=='__main__':
    import sys
    packets=json.loads(open(sys.argv[1],encoding='utf8').read()) if len(sys.argv)>1 else []
    print(json.dumps(refresh(packets)))

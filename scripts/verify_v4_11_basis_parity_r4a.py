"""Independent accepted-artifact comparison, using R4 source adapter at 9/24."""
from scripts.next_round_execution_r4 import *
from scripts.build_v4_11_target_facts_r4a import compressed
from src.v4.adjustment_basis_r4 import parent_bar,observations,admission,basis_id
from src.v4.factors.core import compute_core
from dataclasses import asdict
from collections import Counter,defaultdict
from itertools import groupby
import duckdb,gzip,json,math

OUT='reports/v4_11_r4a/'

def replay():
    entry=verify_protected();receipt=read('reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json')
    accepted_path='reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz'
    if sha(ROOT/accepted_path)!=receipt['hashes']['artifacts'][accepted_path]:raise ValueError('ACCEPTED_ARTIFACT_DRIFT')
    accepted={r['security_id']:r for r in (json.loads(line) for line in gzip.open(ROOT/accepted_path,'rt',encoding='utf8'))}
    if len(accepted)!=5222:raise ValueError('5222_SCOPE_REQUIRED')
    path='data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet';source=bind(path)
    if source['sha256']!=receipt['hashes']['source'][path]:raise ValueError('ACCEPTED_SOURCE_DRIFT')
    calendarpath='data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_sse_20230704_20260924.json'
    dates=[d for d in read(calendarpath)['session_dates'] if d<='2026-09-24']
    statuspath='data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz';states={}
    for line in gzip.open(ROOT/statuspath,'rt',encoding='utf8'):
        r=json.loads(line)
        if r['status']=='SUSPENDED' and r['trade_date']<='2026-09-24':states[r['security_id'],r['trade_date']]='SUSPENDED'
    cols=['canonical_security_id','source_security_key','trade_date','raw_open','raw_high','raw_low','raw_close','qfq_open','qfq_high','qfq_low','qfq_close','qfq_mul','qfq_add','amount','volume','adjusted_quality','trading_status','price_basis','adjustment_source_revision']
    cursor=duckdb.connect().execute('select '+','.join(cols)+' from read_parquet(?) where trade_date<=20260924 order by canonical_security_id,trade_date',[str(ROOT/path)])
    def records():
        while block:=cursor.fetchmany(10000):
            for r in block:yield dict(zip(cols,r))
    replayrows=[];differences=[];counts=Counter();boundary=[];coefficient_changes=0
    comparedkeys=['value','quality_state','unknown_reason','window_identity','window_start_trade_date','window_end_trade_date','calendar_span','actual_count','suspended_count','input_digest','output_digest','contract_id','parameter_set_id']
    for sid,group in groupby(records(),lambda r:r['canonical_security_id']):
        if sid not in accepted:continue
        bars={};last=None
        for source_row in group:
            r=parent_bar(source_row);r['raw_actual_bar']=all(r['raw_'+k] is not None for k in ('open','high','low','close'));r['accepted_source_digest']=source['sha256'];bars[r['date']]=r
            states[sid,r['date']]=r['trading_status']
            # Oracle computes expected identity directly from source columns,
            # without the adapter's basis/admission helper.
            expected=f"{source_row['price_basis']}:{source_row['adjustment_source_revision']}" if source_row['price_basis'] and source_row['adjustment_source_revision'] else None
            if basis_id(r)!=expected:raise ValueError('SOURCE_BASIS_ORACLE_MISMATCH')
            if last and r['quality']==last['quality']=='READY' and expected==last['basis'] and (r['mul'],r['add'])!=last['coefficients']:
                coefficient_changes+=1
                if len(boundary)<12:boundary.append(dict(security_id=sid,previous=last['row'],current=r,expected_basis=expected,oracle_expected='EVALUABLE',actual_admission=admission(r,last['row'])))
            last=dict(basis=expected,coefficients=(r['mul'],r['add']),quality=r['quality'],row=r)
        slots=[bars.get(d,dict(date=d,raw_actual_bar=False)) for d in dates]
        fields={k:asdict(v) for k,v in compute_core(observations(slots,sid,states,source['sha256']),sid).items()}
        for field,current in fields.items():
            old=accepted[sid]['fields'][field]
            for key in comparedkeys:
                x,y=current[key],old[key]
                same=x==y or key=='value' and type(x) in (int,float) and type(y) in (int,float) and abs(x-y)<=1e-12
                if not same:differences.append(dict(security_id=sid,field=field,key=key,accepted=y,replay=x))
            counts[field+':'+current['quality_state']]+=1
        replayrows.append(dict(security_id=sid,trade_date='2026-09-24',fields=fields))
    replayref=compressed('data/v4/confirmation_candidates_r4/V4_03_CORE_PARITY_2026-09-24_R4.json.gz',replayrows)
    # Frozen counterexamples use real rows; only identity/capability is altered.
    from copy import deepcopy
    if not boundary or any(r['actual_admission'] for r in boundary):raise ValueError('REAL_AFFINE_CHANGE_BOUNDARY_REQUIRED')
    cases=[];sample=boundary[0]['current'];target=boundary[0]['previous']
    for name,changes,expected in [('different_basis',{'price_basis':'OTHER_BASIS'},'MIXED_ADJUSTMENT_IDENTITY'),('different_revision',{'adjustment_source_revision':'OTHER_REVISION'},'MIXED_ADJUSTMENT_IDENTITY'),('missing_revision',{'adjustment_source_revision':None},'ADJUSTMENT_UNKNOWN'),('unsupported_adjustment',{'quality':'UNKNOWN'},'ADJUSTMENT_UNKNOWN')]:
        altered=deepcopy(sample);altered.update(changes);actual=admission(altered,target)
        if actual!=expected:raise ValueError(name)
        cases.append(dict(case=name,source=sample,changes=changes,expected=expected,actual=actual))
    reasons=Counter(d['key'] for d in differences)
    result=dict(status='PASS' if not differences and len(replayrows)==5222 else 'FAIL',row_scope=len(replayrows),core_fields=list(fields),field_mapping={f:f for f in fields},compared_keys=comparedkeys,business_mismatches=reasons['value'],quality_mismatches=reasons['quality_state'],unknown_reason_mismatches=reasons['unknown_reason'],all_identity_mismatches=len(differences)-reasons['value']-reasons['quality_state']-reasons['unknown_reason'],numeric_tolerance=1e-12,differences=differences,counts=dict(counts),accepted_artifact=bind(accepted_path),accepted_receipt=bind('reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json'),source=source,status_source=bind(statuspath),calendar_source=bind(calendarpath),replay=replayref,adapter=bind('src/v4/adjustment_basis_r4.py'),real_coefficient_change_pairs=coefficient_changes,corporate_action_boundaries=boundary,independent_counterexamples=cases,accepted_identity='price_basis + adjustment_source_revision',affine_role='REPRODUCIBILITY_AND_CALCULATION_EVIDENCE_ONLY',permissions=PERMISSIONS,accepted=False)
    write(OUT+'V4_03_EXACT_PARITY_R1.json',result)
    print(json.dumps(dict(status=result['status'],scope=len(replayrows),mismatches=len(differences),coefficient_changes=coefficient_changes,difference_sample=differences[:5])))
    if result['status']!='PASS':raise ValueError('R4A_PARITY_GATE_FAIL')
    return result

if __name__=='__main__':replay()

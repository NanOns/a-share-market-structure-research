"""Previously uncovered current equal-weight dated-market relative arithmetic."""
import hashlib,json,math
from scripts.v4_closeout_core_uncovered_numeric_oracle import ROOT,OUT,jsonlines,average
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    report=OUT/'RELATIVE_MARKET_NUMERIC_ORACLE_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_RELATIVE_MARKET_ORACLE')
    prep=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,prep['candidate']).read_bytes());day=candidate['accepted_trade_date'];receipt=json.loads(checked(ROOT,candidate['day_receipt']).read_bytes());replay=json.loads(checked(ROOT,receipt['numeric_core_oracle']).read_bytes());owner=next(x for x in replay['owners'] if x['trade_date']==day)
    bindings=json.loads((checked(ROOT,owner['core']).parents[2]/'SOURCE_BINDINGS.json').read_bytes());identity=json.loads(checked(ROOT,owner['sources']['identity']).read_bytes())['rows'];ids={r['source_security_key'].lower():r['security_id'] for r in identity};core=list(jsonlines(checked(ROOT,owner['core'])));index={r['security_id']:r for r in core}
    calendar=json.loads((ROOT/'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json').read_bytes())['session_dates'];position=calendar.index(day);parameters=json.loads((ROOT/'config/v4_03_parameter_set_v1.json').read_bytes());limit=parameters['contract_literals']['market_reference_max_missing_fraction']
    counts={};errors=[];universes=[]
    for horizon in (1,3,5):
        start=calendar[position-horizon];queries=[q for q in bindings['query_receipts'] if q['method']=='query_all_stock' and q['params'].get('day')==start]
        if len(queries)!=1:raise ValueError('DATED_START_UNIVERSE_RECEIPT_REQUIRED')
        query=queries[0]
        if start=='2026-10-09':path=ROOT/'data/v4/dynamic_daily_sources/dated_universe'/start/'query_all_stock.json'
        else:path=ROOT/'docs/evidence/source_acquisition_r4_20261009/capture/queries'/(query['source_revision']+'.json')
        data=json.loads(path.read_bytes())
        if data.get('target_session',data.get('params',{}).get('day'))!=start or ('row_count' in query and len(data['rows'])!=query['row_count']) or data['received_at']!=query['received_at'] or data['requested_at']!=query['requested_at']:raise ValueError('START_UNIVERSE_QUERY_CONTEXT_MISMATCH')
        members=sorted({ids[r['code'].lower()] for r in data['rows'] if r['code'].lower() in ids and r['code'].lower().startswith(('sh.6','sz.00','sz.30','bj.43','bj.83','bj.87','bj.92'))})
        known={sid:index[sid]['fields']['ret'+str(horizon)]['value'] for sid in members if sid in index and index[sid]['fields']['ret'+str(horizon)]['value'] is not None and math.isfinite(index[sid]['fields']['ret'+str(horizon)]['value'])}
        total=len(members);missing=total-len(known);reason='EMPTY_START_UNIVERSE' if not total else 'MISSING_COVERAGE_EXCEEDED' if missing/total>limit else None
        reference=average(known.values()) if reason is None and known else None
        metadata=dict(contract_id='MARKET_RELATIVE_REFERENCE_V1',parameter_set_id='V4_03_CORE_FACTOR_PARAMETER_SET_V1',universe_count=total,evaluable_count=len(known),missing_count=missing,coverage=len(known)/total if total else None,unknown_reason=reason,evaluable_set_identity=hashlib.sha256(json.dumps(sorted(known),sort_keys=True,separators=(',',':')).encode()).hexdigest())
        field='rel_market_'+str(horizon);counts[field]=0
        for row in core:
            cell=row['fields'][field];value=row['fields']['ret'+str(horizon)]['value'];expected=value-reference if value is not None and reference is not None else None
            for key,actual,wanted in (('value',cell['value'],expected),('quality',cell['quality_state'],'OBSERVED' if expected is not None else 'UNKNOWN'),('reason',cell['unknown_reason'],None if expected is not None else 'DATED_MARKET_REFERENCE_UNPROVEN'),('start_date',cell['start_universe_date'],start),('reference',cell['reference'],metadata)):
                counts[field]+=1
                if actual!=wanted:errors.append(dict(security_id=row['security_id'],field=field,key=key,actual=actual,expected=wanted))
        universes.append(dict(start_date=start,source=ref(ROOT,path),universe_count=total,known=len(known),reference=reference))
    result=dict(contract_id='V4_CURRENT_RELATIVE_MARKET_DATED_UNIVERSE_INDEPENDENT_ORACLE_R1',acceptance='PASS_DATED_RELATIVE_SCOPE' if not errors else 'FAIL',candidate=prep['candidate'],T0=day,core=owner['core'],checks=counts,check_count=sum(counts.values()),universes=universes,error_count=len(errors),first_errors=errors[:100],passed_return_arithmetic_reexecuted=False,source_primary_market_reference_function_called=False,scope='Three current relative fields plus exact dated-universe coverage/identity/UNKNOWN semantics; previously passed endpoint return arithmetic reused')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=result['check_count'],errors=len(errors))))

if __name__=='__main__':main()

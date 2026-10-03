"""Independent arithmetic/readback oracle; imports no runtime evaluator."""
import hashlib
import json
import math
from pathlib import Path

def exact(root,binding):
    raw=(root/binding['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=binding['sha256'] or len(raw)!=binding['bytes']:raise ValueError('EXACT_BINDING')
    return json.loads(raw)

def validate(root,namespace):
    root=Path(root);records=[]
    for path in sorted((root/namespace/'outcomes').glob('*.json')):
        value=json.loads(path.read_bytes());frozen=exact(root,value['frozen_t0']);records.append(value)
        if frozen['enrollment_id']!=value['enrollment_id']:raise ValueError('ENROLLMENT_ID')
        source=frozen['authority']['calendar'];calendar=exact(root,source)
        dates=[d['trade_date'] if isinstance(d,dict) else d for d in calendar['session_dates']]
        index=dates.index(frozen['T0'])+value['horizon'];due=dates[index] if index<len(dates) else None
        if due!=value['due_date']:raise ValueError('DUE_DATE')
        if value['outcome_status']=='PENDING':
            if due and due<=value['report_cutoff']:raise ValueError('FALSE_PENDING')
            if value['price_path']:raise ValueError('PENDING_FUTURE_READ')
            continue
        pathrows=value['price_path']
        if any(r['trade_date']<=frozen['T0'] or r['trade_date']>due for r in pathrows):raise ValueError('PATH_DATE')
        if value['R_N'] is not None and value['outcome_status']=='OBSERVED':
            coeff=pathrows[-1].get('T0_transform_coefficients',pathrows[-1]['transform_coefficients']);p0=coeff['alpha']*frozen['comparison_reference']+coeff['beta']
            values=[]
            for r in pathrows:
                c=r.get('transform_coefficients',{'alpha':1,'beta':0})
                values.append({k:c['alpha']*r[k]+c['beta'] if r.get(k) is not None else None for k in ('close','high','low')})
            expected=values[-1]['close']/p0-1
            if not math.isclose(expected,value['R_N'],abs_tol=1e-12):raise ValueError('R_N')
            actual=[v for r,v in zip(pathrows,values) if r.get('status')!='CONFIRMED_SUSPENSION']
            if value['MFE_N'] is not None:
                mfe=max([0]+[v['high']/p0-1 for v in actual]);mae=min([0]+[v['low']/p0-1 for v in actual]);peak=p0;dd=0
                for v in actual:peak=max(peak,v['close']);dd=min(dd,v['close']/peak-1)
                for field,expected in [('MFE_N',mfe),('MAE_N',mae),('PATH_MDD_CLOSE_N',dd)]:
                    if not math.isclose(expected,value[field],abs_tol=1e-12):raise ValueError(field)
        if value['outcome_status'] in ('MATURED_DATA_MISSING','IDENTITY_UNKNOWN','ADJUSTMENT_UNKNOWN','SUSPENDED_AT_HORIZON') and value['R_N'] is not None:raise ValueError('COERCED_RETURN')
        for key in ('market_benchmark','sector_benchmark'):
            if key not in value:continue
            result=value[key];basket=frozen['market' if key=='market_benchmark' else 'sector'];weights={m['security_id']:m['weight'] for m in basket['members']}
            if any(c['original_weight']!=weights[c['security_id']] for c in result['constituents']):raise ValueError('BENCHMARK_REWEIGHT')
            if result['marked_permission'] or result['relative_market_return_marked'] is not None:raise ValueError('UNFROZEN_MARKED_GATE')
            if result['benchmark_endpoint_coverage']<1-1e-12 and result['relative_return'] is not None:raise ValueError('PARTIAL_FULL_RETURN')
    if not records:raise ValueError('NO_PERSISTED_OUTCOMES')
    keys=[(v['enrollment_id'],v['horizon'],v['outcome_contract_id'],v['evaluation_source_digest']) for v in records]
    if len(keys)!=len(set(keys)):raise ValueError('DUPLICATE_SOURCE_EVALUATION')
    return {'R20D_INDEPENDENT_SETTLEMENT_ORACLE':'PASS_LOCAL','persisted_outcomes':len(records),'HISTORICAL_PIT_EFFECTIVENESS':'NOT_GRANTED'}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--namespace',required=True);args=parser.parse_args()
    print(json.dumps(validate(Path(__file__).resolve().parents[1],args.namespace),indent=2))

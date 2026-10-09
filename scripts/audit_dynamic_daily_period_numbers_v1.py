"""Independent sums/extrema over real saved daily bytes; no period kernel call."""
from pathlib import Path
from datetime import date
from decimal import Decimal
import argparse,json
from workbench_analysis.r43_owner_replay import checked,ref,gzrows
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def key(day,kind):
    if kind=='MONTHLY':return day[:7]
    year,week,_=date.fromisoformat(day).isocalendar();return f'{year}-W{week:02d}'

def audit(root,folder):
    receipt=json.loads((folder/'DAY_RECEIPT.json').read_bytes());day=receipt['target_session']
    replay=json.loads((folder/'owner_v3/CORE_REPLAY.json').read_bytes())
    owner=next(r for r in replay['owners'] if r['trade_date']==day)
    history={r['security_id']:r['bars'] for r in gzrows(checked(root,owner['history']))}
    errors=[];checks=0;coverage={}
    for domain,basis in [('period_raw','raw_ohlc'),('period_adjusted','qfq_ohlc')]:
        rows=gzrows(checked(root,receipt['owners'][domain]));coverage[domain]=len(rows)
        if {r['security_id'] for r in rows}!=set(history):errors.append(dict(domain=domain,reason='IDENTITY_COVERAGE'))
        for row in rows:
            bars=[b for b in history[row['security_id']] if b['trade_date'][:7]==day[:7] and key(b['trade_date'],row['period_type'])==row['period_key']]
            expected=dict(actual_count=len(bars),volume=sum(b['volume'] for b in bars),amount=sum(b['amount'] for b in bars))
            if bars and all(b[basis] for b in bars):
                prices=[[Decimal(str(v)) for v in b[basis]] for b in bars]
                expected.update(open=prices[0][0],high=max(p[1] for p in prices),low=min(p[2] for p in prices),close=prices[-1][3])
            else:expected.update(open=None,high=None,low=None,close=None)
            for field,value in expected.items():
                actual=row[field]
                if field in ('open','high','low','close') and actual is not None:actual=Decimal(str(actual))
                checks+=1
                if actual!=value:errors.append(dict(domain=domain,security_id=row['security_id'],period=row['period_key'],field=field))
    result=dict(contract_id='DD06_INDEPENDENT_REAL_PERIOD_NUMERIC_ORACLE_V1',target_session=day,
        evidence_kind='ACTUAL_SAVED_DAILY_BYTES_INDEPENDENT_SUM_EXTREMA',input_history=owner['history'],
        owners={k:receipt['owners'][k] for k in coverage},row_counts=coverage,checks=checks,errors=errors,
        verifier=ref(root,Path(__file__)),
        acceptance='PASS' if not errors else 'FAIL',external_acceptance='NOT_GRANTED',scope='All securities, current-month formal RAW/QFQ week/month rows')
    path=folder/'PERIOD_NUMERIC_ORACLE.json';atomic_json(root,path,result)
    print(json.dumps(dict(acceptance=result['acceptance'],checks=checks,errors=len(errors),evidence=ref(root,path))))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    result=audit(root,args.folder);raise SystemExit(bool(result['errors']))

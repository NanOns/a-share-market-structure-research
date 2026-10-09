"""Standalone standard-library oracle; no project producer imports or network."""
import argparse,hashlib,json,math,os
from pathlib import Path

def median(v):
    v=sorted(v);n=len(v)
    return None if not n else v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2

def run(path):
    data=json.loads(path.read_bytes());checks=[]
    def check(label,expected,actual):
        if expected is None or actual is None:ok=expected is actual;delta=None
        else:delta=actual-expected;ok=math.isclose(actual,expected,abs_tol=1e-10,rel_tol=1e-10)
        checks.append(dict(label=label,expected=expected,actual=actual,delta=delta,verdict='PASS' if ok else 'FAIL'))
    for s in data['sectors']:
        rows=s['contributions'];ids=[r['security_id'] for r in rows];assert len(ids)==len(set(ids))==s['eligible_count']
        authority=s['authority_rows']
        eligible={m['security_id'] for m in authority if m.get('security_id') and m.get('list_date') and m['list_date']<=data['trade_date'] and (not m.get('delist_date') or m['delist_date']>data['trade_date'])}
        assert eligible==set(ids),'DATED_SOURCE_AUTHORITY_MISMATCH'
        assert s['sector_type']!='THEME' or s['raw_classification']=='GN','STYLE_IS_NOT_CONCEPT'
        assert all(r['sector_id']==s['sector_id'] and r['weight']==1 for r in rows)
        for n in (1,5):
            field='ret'+str(n)
            values=[r[field] for r in rows if r[field] is not None and r[field+'_quality']=='OBSERVED']
            exp=s['expected']['sector_rs'+str(n)]
            check(s['sector_id']+'/rs'+str(n),exp['value'],median(values))
            check(s['sector_id']+'/known'+str(n),exp['known_count'],len(values))
            check(s['sector_id']+'/breadth'+str(n),s['expected']['breadth_ret'+str(n)]['value'],sum(v>0 for v in values)/len(values) if values else None)
            target=s['loo']['excluded_target_id'];own=next(r[field] for r in rows if r['security_id']==target)
            others=[r[field] for r in rows if r['security_id']!=target and r[field] is not None and r[field+'_quality']=='OBSERVED']
            check(s['sector_id']+'/LOO'+str(n),s['loo']['expected_relative']['rel_market_'+str(n)],own-median(others))
        check(s['sector_id']+'/LOO_count',s['loo']['non_target_member_count'],len(rows)-1)
    return dict(scope='TWO_FROZEN_TDX_SECTORS_ONLY_NOT_FULL_MARKET_OR_STATE_ACCEPTANCE',input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checks=checks,error_count=sum(x['verdict']=='FAIL' for x in checks),external_acceptance='NOT_GRANTED')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();result=run(Path(a.input));out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');os.replace(tmp,out);print(json.dumps(dict(checks=len(result['checks']),errors=result['error_count'])));raise SystemExit(bool(result['error_count']))

"""Source-only first pulse basket/baseline proof; stdlib only."""
from pathlib import Path
import json,math,sys
def main():
    here=Path(__file__).parent;p=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else here/'PULSE_SOURCE_ORACLE_INPUT.json').read_text(encoding='utf8'));checks=[]
    def check(row,key,e,a):checks.append(dict(sector_id=row['sector_id'],trade_date=row['trade_date'],field=key,expected=e,actual=a,passed=e==a if e is None or a is None or isinstance(e,list) else math.isclose(e,a,rel_tol=1e-12,abs_tol=1e-12)))
    for r in p['records']:
        episode=r['actual_episode'];ids=sorted(set(r['source_previous_member_ids']));check(r,'frozen_basket',ids,episode['frozen_basket']);returns=[]
        for sid in ids:
            b={v['trade_date']:v for v in r['member_bars'][sid]};old=b[r['previous']]['qfq_ohlc'][3];now=b[r['trade_date']]['qfq_ohlc'][3]
            check(r,'baseline:'+sid,old,episode['pulse_baseline'][sid]);check(r,'pulse_close:'+sid,now,episode['pulse_closes'][sid]);returns.append(now/old-1)
        check(r,'pulse_basket_return',sum(returns)/len(ids),episode['pulse_basket_return'])
    errors=[r for r in checks if not r['passed']];out=dict(contract=p['contract'],checks=len(checks),errors=len(errors),differences=errors,results=checks,observed_pulse_rows=len(p['records']),acceptance='PASS_SCOPED_ACTUAL_FIRST_PULSE_SOURCES' if not errors else 'FAIL');dest=Path(sys.argv[2] if len(sys.argv)>2 else here/'PULSE_SOURCE_ORACLE_RESULT.json');tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(dest);print(json.dumps({k:out[k] for k in ('checks','errors','observed_pulse_rows')}));return bool(errors)
if __name__=='__main__':sys.exit(main())

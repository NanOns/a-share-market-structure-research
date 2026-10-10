"""Independent standard-library reference to declared technical/session quality rules."""
from pathlib import Path
import json,sys
def reasons(states):
    def technical(n,prior=False):
        seq=states[:-1] if prior else states
        if not seq:return 'INSUFFICIENT_HISTORY'
        if not prior and seq[-1]['state'] in ('UNKNOWN','ADJUSTMENT_UNKNOWN','IDENTITY_UNKNOWN','PRE_LISTING'):
            s=seq[-1]['state'];return s if s in ('ADJUSTMENT_UNKNOWN','IDENTITY_UNKNOWN') else 'CURRENT_BAR_UNAVAILABLE'
        count=0
        for row in reversed(seq):
            s=row['state']
            if s in ('UNKNOWN','ADJUSTMENT_UNKNOWN','IDENTITY_UNKNOWN'):return 'UNEXPLAINED_DATA_GAP' if s=='UNKNOWN' else s
            if s=='PRE_LISTING':break
            count+=s=='ACTUAL'
            if count==n:return None
        return 'INSUFFICIENT_HISTORY'
    out={}
    for n in (5,20,60):
        for stem in ('ma','hhv','llv'):out[stem+str(n)]=technical(n)
        for stem in ('prior_high','prior_low'):out[stem+str(n)]=technical(n,True)
    out['tr']=technical(2);out['atr5']=technical(6);out['atr20']=technical(21)
    for n,extra in ((20,5),(60,10)):out['slope'+str(n)]=technical(n+extra) or out['atr20']
    for f in ('hh_progress','ll_progress'):out[f]=technical(10)
    out['prior60_percentile']=technical(60,True) or ('MISSING_OR_SUSPENDED_ENDPOINT' if states[-1]['state']!='ACTUAL' else None)
    if out['tr'] is None and states[-1]['state']!='ACTUAL':out['tr']='CURRENT_BAR_UNAVAILABLE'
    out['pos60']=out['llv60'] or out['hhv60'] or ('CURRENT_BAR_UNAVAILABLE' if states[-1]['state']!='ACTUAL' else None)
    out['range_ratio']=out['hhv5'] or out['hhv20'] or out['llv5'] or out['llv20']
    out['atr_ratio']=out['atr5'] or out['atr20']
    endpoint=None
    if len(states)<2:endpoint='INSUFFICIENT_SESSION_HISTORY'
    elif states[-1]['state']!='ACTUAL' or states[-2]['state']!='ACTUAL':
        endpoint=next((r['state'] for r in states[-2:] if r['state'] in ('ADJUSTMENT_UNKNOWN','IDENTITY_UNKNOWN')),None) or 'MISSING_OR_SUSPENDED_ENDPOINT'
    out['core_price_damage']=out['prior_low20'] or out['atr20'] or endpoint
    return out
def main():
    here=Path(__file__).parent;d=json.loads((here/'EXACT_QUALITY_INPUT.json').read_text(encoding='utf8'));rows=[]
    for r in d['records']:
        expected=reasons(r['states'])
        for field,c in r['actual'].items():rows.append(dict(security_id=r['security_id'],trade_date=r['trade_date'],field=field,expected=expected[field],actual=c['unknown_reason'],passed=expected[field]==c['unknown_reason'] and c['value'] is None,current_source_state=r['states'][-1]['state']))
    errors=[r for r in rows if not r['passed']];out=dict(checks=len(rows),errors=errors,results=rows,scope=d['scope'],status='PASS_SCOPED' if not errors else 'FAIL')
    dest=here/'EXACT_QUALITY_RESULT.json';tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n');tmp.replace(dest)
    print(json.dumps(dict(checks=len(rows),errors=errors)));return bool(errors)
if __name__=='__main__':sys.exit(main())

"""Independent decimal oracle over actual reconstructed daily limits."""
import gzip,hashlib,json,os
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/r4_3_four_session_closeout_20261009'
def load(p):return json.loads(p.read_bytes())
def bound(r):
    p=ROOT/r['path']
    with p.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==r['sha256']
    return p
def rows(p):
    with gzip.open(p,'rt',encoding='utf8') as f:
        for l in f:
            if l.strip():yield json.loads(l)
def main():
    replay=load(OUT/'owner_v3/DAILY_PRICE_LIMIT_REPLAY.json');rule_ref=load(bound(replay['contract']))['legal_rules'];rules={r['rule_id']:r for r in load(bound(rule_ref))['rules']};errors=[];count=0;sample=[];dates=[]
    for owner in replay['owners']:
        known=0;bao_cache={};raw_cache={}
        for row in rows(bound(owner['artifact'])):
            if row['limit_state'] not in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT'):continue
            references=row['source_refs']
            if not bao_cache:bao_cache={r['code'].lower():r for r in load(bound(references[2]))['rows']};raw_cache={r['security_id']:r for r in rows(bound(references[0]))}
            provider=bao_cache[row['source_security_key']];rule=rules[row['rule_id']]
            previous=Decimal(provider['preclose']);ratio=Decimal(rule['limit_ratio']);tick=Decimal(rule['tick']);up=((previous*(1+ratio))/tick).quantize(Decimal('1'),rounding=ROUND_HALF_UP)*tick;down=((previous*(1-ratio))/tick).quantize(Decimal('1'),rounding=ROUND_HALF_UP)*tick
            if up==previous:up+=tick
            if down==previous:down-=tick
            raw=raw_cache[row['security_id']];close=Decimal(str(raw['close']));expected='LIMIT_UP' if close==up else 'LIMIT_DOWN' if close==down else 'NOT_LIMIT'
            observed=(Decimal(row['limit_up_price']),Decimal(row['limit_down_price']),row['limit_state'],row['daily_high_equals_limit_up'],row['daily_low_equals_limit_down'])
            oracle=(up,down,expected,Decimal(str(raw['high']))==up,Decimal(str(raw['low']))==down)
            if observed!=oracle:errors.append(dict(security_id=row['security_id'],trade_date=owner['trade_date'],observed=str(observed),expected=str(oracle)))
            if row['native_isST']!=provider['isST']:errors.append(dict(security_id=row['security_id'],error='DATED_ISST_MISMATCH'))
            known+=1;count+=5
            if len(sample)<40 and (row['native_isST']=='1' or row['limit_state']!='NOT_LIMIT'):sample.append(dict(security_id=row['security_id'],trade_date=owner['trade_date'],rule_id=row['rule_id'],native_isST=row['native_isST'],previous=str(previous),up=str(up),down=str(down),close=str(close),state=expected))
        dates.append(dict(trade_date=owner['trade_date'],known=known,source=owner['artifact'],reported_counts=owner['counts'],unknown_reasons=owner['unknown_reasons']))
    p=OUT/'05_INDEPENDENT_DAILY_PRICE_LIMIT_ORACLE.json';tmp=p.with_suffix('.tmp.limit');tmp.write_text(json.dumps(dict(contract='R43_INDEPENDENT_DATED_DAILY_LIMIT_ORACLE_V1',sources=dates,checks=count,samples=sample,errors=errors,precision='Exact Decimal tick HALF_UP; minimum tick movement',intraday='NOT_OBSERVABLE_FROM_DAILY',acceptance='PASS' if not errors else 'FAIL'),ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,p);print(count,len(errors))
if __name__=='__main__':main()

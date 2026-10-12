"""Independent Fraction ret1/breadth and source index byte numeric oracle."""
import argparse,gzip,json,sys,struct,zipfile
from collections import Counter
from fractions import Fraction
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();r=Path(a.root)
    from workbench_analysis.r43_owner_replay import checked
    from workbench_db.v4_market_fact_pg_r1 import read
    from workbench_db.v4_native import connection
    authority=json.loads((r/'config/core_product_read_authority_r1.json').read_bytes());head=json.loads((r/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes());binding=authority.get('manifest') or authority['dates'][head['accepted_trade_date']];manifest=json.loads(checked(r,binding).read_bytes());day=manifest['T0'];facts=read(r,manifest['market_facts'],day)
    def rows(binding):
        q=checked(r,binding);data=q.read_bytes();data=gzip.decompress(data) if q.suffix=='.gz' else data
        return [json.loads(x) for x in data.splitlines() if x.strip()] if '.jsonl' in q.name else json.loads(data)
    raw={x['security_id']:x for x in rows(facts['sources']['raw'])};core={x['security_id']:x for x in rows(facts['sources']['core'])}
    f=lambda v:Fraction(str(v));diffs=[];counts=Counter(up=0,down=0,flat=0,unknown=0);compared=0;quality_unknown=0;b=manifest['history_index']
    with connection(b['schema'],read_only=True) as pg:
        data=pg.execute('SELECT security,payload->-1,payload->-2 FROM history WHERE version=%s',(b['version'],)).fetchall()
    for sid,last,prior in data:
        value=core[sid]['fields']['ret1']['value'] if sid in raw else None
        if value is None:counts['unknown']+=1;quality_unknown+=1;continue
        if not last or not prior or last['trade_date']!=day or last.get('qfq_ohlc') is None or prior.get('qfq_ohlc') is None:
            diffs.append(dict(sid=sid,reason='KNOWN_RET_WITHOUT_TWO_PRICES'));continue
        expected=f(last['qfq_ohlc'][3])/f(prior['qfq_ohlc'][3])-1
        if abs(f(value)-expected)>Fraction(1,10**12):diffs.append(dict(sid=sid,reason='RET1_SOURCE_ORACLE',expected=str(expected),actual=str(value)))
        compared+=1;counts['up' if expected>0 else 'down' if expected<0 else 'flat']+=1
    for key in counts:
        if counts[key]!=facts['breadth'][key]:diffs.append(dict(field=key,expected=counts[key],actual=facts['breadth'][key]))
    amount=sum((f(x['amount']) for x in raw.values()),Fraction(0))
    if amount!=f(facts['breadth']['amount_cny']):diffs.append(dict(field='amount_cny',expected=str(amount),actual=facts['breadth']['amount_cny']))
    index_comparisons=0
    with zipfile.ZipFile(checked(r,facts['sources']['package'])) as archive:
        for index in facts['indices']:
            expected=[]
            for record in struct.iter_unpack('<IIIIIfII',archive.read(index['source_member'])):
                d=str(record[0]);d=d[:4]+'-'+d[4:6]+'-'+d[6:]
                if d<=day:expected.append((d,record))
            expected=expected[-120:]
            if len(expected)!=len(index['bars']):diffs.append(dict(index=index['symbol'],reason='INDEX_DENOMINATOR'))
            for (date,record),bar in zip(expected,index['bars']):
                if date!=bar['trade_date']:diffs.append(dict(index=index['symbol'],reason='DATE'))
                for offset,field in enumerate(('open','high','low','close'),1):
                    index_comparisons+=1
                    if Fraction(record[offset],100)!=f(bar[field]):diffs.append(dict(index=index['symbol'],date=date,field=field))
                for offset,field in ((5,'amount'),(6,'volume')):
                    index_comparisons+=1
                    if f(record[offset])!=f(bar[field]):diffs.append(dict(index=index['symbol'],date=date,field=field))
    rules=json.loads((r/'config/v4_02_price_limit_rules_r3.json').read_bytes())['rules'];rules={x['rule_id']:x for x in rules}
    limits=facts['limits']['rows'];known_limits=0;limit_numeric=0
    providers={}
    for row in limits:
        if row['limit_state'] not in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT'):continue
        rule=rules[row['rule_id']]
        if not rule['valid_from']<=day or (rule.get('valid_to') and day>rule['valid_to']):diffs.append(dict(sid=row['security_id'],reason='RULE_OUTSIDE_DATE'))
        native=next(x for x in row['source_refs'] if x['path'].endswith('/sources/daily.json'))
        if native['sha256'] not in providers:providers[native['sha256']]={x['code'].lower():x for x in json.loads(checked(r,native).read_bytes())['rows']}
        provider=providers[native['sha256']][row['source_security_key']];reference=Decimal(provider['preclose']);ratio=Decimal(rule['limit_ratio']);tick=Decimal(rule['tick'])
        up=(reference*(1+ratio)/tick).quantize(Decimal(1),rounding=ROUND_HALF_UP)*tick
        down=(reference*(1-ratio)/tick).quantize(Decimal(1),rounding=ROUND_HALF_UP)*tick
        sid=row['security_id'];quote=raw[sid];close=Decimal(str(quote['close']));expected_state='LIMIT_UP' if close==up else 'LIMIT_DOWN' if close==down else 'NOT_LIMIT'
        if (up,down,expected_state)!=(Decimal(row['limit_up_price']),Decimal(row['limit_down_price']),row['limit_state']):diffs.append(dict(sid=sid,reason='LIMIT_PRICE_OR_CLOSE_STATE_ORACLE'))
        extrema=(Decimal(str(quote['high']))==up,Decimal(str(quote['low']))==down,quote['open']==quote['high']==quote['low']==quote['close'] and expected_state in ('LIMIT_UP','LIMIT_DOWN'))
        if extrema!=(row['daily_high_equals_limit_up'],row['daily_low_equals_limit_down'],row['one_price_limit_bar']):diffs.append(dict(sid=sid,reason='DAILY_EXTREMA_ORACLE'))
        known_limits+=1;limit_numeric+=5
    if dict(Counter(x['limit_state'] for x in limits))!=facts['limits']['counts']:diffs.append(dict(reason='LIMIT_FULL_DENOMINATOR'))
    result=dict(contract_id='CORE_MARKET_INDEPENDENT_NUMERIC_ORACLE_R2',status='SCOPED_NUMERIC_PASS' if not diffs else 'FAIL',T0=day,ret1_comparisons=compared,unknown_ret1=quality_unknown,breadth_source_denominator=len(core),raw_actual_quote_count=len(raw),exact_amount_sum=str(amount),index_numeric_comparisons=index_comparisons,limits_full_denominator=len(limits),known_limit_rows=known_limits,limit_price_and_extrema_comparisons=limit_numeric,differences=diffs,source_bindings=facts['sources'],limitations=['Unknown limit lifecycle/reference admission and streak semantics require separate acceptance','Exact source equivalence does not grant cohort PIT or external acceptance'])
    Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='source_bindings'}),flush=True)
    if diffs:raise SystemExit(1)

if __name__=='__main__':main()

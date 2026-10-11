"""Independent pure dated-bar oracle. No runtime database or candidate code."""
from collections import defaultdict
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import sys

SOURCE=Path('G:/codex work/大A交易')
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_external_repair_r2_20261011'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while part:=stream.read(8*1024*1024):h.update(part)
    return h.hexdigest()


def load(ref):
    path=SOURCE/ref['path']
    if sha(path)!=ref['sha256']:raise ValueError('ORACLE_SOURCE_CHANGED')
    with gzip.open(path,'rt',encoding='utf8') if path.suffix=='.gz' else path.open(encoding='utf8') as stream:
        rows=[json.loads(line) for line in stream if line.strip()] if '.jsonl' in path.name else json.load(stream)
    if sha(path)!=ref['sha256']:raise ValueError('ORACLE_SOURCE_CHANGED_AFTER_READ')
    return rows


def derive(rows,period,basis):
    bars=[]
    for row in rows:
        prices=row['raw_ohlc' if basis=='RAW' else 'qfq_ohlc']
        bars.append(dict(trade_date=row['trade_date'],**dict(zip(('open','high','low','close'),prices or [None]*4)),volume=row['volume'],amount=row['amount'],quality='KNOWN' if prices else 'UNKNOWN',reason=None if prices else 'BLOCKED_ADJUSTMENT_EVENT'))
    if period!='D':
        groups=defaultdict(list)
        for bar in bars:
            day=date.fromisoformat(bar['trade_date']);key=day.isocalendar()[:2] if period=='W' else (day.year,day.month)
            groups[key].append(bar)
        result=[];keys=sorted(groups)
        for key in keys:
            group=groups[key];known=all(b['quality']=='KNOWN' for b in group)
            result.append(dict(trade_date=group[-1]['trade_date'],first_trade_date=group[0]['trade_date'],open=group[0]['open'] if known else None,high=max(b['high'] for b in group) if known else None,low=min(b['low'] for b in group) if known else None,close=group[-1]['close'] if known else None,volume=sum(b['volume'] for b in group),amount=sum(b['amount'] for b in group),quality='KNOWN' if known else 'UNKNOWN',actual_count=len(group),period_status='FORMING_AS_OF' if key==keys[-1] else 'CLOSED_OBSERVED_BUCKET'))
        bars=result
    return bars


def main():
    actual=json.loads((OUT/'DEFAULT_FIVE_DATES_RESULT.json').read_bytes())
    prior=json.loads((ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_03_FIVE_DATE_HISTORY_RESULT.json').read_bytes())
    head=json.loads((SOURCE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    selected={s['id'] for s in actual['samples']};sources={};periods={};diffs=[]
    for item in prior['results']:
        day=item['T0'];sources[day]={r['security_id']:r['bars'] for r in load(item['source_binding']) if r['security_id'] in selected}
        periods[day]={}
        for domain in ('period_raw','period_adjusted'):
            ref=head['owners'][day].get(domain)
            periods[day][domain]=None if ref is None else {(r['security_id'],r['period_type']):r for r in load(ref)}
    for index,case in enumerate(actual['results']):
        q=case['query'];day=q['trade_date'];sid=case['security_id'];period=q['period'];basis=q['price_basis']
        data=derive(sources[day][sid],period,basis)
        domain='period_raw' if basis=='RAW' else 'period_adjusted'
        if period!='D' and data:
            formal=periods[day][domain]
            if formal is None:
                if case['status']!='SOURCE_INCOMPLETE':diffs.append(dict(case=index,reason='PERIOD_OWNER_GAP_HIDDEN'))
                continue
            final=formal.get((sid,'WEEKLY' if period=='W' else 'MONTHLY'))
            if final:data[-1].update(period_status=final['period_status'],calendar_count=final['calendar_count'],suspended_count=final['suspended_count'],formal_period_source=head['owners'][day][domain])
        for i,bar in enumerate(data):
            for window in (5,20,60):
                sample=data[max(0,i-window+1):i+1]
                bar['ma'+str(window)]=sum(b['close'] for b in sample)/window if len(sample)==window and all(b['close'] is not None for b in sample) else None
        end=max(0,len(data)-q['offset']);start=max(0,end-q['limit'])
        if (case['items'],case['total'])!=(data[start:end],len(data)):diffs.append(dict(case=index,reason='EXACT_CHART_PAYLOAD_DIFF'))
    result=dict(contract_id='R4_INDEPENDENT_DATED_SOURCE_CHART_ORACLE_R1',denominator=len(actual['results']),differences=diffs,current_status='SCOPED_SOURCE_ORACLE_PASS' if not diffs else 'FAIL',source_bindings=[r['source_binding'] for r in prior['results']],source_hashes_verified_before_after=True,limitations=['Independent pure bar calculation; reconstructed sources, not historical PIT','Period owner gaps are explicit, not READY cases'])
    path=OUT/'DEFAULT_FIVE_DATES_ORACLE.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print(json.dumps(dict(cases=result['denominator'],differences=len(diffs))),flush=True)
    if diffs:raise ValueError('CHART_ORACLE_DIFFERENCE')


if __name__=='__main__':main()

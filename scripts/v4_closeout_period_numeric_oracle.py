"""Independent full dated aggregation oracle; no kernel or status synthesis."""
import argparse,calendar,gc,gzip,hashlib,json,sys
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]

def key(day,kind):
    d=date.fromisoformat(day)
    if kind=='MONTHLY':return day[:7]
    y,w,_=d.isocalendar();return f'{y}-W{w:02d}'

def main():
    from workbench_db.v4_period_pg_r1 import read
    from workbench_analysis.r43_owner_replay import checked
    from workbench_analysis.market_source_acquisition import official_sessions
    from workbench_service.core_product_bff_r1 import dated_product_manifest
    p=argparse.ArgumentParser();p.add_argument('day');p.add_argument('--label',default='R1');args=p.parse_args()
    root=Path('G:/codex_tmp/v4_ui_default_r1');day=args.day
    out=Path('G:/codex_tmp/v4_full_closeout_20261012/period_oracle')/args.label/day
    out.mkdir(parents=True,exist_ok=True)
    if (out/'RESULT.json').exists():raise ValueError('PRESERVE_ORIGINAL_ORACLE_RESULT')
    head=(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes();token=hashlib.sha256(head).hexdigest()
    authority=(root/'config/core_product_read_authority_r1.json').read_bytes()
    manifest=dated_product_manifest(root,json.loads(authority),day)
    sessions=official_sessions(root);period_calendar=defaultdict(list)
    for d in sessions:
        for kind in ('WEEKLY','MONTHLY'):period_calendar[kind,key(d,kind)].append(d)
    source=manifest['source_bindings']['history'];checks=rows_count=diff_count=0;diffs=[];counts={}
    def compare(row,field,expected):
        nonlocal checks,diff_count
        checks+=1;actual=row.get(field)
        equal=Decimal(str(actual))==expected if isinstance(expected,Decimal) and actual is not None else actual==expected
        if not equal:
            diff_count+=1
            if len(diffs)<40:diffs.append(dict(security_id=row['security_id'],period=row['period_key'],basis=row['price_basis'],field=field,actual=actual,expected=str(expected) if isinstance(expected,Decimal) else expected))
    for domain,prices_field in (('period_raw','raw_ohlc'),('period_adjusted','qfq_ohlc')):
        values=read(root,manifest['period_owners'][domain],day,domain,token)
        by=defaultdict(list)
        for row in values:by[row['security_id']].append(row)
        source_ids=set();domain_checks_before=checks
        with gzip.open(checked(root,source),'rt',encoding='utf8') as stream:
            for line in stream:
                item=json.loads(line);sid=item['security_id'];history=item['bars']
                if not history:continue
                source_ids.add(sid);bars={bar['trade_date']:bar for bar in history}
                groups=defaultdict(list)
                for bar in history:
                    for kind in ('WEEKLY','MONTHLY'):groups[kind,key(bar['trade_date'],kind)].append(bar)
                for row in by.get(sid,[]):
                    rows_count+=1;kind=row['period_type'];pk=row['period_key'];cutoff=row['as_of_date']
                    dates=[d for d in period_calendar[kind,pk] if history[0]['trade_date']<=d<=cutoff]
                    actual=[bar for bar in groups[kind,pk] if bar['trade_date']<=cutoff]
                    missing=[d for d in dates if d not in bars]
                    adjustment=any(not bar.get(prices_field) for bar in actual)
                    blocked_prices=adjustment or any(d<cutoff for d in missing)
                    prices=[list(map(lambda v:Decimal(str(v)),bar[prices_field])) for bar in actual if bar.get(prices_field)]
                    expected=[None]*4 if blocked_prices or not prices else [prices[0][0],max(x[1] for x in prices),min(x[2] for x in prices),prices[-1][3]]
                    for field,value in zip(('open','high','low','close'),expected):compare(row,field,value)
                    compare(row,'actual_count',len(actual));compare(row,'calendar_count',len(dates))
                    compare(row,'unknown_count',len(missing));compare(row,'suspended_count',0);compare(row,'data_gap_count',0)
                    compare(row,'volume',sum(bar['volume'] for bar in actual))
                    compare(row,'amount',sum(float(bar['amount']) for bar in actual))
                    compare(row,'price_basis','RAW' if domain=='period_raw' else 'QFQ')
                    compare(row,'PIT_ELIGIBLE',False);compare(row,'production_accepted',False)
                    compare(row,'knowledge_lineage','RECONSTRUCTED')
                    expected_status='BLOCKED_BY_ADJUSTMENT' if adjustment else 'BLOCKED_BY_UNKNOWN_STATUS' if missing else 'NO_ACTUAL_BARS' if not actual else 'CLOSED_ONLY_READY' if row['period_view']=='CLOSED_ONLY' else 'AS_OF_PARTIAL_READY'
                    compare(row,'period_status',expected_status)
                if len(source_ids)%500==0:print(json.dumps(dict(domain=domain,securities=len(source_ids),checks=checks,differences=diff_count)),flush=True)
        if set(by)!=source_ids:raise ValueError('PERIOD_ORACLE_SECURITY_DENOMINATOR_MISMATCH')
        counts[domain]=dict(securities=len(source_ids),rows=len(values),checks=checks-domain_checks_before)
        del values,by;gc.collect()
    if (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()!=head:raise ValueError('PERIOD_ORACLE_HEAD_CHANGED')
    result=dict(contract_id='V4_FULL_DATED_PERIOD_AGGREGATION_INDEPENDENT_ORACLE_R1',day=day,head_token=token,
        source=source,period_bindings=manifest['period_owners'],domains=counts,rows=rows_count,checks=checks,
        differences=diff_count,first_differences=diffs,status='PASS_AGGREGATION_ONLY' if not diff_count else 'FAIL',
        adjustment_factor_oracle='SEPARATE_REQUIRED',production_accepted=False,
        oracle_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status=result['status'],checks=checks,differences=diff_count)),flush=True)
    if diff_count:raise SystemExit(1)
if __name__=='__main__':main()

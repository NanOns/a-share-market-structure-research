from pathlib import Path
import json,gzip,collections,hashlib,os,bisect
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
core=json.loads((OUT/'A4_B2_CORE_SENSITIVITY.json').read_bytes())
cases=sorted({(r['day'],int(r['field'][3:])) for r in core['deltas'] if r['field'] in ('ret1','ret3','ret5','ret20')})
head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes());r=json.loads((ROOT/head['day_receipt']['path']).read_bytes());replay=json.loads((ROOT/r['numeric_core_oracle']['path']).read_bytes());hist=ROOT/replay['owners'][-1]['history']['path']
import zipfile,struct
with zipfile.ZipFile(ROOT/replay['owners'][-1]['sources']['package']['path']) as z:
    name=next(n for n in z.namelist() if Path(n).name.lower()=='sh000001.day')
    dates=sorted({str(r[0])[:4]+'-'+str(r[0])[4:6]+'-'+str(r[0])[6:] for r in struct.iter_unpack('<IIIIIfII',z.read(name)) if r[0]<=20261009})
needed={d for day,n in cases for d in (day,dates[dates.index(day)-n])}
def quotes(path):
    result={}
    with gzip.open(path,'rt',encoding='utf8') as f:
        for line in f:
            row=json.loads(line);result[row['security_id']]={b['trade_date']:b['qfq_ohlc'][3] for b in row['bars'] if b['trade_date'] in needed and b['qfq_ohlc'] is not None}
    return result
before=quotes(hist);after=quotes(BASE/'candidate_v0_3_history.jsonl.gz');receipts=[]
for day,n in cases:
    start=dates[dates.index(day)-n]
    a={sid:q[day]/q[start]-1 for sid,q in before.items() if day in q and start in q and q[start]>0}
    b={sid:q[day]/q[start]-1 for sid,q in after.items() if day in q and start in q and q[start]>0}
    assert a.keys()==b.keys()
    def rank(values):
        ordered=sorted(values.values());size=len(ordered)
        return {sid:100*(bisect.bisect_left(ordered,v)+.5*(bisect.bisect_right(ordered,v)-bisect.bisect_left(ordered,v)-1))/(size-1) for sid,v in values.items()}
    ar,br=rank(a),rank(b)
    deltas=[dict(security_id=sid,old=ar[sid],candidate=br[sid],return_old=a[sid],return_candidate=b[sid]) for sid in ar if ar[sid]!=br[sid]]
    receipts.append(dict(day=day,n=n,denominator=len(a),return_changed_count=sum(a[sid]!=b[sid] for sid in a),rank_changed_count=len(deltas),deltas=deltas))
value=dict(contract_id='HISTORICAL_FULL_CROSS_SECTION_QFQ_RPS_SENSITIVITY_R3',scope='Every frozen latest-universe stock at dates where seven-stock ret sensitivity changed; endpoint-valid reconstructed subset',not_legal_dated_pit_population=True,quality_eligibility_not_promoted=True,formula='100*(lower + 0.5*(ties-1))/(N-1)',cases=receipts,acceptance='DEPENDENCY_SENSITIVITY_MEASURED; HISTORICAL_FORMAL_DENOMINATOR_GATE_OPEN')
p=OUT/'A4_B2_RPS_SENSITIVITY.json';tmp=p.with_suffix('.tmp');tmp.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode());os.replace(tmp,p)
print('RPS_CASES',len(cases),'RANK_DELTA_ROWS',sum(r['rank_changed_count'] for r in receipts))

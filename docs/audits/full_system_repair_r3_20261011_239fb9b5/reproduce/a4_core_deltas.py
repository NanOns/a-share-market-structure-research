from pathlib import Path
import sys,json,gzip,os,hashlib,collections,zipfile,struct,time
from dataclasses import asdict
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from v4.factors.core import Bar,Observation,compute_core
receipt=json.loads((OUT/'A4_CANDIDATE_RECOMPUTE.json').read_bytes());wanted={r['security_id'] for r in receipt['deltas']}
head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes());dayrec=json.loads((ROOT/head['day_receipt']['path']).read_bytes());replay=json.loads((ROOT/dayrec['numeric_core_oracle']['path']).read_bytes());owner=replay['owners'][-1]
def read_wanted(path):
    rows={}
    with gzip.open(path,'rt',encoding='utf8') as f:
        for line in f:
            row=json.loads(line)
            if row['security_id'] in wanted:rows[row['security_id']]=row
    return rows
old=read_wanted(ROOT/owner['history']['path']);new=read_wanted(BASE/'candidate_v0_3_history.jsonl.gz')
package=ROOT/owner['sources']['package']['path']
with zipfile.ZipFile(package) as z:
    name=next(n for n in z.namelist() if Path(n).name.lower()=='sh000001.day')
    sessions=sorted({str(r[0])[:4]+'-'+str(r[0])[4:6]+'-'+str(r[0])[6:] for r in struct.iter_unpack('<IIIIIfII',z.read(name)) if r[0]<=20261009})
def obs(bars):
    rows={b['trade_date']:b for b in bars};result=[]
    for day in sessions:
        if day<bars[0]['trade_date']:continue
        b=rows.get(day);q=b['qfq_ohlc'] if b else None
        # The sensitivity experiment never infers a suspension or PIT quality
        # for missing dates. Both sides share the exact UNKNOWN classifications.
        state='ACTUAL' if q else 'ADJUSTMENT_UNKNOWN' if b else 'UNKNOWN'
        result.append(Observation(day,state,Bar(*q,float(b['amount']),float(b['volume']),'SAME_SENSITIVITY_COORDINATE','SAME_SOURCE') if q else None))
    return result
deltas=[];counts=collections.Counter();current=[];started=time.perf_counter()
for sid in sorted(wanted):
    before=obs(old[sid]['bars']);after=obs(new[sid]['bars']);first=min(r['trade_date'] for r in receipt['deltas'] if r['security_id']==sid)
    for day in sessions:
        if day<first:continue
        a=compute_core(before,sid,asof=day);b=compute_core(after,sid,asof=day)
        changed=[]
        for field in a:
            counts['compared_fields']+=1
            left=(a[field].value,a[field].quality_state,a[field].unknown_reason)
            right=(b[field].value,b[field].quality_state,b[field].unknown_reason)
            if left!=right:
                changed.append(field);deltas.append(dict(security_id=sid,day=day,field=field,old=dict(value=left[0],quality=left[1],reason=left[2]),candidate=dict(value=right[0],quality=right[1],reason=right[2])))
        counts['security_dates']+=1
        if day in head['published_sessions']:current.append(dict(security_id=sid,day=day,field_count=len(a),changed_fields=changed))
    print('CORE_SENSITIVITY',sid,len(deltas),flush=True)
p=OUT/'A4_B2_CORE_SENSITIVITY.json';tmp=p.with_suffix('.tmp');tmp.write_bytes((json.dumps(dict(contract_id='EXACT_QFQ_CORE_SENSITIVITY_R3',scope='All compute_core fields for seven changed-stock histories at every native session from first change to cutoff; missing sessions UNKNOWN on both sides',current_five_dates=current,counts=dict(counts),changed_fields=dict(collections.Counter(r['field'] for r in deltas)),deltas=deltas,unchanged_stock_price_proof='Every other stock candidate QFQ cell byte-value parity; full recompute receipt',formal_producer_consumer_admission=False,legal_prior_replay=False,acceptance='SENSITIVITY_MEASUREMENT_ONLY; full Profile/Structure/D0D1D2/Forward consumers retain separate source and permission gates',seconds=time.perf_counter()-started),ensure_ascii=False,indent=2)+'\n').encode());os.replace(tmp,p)
print('CORE_DONE',dict(counts),len(deltas),flush=True)

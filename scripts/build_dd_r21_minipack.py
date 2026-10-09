"""Extract bounded frozen samples; never run a producer or download a source."""
from pathlib import Path
import gzip,hashlib,json,sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.operational_daily_storage_v1 import atomic_json
OUT=ROOT/'docs/evidence/dynamic_daily_r2_20261009/minipack'
SEED='V4-DD-R2.1-20261009-SHA256-PREFROZEN'

def load(path):return json.loads(Path(path).read_bytes())
def rows(binding):
    p=Path(binding['path']);p=p if p.is_absolute() else ROOT/p
    with gzip.open(p,'rt',encoding='utf8') as f:
        for line in f:yield json.loads(line)
def write(name,value):atomic_json(ROOT,OUT/name,value)
def checked(binding):
    p=Path(binding['path']);p=p if p.is_absolute() else ROOT/p
    digest=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
    if digest!=binding['sha256']:raise ValueError('FROZEN_BINDING_MISMATCH:'+str(p))
    return p

def main():
    head=load(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');local=[];cases=[]
    for day in ['2026-10-08','2026-10-09']:
        owners=head['owners'][day];life=load(checked(owners['lifecycle']))
        identity={r['security_id']:r for r in load(checked(life['identity']))['rows']}
        pool=sorted(life['active_security_ids']);observations={r['security_id']:r for r in life['source_rows']}
        ordered=sorted(pool,key=lambda sid:hashlib.sha256((SEED+'|'+day+'|'+sid).encode()).hexdigest())
        random=ordered[:25];edges=[]
        for board in ['SH_MAIN','SZ_MAIN','CHINEXT','STAR']:
            pick=next((s for s in ordered if identity.get(s,{}).get('board_scope')==board and s not in random+edges),None)
            if pick:edges.append(pick)
        edges+= [s for s in ordered if observations.get(s,{}).get('status')=='SUSPENDED' and s not in random+edges][:4]
        chosen=random+edges
        # Freeze names before opening any measured factor/history/period values.
        write('sampling/'+day+'.json',dict(seed=SEED,rule='ascending SHA256(seed|trade_date|security_id)',
            accepted_pool=pool,seeded_random_sample=random,mandatory_edge_cases=edges,
            identity=[dict(security_id=s,board_scope=identity.get(s,{}).get('board_scope'),source_security_key=identity.get(s,{}).get('source_security_key'),status=observations.get(s,{}).get('status')) for s in chosen],
            stratification_gaps=['event/no-event, anomalous price/volume, code-lineage not guaranteed by pre-value strata; no population claim']))
        core={r['security_id']:r for r in rows(owners['core'])}
        replay=load(Path(owners['core']['path']).parent.parent.parent/'CORE_REPLAY.json')
        owner=next(r for r in replay['owners'] if r['trade_date']==day)
        history_binding=owner['history'];checked(history_binding)
        history={r['security_id']:r['bars'] for r in rows(history_binding) if r['security_id'] in chosen}
        wanted=['ma20','atr20','amount_ratio20','volume_ratio20']
        samples=[]
        for sid in chosen:
            fields=core[sid]['fields'];start=min((fields[k]['window_start_trade_date'] for k in wanted if fields[k]['window_start_trade_date']),default=day)
            bars=[b for b in history[sid] if start<=b['trade_date']<=day]
            samples.append(dict(security_id=sid,bars=bars,status=observations.get(sid,{}).get('status'),
                expected={k:{z:fields[k][z] for z in ('value','quality_state','unknown_reason','window_start_trade_date','window_end_trade_date')} for k in wanted},
                source_history=history_binding,scope='frozen normalized daily RAW/QFQ inputs; affine/event origin NOT_VERIFIABLE'))
        cohort=[dict(security_id=s,ret5=core[s]['fields']['ret5']['value'],ret20=core[s]['fields']['ret20']['value'],
            rps5=core[s]['fields']['rps5']['value'],rps20=core[s]['fields']['rps20']['value']) for s in pool]
        sector_rows=sorted(rows(owners['sector']),key=lambda r:(len(r['member_ids']),r['sector_id']))[:3]
        sectors=[]
        for sector in sector_rows:
            ids=sector['member_ids'];sectors.append(dict(sector_id=sector['sector_id'],member_ids=ids,
                contributions=[dict(security_id=s,ret1=core[s]['fields']['ret1']['value']) for s in ids],
                expected={k:sector['fields'][k]['value'] for k in ('sector_rs1','breadth_ret1')},
                scope='complete selected-sector ret1 contribution denominator; other Native fields and LOO state NOT_VERIFIABLE'))
        write('numerical/'+day+'.json',dict(trade_date=day,core=samples,cohort=cohort,sectors=sectors,
            market_scope='NOT_VERIFIABLE: complete market path/limit/common endpoint chain omitted',
            rps_scope='full ranking vector and ties only; antecedent all-cohort returns NOT_VERIFIABLE'))
        period_bindings={k:owners.get(k) for k in ('period_raw','period_adjusted')}
        if day=='2026-10-08':
            for k in period_bindings:
                name='PERIOD_RAW.jsonl.gz' if k=='period_raw' else 'PERIOD_ADJUSTED.jsonl.gz'
                p=ROOT/'docs/evidence/dynamic_daily_20261009/periods'/name
                period_bindings[k]=dict(path=str(p),sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest())
        for domain,binding in period_bindings.items():
            for period in rows(binding):
                if period['security_id'] not in chosen:continue
                sid=period['security_id'];kind=period['period_type'];key=period['period_key']
                from datetime import date
                def pkey(d):
                    y,w,_=date.fromisoformat(d).isocalendar()
                    return d[:7] if kind=='MONTHLY' else f'{y}-W{w:02d}'
                bars=[b for b in history[sid] if b['trade_date']<=day and pkey(b['trade_date'])==key]
                if not bars and period.get('actual_count',0):continue
                cases.append(dict(trade_date=day,evidence_kind='SOURCE_RECEIPT_REPLAY',domain=domain,
                    expected=period,bars=bars,source_history=history_binding,source_period=binding,
                    scope='OHLCV/amount over frozen as-of daily inputs; source adjustment lineage NOT_VERIFIABLE'))
        for binding in [owners['core'],history_binding,*period_bindings.values(),*owner['sources'].values()]:
            if not isinstance(binding,dict) or 'path' not in binding:continue
            p=Path(binding['path']);p=p if p.is_absolute() else ROOT/p
            if p.is_file():local.append(dict(path=str(p),bytes=p.stat().st_size,sha256=binding.get('sha256'),reason='LOCAL_ONLY_FULL_SOURCE_OR_OWNER; never uploaded'))
    write('periods/PERIOD_ORACLE_CASES.json',cases)
    write('LOCAL_ONLY_MANIFEST.json',local)
    amount=ROOT/'data/v4/dynamic_daily_owners/2026-10-09/6c04ca70243fb34e33adef9e472fa229fab57aa8968a1b93db70d72105021917/AMOUNT_CROSS_SOURCE_AUDIT.json'
    a=load(amount);diff=a['differences'];deltas=[float(r['native_amount'])-float(r['baostock_amount']) for r in diff]
    ranked=sorted(diff,key=lambda r:float(r['native_amount'])-float(r['baostock_amount']))
    samples=[ranked[round(i*(len(ranked)-1)/14)] for i in range(15)]
    write('amount/DD_A05.json',dict(trade_date='2026-10-09',reported_count=len(diff),min_delta=min(deltas),max_delta=max(deltas),
        negative_count=sum(v<0 for v in deltas),positive_count=sum(v>0 for v in deltas),representative_samples=samples,
        acceptance='OPEN',native_primary_replaced=False,origin_path=str(amount)))
    write('MANIFEST.json',dict(contract='V4-DD-EXTERNAL-REMEDIATION-R2.1',generated_at=datetime.now(timezone.utc).isoformat(),
        T0=['2026-10-08','2026-10-09'],source_head_sha256=hashlib.sha256((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()).hexdigest(),
        scope='independent formulas over bounded frozen inputs; external signoff NOT_GRANTED',full_owner_or_raw_zip_included=False))
    print(json.dumps(dict(sample_counts=[33,33],period_cases=len(cases),output=str(OUT))))

if __name__=='__main__':main()

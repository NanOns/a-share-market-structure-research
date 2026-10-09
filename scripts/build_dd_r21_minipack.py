"""Extract bounded frozen samples; never run a producer or download a source."""
from pathlib import Path
import gzip,hashlib,json,sys
from collections import defaultdict
from statistics import median
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from tdx.gbbq_reader import read_gbbq
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
    old_cases=load(OUT/'periods/PERIOD_ORACLE_CASES.json') if (OUT/'periods/PERIOD_ORACLE_CASES.json').is_file() else []
    for day in ['2026-10-08','2026-10-09']:
        owners=head['owners'][day];life=load(checked(owners['lifecycle']))
        identity_document=load(checked(life['identity']))
        identity={r['security_id']:r for r in identity_document['rows']}
        pool=sorted(life['active_security_ids']);observations={r['security_id']:r for r in life['source_rows']}
        ordered=sorted(pool,key=lambda sid:hashlib.sha256((SEED+'|'+day+'|'+sid).encode()).hexdigest())
        replay=load(Path(owners['core']['path']).parent.parent.parent/'CORE_REPLAY.json')
        owner=next(r for r in replay['owners'] if r['trade_date']==day)
        history_binding=owner['history'];checked(history_binding)
        events=defaultdict(list)
        for event in read_gbbq(checked(owner['sources']['gbbq'])):
            if event.category==1 and event.event_date<=int(day.replace('-','')):events[event.security_id.upper()].append(event)
        # Eligibility is classified from source history and identity facts only.
        # No measured Core/Profile/period expected values are opened before freeze.
        eligibility={};classification={}
        for row in rows(history_binding):
            sid=row['security_id']
            if sid not in identity:continue
            bars=[b for b in row['bars'] if b['trade_date']<=day];window=bars[-21:]
            start=window[0]['trade_date'] if window else day
            code=identity[sid]['source_security_key'].upper()
            eventful=any(int(start.replace('-',''))<e.event_date<=int(day.replace('-','')) for e in events[code])
            previous=[b['volume'] for b in window[:-1]]
            ratio=window[-1]['volume']/median(previous) if previous and median(previous)>0 else None
            classification[sid]=dict(source_window_start=start,actual_bars_available=len(bars),event_in_window=eventful,volume_median_ratio=ratio)
            eligibility[sid]=dict(event=eventful,no_event=not eventful,anomalous_volume=ratio is not None and (ratio>=3 or ratio<=.2),window_boundary=0<len(bars)<=21)
        boundary_codes={e['source_security_key'].upper() for e in identity_document.get('boundary_events',[])}
        strata={**{board:[s for s in ordered if identity[s].get('board_scope')==board] for board in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR')},
            'suspended':[s for s in ordered if observations.get(s,{}).get('status')=='SUSPENDED'],
            **{name:[s for s in ordered if eligibility.get(s,{}).get(name)] for name in ('event','no_event','anomalous_volume','window_boundary')},
            'identity_boundary':[s for s in ordered if identity[s]['source_security_key'].upper() in boundary_codes]}
        random=ordered[:25];edges=[];strata_picks={};gaps=[]
        for name,candidates in strata.items():
            pick=next((s for s in candidates if s not in random+edges),None)
            if pick:edges.append(pick);strata_picks[name]=pick
            elif candidates:strata_picks[name]=next(s for s in random+edges if s in candidates)
            else:gaps.append(dict(stratum=name,reason='NO_LEGAL_ACCEPTED_SOURCE_SAMPLE',eligible_count=0))
        chosen=random+edges
        prior=OUT/'sampling'/f'{day}.json';archive=OUT/'sampling/original_v1'/f'{day}.json'
        if prior.is_file() and not archive.is_file():write('sampling/original_v1/'+day+'.json',load(prior))
        # This explicitly versioned continuation replaces only the edge strata.
        write('sampling/'+day+'.json',dict(version='2.0.0',seed=SEED,rule='ascending SHA256(seed|trade_date|security_id)',
            accepted_pool=pool,seeded_random_sample=random,mandatory_edge_cases=edges,
            selection_sequence=list(strata),strata_candidates=strata,strata_picks=strata_picks,
            classification_policy='source history only: category1 action inside last21 actual bars; median prior-volume ratio >=3 or <=0.2; <=21 actual bars; dated identity boundary',
            classification=[dict(security_id=s,**classification.get(s,{})) for s in chosen],
            source_history=history_binding,source_actions=owner['sources']['gbbq'],source_identity=life['identity'],
            identity=[dict(security_id=s,board_scope=identity.get(s,{}).get('board_scope'),source_security_key=identity.get(s,{}).get('source_security_key'),status=observations.get(s,{}).get('status')) for s in chosen],
            stratification_gaps=gaps,identity_scope='dated listing boundary; no active accepted code-change relation proved',measured_values_read_after_freeze=True))
        core={r['security_id']:r for r in rows(owners['core'])}
        history={r['security_id']:r['bars'] for r in rows(history_binding) if r['security_id'] in chosen}
        wanted=['ma20','atr20','amount_ratio20','volume_ratio20']
        samples=[]
        for sid in chosen:
            fields=core[sid]['fields'];start=min((fields[k]['window_start_trade_date'] for k in wanted if fields[k]['window_start_trade_date']),default=day)
            bars=[b for b in history[sid] if start<=b['trade_date']<=day]
            samples.append(dict(security_id=sid,bars=bars,status=observations.get(sid,{}).get('status'),
                expected={k:fields[k] for k in wanted},source_core=owners['core'],source_revision=owner['source_digest'],
                adjustment_events=[e.as_dict() for e in events[identity[sid]['source_security_key'].upper()] if int(start.replace('-',''))<e.event_date<=int(day.replace('-',''))],
                source_actions=owner['sources']['gbbq'],formula_contract='CORE_FACTOR_V1 / tdx-affine-qfq-v0.2',T0=day,
                source_history=history_binding,scope='frozen normalized daily RAW/QFQ inputs and category1 event parameters; raw ZIP antecedent remains local only'))
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
            formula_catalog=dict(ma20=dict(formula='mean last 20 valid actual QFQ closes',unit='CNY',contract='CORE_FACTOR_V1'),atr20=dict(formula='mean 20 true ranges from 21 valid actual QFQ bars',unit='CNY',contract='CORE_FACTOR_V1'),amount_ratio20=dict(formula='current native amount / mean prior 20 actual native amounts',unit='ratio',contract='CORE_FACTOR_V1'),volume_ratio20=dict(formula='current native volume / mean prior 20 actual native volumes',unit='ratio',contract='CORE_FACTOR_V1'),null_policy='formal quality_state and unknown_reason retained; incomplete antecedents NOT_VERIFIABLE',comparison=dict(rel_tol=1e-10,abs_tol=1e-10)),
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
                    algorithm_contract_id='V4_02_FORMAL_RAW_QFQ_PERIODS_V1',window_identity=period['source_daily_digest'],source_revision=history_binding['sha256'],
                    scope='OHLCV/amount over frozen as-of daily inputs; source adjustment lineage NOT_VERIFIABLE'))
        for binding in [owners['core'],history_binding,*period_bindings.values(),*owner['sources'].values()]:
            if not isinstance(binding,dict) or 'path' not in binding:continue
            p=Path(binding['path']);p=p if p.is_absolute() else ROOT/p
            if p.is_file():local.append(dict(path=str(p),bytes=p.stat().st_size,sha256=binding.get('sha256'),reason='LOCAL_ONLY_FULL_SOURCE_OR_OWNER; never uploaded'))
    cases.extend(c for c in old_cases if c.get('evidence_kind')=='FIXTURE')
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
    print(json.dumps(dict(sample_counts=[len(load(OUT/'sampling'/f'{d}.json')['seeded_random_sample'])+len(load(OUT/'sampling'/f'{d}.json')['mandatory_edge_cases']) for d in ('2026-10-08','2026-10-09')],period_cases=len(cases),output=str(OUT))))

if __name__=='__main__':main()

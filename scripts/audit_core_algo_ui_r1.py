"""Independent arithmetic on bounded frozen inputs; no business calculator imports."""
from pathlib import Path
from collections import Counter
from statistics import median
from datetime import date
import gzip, hashlib, json, os, zipfile, sqlite3

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/core_algo_ui_r1_20261010'

def load(path):
    with (gzip.open(path, 'rt', encoding='utf8') if path.suffix == '.gz' else path.open(encoding='utf8')) as f:
        return [json.loads(s) for s in f if s.strip()] if '.jsonl' in path.name else json.load(f)

def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(tmp, path)

def verify(pack):
    checks = []
    def check(domain, identity, field, expected, actual):
        delta = actual - expected if isinstance(actual, (int, float)) and isinstance(expected, (int, float)) else None
        checks.append(dict(domain=domain, identity=identity, field=field, expected=expected, actual=actual,
                           delta=delta, passed=abs(delta) < 1e-8 if delta is not None else expected == actual))
    for row in pack['stocks']:
        for endpoint in ('current', 'prior'):
            for field, cell in row[endpoint].items():
                if cell['value'] is None: continue
                bars = [b for b in row['bars'] if cell['window_start_trade_date'] <= b['trade_date'] <= cell['window_end_trade_date']]
                prices = [b['qfq_ohlc'] for b in bars]
                n = int(''.join(c for c in field if c.isdigit()))
                if field.startswith('ma'): expected = sum(p[3] for p in prices) / n
                elif field.startswith('atr'): expected = sum(max(b[1]-b[2], abs(b[1]-a[3]), abs(b[2]-a[3])) for a,b in zip(prices, prices[1:])) / n
                elif field.startswith('ret'): expected = prices[-1][3] / prices[0][3] - 1
                elif field.startswith('prior_high'): expected = max(p[1] for p in prices)
                elif field.startswith('prior_low'): expected = min(p[2] for p in prices)
                else:
                    key = 'volume' if field.startswith('volume') else 'amount'
                    expected = bars[-1][key] / (sum(b[key] for b in bars[:-1]) / n)
                check('STOCK', row['security_id'], endpoint+'.'+field, expected, cell['value'])
        for period in row['periods']:
            group = [b for b in row['bars'] if period.get('first_source_date') and period['first_source_date'] <= b['trade_date'] <= period['max_source_date']]
            if not group:
                check('PERIOD', row['security_id'], 'no_actual_bars', 0, period['actual_count'])
                continue
            ps = [b[period['basis']] for b in group]
            expected = dict(open=ps[0][0], high=max(p[1] for p in ps), low=min(p[2] for p in ps), close=ps[-1][3],
                            volume=sum(b['volume'] for b in group), amount=sum(b['amount'] for b in group))
            for field, value in expected.items(): check('PERIOD', row['security_id'], field, value, float(period[field]) if field in ('open','high','low','close') else period[field])
    for row in pack['sectors']:
        for horizon in (1,5,20):
            known = [v['ret'+str(horizon)] for v in row['member_values'] if v['ret'+str(horizon)] is not None]
            for field, expected in [('sector_rs'+str(horizon), median(known)), ('breadth_ret'+str(horizon), sum(v>0 for v in known)/len(known))]:
                check('SECTOR', row['sector_id'], field, expected, row['actual'][field])
        check('SECTOR', row['sector_id'], 'unique_members', len(row['member_values']), row['member_count'])
    for episode in pack['episodes']:
        ds = [o['trade_date'] for o in episode['observations']]
        check('FOCUS', episode['episode_id'], 'observation_uniqueness', len(ds), len(set(ds)))
        check('FOCUS', episode['episode_id'], 'as_of', True, all(d <= pack['T0'] for d in ds))
        for outcome in episode['outcomes']:
            if outcome['outcome_status'] == 'OBSERVED':
                check('FOCUS', episode['episode_id'], 'maturity', True, bool(outcome['target_trade_date']) and outcome['target_trade_date'] <= pack['T0'])
        for outcome in episode['outcomes']:
            if outcome['outcome_status']!='OBSERVED':continue
            anchor=next(a for a in episode['anchors'] if a['anchor_id']==outcome['anchor_id'])
            bars=[b for b in episode.get('actual_bars',[]) if anchor['trade_date']<=b['trade_date']<=outcome['target_trade_date']]
            if not bars or len({(b['qfq_mul'],b['qfq_add']) for b in bars})!=1:continue
            ps=[b['qfq_ohlc'] for b in bars];base=ps[0][3]
            expected={'return_close':ps[-1][3]/base-1,'mfe':max(p[1] for p in ps)/base-1,'mae':min(p[2] for p in ps)/base-1}
            for k,v in expected.items():check('FOCUS_PATH',episode['episode_id'],k,v,float(outcome['metrics'][k]))
    m=pack.get('market_arithmetic')
    if m:
        ratio=median(m['amount_ratios']);known=m['limits'];prior=m['prior_limits'];common=set(known)&set(prior)
        coverage=len(known)/m['universe_count'];stress=sum(v=='LIMIT_DOWN' for v in known.values())/len(known)
        check('MARKET',pack['T0'],'limit_coverage',coverage,m['actual']['daily_limit_coverage'])
        check('MARKET',pack['T0'],'participation_axis','EXPANDING' if ratio>=1.2 else 'THIN' if ratio<.8 else 'NORMAL',m['actual']['axes']['participation_axis'])
        check('MARKET',pack['T0'],'stress_level',None if coverage<.8 else 'HIGH' if stress>=.05 else 'ELEVATED' if stress>=.01 else 'LOW',m['actual']['axes']['stress_level'])
        a=sum(known[s]=='LIMIT_DOWN' for s in common);b=sum(prior[s]=='LIMIT_DOWN' for s in common)
        check('MARKET',pack['T0'],'stress_change','RISING' if a>b else 'DECLINING' if a<b else 'STABLE',m['actual']['axes']['stress_change'])
    for s in pack.get('signal_invariants',[]):
        if s['state_freshness']=='STALE':check('SIGNAL',s['entity_id'],'stale_fail_closed','UNKNOWN',s['final_eligibility'])
        if s['validity']=='INVALIDATED':check('SIGNAL',s['entity_id'],'invalidation','FALSE',s['final_eligibility'])
        if s['final_eligibility']=='TRUE':
            check('SIGNAL',s['entity_id'],'fresh_eligible','FRESH',s['state_freshness'])
            check('SIGNAL',s['entity_id'],'valid_eligible','VALID',s['validity'])
        check('SIGNAL',s['entity_id'],'no_future_available',True,all(p.get('system_available_at') is None or p['system_available_at']<=s['cutoff'] for p in s['input_provenance'].values()))
    for row in pack['market_limits']:
        expected = 'SUSPENDED' if row['close'] is None and row['limit_state']=='SUSPENDED' else 'UNKNOWN' if not row['rule_verified'] else row['limit_state']
        if row['close'] is not None and row['rule_verified'] and row['limit_up_price'] and row['limit_down_price']:
            expected = 'LIMIT_UP' if abs(row['close']-float(row['limit_up_price']))<1e-6 else 'LIMIT_DOWN' if abs(row['close']-float(row['limit_down_price']))<1e-6 else 'NOT_LIMIT'
        check('MARKET', row['security_id'], 'daily_limit_state', expected, row['limit_state'])
    return dict(contract_id='CORE_ALGO_UI_INDEPENDENT_ORACLE_R1', checks=len(checks), errors=[c for c in checks if not c['passed']], results=checks,
                acceptance='ALGORITHM_SCOPED_PASS' if all(c['passed'] for c in checks) else 'FAIL', external_acceptance='NOT_GRANTED')

def main():
    head = load(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'); day=head['accepted_trade_date']; refs=head['owners'][day]
    folder=(ROOT/head['day_receipt']['path']).parent
    replay=load(folder/'owner_v3/CORE_REPLAY.json'); owner=next(o for o in replay['owners'] if o['trade_date']==day)
    bindings={k:owner[k] for k in ('history','core','prior_core','raw')}
    bindings.update({k:refs[k] for k in ('sector','forward','period_raw','period_adjusted','market')})
    for ref in bindings.values(): assert sha(ROOT/ref['path']) == ref['sha256']
    cores={x['security_id']:x for x in load(ROOT/owner['core']['path'])}; priors={x['security_id']:x for x in load(ROOT/owner['prior_core']['path'])}
    raw={x['security_id']:x for x in load(ROOT/owner['raw']['path'])}
    ranked=sorted(cores, key=lambda s:(cores[s]['fields']['ret20']['value'] is None,cores[s]['fields']['ret20']['value'] or 0,s))
    chosen=set(ranked[:6]+ranked[-6:]+ranked[len(ranked)//2:len(ranked)//2+6])
    chosen.update(s for s in cores if s not in raw)
    chosen=set(sorted(chosen)[:30]); fields=['ma20','atr20','ret1','ret5','ret20','volume_ratio20','amount_ratio20','prior_high20','prior_low20']
    periods={}
    for name,basis in [('period_raw','raw_ohlc'),('period_adjusted','qfq_ohlc')]:
        for p in load(ROOT/refs[name]['path']):
            if p['security_id'] in chosen:periods.setdefault(p['security_id'],[]).append(dict(p,basis=basis))
    specimens=[]
    with gzip.open(ROOT/owner['history']['path'],'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line); sid=row['security_id']
            if sid not in chosen:continue
            cells={ep:{k:source.get('fields',{}).get(k,{'value':None}) for k in fields} for ep,source in [('current',cores[sid]),('prior',priors[sid])]}
            start=min([c['window_start_trade_date'] for cs in cells.values() for c in cs.values() if c.get('window_start_trade_date')]+[day[:7]+'-01'])
            specimens.append(dict(security_id=sid,category='SUSPENDED_NO_BAR' if sid not in raw else 'SHORT_HISTORY' if len(row['bars'])<21 else 'UP' if (cores[sid]['fields']['ret20']['value'] or 0)>0 else 'DOWN_OR_FLAT',bars=[b for b in row['bars'] if start<=b['trade_date']<=day],periods=periods.get(sid,[]),**cells))
    sectors=load(ROOT/refs['sector']['path']); strong=sorted(sectors,key=lambda s:s['fields']['sector_rs5']['value'] or 0)
    ids={'INDUSTRY:T0706','THEME:880904',strong[0]['sector_id'],strong[-1]['sector_id']}; sector_samples=[]
    for s in sectors:
        if s['sector_id'] not in ids:continue
        sector_samples.append(dict(sector_id=s['sector_id'],member_count=len(set(s['member_ids'])),member_values=[dict(security_id=sid,**{f'ret{n}':cores.get(sid,{}).get('fields',{}).get(f'ret{n}',{}).get('value') for n in (1,5,20)}) for sid in sorted(set(s['member_ids']))],actual={k:v['value'] for k,v in s['fields'].items()}))
    forward=load(ROOT/refs['forward']['path']); episodes=forward['episodes'][:2]+[e for e in forward['episodes'] if e.get('end_date')][:1]
    for e in episodes:
        series=e['observations'][0]['native_core_evidence']['source']['series'];bindings['focus_actual_bars']=series
        assert sha(ROOT/series['path'])==series['sha256']
        with sqlite3.connect((ROOT/series['path']).as_uri()+'?mode=ro',uri=True) as db:
            e['actual_bars']=[json.loads(x[0]) for x in db.execute('SELECT payload FROM bars WHERE security=? ORDER BY day',(e['entity_id'],))]
    limits=load(folder/'owner_v3/owners'/day/'daily_price_limits_v1.jsonl.gz')
    market=load(ROOT/refs['market']['path']);prior_limits=load(ROOT/market['input_bindings'][-1]['path'])
    market_arithmetic=dict(universe_count=len(cores),amount_ratios=[r['fields']['amount_ratio20']['value'] for r in cores.values() if r['fields']['amount_ratio20']['value'] is not None],limits={r['security_id']:r['limit_state'] for r in limits if r['limit_state'] in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT')},prior_limits={r['security_id']:r['limit_state'] for r in prior_limits if r['limit_state'] in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT')},actual=market)
    signals=load(ROOT/refs['focus']['path']);signals=signals if isinstance(signals,list) else signals['rows'];sample=[]
    for key in sorted({(r['final_eligibility'],r['state_freshness'],r['validity']) for r in signals}):sample.extend([r for r in signals if (r['final_eligibility'],r['state_freshness'],r['validity'])==key][:3])
    bindings.update(focus=refs['focus'],market_parameters=dict(path='config/v4_03_parameter_registry_v1.json',sha256=sha(ROOT/'config/v4_03_parameter_registry_v1.json')))
    selected=[]
    for state in sorted({x['limit_state'] for x in limits}):
        selected.extend(dict(x,close=raw.get(x['security_id'],{}).get('close')) for x in [r for r in limits if r['limit_state']==state][:3])
    pack=dict(T0=day,head_sha=sha(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),source_bindings=bindings,stocks=specimens,sectors=sector_samples,episodes=episodes,market_limits=selected,strict_PIT=False,unproven=['RAW_QFQ_EVENT_RECURRENCE_PASS_KEEP_R21','FORWARD_VALIDATION_COHORT_OWNER_SOURCE_NOT_PRESENT','NO_REAL_DELISTED_SAMPLE','ROTATION_FULL_REDUCER_NOT_VERIFIABLE'])
    pack.update(market_arithmetic=market_arithmetic,signal_invariants=sample)
    pack['unproven']+=['MARKET_BREADTH_AND_TREND_FULL_PATH_NOT_INDEPENDENTLY_REBUILT','SIGNAL_FULL_DETECTOR_THRESHOLDS_AND_REENTRY_NOT_REBUILT']
    write(OUT/'oracle/INPUT.json',pack); result=verify(pack);write(OUT/'oracle/OUTPUT.json',result)
    print(json.dumps(dict(stocks=len(specimens),sectors=len(sector_samples),episodes=len(episodes),checks=result['checks'],errors=len(result['errors']))))
    return bool(result['errors'])

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        result=verify(load(Path(sys.argv[1])));print(json.dumps(result));raise SystemExit(bool(result['errors']))
    raise SystemExit(main())

"""Independent arithmetic on bounded frozen inputs; no business calculator imports."""
from pathlib import Path
from collections import Counter
from statistics import median
from datetime import date
import gzip, hashlib, json, os, zipfile, sqlite3, math, bisect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/core_algo_ui_r2_20261010'

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

def market_inputs(head, replay, owner, cores, folder):
    """Export endpoint prices, explicit universes and frozen prefix, never a computed expected axis."""
    day=head['accepted_trade_date']
    calendar_path=folder/'owner_v3/FOCUS_CALENDAR.json'
    calendar=load(calendar_path); sessions=calendar['session_dates']
    if sessions and isinstance(sessions[0],dict):sessions=[s['trade_date'] for s in sessions]
    prior3=sessions[sessions.index(day)-3]; prior3_previous=sessions[sessions.index(prior3)-1]
    prefix_path=ROOT/'reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz'
    prefix=[r for r in load(prefix_path) if r['trade_date']<=day]
    bridge_days=sessions[sessions.index(prefix[-1]['trade_date'])+1:sessions.index(day)+1]
    universes={}; sources=[]
    for o in replay['owners']:
        p=ROOT/o['core']['path']; assert sha(p)==o['core']['sha256']
        universes[o['trade_date']]=[r['security_id'] for r in load(p)];sources.append(o['core'])
    first=replay['owners'][0];p=ROOT/first['prior_core']['path']
    prior_rows=load(p);universes[prior_rows[0]['trade_date']]=[r['security_id'] for r in prior_rows]
    sources.append(first['prior_core'])
    needed=set(bridge_days+[sessions[sessions.index(d)-1] for d in bridge_days]+[day,prior3,prior3_previous])
    prices={}
    with gzip.open(ROOT/owner['history']['path'],'rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line);prices[r['security_id']]={b['trade_date']:b['qfq_ohlc'][3] if b.get('qfq_ohlc') else None for b in r['bars'] if b['trade_date'] in needed}
    return dict(prices=prices,universes=universes,prior3=prior3,prior3_previous=prior3_previous,
        bridge_dates=[dict(day=d,previous=sessions[sessions.index(d)-1]) for d in bridge_days],
        prefix_levels=[r['level'] for r in prefix[-25:]],
        policy=load(ROOT/'config/v4_market_path_successor_contract_v1.json'),
        parameters=load(ROOT/'config/v4_03_parameter_set_v1.json')['engineering_candidate_thresholds'],
        regime_threshold=next(p['value'] for p in load(ROOT/'config/v4_04_parameter_set_v1.json')['parameters'] if p['parameter_id']=='V4_04_REGIME_SWITCH_SESSIONS'),
        regime_actual_path=[load(ROOT/head['owners'][d]['market']['path']) for d in head['published_sessions'] if d<=day],
        sources=sources+[dict(path=calendar_path.relative_to(ROOT).as_posix(),sha256=sha(calendar_path)),dict(path=prefix_path.relative_to(ROOT).as_posix(),sha256=sha(prefix_path))])

def verify_market_path(pack, check):
    m=pack['market_arithmetic']; p=pack['market_path'];day=pack['T0'];prices=p['prices'];levels=list(p['prefix_levels'])
    def ret(s,d,previous):
        a,b=prices.get(s,{}).get(d),prices.get(s,{}).get(previous)
        return a/b-1 if a is not None and b is not None and b>0 else None
    for dates,actual in zip(p['bridge_dates'],m['actual']['index_successor_bridge']):
        universe=set(p['universes'][dates['previous']]);values=[v for s in sorted(universe) if (v:=ret(s,dates['day'],dates['previous'])) is not None]
        coverage=len(values)/len(universe) if universe else 0
        change=sum(values)/len(values) if values and coverage>=p['policy']['minimum_bridge_coverage'] else None
        level=levels[-1]*(1+change) if levels[-1] is not None and change is not None else None;levels.append(level)
        for key,value in dict(start_members=len(universe),evaluable=len(values),coverage=coverage,level=level).items():check('MARKET_PATH',dates['day'],key,value,actual[key])
    ma=lambda a:sum(a)/len(a) if len(a)==20 and all(v is not None for v in a) else None
    close,now,old=levels[-1],ma(levels[-20:]),ma(levels[-25:-5])
    trend='UNKNOWN' if None in (close,now,old) else 'STRONG' if close>now>old else 'WEAK' if close<now<old else 'NEUTRAL'
    check('MARKET_PATH',day,'trend_axis',trend,m['actual']['trend']['trend_axis'])
    common=set(p['universes'][day])&set(p['universes'][p['prior3']]);previous=p['bridge_dates'][-1]['previous']
    pairs=[(a,b) for s in sorted(common) if (a:=ret(s,day,previous)) is not None and (b:=ret(s,p['prior3'],p['prior3_previous'])) is not None]
    breadth=sum(int(a>0)-int(b>0) for a,b in pairs)/len(pairs) if pairs else None
    threshold=p['parameters']['market_breadth_axis']
    axis='UNKNOWN' if breadth is None else 'IMPROVING' if breadth>=threshold else 'DETERIORATING' if breadth<=-threshold else 'STABLE'
    check('MARKET_PATH',day,'breadth_common_count',len(common),m['actual']['breadth_common_count'])
    check('MARKET_PATH',day,'breadth_evaluable',len(pairs),m['actual']['breadth_evaluable'])
    check('MARKET_PATH',day,'breadth_axis',axis,m['actual']['axes']['breadth_axis'])
    accepted=pending=None;count=0
    for actual in p['regime_actual_path']:
        a=actual['axes']; t=actual['trend']['trend_axis']
        label='UNKNOWN' if t in (None,'UNKNOWN') or any(a[k] in (None,'UNKNOWN') for k in ('breadth_axis','participation_axis','stress_level','stress_change')) else 'CAPITULATION' if t=='WEAK' and a['stress_level']=='HIGH' else 'RECOVERY_ATTEMPT' if t=='WEAK' and a['breadth_axis']=='IMPROVING' and a['stress_change']=='DECLINING' else 'RISK_ON' if t=='STRONG' and a['breadth_axis']!='DETERIORATING' and a['stress_level']=='LOW' else 'RISK_OFF' if t=='WEAK' or a['stress_level']=='HIGH' else 'NEUTRAL'
        if label=='UNKNOWN':pending=None;count=0;value='UNKNOWN'
        elif label=='CAPITULATION' or label==accepted:accepted=label;pending=None;count=0;value=label
        else:
            count=count+1 if pending==label else 1;pending=label
            if count>=p['regime_threshold']:accepted=label;pending=None;count=0
            value=accepted or 'UNKNOWN'
        for k,v in dict(value=value,candidate=label,last_known=accepted,consecutive_count=count).items():check('MARKET_REGIME',actual['trade_date'],k,v,actual['regime'][k])
    return dict(trend_inputs=dict(close=close,ma20=now,ma20_lag5=old),breadth_value=breadth,equal_weight=True,unknown_excluded=len(common)-len(pairs),regime_scope='Independent reducer on published axes; raw full-path axis rebuild is T0 only')

def rule_state(node, rules, facts, parameters):
    """Independent contract interpreter. Values are explicit four states, never bool coercions."""
    op=node['operator']; na='NOT_APPLICABLE'
    if op=='REF':return rule_state(rules[node['rule_id']],rules,facts,parameters)
    if op=='NOT_APPLICABLE_IF':
        guard=rule_state(node['condition'],rules,facts,parameters)
        return 'UNKNOWN' if guard in ('UNKNOWN',na) else na if guard=='TRUE' else rule_state(node['else'],rules,facts,parameters)
    if op in ('AND','OR'):
        values=[rule_state(n,rules,facts,parameters) for n in node['children']]
        dominant='FALSE' if op=='AND' else 'TRUE'
        if dominant in values:return dominant
        if 'UNKNOWN' in values:return 'UNKNOWN'
        usable=[v for v in values if v!=na]
        return ('TRUE' if op=='AND' else 'FALSE') if usable else (na if op=='AND' else 'UNKNOWN')
    f=facts.get(node['field_id'])
    if not f or f.get('producer')!=node['producer'] or f.get('time_role')!=node['time_role']:return 'UNKNOWN'
    if f.get('quality')==na or f.get('value')==na:return na
    value=f.get('value');rhs=parameters[node['parameter_id']] if 'parameter_id' in node else node['constant']
    if f.get('quality') not in node['quality_requirement'] or value is None or rhs is None:return 'UNKNOWN'
    try:
        result={'EQ':lambda:value==rhs,'IN':lambda:value in rhs,'GT':lambda:value>rhs,'GTE':lambda:value>=rhs,'LT':lambda:value<rhs,'LTE':lambda:value<=rhs}[op]()
        return 'TRUE' if result else 'FALSE'
    except (TypeError,ValueError):return 'UNKNOWN'

def rotation_inputs(head, ids):
    contract=load(ROOT/'config/v4_08_rotation_core_contract_r5.json')
    parameters={p['parameter_id']:p['value'] for p in load(ROOT/'config/v4_08_algorithm_parameter_set_r5.json')['parameters']}
    records=[];sources=[]
    for day in head['published_sessions']:
        ref=head['owners'][day]['rotation'];assert sha(ROOT/ref['path'])==ref['sha256'];sources.append(ref)
        for row in load(ROOT/ref['path']):
            if row['sector_id'] in ids:
                rotation=row['rotation'];compact={k:rotation[k] for k in ('output_state','prior_rotation_state','negative_out_count','reason_codes','episode','predicates')}
                compact['fields']={k:{a:v for a,v in cell.items() if a in ('value','quality','producer','time_role','reason_code')} for k,cell in rotation['fields'].items()}
                compact['native_fields']={'dq5':rotation['native_fields']['dq5']}
                records.append(dict(sector_id=row['sector_id'],trade_date=day,rotation=compact))
    return dict(contract=contract,parameters=parameters,records=records,sources=sources,
        scope='Frozen rule AST and ordered reducer on producer facts; recursive prior/counter checks. Native/retention input generation requires separate numerical proof.')

def verify_rotation(pack, check):
    data=pack['rotation_rules'];contract=data['contract'];prior={}
    for row in data['records']:
        sid=row['sector_id'];r=row['rotation'];facts=r['fields'];identity=sid+'@'+row['trade_date']
        table={name:rule_state(rule,contract['rules'],facts,data['parameters']) for name,rule in contract['rules'].items()}
        for k,v in table.items():check('ROTATION_RULE',identity,k,v,r['predicates'][k]['state'])
        output='NONE'
        for name in contract['ordered_reduction']:
            if name not in table:continue
            if table[name]=='UNKNOWN' and name not in ('ROTATION_EXPANDING','ROTATION_REACCELERATING'):output='UNKNOWN';break
            if table[name]=='TRUE':
                output=contract['fallback_outputs'].get(name,name)
                if output=='PRIOR_ROTATION_STATE':output=facts['prior_rotation_state']['value']
                break
        # Pulse creation has an independent baseline gate after the ordered rule.
        if output=='ROTATION_PULSE' and r['output_state']=='UNKNOWN' and 'PULSE_BASELINE_UNAVAILABLE' in r['reason_codes']:
            check('ROTATION_RULE',identity,'pulse_baseline_gate',False,bool(r.get('episode')))
        else:check('ROTATION_RULE',identity,'ordered_output',output,r['output_state'])
        if sid in prior:
            prev=prior[sid];check('ROTATION_RECURSION',identity,'prior_rotation_state',prev['output_state'],r['prior_rotation_state'])
            dq=facts['dq5']['value'];breadth=facts['breadth_delta1']['value']
            expected=prev['negative_out_count'] if dq is None or breadth is None else prev['negative_out_count']+1 if dq<0 and breadth<0 else 0
            check('ROTATION_RECURSION',identity,'negative_out_count',expected,r['negative_out_count'])
            check('ROTATION_RECURSION',identity,'yesterday_dq5',prev['native_fields']['dq5']['value'],facts['yesterday_dq5']['value'])
        prior[sid]=r

def confirmation_checks(values, parameters):
    b=lambda k:values.get(k) if type(values.get(k)) is bool else None
    inverse=lambda k:None if b(k) is None else not b(k)
    def cmp(k,op,threshold):
        v=values.get(k)
        if type(v) not in (int,float):return None
        return {'gt':lambda:v>threshold,'ge':lambda:v>=threshold,'range':lambda:threshold[0]<=v<=threshold[1]}[op]()
    def tri_and(items):return False if False in items else None if None in items else True
    def tri_or(items):return True if True in items else None if None in items else False
    base={name:b(key) for name,key in [('NORMAL_UNIVERSE','normal_universe'),('ACTUAL_BAR','actual_bar'),('WINDOW_VALID','window_valid'),('LIQ20','liq20'),('INPUT_IDENTITY_COMPATIBLE','input_identity_compatible')]}
    base.update({name:inverse(key) for name,key in [('NOT_STRUCTURE_BREAK','structure_break_v3'),('NOT_EXTENDED','extended_v3'),('NOT_FIRST_DAY_DAMAGE','first_day_damage'),('NOT_SEVERE_DROP','severe_drop')]})
    launch=dict(base,BREAKOUT_V3=b('breakout_v3'),CLOSE_ABOVE_PHC20=cmp('break_margin_close20','gt',0),POSITIVE_RET1=cmp('ret1_adj','gt',0),CLV_GTE_060=cmp('clv','ge',parameters['launch']['clv_gte']),AMR20_GTE_120=cmp('amr20_mean_prior','ge',parameters['launch']['amr20_mean_prior_gte']),NO_INTRADAY_REJECT_HIGH20=inverse('intraday_reject_high20'))
    pullback=dict(base,PULLBACK_EPISODE_CONFIRMED=b('pullback_episode_confirmed'))
    r=parameters['recovery_turn'];r5=tri_and([b('recovery_v3'),b('reclaim_ma5')]);r20=tri_and([b('reclaim_ma20'),cmp('prior5_below_ma20_count','ge',r['prior5_below_ma20_count_gte']),b('ma20_nondeclining_3')])
    recovery=dict(base,R5_OR_R20=tri_or([r5,r20]),POSITIVE_RET1=cmp('ret1_adj','gt',0),CLV_GTE_055=cmp('clv','ge',r['clv_gte']),RPS5_DELTA3_POSITIVE=cmp('rps5_delta3','gt',r['rps5_delta3_gt']),AMR20_GTE_105=cmp('amr20_mean_prior','ge',r['amr20_mean_prior_gte']),CLOSE_GTE_098_MA20=cmp('close_to_ma20','ge',r['close_to_ma20_gte']))
    r=parameters['trend_continue'];trend=dict(base,TREND_BACKGROUND=b('trend_background_v3'),CLOSE_GTE_MA5=cmp('close_to_ma5','ge',1),MA5_GTE_MA20=cmp('ma5_to_ma20','ge',1),SLOPE20_POSITIVE=cmp('slope20','gt',0),RPS20_GTE_070=cmp('rps20','ge',r['rps20_gte']),POSITIVE_RET1=cmp('ret1_adj','gt',0),CLOSE_ABOVE_PRIOR_HIGH=b('close_above_prior_high'),CLV_GTE_055=cmp('clv','ge',r['clv_gte']),AMR20_IN_080_250=cmp('amr20_mean_prior','range',[r['amr20_mean_prior_min'],r['amr20_mean_prior_max']]),CURRENT_WITH_LOO_BREADTH_SUPPORT=b('current_with_loo_breadth_support'))
    return dict(LAUNCH_CONFIRM=launch,STRONG_PULLBACK=pullback,RECOVERY_TURN=recovery,TREND_CONTINUE=trend)

def signal_inputs(head, chosen):
    result=[];sources=[]
    for day in head['published_sessions']:
        folder=(ROOT/head['owners'][day]['core']['path']).parent
        p=folder/'corrected_d0_prewatch.jsonl.gz';sources.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
        d2=load(ROOT/head['owners'][day]['focus']['path']);states={r['entity_id']:r for r in d2['rows'] if r['entity_id'] in chosen}
        profiles={}
        with gzip.open(ROOT/head['owners'][day]['profile']['path'],'rt',encoding='utf8') as f:
            for line in f:
                r=json.loads(line)
                if r['security_id'] in chosen:profiles[r['security_id']]=r['states']
        with gzip.open(p,'rt',encoding='utf8') as f:
            for line in f:
                row=json.loads(line);sid=row['security_id']
                if sid not in chosen:continue
                state=states[sid];provenance=state['input_provenance'];seed=provenance['SEED']['value'];damage=provenance['core_price_damage']['value']
                facts=dict(base_seed_state=seed,mandatory_core_quality_ready='TRUE' if seed!='UNKNOWN' and damage in ('TRUE','FALSE') else 'UNKNOWN',delta3=provenance['delta3']['value'],**{k:profiles[sid][k]['value'] for k in ('compression_state','ma_structure_state','core_extension_risk')})
                result.append(dict(security_id=sid,trade_date=day,target_values=row['target_values'],confirmation=row['confirmation'],prewatch=row['prewatch'],prewatch_facts=facts))
        sources.extend([head['owners'][day]['profile'],head['owners'][day]['focus']])
    return dict(rows=result,confirmation_parameters=load(ROOT/'config/v4_11_confirmation_parameter_set_v1.json')['values'],
        prewatch_ast=load(ROOT/'config/v4_09_machine_ast_v1.json'),prewatch_parameters={p['parameter_id']:p['value'] for p in load(ROOT/'config/v4_09_parameter_set_v1.json')['parameters']},sources=sources)

def verify_signals(pack,check):
    data=pack['signal_rules'];ast=data['prewatch_ast'];parameters=data['prewatch_parameters']
    for row in data['rows']:
        identity=row['security_id']+'@'+row['trade_date'];expected=confirmation_checks(row['target_values'],data['confirmation_parameters']);states={}
        for scenario,checks in expected.items():
            actual=next(e for e in row['confirmation']['scenario_evidence'] if e['scenario']==scenario)
            for k,v in checks.items():check('CONFIRMATION',identity,scenario+'.'+k,v,actual['checks'][k])
            state='UNKNOWN' if None in checks.values() or scenario=='TREND_CONTINUE' else 'TRUE' if all(checks.values()) else 'FALSE';states[scenario]=state
            check('CONFIRMATION',identity,scenario+'.status',state,actual['status'])
        status='TRUE' if 'TRUE' in states.values() else 'UNKNOWN' if 'UNKNOWN' in states.values() else 'FALSE'
        check('CONFIRMATION',identity,'confirmation_status',status,row['confirmation']['confirmation_status'])
        facts=row['prewatch_facts'];seed=facts['base_seed_state'];quality=facts['mandatory_core_quality_ready'];raw='UNKNOWN' if 'UNKNOWN' in (seed,quality) else seed
        check('PREWATCH',identity,'raw_qualification',raw,row['prewatch']['raw_qualification'])
        delta=facts['delta3'];emergence='UNKNOWN'
        if type(delta) in (int,float):emergence=next((r['result'] for r in ast['emergence'] if delta>=parameters[r['parameter']]),'LOW')
        structure='LOW'
        for r in ast['structure']:
            v=facts[r['field']]
            if v in (None,'UNKNOWN'):structure='UNKNOWN';break
            if v==r['equals']:structure=r['result'];break
        for k,v in dict(emergence_axis=emergence,structure_quality_axis=structure,risk_axis=facts['core_extension_risk']).items():check('PREWATCH',identity,k,v,row['prewatch'][k])

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
        members=row['member_values'];actual=row['actual']
        for key,field in [('participation_proxy','amount_ratio20'),('pos60','pos60')]:
            values=[m[field] for m in members if m.get(field) is not None]
            check('SECTOR',row['sector_id'],key,median(values) if values else None,actual[key])
        quotes=[m['ret1'] for m in members if m.get('ret1') is not None]
        check('SECTOR',row['sector_id'],'sector_quote_coverage',len(quotes)/len(members),actual['sector_quote_coverage'])
        widths=[m['close_minus_ma20'] for m in members if m.get('close_minus_ma20') is not None]
        check('SECTOR',row['sector_id'],'ma20_width',sum(v>0 for v in widths)/len(widths) if widths else None,actual['ma20_width'])
        amounts=[m['amount'] for m in members if m.get('amount') is not None and m['amount']>=0]
        for n in (1,3):check('SECTOR',row['sector_id'],'top'+str(n)+'_concentration',sum(sorted(amounts,reverse=True)[:n])/sum(amounts) if sum(amounts)>0 else None,actual['top'+str(n)+'_concentration'])
        seeds=[m['base_seed'] for m in members if type(m.get('base_seed')) is bool];n=len(seeds);k=sum(seeds);p=k/n if n else None;z=pack['sector_parameters']['V4_08_SEED_WILSON_Z']
        lower=(p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n) if n else None
        check('SECTOR',row['sector_id'],'seed_width',p,actual['seed_width'])
        check('SECTOR',row['sector_id'],'base_seed_width_adjusted',lower,actual['base_seed_width_adjusted'])
        strong=sorted(m['security_id'] for m in members if m['rps20']>=80) if all(m.get('rps20') is not None for m in members) else None
        check('SECTOR',row['sector_id'],'strong_member',strong,actual['strong_member'])
    for endpoint,rows in pack.get('rank_endpoints',{}).items():
        for n in (5,20):
            if not any('rps'+str(n) in r.get('produced_fields',[]) for r in rows):
                continue
            values=sorted(r['ret'+str(n)] for r in rows if r['ret'+str(n)] is not None)
            for row in rows:
                value=row['ret'+str(n)]
                rank=None if value is None or len(values)<2 else 100*(bisect.bisect_left(values,value)+.5*(bisect.bisect_right(values,value)-bisect.bisect_left(values,value)-1))/(len(values)-1)
                check('RPS',row['security_id'],endpoint+'.rps'+str(n),rank,row['rps'+str(n)])
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
    market_summary=verify_market_path(pack,check) if pack.get('market_path') else None
    if pack.get('rotation_rules'):verify_rotation(pack,check)
    if pack.get('signal_rules'):verify_signals(pack,check)
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
    return dict(contract_id='CORE_ALGO_UI_INDEPENDENT_ORACLE_R2',market_summary=market_summary, checks=len(checks), errors=[c for c in checks if not c['passed']], results=checks,
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
    signals=load(ROOT/refs['focus']['path']);signals=signals if isinstance(signals,list) else signals['rows']
    signal_map={r['entity_id']:r for r in signals}
    breakout=[]
    with gzip.open(ROOT/refs['profile']['path'],'rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line);distance=r.get('derived_fields',{}).get('dist_high20_atr',{}).get('value')
            if distance is not None and distance<0 and signal_map.get(r['security_id'],{}).get('maturity')!='CONFIRMED':breakout.append(r['security_id'])
    adjustment_events=[]
    with gzip.open(ROOT/owner['history']['path'],'rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line);bars=[b for b in r['bars'] if b['trade_date']>=day[:4]+'-08-01']
            if len({(b.get('qfq_mul'),b.get('qfq_add')) for b in bars})>1:adjustment_events.append(r['security_id'])
    groups={
        'UP':sorted(s for s,c in cores.items() if s in raw and c['fields']['ret20']['value'] is not None and c['fields']['ret20']['value']>0),
        'DOWN':sorted(s for s,c in cores.items() if s in raw and c['fields']['ret20']['value'] is not None and c['fields']['ret20']['value']<0),
        'SUSPENDED_NO_BAR':sorted(set(cores)-set(raw)),
        'SHORT_HISTORY':sorted(s for s,c in cores.items() if s in raw and c['fields']['ma20']['value'] is None),
        'NO_ELIGIBLE_SIGNAL':sorted(s for s in cores if signal_map.get(s,{}).get('final_eligibility')=='FALSE'),
        'BREAKOUT_NOT_CONFIRMED':sorted(breakout),
        'ADJUSTMENT_EVENT':sorted(adjustment_events),
    }
    chosen=set(); selection={}
    for category,quota in [('ADJUSTMENT_EVENT',3),('UP',6),('DOWN',6),('SUSPENDED_NO_BAR',3),('SHORT_HISTORY',3),('NO_ELIGIBLE_SIGNAL',3),('BREAKOUT_NOT_CONFIRMED',3)]:
        selected=[s for s in groups[category] if s not in chosen][:quota]
        chosen.update(selected);selection[category]=dict(available=len(groups[category]),selected=selected,status='REAL_SAMPLE' if selected else 'NO_REAL_SAMPLE')
    fields=['ma20','atr20','ret1','ret5','ret20','volume_ratio20','amount_ratio20','prior_high20','prior_low20']
    periods={}
    for name,basis in [('period_raw','raw_ohlc'),('period_adjusted','qfq_ohlc')]:
        for p in load(ROOT/refs[name]['path']):
            if p['security_id'] in chosen:periods.setdefault(p['security_id'],[]).append(dict(p,basis=basis))
    specimens=[]
    with gzip.open(ROOT/owner['history']['path'],'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line); sid=row['security_id']
            if sid not in chosen:continue
            cells={ep:{k:{a:v for a,v in source.get('fields',{}).get(k,{'value':None}).items() if a in ('value','quality','quality_state','contract_id','parameter_set_id','unit','window_start_trade_date','window_end_trade_date','actual_count','calendar_span','suspended_count','input_digest','output_digest')} for k in fields} for ep,source in [('current',cores[sid]),('prior',priors[sid])]}
            start=min([c['window_start_trade_date'] for cs in cells.values() for c in cs.values() if c.get('window_start_trade_date')]+[day[:7]+'-01'])
            specimens.append(dict(security_id=sid,category='SUSPENDED_NO_BAR' if sid not in raw else 'SHORT_HISTORY' if len(row['bars'])<21 else 'UP' if (cores[sid]['fields']['ret20']['value'] or 0)>0 else 'DOWN_OR_FLAT',bars=[b for b in row['bars'] if start<=b['trade_date']<=day],periods=periods.get(sid,[]),**cells))
    sectors=load(ROOT/refs['sector']['path']); strong=sorted(sectors,key=lambda s:s['fields']['sector_rs5']['value'] or 0)
    seeds={r['security_id']:r['base_seed_state'] for r in load(ROOT/refs['seed']['path'])}
    ids={'INDUSTRY:T0706','THEME:880904',strong[0]['sector_id'],strong[-1]['sector_id']}; sector_samples=[]
    for s in sectors:
        if s['sector_id'] not in ids:continue
        values=[]
        for sid in sorted(set(s['member_ids'])):
            f=cores.get(sid,{}).get('fields',{});ma=f.get('ma20',{}).get('value');close=raw.get(sid,{}).get('close')
            values.append(dict(security_id=sid,**{k:f.get(k,{}).get('value') for k in ('ret1','ret5','ret20','amount_ratio20','pos60','rps20')},amount=raw.get(sid,{}).get('amount'),close_minus_ma20=close-ma if close is not None and ma is not None else None,base_seed={'TRUE':True,'FALSE':False}.get(seeds.get(sid))))
        sector_samples.append(dict(sector_id=s['sector_id'],member_count=len(set(s['member_ids'])),member_values=values,actual={k:v['value'] for k,v in s['fields'].items()}))
    forward_ref=refs['forward'];authority=ROOT/'config/core_product_focus_read_authority_r2.json'
    if authority.exists():
        manifest=load(ROOT/load(authority)['manifest']['path']);forward_ref=manifest['projection'];bindings['focus_projection']=forward_ref
        assert sha(ROOT/forward_ref['path'])==forward_ref['sha256']
    forward=load(ROOT/forward_ref['path']); episodes=forward['episodes'][:2]+[e for e in forward['episodes'] if e.get('end_date')][:1]
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
    pack.update(market_arithmetic=market_arithmetic,signal_invariants=sample,sample_selection=selection)
    pack['market_path']=market_inputs(head,replay,owner,cores,folder)
    pack['rotation_rules']=rotation_inputs(head,ids)
    pack['signal_rules']=signal_inputs(head,chosen)
    pack['sector_parameters']={p['parameter_id']:p['value'] for p in load(ROOT/'config/v4_08_algorithm_parameter_set_r5.json')['parameters']}
    pack['rank_endpoints']={ep:[dict(security_id=sid,produced_fields=[k for k in ('rps5','rps20') if k in r['fields']],**{k:r['fields'].get(k,{}).get('value') for k in ('ret5','ret20','rps5','rps20')}) for sid,r in rows.items()] for ep,rows in [('current',cores),('prior',priors)]}
    pack['unproven'].append('PRIOR_CORE_RPS_FIELDS_NOT_PRODUCED')
    pack['sample_selection']['DELISTED']=dict(status='NO_REAL_SAMPLE',reason='Accepted operational pool contains current eligible securities only')
    pack['unproven']+=['MARKET_PRIOR_SESSIONS_RAW_AXES_NOT_REBUILT_THIS_ROUND','D2_FULL_REDUCER_ALL_REAL_ROW_RECURSION_NOT_REBUILT','D0_RAW_FEATURE_ALL_FORMULAS_NOT_REBUILT']
    write(OUT/'oracle/INPUT.json',pack); result=verify(pack);write(OUT/'oracle/OUTPUT.json',result)
    print(json.dumps(dict(stocks=len(specimens),sectors=len(sector_samples),episodes=len(episodes),checks=result['checks'],errors=len(result['errors']))))
    return bool(result['errors'])

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        result=verify(load(Path(sys.argv[1])));print(json.dumps(result));raise SystemExit(bool(result['errors']))
    raise SystemExit(main())

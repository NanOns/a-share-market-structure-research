"""Standalone reference equations/reducer. Imports only the Python standard library.

Run: python P0_ALG_FULL_RECURSION_ORACLE.py [input.json] [result.json]
Reference authority: frozen V4-10 R1.2 rules and R5 rotation contracts.
This program does not import, execute, or extract any business calculator.
"""
from pathlib import Path
from statistics import mean,median,pstdev,stdev
import json,math,sys,copy

def d0_features(bars):
    n=len(bars)
    def win(count,lag=0,fields=('close',),raw=False):
        a=bars[n-count-lag:n-lag if lag else n] if n>=count+lag else []
        if len(a)!=count:return None
        result=[]
        for b in a:
            q=b.get('raw_ohlc' if raw else 'qfq_ohlc')
            if q is None:return None
            r=dict(zip(('open','high','low','close'),q),amount=b.get('amount'),volume=b.get('volume'))
            if any(type(r.get(k)) not in (int,float) or not math.isfinite(r[k]) or r[k]<=0 for k in fields):return None
            result.append(r)
        return result
    def avg(count,lag=0):
        a=win(count,lag);return mean(r['close'] for r in a) if a else None
    t=win(1,fields=('open','high','low','close','amount','volume'))
    # Formal today also requires positive raw open/close.
    if not win(1,fields=('open','close'),raw=True):t=None
    c,h,l,a,v=(t[0][k] if t else None for k in ('close','high','low','amount','volume'))
    prior=win(20,1,('close','high','amount','volume'))
    pw=win(1,1);pc=pw[0]['close'] if pw else None
    ma5,ma10,ma20=(avg(k) for k in (5,10,20))
    def ratio(a,b):return a/b if a is not None and b is not None and b>0 else None
    def minus1(a):return None if a is None else a-1
    result=dict(ma5=ma5,ma10=ma10,ma20=ma20,bias20=minus1(ratio(c,ma20)),ret1_adj=minus1(ratio(c,pc)),logret1=math.log(c/pc) if c and pc else None,clv=(c-l)/(h-l) if c and h and l and h>l else None)
    p5=win(5,1,('amount',));raw_prior=win(20,1,('close','high','amount','volume'),raw=True)
    raw_today=win(1,fields=('open','high','low','close','amount','volume'),raw=True)
    for name,f in [('mean',mean),('median',median)]:
        result['amr20_'+name+'_prior']=ratio(raw_today[0]['amount'] if raw_today else None,f(r['amount'] for r in raw_prior) if raw_prior else None)
    result['amr5_mean_prior']=ratio(a,mean(r['amount'] for r in p5) if p5 else None)
    result['liq20_amount']=median(r['amount'] for r in raw_prior) if raw_prior else None
    result['vr20_mean_prior']=ratio(v,mean(r['volume'] for r in prior) if prior else None)
    for k in (3,5,20):
        w=win(k+1);result[f'ret{k}_adj']=minus1(ratio(c,w[0]['close'])) if w else None
    for k in (5,20):
        w=win(k,fields=('high','low','close'));lo=min(r['low'] for r in w) if w else None;hi=max(r['high'] for r in w) if w else None
        result[f'pos{k}_hl']=(c-lo)/(hi-lo) if c and hi and lo and hi>lo else None
        w=win(k);result[f'range{k}_close']=max(r['close'] for r in w)/min(r['close'] for r in w)-1 if w else None
    w=win(20,fields=('high','low','close'));result['dist_high20_hl']=c/max(r['high'] for r in w)-1 if c and w else None
    w=win(20);peak=0;dd=[]
    for r in w or []:peak=max(peak,r['close']);dd.append(r['close']/peak-1)
    result['mdd20_close']=min(dd) if dd else None
    for lag,stem in ((0,'sigma20_v3'),(1,'sigma20_prior')):
        w=win(21,lag);rets=[math.log(b['close']/a['close']) for a,b in zip(w,w[1:])] if w else None
        result[stem]=pstdev(rets) if rets else None
        if lag==0:result['vol20_sample']=stdev(rets) if rets else None
    for lag,suffix in ((0,''),(1,'_prior')):
        w=win(20,lag);ys=[math.log(r['close']) for r in w] if w else None
        if ys:
            xm=(len(ys)-1)/2;ym=mean(ys);beta=sum((i-xm)*(y-ym) for i,y in enumerate(ys))/sum((i-xm)**2 for i in range(len(ys)));sst=sum((y-ym)**2 for y in ys)
            result['slope20'+suffix]=beta;result['r2_20'+suffix]=1-sum((y-ym-beta*(i-xm))**2 for i,y in enumerate(ys))/sst if sst else None
        else:result['slope20'+suffix]=result['r2_20'+suffix]=None
    for k in (5,20):
        old=avg(k,1);result['reclaim_ma'+str(k)]=pc<=old and c>avg(k) if all(x is not None for x in (pc,old,c,avg(k))) else None
    result['close_to_ma5']=ratio(c,ma5);result['close_to_ma20']=ratio(c,ma20);result['ma5_to_ma20']=ratio(ma5,ma20)
    result['close_above_prior_high']=c>bars[-2]['qfq_ohlc'][1] if c is not None and len(bars)>1 and bars[-2].get('qfq_ohlc') else None
    sigma=result['sigma20_v3'];result['extension_z20']=math.log(c/ma20)/(sigma*math.sqrt(20)) if c and ma20 and sigma else None
    return result

STATE_FIELDS=('maturity','health','validity','tracking','final_eligibility','state_freshness','downgrade_candidate','downgrade_count','expiry_count','improvement_baseline','market_age','exit_session_index')
def classifier(row,p):
    bars=row['bars'];close=[b.get('qfq_ohlc',[None]*4)[3] if b.get('qfq_ohlc') and b.get('raw_ohlc') else None for b in bars];amount=[b.get('amount') if b.get('raw_ohlc') else None for b in bars];n=len(close)
    def average(k,lag=0):
        a=close[n-k-lag:n-lag if lag else n];return mean(a) if len(a)==k and None not in a else None
    def range_(k):
        a=close[-k:];return max(a)/min(a)-1 if len(a)==k and None not in a and min(a)>0 else None
    def ratio(a,b):return a/b if a is not None and b is not None and b>0 else None
    def cmp(v,op,z):return None if v is None else op(v,z)
    def AND(a):return False if False in a else None if None in a else True
    c=close[-1];old=close[-2] if n>1 else None;m=average(20);m3=average(20,3);m5=average(20,5);m1=average(20,1);f5=average(5);f5p=average(5,1);cm=ratio(c,m);r5,r20=range_(5),range_(20)
    pa=amount[-21:-1];am=mean(pa) if len(pa)==20 and None not in pa else None;med=median(pa) if len(pa)==20 and None not in pa else None;amr=ratio(amount[-1],am);liq=med>=p['risk']['liquidity20_amount_gte'] if med is not None else None
    ph=close[-21:-1];ph=max(ph) if len(ph)==20 and None not in ph else None;dist=ratio(c,ph);dist=None if dist is None else dist-1
    bias=None if cm is None else cm-1;seq=close[-21:];logs=[math.log(b/a) for a,b in zip(seq,seq[1:])] if len(seq)==21 and None not in seq else None;sig=pstdev(logs) if logs else None;z=math.log(cm)/(sig*math.sqrt(20)) if cm and sig else None
    extended=AND([cmp(bias,lambda a,b:a>=b,p['risk']['bias20_gte']),cmp(z,lambda a,b:a>=b,p['risk']['extension_z20_gte'])]);notextended=None if extended is None else not extended
    rps=row['target_values'].get('rps20');delta=row['target_values'].get('rps5_delta3')
    b,s,r,t,k=(p[x] for x in ('BREAKOUT','SETUP','RECOVERY','TREND_BACKGROUND','STRUCTURE_BREAK'))
    checks={
      'BREAKOUT':dict(LIQUIDITY=liq if b['requires_liquidity'] else True,NEW_HIGH20=cmp(dist,lambda a,z:a>z,0),ABOVE_MA20=cmp(cm,lambda a,z:a>=z,1),AMOUNT_EXPANSION=cmp(amr,lambda a,z:a>=z,b['amount_vs_prior20_gte']),NOT_EXTENDED=notextended if b['reject_extended'] else True),
      'SETUP':dict(LIQUIDITY=liq if s['requires_liquidity'] else True,CLOSE_TO_MA20=None if cm is None else s['close_to_ma20_min']<=cm<=s['close_to_ma20_max'],MA20_NONDECLINING_3=m-m3>=s['ma20_delta3_gte'] if m is not None and m3 is not None else None,NEAR_PRIOR_HIGH20=None if dist is None else s['dist_high20_min']<=dist<=s['dist_high20_max'],RANGE_CONTRACTION=r5<=s['range5_to_range20_lte']*r20 if r5 is not None and r20 is not None and r20>0 else None,RPS5_IMPROVING=cmp(delta,lambda a,z:a>=z,s['rps5_delta3_gte']),NOT_EXTENDED=notextended if s['reject_extended'] else True),
      'RECOVERY':dict(LIQUIDITY=liq if r['requires_liquidity'] else True,MA20_NONDECLINING_3=m>=m3 if m is not None and m3 is not None else None,PREVIOUS_BELOW_MA5=old<=f5p if old is not None and f5p is not None else None,CURRENT_ABOVE_MA5=c>f5 if c is not None and f5 is not None else None,ABOVE_MA20_FLOOR=cmp(cm,lambda a,z:a>=z,r['close_to_ma20_gte']),RPS5_IMPROVING=cmp(delta,lambda a,z:a>z,r['rps5_delta3_gt']),AMOUNT_EXPANSION=cmp(amr,lambda a,z:a>=z,r['amount_vs_prior20_gte']),NOT_EXTENDED=notextended if r['reject_extended'] else True),
      'TREND_BACKGROUND':dict(ABOVE_MA20=cmp(cm,lambda a,z:a>=z,1),MA20_RISING_5=m>m5 if m is not None and m5 is not None else None,RPS20=cmp(rps,lambda a,z:a>=z,t['rps20_gte'])),
      'STRUCTURE_BREAK':dict(CURRENT_BELOW_MA20=cmp(cm,lambda a,z:a<z,k['close_to_ma20_lt']),PREVIOUS_BELOW_MA20=cmp(ratio(old,m1),lambda a,z:a<z,k['close_to_ma20_lt']))}
    return checks,extended,{k.lower():AND(list(v.values())) for k,v in checks.items()}

def state_step(f,prior,index,p):
    val=lambda k:f.get(k,{}).get('value','UNKNOWN')
    episode=prior.get('episode_id') if prior else None;old=prior['maturity'] if prior else 'NONE'
    out=dict(maturity=old,health='UNKNOWN',validity='UNKNOWN',tracking=prior['tracking'] if prior else 'CLOSED',final_eligibility='UNKNOWN',state_freshness='STALE',downgrade_candidate=None,downgrade_count=0,expiry_count=prior.get('expiry_count',0) if prior else 0,improvement_baseline=prior.get('improvement_baseline') if prior else None,market_age=prior.get('market_age',0)+index-prior['session_index'] if prior else 0,exit_session_index=prior.get('exit_session_index') if prior else None)
    if episode and val('core_price_damage')=='TRUE':
        out.update(maturity='NONE',health='DAMAGED',validity='INVALIDATED',tracking='FOLLOWUP',final_eligibility='FALSE',state_freshness='FRESH',exit_session_index=index);return out
    # Frozen invalidation is not implemented in this real candidate interface;
    # its UNKNOWN remains a required predicate only once an episode exists.
    unknown=any(val(k)=='UNKNOWN' for k in ('CONFIRMED','PREWATCH','SEED','core_price_damage','suspended')) or bool(episode and val('frozen_invalidation')=='UNKNOWN')
    if unknown or val('suspended')=='TRUE':return out
    stage=next((k for k in ('CONFIRMED','PREWATCH','SEED') if val(k)=='TRUE'),'NONE');rank={'NONE':0,'SEED':1,'PREWATCH':2,'WARM':3,'CONFIRMED':4}
    out.update(validity='VALID',state_freshness='FRESH',final_eligibility='TRUE' if stage!='NONE' else 'FALSE')
    if rank[stage]<rank[old]:
        count=1
        if prior and prior.get('downgrade_candidate')==stage:
            count=prior['downgrade_count']+1 if index==prior['session_index']+1 else prior['downgrade_count'] if index==prior['session_index'] else 1
        out.update(downgrade_candidate=stage,downgrade_count=count)
        if count<p['downgrade_sessions']:stage=old
    out['maturity']=stage;metric=val('delta3');metric=None if metric=='UNKNOWN' else metric;risk=val('risk')
    out['health']='EXHAUSTED' if risk=='EXTREME' else 'UNKNOWN' if metric is None or risk=='UNKNOWN' else 'WEAKENING' if metric < -p['health_deadband_pp'] else 'IMPROVING' if metric > p['health_deadband_pp'] else 'STABLE'
    if stage in ('SEED','PREWATCH') and out['final_eligibility']=='TRUE':
        base=out['improvement_baseline']
        if rank[stage]>rank[old] or base is None or metric is not None and metric-base>=p['expiry_improvement_pp']:out.update(expiry_count=1,improvement_baseline=metric)
        elif not prior or index>prior['session_index']:out['expiry_count']+=1
        if metric is None:out['expiry_count']=prior.get('expiry_count',0) if prior else 0
        if out['expiry_count']>=p['expiry_sessions']:out.update(maturity='NONE',final_eligibility='FALSE',tracking='FOLLOWUP',exit_session_index=index);stage='NONE'
    else:out['expiry_count']=0
    if stage=='NONE':
        out['tracking']='FOLLOWUP' if episode else 'CLOSED'
        if episode and old!='NONE':out['exit_session_index']=index
        if episode and val('followup_complete')=='TRUE':out['tracking']='CLOSED'
    elif out['final_eligibility']=='TRUE':
        exited=prior and prior.get('exit_session_index') is not None and old=='NONE'
        if exited and index<=prior['exit_session_index']:out.update(maturity='NONE',final_eligibility='FALSE',tracking=prior['tracking'])
        elif not episode or exited:out.update(tracking='ACTIVE',exit_session_index=None,market_age=0)
        else:out['tracking']='ACTIVE'
    else:out['tracking']=prior['tracking'] if prior else 'CLOSED'
    return out

def main():
    here=Path(__file__).parent;pack=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else here/'P0_ALG_ORACLE_INPUT.json').read_text(encoding='utf8'));checks=[];traces=[]
    def check(domain,identity,field,expected,actual):
        ok=type(expected) is type(actual) and expected==actual
        if type(expected) in (int,float) and type(actual) in (int,float):ok=math.isclose(expected,actual,abs_tol=1e-10,rel_tol=1e-10)
        checks.append(dict(domain=domain,identity=identity,field=field,expected=expected,actual=actual,passed=ok,delta=actual-expected if type(expected) in (int,float) and type(actual) in (int,float) else None))
    for r in pack['d0']:
        for k,v in d0_features(r['bars']).items():
            if k in r['target_values']:check('D0_RAW',r['security_id']+'@'+r['trade_date'],k,v,r['target_values'][k])
        if 'classifier_parameters' in pack:
            groups,extended,signals=classifier(r,pack['classifier_parameters'])
            for group,fields in groups.items():
                for k,v in fields.items():check('D0_CLASSIFIER',r['security_id']+'@'+r['trade_date'],group+'.'+k,v,r['signals']['checks'][group][k])
            for k,v in dict(signals,extended=extended).items():check('D0_CLASSIFIER',r['security_id']+'@'+r['trade_date'],k,v,r['signals'][k])
    prior={}
    for r in pack['d2']:
        sid=r['entity_id'];prev=prior.get(sid);expected=state_step(r['facts'],prev,r['session_index'],pack['parameters'])
        for k,v in expected.items():check('D2_RECURSION',sid+'@'+r['trade_date'],k,v,r['actual'][k])
        traces.append(dict(entity_id=sid,trade_date=r['trade_date'],prior_state=None if prev is None else {k:prev[k] for k in STATE_FIELDS},new_facts={k:v['value'] for k,v in r['facts'].items()},expected=expected,actual=r['actual'],first_available_scope='RECONSTRUCTED_NOT_AS_RECORDED'))
        prior[sid]=dict(r['actual'],session_index=r['session_index'])
    for s in pack['sectors']:
        cs=list(s['contributions'].values());identity=s['sector_id']+'@'+s['trade_date']
        check('NATIVE',identity,'unique_members',len(set(s['member_ids'])),len(s['member_ids']))
        for n in (1,5):
            known=[r.get('ret'+str(n)) for r in cs if r.get('ret'+str(n)) is not None]
            check('NATIVE',identity,'sector_rs'+str(n),median(known) if known else None,s['fields']['sector_rs'+str(n)]['value'])
            check('NATIVE',identity,'breadth_ret'+str(n),sum(v>0 for v in known)/len(known) if known else None,s['fields']['breadth_ret'+str(n)]['value'])
    native={(s['sector_id'],s['trade_date']):s for s in pack['sectors']};rotprior={}
    def retained(ids,truth):return None if not ids or any(truth.get(m) is None for m in ids) else sum(truth[m] is True for m in ids)/len(ids)
    for r in pack['rotations']:
        sid,date=r['sector_id'],r['trade_date'];v=r['rotation'];prev=r.get('exact_producer_prior') or rotprior.get(sid);f=v['fields'];identity=sid+'@'+date;c=r['contributions'];episode=(prev or {}).get('episode')
        if prev:
            check('ROTATION_RECURSION',identity,'prior_rotation_state',prev['output_state'],v['prior_rotation_state'])
            dq,b=f['dq5']['value'],f['breadth_delta1']['value'];count=prev['negative_out_count'] if dq is None or b is None else prev['negative_out_count']+1 if dq<0 and b<0 else 0
            check('ROTATION_RECURSION',identity,'negative_out_count',count,v['negative_out_count'])
        if episode:
            ids=episode['frozen_basket'];usable={m:c.get(m,{}).get('close') if c.get(m,{}).get('price_basis_id')==episode['price_basis_ids'].get(m) else None for m in ids}
            values=[usable[m]/episode['pulse_baseline'][m]-1 for m in ids if usable[m] is not None and episode['pulse_baseline'].get(m) is not None and episode['pulse_baseline'][m]>0]
            cum=sum(values)/len(ids) if ids and len(values)==len(ids) else None;pulse=episode['pulse_basket_return'];pr=cum/pulse if cum is not None and pulse is not None and pulse>0 else None
            seedtruth={m:c.get(m,{}).get('base_seed') for m in ids};pt={m:None if usable[m] is None or episode['pulse_closes'].get(m) is None else usable[m]>=episode['pulse_closes'][m] for m in ids}
            for k,e in [('basket_cumulative_return',cum),('sector_price_retention_core',pr),('base_seed_retention',retained(episode.get('base_seed_set'),seedtruth)),('breadth_retention',retained(episode.get('breadth_positive_set'),pt))]:check('ROTATION_BASKET',identity,k,e,f[k]['value'])
            age=pack['calendar'].index(date)-pack['calendar'].index(episode['pulse_date']);check('ROTATION_BASKET',identity,'pulse_age_sessions',age,f['pulse_age_sessions']['value'])
        new=v.get('episode')
        if new and new['pulse_date']==date and prev:
            ps=native.get((sid,prev['trade_date']));ids=sorted(set(ps['member_ids'])) if ps else None
            if ids is not None:check('ROTATION_PULSE',identity,'frozen_basket',ids,new['frozen_basket'])
            values=[new['pulse_closes'][m]/new['pulse_baseline'][m]-1 for m in new['frozen_basket']];check('ROTATION_PULSE',identity,'pulse_basket_return',sum(values)/len(values),new['pulse_basket_return'])
        rotprior[sid]=dict(v,trade_date=date)
    current={s['sector_id']:s for s in pack['sectors'] if s['trade_date']==pack['T0']}
    for r in pack['loo']:
        s=current[r['sector_id']];sid=r['security_id'];others={k:v for k,v in s['contributions'].items() if k!=sid};a=r['actual'];identity=sid+'@'+r['sector_id']
        check('LOO',identity,'non_target_member_count',len(others),a['non_target_member_count'])
        for n in (1,5):
            vals=[v.get('ret'+str(n)) for v in others.values() if v.get('ret'+str(n)) is not None];v=s['contributions'].get(sid,{}).get('ret'+str(n));e=v-median(vals) if v is not None and vals else None
            if 'rel_market_'+str(n) in a['relative_substitutions']:check('LOO',identity,'rel_market_'+str(n),e,a['relative_substitutions']['rel_market_'+str(n)])
    # Independent counterfactuals, expressly FIXTURE_ONLY; do not publish them.
    f={k:dict(value='FALSE') for k in ('CONFIRMED','PREWATCH','SEED','core_price_damage','suspended','frozen_invalidation','followup_complete')};f.update(delta3=dict(value=4),risk=dict(value='LOW'));f['CONFIRMED']['value']='TRUE'
    seed=dict(maturity='CONFIRMED',health='STABLE',validity='VALID',tracking='ACTIVE',final_eligibility='TRUE',state_freshness='FRESH',downgrade_candidate=None,downgrade_count=0,expiry_count=0,improvement_baseline=None,market_age=1,exit_session_index=None,episode_id='FIXTURE',session_index=9)
    damaged=copy.deepcopy(f);damaged['core_price_damage']['value']='TRUE';x=state_step(damaged,seed,10,pack['parameters']);check('FIXTURE_ONLY','same_day_conflict','validity','INVALIDATED',x['validity'])
    exited=dict(seed,maturity='NONE',exit_session_index=10,session_index=10,tracking='FOLLOWUP');x=state_step(f,exited,10,pack['parameters']);check('FIXTURE_ONLY','same_day_reentry','final_eligibility','FALSE',x['final_eligibility'])
    f2=copy.deepcopy(f);f2['CONFIRMED']['value']='FALSE';x=state_step(f2,seed,10,pack['parameters']);check('FIXTURE_ONLY','same_facts_prior_stage','maturity','CONFIRMED',x['maturity']);check('FIXTURE_ONLY','same_facts_no_prior','maturity','NONE',state_step(f2,None,10,pack['parameters'])['maturity'])
    check('FIXTURE_ONLY','missing_member_frozen_denominator','retention',None,retained(['a','b'],{'a':True,'b':None}))
    errors=[c for c in checks if not c['passed']];counts={d:sum(c['domain']==d for c in checks) for d in sorted({c['domain'] for c in checks})}
    out=dict(contract=pack['contract'],checks=len(checks),errors=len(errors),counts=counts,differences=errors,results=checks,transition_traces=traces,unproven=['Historical first availability','Full upstream D0 classifier predicates not covered by listed equations','Complete cross-sectional LOO rank/rotation lineage','REAL_REENTRY_NOT_OBSERVED; fixtures are not market events'],acceptance='PASS_SCOPED' if not errors else 'FAIL')
    dest=Path(sys.argv[2] if len(sys.argv)>2 else here/'P0_ALG_ORACLE_RESULT.json');tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(dest)
    print(json.dumps(dict(checks=len(checks),errors=len(errors),counts=counts)));return bool(errors)
if __name__=='__main__':sys.exit(main())

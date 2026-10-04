"""Append-only V4-15 engineering settlement. No provider or trading interfaces."""
import copy
import hashlib
import json
import math
from .v4_current_stage_authority import CurrentStageAuthority

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

HORIZONS=(1,3,5,10,20)

def due_plan(sessions,t0,cutoff):
    index=sessions.index(t0)
    return [{'horizon':n,'due_date':sessions[index+n] if index+n<len(sessions) else None,
             'outcome_status':'PENDING' if index+n>=len(sessions) or sessions[index+n]>cutoff else 'DUE'} for n in HORIZONS]

def percentile(values,value):
    return (sum(x<value for x in values)+(sum(x==value for x in values)-1)/2)/(len(values)-1) if len(values)>1 else 0.5

def freeze_controls(universe,signal,event_count,legacy=None):
    pool=[r for r in universe if r.get('hard_safety') is True]
    delta_pool=[r for r in pool if isinstance(r.get('delta3'),(int,float)) and math.isfinite(r['delta3'])]
    b=sorted(delta_pool,key=lambda r:(-r['delta3'],r['security_id']))[:event_count]
    features=('prior20_mean_amount','vol20','RPS20')
    complete=[r for r in pool if all(isinstance(r.get(k),(int,float)) and math.isfinite(r[k]) for k in features) and r['prior20_mean_amount']>0]
    vals={k:[math.log(r[k]) if k==features[0] else r[k] for r in complete] for k in features}
    def ranks(r):return [percentile(vals[k],math.log(r[k]) if k==features[0] else r[k]) for k in features]
    candidates=[r for r in complete if not r.get('prewatch_final_eligible') and r['security_id']!=signal['security_id']]
    industry=signal.get('primary_industry')
    scope='MATCH_SCOPE_INDUSTRY' if industry else 'MATCH_SCOPE_MARKET'
    if industry:candidates=[r for r in candidates if r.get('primary_industry')==industry]
    ranked=[]
    if signal in complete and len(complete)>=2:
        sr=ranks(signal)
        ranked=sorted([(sum(abs(x-y) for x,y in zip(sr,ranks(r))),r) for r in candidates],key=lambda p:(p[0],p[1]['security_id']))[:3]
    out={'A':{'status':'NOT_AVAILABLE' if legacy is None else 'OBSERVED','control_entity_ids':[] if legacy is None else sorted(legacy)},
         'B':{'control_entity_ids':[r['security_id'] for r in b],'requested_count':event_count,'control_count':len(b),'reason_codes':([] if len(b)==event_count else ['INSUFFICIENT_POOL'])+(['UNKNOWN_DELTA3_EXCLUDED'] if len(delta_pool)!=len(pool) else [])},
         'C':{'control_entity_ids':[r['security_id'] for _,r in ranked],'control_distance':[d for d,_ in ranked],'match_scope':scope,'control_count':len(ranked),'control_feature_snapshot':copy.deepcopy(complete),'reason_codes':[] if signal in complete and len(complete)>=2 else ['UNKNOWN_OR_INSUFFICIENT_RANK_BASIS']}}
    out['assignment_digest']=digest(out)
    return out

def freeze_basket(rows,t0,kind='MARKET'):
    rows=sorted(rows,key=lambda r:r['security_id'])
    if any(not isinstance(r.get('close'),(int,float)) or r['close']<=0 for r in rows):raise ValueError('T0_REFERENCE_UNVERIFIED')
    members=[{'security_id':r['security_id'],'reference':r['close'],'weight':1/len(rows),'fixed_shares':1/len(rows)/r['close'],'adjustment_identity':r.get('adjustment_identity')} for r in rows]
    result={'T0':t0,'kind':kind,'members':members,'quality':'OBSERVED' if rows and (kind!='SECTOR' or len(rows)>=2) else 'UNKNOWN_UNAVAILABLE','constituent_policy':'FIXED_ORIGINAL_WEIGHTS_NO_REWEIGHT'}
    result['benchmark_id']=digest(result)
    return result

def price_path(reference,rows,basis_date):
    """Rows exclude T0. All supplied transforms map to the one endpoint basis."""
    out={'R_N':None,'MFE_N':None,'MAE_N':None,'PATH_MDD_CLOSE_N':None,'evaluation_basis_date':basis_date,'actual_count':0,'reason_codes':[]}
    if not rows:return dict(out,outcome_status='MATURED_DATA_MISSING')
    endpoint=rows[-1]
    for r in [endpoint]:
        if r.get('verified_identity') is not True:return dict(out,outcome_status='IDENTITY_UNKNOWN')
        if r.get('verified_adjustment') is not True or r.get('evaluation_basis_date')!=basis_date:return dict(out,outcome_status='ADJUSTMENT_UNKNOWN')
        coeff=r.get('transform_coefficients',{'alpha':1,'beta':0})
        if not all(isinstance(coeff.get(k),(int,float)) and math.isfinite(coeff[k]) for k in ('alpha','beta')) or coeff['alpha']<=0:return dict(out,outcome_status='ADJUSTMENT_UNKNOWN')
    if endpoint.get('T0_basis_verified') is not True:return dict(out,outcome_status='ADJUSTMENT_UNKNOWN')
    transforms=endpoint.get('T0_transform_coefficients',endpoint.get('transform_coefficients',{'alpha':1,'beta':0}))
    if not endpoint.get('verified_adjustment',False):return dict(out,outcome_status='ADJUSTMENT_UNKNOWN')
    p0=transforms['alpha']*reference+transforms['beta']
    if p0<=0:return dict(out,outcome_status='ADJUSTMENT_UNKNOWN')
    out.update(evaluation_comparison_reference=p0,evaluation_adjustment_identity=endpoint.get('adjustment_identity'),transform_coefficients=transforms,transform_digest=digest(transforms),source_asof=endpoint.get('source_asof'),available_at=endpoint.get('available_at'))
    if endpoint.get('status')=='DELISTED':
        if endpoint.get('terminal_evidence') and endpoint.get('terminal_verified') is True and endpoint.get('terminal_value') is not None:out['R_N']=endpoint['terminal_value']/p0-1
        return dict(out,outcome_status='DELISTED_BEFORE_HORIZON')
    if endpoint.get('status')=='CONFIRMED_SUSPENSION':return dict(out,outcome_status='SUSPENDED_AT_HORIZON')
    if endpoint.get('close') is None:return dict(out,outcome_status='MATURED_DATA_MISSING')
    def value(r,k):
        t=r.get('transform_coefficients',{'alpha':1,'beta':0});return t['alpha']*r[k]+t['beta']
    out['R_N']=value(endpoint,'close')/p0-1
    actual=[r for r in rows if r.get('status')!='CONFIRMED_SUSPENSION']
    out['actual_count']=len(actual)
    if any(r.get(k) is None for r in actual for k in ('close','high','low')) or any(r.get('verified_identity') is not True or r.get('verified_adjustment') is not True or r.get('evaluation_basis_date')!=basis_date for r in actual):
        return dict(out,outcome_status='OBSERVED',path_quality='MATURED_DATA_MISSING',reason_codes=['UNKNOWN_INTERIOR_GAP'])
    high=max([p0]+[value(r,'high') for r in actual]);low=min([p0]+[value(r,'low') for r in actual]);peak=p0;dd=0
    for r in actual:
        close=value(r,'close');peak=max(peak,close);dd=min(dd,close/peak-1)
    out.update(MFE_N=high/p0-1,MAE_N=low/p0-1,PATH_MDD_CLOSE_N=dd,path_quality='OBSERVED' if len(actual)==len(rows) else 'CONFIRMED_INTERIOR_SUSPENSION_OMITTED',outcome_status='OBSERVED')
    return out

def benchmark(basket,rows_by_member,absolute_return,evaluation_basis_date=None):
    contribution=coverage=suspended=delisted=unknown=0;states=[]
    for m in basket['members']:
        r=rows_by_member.get(m['security_id'],{});state='ACTUAL_ENDPOINT'
        if r.get('verified_identity') is not True:state='IDENTITY_UNKNOWN'
        elif r.get('verified_adjustment') is not True or r.get('T0_basis_verified') is not True or (evaluation_basis_date is not None and r.get('evaluation_basis_date')!=evaluation_basis_date):state='ADJUSTMENT_UNKNOWN'
        elif r.get('status')=='DELISTED':state='DELISTED'
        elif r.get('status')=='CONFIRMED_SUSPENSION':state='CONFIRMED_SUSPENSION'
        elif r.get('close') is None:state='DATA_MISSING'
        if state=='ACTUAL_ENDPOINT':
            t=r.get('transform_coefficients',{'alpha':1,'beta':0});t0=r.get('T0_transform_coefficients',t);p0=t0['alpha']*m['reference']+t0['beta'];close=t['alpha']*r['close']+t['beta'];contribution+=m['weight']*close/p0;coverage+=m['weight']
        elif state=='DELISTED' and r.get('terminal_verified') is True and r.get('terminal_evidence') and r.get('terminal_value') is not None:
            t=r.get('T0_transform_coefficients',r.get('transform_coefficients',{'alpha':1,'beta':0}));contribution+=m['weight']*r['terminal_value']/(t['alpha']*m['reference']+t['beta']);coverage+=m['weight'];delisted+=m['weight']
        elif state=='DELISTED':delisted+=m['weight']
        elif state=='CONFIRMED_SUSPENSION':suspended+=m['weight']
        else:unknown+=m['weight']
        states.append({'security_id':m['security_id'],'state':state,'original_weight':m['weight']})
    observed=abs(coverage-1)<1e-12 and basket['quality']!='UNKNOWN_UNAVAILABLE'
    return {'benchmark_id':basket['benchmark_id'],'benchmark_quality':'OBSERVED' if observed else 'PARTIAL_UNVALUED','benchmark_endpoint_coverage':coverage,'benchmark_missing_weight':1-coverage,'benchmark_suspended_weight':suspended,'benchmark_delisted_weight':delisted,'benchmark_unknown_weight':unknown,'observed_contribution':contribution,'return':contribution-1 if observed else None,'relative_return':absolute_return-(contribution-1) if observed and absolute_return is not None else None,'relative_market_return_marked':None,'marked_permission':False,'constituents':states}

class VectorPriceSource:
    evidence_class='ENGINEERING_VECTOR'
    def __init__(self,rows,binding=None):self.rows=copy.deepcopy(rows);self.binding=binding or {'sha256':digest(rows)};self.read_log=[]
    def read(self,security_id,date,basis_date,cutoff):
        self.read_log.append({'security_id':security_id,'trade_date':date,'basis_date':basis_date,'cutoff':cutoff})
        r=copy.deepcopy(self.rows.get(security_id,{}).get(date,{}))
        available=r.get('available_at',date)
        if date>cutoff or available is None or available>cutoff:r={}
        r.setdefault('trade_date',date);r.setdefault('evaluation_basis_date',basis_date)
        return r

class AcceptedPriceSource(VectorPriceSource):
    evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED'
    def __init__(self,authority,binding):
        if not isinstance(authority,CurrentStageAuthority):raise ValueError('CURRENT_V4_14_AUTHORITY_REQUIRED')
        allowed=[]
        def walk(v):
            if isinstance(v,dict):
                if {'path','sha256'}<=v.keys():allowed.append(v)
                else:
                    for x in v.values():walk(x)
            elif isinstance(v,list):
                for x in v:walk(x)
        walk(authority.data)
        if binding not in allowed:raise ValueError('SOURCE_NOT_BOUND_BY_ACCEPTED_DATA_HEAD')
        if binding!=authority.data['component_artifacts']['ADJUSTED_DAILY']:raise ValueError('ACCEPTED_ADJUSTED_DAILY_ONLY')
        raw=authority.read(binding);artifact=json.loads(raw);rows={}
        if artifact['contract_id']!='DM01_ADJUSTED_DAILY_ARTIFACT_R3_3':raise ValueError('ACCEPTED_ADJUSTED_SOURCE_CONTRACT')
        for row in artifact['rows']:
            date=row['trade_date'];ready=row['adjustment_readiness']=='READY'
            # Durable artifact is one dated adjusted snapshot. Cross-date rebasing is
            # not fabricated; identity transforms are admitted only on this basis.
            rows.setdefault(row['security_id'],{})[date]={'trade_date':date,'evaluation_basis_date':date,'close':float(row['close']) if ready else None,'high':float(row['high']) if ready else None,'low':float(row['low']) if ready else None,'verified_identity':row.get('identity_quality')=='R6_2_DATED_ROSTER_OBSERVED','verified_adjustment':ready,'T0_basis_verified':False,'transform_coefficients':{'alpha':1,'beta':0},'adjustment_identity':row['adjustment_source_revision'],'source_asof':date,'available_at':None,'available_at_unknown':True,'knowledge_lineage':row['knowledge_lineage'],'first_available_at_target_proven':False}
        if any(date>authority.data['accepted_trade_date'] for values in rows.values() for date in values):raise ValueError('SOURCE_EXCEEDS_ACCEPTED_DATA_HEAD')
        super().__init__(rows,binding)

class SettlementRuntime:
    def __init__(self,authority,store):
        if not isinstance(authority,CurrentStageAuthority):raise ValueError('CURRENT_V4_14_AUTHORITY_REQUIRED')
        self.authority=authority;self.store=store
    def crossed_control(self,freeze_ref,security_id,trade_date,publication_ref):
        frozen=self.store.read(freeze_ref)
        if trade_date<frozen['T0']:raise ValueError('CONTROL_CROSS_BEFORE_T0')
        assigned={sid for k in ('A','B','C') for sid in frozen['controls'][k]['control_entity_ids']}
        if security_id not in assigned:raise ValueError('CONTROL_NOT_FROZEN_ASSIGNMENT')
        row={'frozen_t0':freeze_ref,'security_id':security_id,'crossed_signal_at':trade_date,'publication':publication_ref,'assignment_digest':frozen['controls']['assignment_digest'],'ITT_RETAINED':True}
        return self.store.append('control_crossings',digest(row),row)
    def competing_outcome(self,freeze_ref,events,report_cutoff):
        frozen=self.store.read(freeze_ref);priority={'INVALIDATED':0,'CONFIRMED':1,'EXPIRED':2}
        eligible=[e for e in events if frozen['T0']<=e['trade_date']<=report_cutoff and e['event'] in priority]
        eligible.sort(key=lambda e:(e['trade_date'],priority[e['event']]))
        first=eligible[0] if eligible else None
        row={'frozen_t0':freeze_ref,'competing_event':first['event'] if first else None,'first_event_trade_date':first['trade_date'] if first else None,'competing_source_publication':first.get('publication') if first else None,'censoring_state':'OBSERVED' if first else 'RIGHT_CENSORED','report_cutoff':report_cutoff,'price_settlement_continues':True}
        return self.store.append('competing_outcomes',digest(row),row)
    def freeze_rotation(self,pulse_date,members,known_at,previous_references):
        sessions=self.authority.sessions;previous=sessions[sessions.index(pulse_date)-1]
        if known_at>=pulse_date or set(previous_references)!=set(members):raise ValueError('ROTATION_FUTURE_MEMBERS_OR_MISSING_REFERENCE')
        basket=freeze_basket([{'security_id':sid,'close':previous_references[sid]} for sid in members],previous,'ROTATION')
        basket.update(pulse_trade_date=pulse_date,pulse_members=sorted(members),known_at=known_at,pulse_reference=previous)
        return self.store.append('rotation_baskets',digest(basket),basket)
    def freeze_t0(self,enrollment_ref,t0_snapshot_ref,event_count=None):
        enrollment=self.store.read(enrollment_ref);snapshot=self.store.read(t0_snapshot_ref);t0=enrollment['T0']
        reconstructed=snapshot.get('evidence_class')=='RECONSTRUCTED_ASOF' and enrollment.get('cohort_namespace') in ('RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED')
        available=snapshot.get('available_at',t0)
        if snapshot['trade_date']!=t0 or snapshot.get('source_asof',t0)>t0 or (not reconstructed and (available is None or available>t0)):raise ValueError('T0_SNAPSHOT_FUTURE_LEAK')
        universe=snapshot['universe'];entity_type=enrollment.get('entity_type','STOCK')
        if entity_type=='SECTOR':
            subject_rows=[r for r in universe if r.get('primary_industry')==enrollment['entity_id'] or enrollment['entity_id'] in r.get('sector_ids',[])]
            signal={'security_id':enrollment['entity_id'],'primary_industry':enrollment['entity_id']}
        else:
            signal=next((r for r in universe if r['security_id']==enrollment['entity_id']),None)
            if signal is None:raise ValueError('T0_SIGNAL_REFERENCE_UNAVAILABLE')
        event_refs=snapshot.get('logical_event_refs',[])
        if event_refs:
            events=[self.store.read(r) for r in event_refs];event_count=len({e['logical_event_id'] for e in events if e.get('entity_type')=='STOCK' and e.get('event_trade_date',e.get('trade_date'))==t0 and e.get('event_type')==enrollment.get('event_type',enrollment.get('signal_type'))})
        elif event_count is None:event_count=1
        eligible=[r for r in universe if r.get('research_eligible') is True];sector=[r for r in eligible if r['security_id']!=signal['security_id'] and signal.get('primary_industry') and r.get('primary_industry')==signal['primary_industry']]
        value={'enrollment':enrollment_ref,'enrollment_id':enrollment['enrollment_id'],'T0':t0,'signal_id':signal['security_id'],'comparison_reference':enrollment['comparison_reference'],'snapshot':t0_snapshot_ref,'market':freeze_basket(eligible,t0),'sector':freeze_basket(sector,t0,'SECTOR'),'controls':freeze_controls(universe,signal,event_count,snapshot.get('legacy')),'authority':self.authority.bindings(),'HISTORICAL_PIT_EFFECTIVENESS':'NOT_GRANTED','production':False,'shadow':False,'focus':False}
        value['entity_type']=entity_type
        if entity_type=='SECTOR':
            value['subject_basket']=freeze_basket(subject_rows,t0,'SECTOR');value['comparison_reference']=1
            value['controls']=freeze_controls([],signal,0,None)
            for key in ('A','B','C'):value['controls'][key]['status']='NOT_APPLICABLE_SECTOR'
        for i,key in enumerate(('market','sector')):
            ids=enrollment.get('benchmark_ids',[digest([enrollment['enrollment_id'],'MARKET']),digest([enrollment['enrollment_id'],'SECTOR'])]);bid=ids[key] if isinstance(ids,dict) else ids[i]
            basket=value[key];basket['constituent_digest']=basket['benchmark_id'];basket['benchmark_id']=bid
        for i,key in enumerate(('A','B','C')):
            ids=enrollment.get('control_assignment_ids',[digest([enrollment['enrollment_id'],k]) for k in ('A','B','C')]);value['controls'][key]['control_assignment_id']=ids[key] if isinstance(ids,dict) else ids[i]
        value['controls'].pop('assignment_digest',None);value['controls']['assignment_digest']=digest(value['controls'])
        return self.store.append('t0_freezes',enrollment['enrollment_id'],value)
    def settle(self,freeze_ref,source,cutoff,horizons=HORIZONS):
        if not isinstance(source,(VectorPriceSource,AcceptedPriceSource)):raise ValueError('NO_RAW_PROVIDER_SOURCE')
        frozen=self.store.read(freeze_ref);t0=frozen['T0'];sessions=self.authority.sessions;start=sessions.index(t0);outputs=[]
        for due in due_plan(sessions,t0,cutoff):
            n=due['horizon']
            if n not in horizons:continue
            self.store.append('due_plans',digest([freeze_ref,cutoff,n]),dict(due,frozen_t0=freeze_ref,report_cutoff=cutoff))
            basis=due['due_date'];rows=[]
            if due['outcome_status']=='DUE':
                for date in sessions[start+1:start+n+1]:
                    if frozen.get('entity_type')=='SECTOR':
                        basket=frozen['subject_basket'];ep={m['security_id']:source.read(m['security_id'],date,basis,cutoff) for m in basket['members']};b=benchmark(basket,ep,None,basis);close=1+b['return'] if b['return'] is not None else None
                        rows.append({'trade_date':date,'close':close,'high':close,'low':close,'verified_identity':True,'verified_adjustment':True,'T0_basis_verified':True,'evaluation_basis_date':basis,'transform_coefficients':{'alpha':1,'beta':0},'source_asof':date,'available_at':date,'price_extrema':'CLOSE_ONLY'})
                    else:rows.append(source.read(frozen['signal_id'],date,basis,cutoff))
            result={'outcome_status':'PENDING','R_N':None,'MFE_N':None,'MAE_N':None,'PATH_MDD_CLOSE_N':None} if not rows else price_path(frozen['comparison_reference'],rows,basis)
            identity=[frozen['enrollment_id'],n,'FORWARD_PRICE_PATH_V1',source.binding['sha256']]
            result.update(enrollment_id=frozen['enrollment_id'],horizon=n,due_date=basis,report_cutoff=cutoff,frozen_t0=freeze_ref,evaluation_source=source.binding,evaluation_source_digest=source.binding['sha256'],evaluation_source_identity=source.binding,outcome_contract_id='FORWARD_PRICE_PATH_V1',evidence_class=source.evidence_class,outcome_revision_id=digest(identity),price_path=rows,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED')
            if rows:
                members={m['security_id'] for key in ('market','sector') for m in frozen[key]['members']};endpoints={sid:source.read(sid,basis,basis,cutoff) for sid in sorted(members)}
                result['market_benchmark']=benchmark(frozen['market'],endpoints,result['R_N'],basis);result['sector_benchmark']=benchmark(frozen['sector'],endpoints,result['R_N'],basis)
                result['sector_benchmark']['MFE_CLOSE']=None;result['sector_benchmark']['MAE_CLOSE']=None
                if frozen['sector']['quality']=='OBSERVED':
                    points=[]
                    for date in sessions[start+1:start+n+1]:
                        ep={sid:source.read(sid,date,basis,cutoff) for sid in [m['security_id'] for m in frozen['sector']['members']]};b=benchmark(frozen['sector'],ep,None,basis)
                        if b['return'] is None:points=[];break
                        points.append(b['return'])
                    if points:result['sector_benchmark'].update(MFE_CLOSE=max([0]+points),MAE_CLOSE=min([0]+points))
                result['controls']={}
                for key in ('A','B','C'):
                    assigned=frozen['controls'][key]
                    control_outcomes=[]
                    t0_by_id={r['security_id']:r for r in self.store.read(frozen['snapshot'])['universe']}
                    for sid in assigned['control_entity_ids']:
                        path=[source.read(sid,date,basis,cutoff) for date in sessions[start+1:start+n+1]]
                        control_outcomes.append(dict(price_path(t0_by_id[sid]['close'],path,basis),security_id=sid))
                    result['controls'][key]={'control_assignment_id':assigned['control_assignment_id'],'assignment_digest':frozen['controls']['assignment_digest'],'ITT_RETAINED':True,'outcomes':control_outcomes}
            existing=self.store.refs('outcomes');same=next((r for r in existing if self.store.read(r)['outcome_revision_id']==result['outcome_revision_id']),None)
            if same:outputs.append(same)
            else:
                previous=[r for r in existing if self.store.read(r)['enrollment_id']==frozen['enrollment_id'] and self.store.read(r)['horizon']==n]
                result['revision_sequence']=1+len(previous);result['evaluation_revision']=result['revision_sequence'];result['supersedes']=max(previous,key=lambda r:self.store.read(r)['revision_sequence']) if previous else None
                result['revision_reason']='FIRST_OBSERVED' if not previous else 'ACCEPTED_EVALUATION_SOURCE_REVISION';result['first_observed_id']=min((self.store.read(r) for r in previous),key=lambda x:x['revision_sequence'])['outcome_revision_id'] if previous else result['outcome_revision_id'];result['latest_corrected_id']=result['outcome_revision_id']
                outputs.append(self.store.append('outcomes',result['outcome_revision_id'],result))
        return outputs
    def readback(self,freeze_ref,asof):
        frozen=self.store.read(freeze_ref);rows=[self.store.read(r) for r in self.store.refs('outcomes')];rows=[r for r in rows if r['enrollment_id']==frozen['enrollment_id'] and r['report_cutoff']<=asof]
        groups={}
        for r in rows:groups.setdefault(r['horizon'],[]).append(r)
        for values in groups.values():values.sort(key=lambda r:r['revision_sequence'])
        return {'frozen_t0':freeze_ref,'readback_asof':asof,'FIRST_OBSERVED':{n:next((r for r in v if r['outcome_status']!='PENDING'),v[0]) for n,v in groups.items()},'LATEST_CORRECTED':{n:v[-1] for n,v in groups.items()},'pending_items':[r for r in rows if r['outcome_status']=='PENDING'],'matured_items':[r for r in rows if r['outcome_status']!='PENDING'],'due_items':[r for r in rows if r['due_date']==asof],'benchmark_control_bindings':{'market':frozen['market'],'sector':frozen['sector'],'controls':frozen['controls']},'degradation_reasons':sorted({r['outcome_status'] for r in rows if r['outcome_status'] not in ('OBSERVED','PENDING')})}

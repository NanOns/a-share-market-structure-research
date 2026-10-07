"""Simulation-only Forward V1.2; additive maturity identity and owner price domain."""
import copy
from types import FunctionType
from . import v4_15_forward_p1 as previous
from . import v4_15_settlement as historical
from . import v4_15_settlement_successor as accepted
from .v4_15_settlement import digest, due_plan, HORIZONS, freeze_basket, freeze_controls, VectorPriceSource, AcceptedPriceSource
CONTRACT_ID = 'FORWARD_PRICE_PATH_V1_2'

def domain_reason(row):
    if row.get('status') == 'CONFIRMED_SUSPENSION': return None
    if row.get('status') == 'DELISTED':
        value=row.get('terminal_value')
        if value is not None and (not accepted.finite(value) or value < 0): return 'INVALID_TERMINAL_DOMAIN'
        return None
    coeff=row.get('transform_coefficients')
    for key in ('close','high','low','open'):
        value=row.get(key)
        if value is None: continue
        if not accepted.finite(value) or value <= 0: return 'INVALID_ACTUAL_PRICE_DOMAIN'
        if accepted.validate_affine(coeff):
            transformed=coeff['alpha']*value+coeff['beta']
            if not accepted.finite(transformed) or transformed <= 0: return 'INVALID_TRANSFORMED_PRICE_DOMAIN'
    low, high = row.get('low'), row.get('high')
    if low is not None and high is not None:
        if low > high: return 'INVALID_OHLC_ENVELOPE'
        for key in ('close','open'):
            if row.get(key) is not None and not low <= row[key] <= high: return 'INVALID_OHLC_ENVELOPE'
    elif (low is not None and row.get('close') is not None and low > row['close']) or (high is not None and row.get('close') is not None and high < row['close']):
        return 'INVALID_OHLC_ENVELOPE'
    return None

def price_path(reference,rows,basis_date,expected_identity=None):
    result=previous.price_path(reference,rows,basis_date,expected_identity)
    if not rows: return result
    endpoint=rows[-1]
    reason=domain_reason(endpoint)
    if not accepted.finite(reference) or reference <= 0: reason='INVALID_NATIVE_T0_PRICE_DOMAIN'
    if reason:
        result.update(R_N=None,MFE_N=None,MAE_N=None,PATH_MDD_CLOSE_N=None,
            outcome_status='MATURED_DATA_MISSING',endpoint_quality='PRICE_DOMAIN_UNKNOWN',
            path_quality='MATURED_DATA_MISSING',reason_codes=[reason])
        return result
    if result['R_N'] is not None and endpoint.get('status') != 'DELISTED':
        reasons=sorted({domain_reason(r) for r in rows[:-1] if domain_reason(r)})
        if reasons:
            result.update(MFE_N=None,MAE_N=None,PATH_MDD_CLOSE_N=None,
                path_quality='MATURED_DATA_MISSING',reason_codes=sorted(set(result.get('reason_codes',[])+reasons)))
    return result

def freeze_sector_basket(rows,t0,subject_id,snapshot_binding):
    basket=previous.freeze_sector_basket(rows,t0,subject_id,snapshot_binding)
    basket['basket_contract_id']='SECTOR_BASKET_FORWARD_PATH_V2'
    identity={k:v for k,v in basket.items() if k not in ('sector_basket_identity_digest','sector_basket_source_digest')}
    basket['sector_basket_identity_digest']=digest(identity)
    return basket

sector_path=FunctionType(previous.sector_path.__code__,dict(previous.sector_path.__globals__,price_path=price_path),
    previous.sector_path.__name__,previous.sector_path.__defaults__)

def benchmark(basket,rows_by_member,absolute_return,evaluation_basis_date=None):
    rows=copy.deepcopy(rows_by_member)
    for sid,row in rows.items():
        if domain_reason(row): rows[sid]=dict(row,verified_adjustment=False)
    return accepted.benchmark(basket,rows,absolute_return,evaluation_basis_date)

class SettlementRuntime(historical.SettlementRuntime):
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
            value['subject_basket']=freeze_sector_basket(subject_rows,t0,enrollment['entity_id'],t0_snapshot_ref);value['comparison_reference']=1
            value['controls']=freeze_controls([],signal,0,None)
            for key in ('A','B','C'):value['controls'][key]['status']='NOT_APPLICABLE_SECTOR'
        for i,key in enumerate(('market','sector')):
            ids=enrollment.get('benchmark_ids',[digest([enrollment['enrollment_id'],'MARKET']),digest([enrollment['enrollment_id'],'SECTOR'])]);bid=ids[key] if isinstance(ids,dict) else ids[i]
            basket=value[key];basket['constituent_digest']=basket['benchmark_id'];basket['benchmark_id']=bid
        for i,key in enumerate(('A','B','C')):
            ids=enrollment.get('control_assignment_ids',[digest([enrollment['enrollment_id'],k]) for k in ('A','B','C')]);value['controls'][key]['control_assignment_id']=ids[key] if isinstance(ids,dict) else ids[i]
        value['controls'].pop('assignment_digest',None);value['controls']['assignment_digest']=digest(value['controls'])
        value['forward_contract_id']=CONTRACT_ID
        return self.store.append('t0_freezes',digest([enrollment['enrollment_id'],CONTRACT_ID]),value)

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
                        basket=frozen['subject_basket']
                        rows.append({'trade_date':date,'members':{m['security_id']:source.read(m['security_id'],date,basis,cutoff) for m in basket['members']}})
                    else:rows.append(source.read(frozen['signal_id'],date,basis,cutoff))
            expected_identity=next((r.get('adjustment_identity') for r in self.store.read(frozen['snapshot'])['universe'] if r['security_id']==frozen['signal_id']),None)
            result={'outcome_status':'PENDING','R_N':None,'MFE_N':None,'MAE_N':None,'PATH_MDD_CLOSE_N':None} if not rows else (sector_path(frozen['subject_basket'],rows,basis,source.binding) if frozen.get('entity_type')=='SECTOR' else price_path(frozen['comparison_reference'],rows,basis,expected_identity))
            identity=[frozen['enrollment_id'],n,CONTRACT_ID,source.binding['sha256'],due['outcome_status'],basis,digest(sessions)]
            result.update(enrollment_id=frozen['enrollment_id'],horizon=n,due_date=basis,report_cutoff=cutoff,frozen_t0=freeze_ref,evaluation_source=source.binding,evaluation_source_digest=source.binding['sha256'],evaluation_source_identity=source.binding,outcome_contract_id=CONTRACT_ID,evidence_class=source.evidence_class,outcome_revision_id=digest(identity),price_path=rows,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED')
            result.update(production=False, shadow=False, focus=False, runtime_authorized=False, maturity_role=due['outcome_status'], accepted_session_identity=digest(sessions))
            if frozen.get('entity_type')=='SECTOR':
                result.update(MFE_N=None,MAE_N=None,PATH_MDD_CLOSE_N=None,
                              MFE_CLOSE=result.get('MFE_CLOSE'),MAE_CLOSE=result.get('MAE_CLOSE'),
                              stock_extrema_applicability='NOT_APPLICABLE_SECTOR')
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
                previous=[r for r in existing if self.store.read(r)['enrollment_id']==frozen['enrollment_id'] and self.store.read(r)['horizon']==n and self.store.read(r).get('outcome_contract_id')==CONTRACT_ID and self.store.read(r).get('frozen_t0')==freeze_ref]
                result['revision_sequence']=1+len(previous);result['evaluation_revision']=result['revision_sequence'];result['supersedes']=max(previous,key=lambda r:self.store.read(r)['revision_sequence']) if previous else None
                observed=[self.store.read(r) for r in previous if self.store.read(r)['outcome_status']!='PENDING']
                result['first_observed_id']=(min(observed,key=lambda x:x['revision_sequence'])['outcome_revision_id'] if observed else (result['outcome_revision_id'] if result['outcome_status']!='PENDING' else None))
                result['latest_corrected_id']=(result['outcome_revision_id'] if result['outcome_status']!='PENDING' else (max(observed,key=lambda x:x['revision_sequence'])['outcome_revision_id'] if observed else None))
                result['revision_reason']='PLANNER_PENDING_OBSERVATION' if due['outcome_status']=='PENDING' else ('FIRST_OBSERVED' if not observed else 'ACCEPTED_EVALUATION_SOURCE_REVISION')
                outputs.append(self.store.append('outcomes',result['outcome_revision_id'],result))
        return outputs

    def readback(self,freeze_ref,asof):
        frozen=self.store.read(freeze_ref)
        rows=[self.store.read(r) for r in self.store.refs('outcomes')]
        rows=[r for r in rows if r.get('frozen_t0')==freeze_ref and r.get('outcome_contract_id')==CONTRACT_ID and r['report_cutoff']<=asof]
        groups={}
        for row in rows: groups.setdefault(row['horizon'],[]).append(row)
        first={};latest={}
        for n,values in groups.items():
            matured=sorted((r for r in values if r['outcome_status']!='PENDING'),key=lambda r:r['revision_sequence'])
            if matured: first[n]=matured[0];latest[n]=matured[-1]
        return dict(frozen_t0=freeze_ref,readback_asof=asof,FIRST_OBSERVED=first,LATEST_CORRECTED=latest,
            pending_items=[r for r in rows if r['outcome_status']=='PENDING' and r['horizon'] not in latest],
            pending_history=[r for r in rows if r['outcome_status']=='PENDING'],
            matured_items=[r for r in rows if r['outcome_status']!='PENDING'],
            due_items=[r for r in latest.values() if r['due_date']==asof],
            benchmark_control_bindings={k:frozen[k] for k in ('market','sector','controls')},
            degradation_reasons=sorted({r['outcome_status'] for r in rows if r['outcome_status'] not in ('PENDING','OBSERVED')}))

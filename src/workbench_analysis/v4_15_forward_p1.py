"""Candidate Forward 1.1: independent endpoints and dedicated sector baskets.

No historical outcome, active authority, source contract or migration is mutated.
IA03 same-source pending/due identity and IA04 price-domain debt remain open.
"""
import copy
from . import v4_15_settlement as historical
from . import v4_15_settlement_successor as accepted

CONTRACT_ID = 'FORWARD_PRICE_PATH_V1_1'
benchmark = accepted.benchmark

def price_path(reference, rows, basis_date, expected_identity=None):
    if not rows:
        return historical.price_path(reference, rows, basis_date)
    endpoint = rows[-1]
    out = accepted.price_path(reference, [endpoint], basis_date)
    if expected_identity is not None and endpoint.get('adjustment_identity') != expected_identity:
        out.update(R_N=None, MFE_N=None, MAE_N=None, PATH_MDD_CLOSE_N=None,
                   outcome_status='ADJUSTMENT_UNKNOWN', reason_codes=['ENDPOINT_IDENTITY_MISMATCH'])
    out['endpoint_quality'] = 'OBSERVED' if out['R_N'] is not None else out['outcome_status']
    if out['R_N'] is None or endpoint.get('status') == 'DELISTED':
        out['path_quality'] = 'NOT_AVAILABLE_TERMINAL_OR_ENDPOINT'
        return out
    identity = endpoint.get('adjustment_identity')
    reasons = []
    for row in rows[:-1]:
        if row.get('verified_identity') is not True:
            reasons.append('INTERIOR_IDENTITY_UNKNOWN')
        if row.get('status') == 'CONFIRMED_SUSPENSION':
            if row.get('verified_adjustment') is not True or row.get('evaluation_basis_date') != basis_date:
                reasons.append('INTERIOR_SUSPENSION_PROOF_UNKNOWN')
            continue
        if not accepted.valid_row(row, basis_date, identity):
            reasons.append('INTERIOR_AFFINE_OR_BASIS_UNKNOWN')
        if row.get('status') != 'CONFIRMED_SUSPENSION':
            coeff = row.get('transform_coefficients')
            for key in ('close', 'high', 'low'):
                value = row.get(key)
                if value is None:
                    reasons.append('UNKNOWN_INTERIOR_GAP')
                elif not accepted.finite(value) or (accepted.validate_affine(coeff) and
                        not accepted.finite(coeff['alpha'] * value + coeff['beta'])):
                    reasons.append('INTERIOR_VALUE_UNKNOWN')
    if reasons:
        out.update(MFE_N=None, MAE_N=None, PATH_MDD_CLOSE_N=None,
                   path_quality='MATURED_DATA_MISSING', reason_codes=sorted(set(reasons)),
                   actual_count=sum(r.get('status') != 'CONFIRMED_SUSPENSION' for r in rows))
        return out
    full = accepted.price_path(reference, rows, basis_date)
    full['endpoint_quality'] = out['endpoint_quality']
    return full

def freeze_sector_basket(rows, t0, subject_id, snapshot_binding):
    if len({r['security_id'] for r in rows}) != len(rows):
        raise ValueError('DUPLICATE_FROZEN_MEMBER')
    basket = historical.freeze_basket(rows, t0, 'SECTOR')
    by_id = {r['security_id']: r for r in rows}
    for member in basket['members']:
        member['source_identity'] = by_id[member['security_id']].get('source_identity')
    basket.update(sector_subject_id=subject_id, membership_snapshot=copy.deepcopy(snapshot_binding),
                  T0_evaluation_basis=t0, basket_contract_id='SECTOR_BASKET_FORWARD_PATH_V1')
    basket['sector_basket_identity_digest'] = historical.digest(basket)
    basket['sector_basket_source_digest'] = historical.digest([
        {'security_id': m['security_id'], 'source_identity': m['source_identity'],
         'adjustment_identity': m['adjustment_identity']} for m in basket['members']])
    return basket

def sector_path(basket, points, basis_date, source_binding):
    """Points contain dated member valuations, never synthetic stock OHLC."""
    out = dict(R_N=None, MFE_N=None, MAE_N=None, MFE_CLOSE=None, MAE_CLOSE=None,
               PATH_MDD_CLOSE_N=None, stock_extrema_applicability='NOT_APPLICABLE_SECTOR',
               outcome_status='MATURED_DATA_MISSING', endpoint_quality='UNKNOWN_UNAVAILABLE',
               path_quality='UNKNOWN_UNAVAILABLE', reason_codes=[], member_valuations=[],
               evaluation_basis_date=basis_date, evaluation_source=source_binding,
               sector_basket_identity_digest=basket.get('sector_basket_identity_digest'),
               sector_basket_source_digest=basket.get('sector_basket_source_digest'))
    if (len(basket['members']) < 2 or basket.get('quality') != 'OBSERVED' or
            basket.get('constituent_policy') != 'FIXED_ORIGINAL_WEIGHTS_NO_REWEIGHT'):
        out['reason_codes'] = ['SECTOR_SUBJECT_INELIGIBLE']
        return out
    if not basket.get('sector_basket_identity_digest') or not basket.get('membership_snapshot'):
        out['reason_codes'] = ['FROZEN_BASKET_IDENTITY_MISSING']
        return out
    identity = {k: v for k, v in basket.items() if k not in ('sector_basket_identity_digest', 'sector_basket_source_digest')}
    if historical.digest(identity) != basket['sector_basket_identity_digest']:
        out['reason_codes'] = ['FROZEN_BASKET_IDENTITY_MISMATCH']
        return out
    frozen_sources = [{'security_id': m['security_id'], 'source_identity': m['source_identity'],
                       'adjustment_identity': m['adjustment_identity']} for m in basket['members']]
    if historical.digest(frozen_sources) != basket['sector_basket_source_digest']:
        out['reason_codes'] = ['FROZEN_BASKET_SOURCE_MISMATCH']
        return out
    if points and (points[-1]['trade_date'] != basis_date or any(p['trade_date'] > basis_date for p in points)):
        out['reason_codes'] = ['SECTOR_ENDPOINT_DATE_MISMATCH']
        return out
    values = []
    for point in points:
        contribution = coverage = 0
        members = []
        for member in basket['members']:
            row = point['members'].get(member['security_id'], {})
            valid_identity = (isinstance(member.get('adjustment_identity'), str) and
                              bool(member['adjustment_identity']) and
                              isinstance(member.get('source_identity'), str) and bool(member['source_identity']) and
                              row.get('source_identity') == member['source_identity'])
            valuation_row = {k: v for k, v in row.items() if k not in ('high', 'low')}
            result = price_path(member['reference'], [valuation_row], basis_date, member.get('adjustment_identity'))
            value = result['R_N'] if valid_identity else None
            if value is not None:
                contribution += member['weight'] * (1 + value)
                coverage += member['weight']
            members.append(dict(security_id=member['security_id'], original_weight=member['weight'],
                                endpoint_return=value, endpoint_quality=result['endpoint_quality'] if valid_identity else 'SOURCE_IDENTITY_UNKNOWN'))
        observed = abs(coverage - 1) < 1e-12
        values.append(contribution - 1 if observed else None)
        out['member_valuations'].append(dict(trade_date=point['trade_date'], members=members,
                                             coverage=coverage, missing_weight=1-coverage,
                                             basket_close_return=values[-1]))
    if not values or values[-1] is None:
        out['reason_codes'] = ['SECTOR_ENDPOINT_MEMBER_UNVALUED']
        return out
    out.update(R_N=values[-1], outcome_status='OBSERVED', endpoint_quality='OBSERVED')
    if any(v is None for v in values):
        out['reason_codes'] = ['SECTOR_INTERIOR_MEMBER_UNVALUED']
        return out
    out.update(MFE_CLOSE=max([0] + values), MAE_CLOSE=min([0] + values),
               path_quality='OBSERVED')
    return out

# Frozen revision/control logic is reused verbatim; candidate identity is additive.
from .v4_15_settlement import digest, due_plan, HORIZONS, freeze_basket, freeze_controls, VectorPriceSource, AcceptedPriceSource

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
            identity=[frozen['enrollment_id'],n,CONTRACT_ID,source.binding['sha256']]
            result.update(enrollment_id=frozen['enrollment_id'],horizon=n,due_date=basis,report_cutoff=cutoff,frozen_t0=freeze_ref,evaluation_source=source.binding,evaluation_source_digest=source.binding['sha256'],evaluation_source_identity=source.binding,outcome_contract_id=CONTRACT_ID,evidence_class=source.evidence_class,outcome_revision_id=digest(identity),price_path=rows,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED')
            result.update(production=False, shadow=False, focus=False, runtime_authorized=False)
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
                previous=[r for r in existing if self.store.read(r)['enrollment_id']==frozen['enrollment_id'] and self.store.read(r)['horizon']==n]
                result['revision_sequence']=1+len(previous);result['evaluation_revision']=result['revision_sequence'];result['supersedes']=max(previous,key=lambda r:self.store.read(r)['revision_sequence']) if previous else None
                result['revision_reason']='FIRST_OBSERVED' if not previous else 'ACCEPTED_EVALUATION_SOURCE_REVISION';result['first_observed_id']=min((self.store.read(r) for r in previous),key=lambda x:x['revision_sequence'])['outcome_revision_id'] if previous else result['outcome_revision_id'];result['latest_corrected_id']=result['outcome_revision_id']
                outputs.append(self.store.append('outcomes',result['outcome_revision_id'],result))
        return outputs

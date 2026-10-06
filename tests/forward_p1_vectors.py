"""Serializable contract counterfactuals; all inputs are engineering fixtures."""
import copy
from workbench_analysis import v4_15_settlement as historical
from workbench_analysis import v4_15_settlement_successor as previous
from workbench_analysis import v4_15_forward_p1 as candidate
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority

BASIS = '2030-01-04'

def row(close=11):
    return dict(close=close, high=close+1, low=close-1, verified_identity=True,
                verified_adjustment=True, T0_basis_verified=True, evaluation_basis_date=BASIS,
                adjustment_identity='AFFINE_A', source_identity='LOCAL_SOURCE_A',
                transform_coefficients={'alpha':1,'beta':0})

class MemoryStore:
    def __init__(self): self.data = {}
    def append(self, kind, key, value):
        ref = (kind, key)
        if ref in self.data and self.data[ref] != value: raise ValueError('IMMUTABLE_CONFLICT')
        self.data[ref] = copy.deepcopy(value)
        return ref
    def read(self, ref): return copy.deepcopy(self.data[ref])
    def refs(self, kind): return [r for r in self.data if r[0] == kind]

class FixtureAuthority(CurrentStageAuthority):
    def __init__(self): self.sessions = [f'2030-01-{n:02}' for n in range(1,23)]
    def bindings(self): return {'evidence_class':'ENGINEERING_FIXTURE_ONLY'}

def runtime_fixture(sector=False):
    store = MemoryStore()
    universe = [dict(security_id=s, close=10, research_eligible=True, primary_industry='IND',
                    adjustment_identity='AFFINE_A', source_identity='LOCAL_SOURCE_A') for s in ('A','B','C')]
    snapshot = store.append('snapshots','s',dict(trade_date='2030-01-01', universe=universe))
    enrollment = store.append('enrollments','e',dict(enrollment_id='E', T0='2030-01-01',
                              entity_type='SECTOR' if sector else 'STOCK', entity_id='IND' if sector else 'A', comparison_reference=10))
    authority = FixtureAuthority()
    runtime = candidate.SettlementRuntime(authority, store)
    freeze = runtime.freeze_t0(enrollment, snapshot)
    rows = {s:{f'2030-01-{n:02}':row() for n in range(2,23)} for s in ('A','B','C')}
    return runtime, store, freeze, historical.VectorPriceSource(rows), enrollment, snapshot

def revision_vector(sector=False):
    runtime, store, freeze, source, enrollment, snapshot = runtime_fixture(sector)
    old_runtime = previous.SettlementRuntime(runtime.authority, store)
    old_freeze = old_runtime.freeze_t0(enrollment, snapshot)
    old_ref = old_runtime.settle(old_freeze, source, BASIS, (3,))[0]
    historical_value = store.read(old_ref)
    first = runtime.settle(freeze, source, BASIS, (3,))[0]
    source.rows['A']['2030-01-04']['close'] = 12
    source.binding = {'sha256':historical.digest(source.rows)}
    corrected = runtime.settle(freeze, source, BASIS, (3,))[0]
    assert store.read(old_ref) == historical_value and first != corrected
    assert store.read(corrected)['supersedes'] == first
    return dict(historical=historical_value, first=store.read(first), corrected=store.read(corrected),
                historical_unchanged=True, readback=runtime.readback(freeze,BASIS))

def stock_vector(number):
    rows = [row(10.5), row()]
    reference = 10
    expected = .1
    identity = None
    expectation = 'Verified T0/endpoint return; path requires every participating coordinate.'
    if number == 2: rows[0] = {}
    if number == 3: rows[0].pop('transform_coefficients')
    if number == 4: rows[-1]['transform_coefficients']={'alpha':0,'beta':0}; expected=None
    if number == 5: rows[-1]['T0_transform_coefficients']={'alpha':0,'beta':0}; expected=None
    if number == 6: identity='FROZEN_OTHER'; expected=None
    if number == 7: rows[-1]['evaluation_basis_date']='2030-01-03'; expected=None
    if number == 8: rows[0].update(status='CONFIRMED_SUSPENSION',close=None,high=None,low=None)
    if number == 9:
        rows[0]={}; reference=20
        rows[-1].update(T0_transform_coefficients={'alpha':.5,'beta':0})
    if number == 10:
        proof = revision_vector()
        return dict(id='STK-10', input={'corrected_source':True}, contract_expectation='Append correction without rewriting history',
                    old_result=proof['historical'], new_result=proof, why_contract_matches='Three immutable outcome revisions with explicit supersedes')
    if number == 12: rows=[row(10.5), {}, row()]
    old=previous.price_path(reference,rows,BASIS)
    new=candidate.price_path(reference,rows,BASIS,identity)
    assert new['R_N'] is None if expected is None else abs(new['R_N']-expected)<1e-12
    if number in (2,3,9,12):
        assert new['MFE_N'] is None and new['MAE_N'] is None and new['PATH_MDD_CLOSE_N'] is None
    if number == 1:
        assert all(new[k]==old[k] for k in ('R_N','MFE_N','MAE_N','PATH_MDD_CLOSE_N'))
    if number == 8: assert new['path_quality']=='CONFIRMED_INTERIOR_SUSPENSION_OMITTED'
    if number == 11:
        rows[0]={}; new=candidate.price_path(10,rows,BASIS)
        old=previous.price_path(10,rows,BASIS)
        basket=historical.freeze_basket([dict(security_id='B',close=10)],'2030-01-01')
        b=candidate.benchmark(basket,{'B':row(10.5)},new['R_N'],BASIS)
        assert abs(b['relative_market_return']-.05)<1e-12
        new['relative_market_proof']=b
    return dict(id=f'STK-{number:02}', input={'reference':reference,'rows':rows,'basis':BASIS,'expected_identity':identity},
                contract_expectation={'R_N':expected,'rule':expectation},old_result=old,new_result=new,
                why_contract_matches='Endpoint admission remains strict; incomplete interior only degrades path metrics; no interpolation.')

def sector_vector(number):
    members=[dict(security_id=s,close=10,adjustment_identity='AFFINE_A',source_identity='LOCAL_SOURCE_A') for s in ('A','B')]
    basket=candidate.freeze_sector_basket(members,'2030-01-01','IND',{'sha256':historical.digest(members),'path':'engineering_membership.json'})
    points=[dict(trade_date='2030-01-02',members={s:row(10.5) for s in ('A','B')}),
            dict(trade_date=BASIS,members={s:row() for s in ('A','B')})]
    expected=.1
    if number == 2: points[0]['members']['A']={}
    if number == 3: points[-1]['members']['A']={};expected=None
    if number == 4:
        for point in points: point['members']['A']['T0_transform_coefficients']={'alpha':.5,'beta':0};point['members']['A']['transform_coefficients']={'alpha':.5,'beta':0}
    if number == 5:
        points[-1]['members']['NEW']=row(99)
        assert [m['security_id'] for m in basket['members']]==['A','B']
    if number == 8:
        basket=candidate.freeze_sector_basket(members[:1],'2030-01-01','IND',{'sha256':'fixture'});expected=None
    if number in (11,12):
        proof=revision_vector(True)
        return dict(id=f'SEC-{number:02}',input={'sector_correction':True},contract_expectation='Append successor; historical sector outcome immutable',
                    old_result=proof['historical'],new_result=proof,why_contract_matches='Historical bytes preserved; new basket path and correction have unique immutable revisions')
    # Reproduce the old aggregate-stock route exactly; no invented adjustment identity.
    old_rows=[]
    for point in points:
        b=previous.benchmark(basket,point['members'],None,BASIS)
        close=None if b['return'] is None else 1+b['return']
        old_rows.append(dict(close=close,high=close,low=close,verified_identity=True,
                             verified_adjustment=True,T0_basis_verified=True,evaluation_basis_date=BASIS,
                             transform_coefficients={'alpha':1,'beta':0}))
    old=previous.price_path(1,old_rows,BASIS)
    new=candidate.sector_path(basket,points,BASIS,{'sha256':'engineering-source'})
    assert new['R_N'] is None if expected is None else abs(new['R_N']-expected)<1e-12
    assert new['MFE_N'] is None and new['MAE_N'] is None
    assert new['PATH_MDD_CLOSE_N'] is None
    assert not any(k in new for k in ('high','low','adjustment_identity'))
    if number==2: assert new['MFE_CLOSE'] is None and new['MAE_CLOSE'] is None
    if number==3: assert new['member_valuations'][-1]['coverage']==.5
    if number==9:
        independent=historical.freeze_basket(members,'2030-01-01','SECTOR')
        relative=candidate.benchmark(independent,points[-1]['members'],.2,BASIS)
        tiny=candidate.freeze_sector_basket(members[:1],'2030-01-01','OTHER',{'sha256':'fixture'})
        assert candidate.sector_path(tiny,points,BASIS,{'sha256':'fixture'})['R_N'] is None
        assert abs(relative['relative_sector_return']-.1)<1e-12
        new['independent_relative_sector']=relative
    if number==10:
        market=historical.freeze_basket(members,'2030-01-01','MARKET')
        assert candidate.benchmark(market,points[-1]['members'],.2,BASIS)==previous.benchmark(market,points[-1]['members'],.2,BASIS)
    return dict(id=f'SEC-{number:02}',input={'basket':basket,'points':points,'basis':BASIS},
                contract_expectation={'R_N':expected,'stock_extrema':'NOT_APPLICABLE','policy':'FIXED_ORIGINAL_WEIGHTS_NO_REWEIGHT'},
                old_result=old,new_result=new,why_contract_matches='Frozen independent basket identity, individually verified members, complete original-weight coverage; only close extrema.')

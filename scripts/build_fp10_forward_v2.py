"""Full bounded Forward continuation, preserving cohort and original T0 freezes."""
import collections,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import enter,operational_path
from workbench_service.production_v4 import frozen_current_reader,ProductionV4ResearchReader
from workbench_service.forward_daily import CONTRACT,ForwardStore,OperationalForwardAuthority,LocalForwardPriceSource,calendar_extension,verify_due_settlement
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.joint_release import checked_path
from focus_tracker.v4_daily_driver import path_inputs
from focus_tracker.v4_path_adapter import AcceptedPaths
from workbench_analysis.v4_15_settlement import due_plan
from workbench_analysis.v4_15_settlement_successor import SettlementRuntime

def build():
    out=enter(10);current,_=frozen_current_reader(ROOT);contract,_=current._contract();ctx=current.load_context()['context'];day=ctx['accepted_trade_date']
    market=json.loads(operational_path('v4_market_operational_authority_v1.json').read_bytes())
    stocks=json.loads(operational_path('v4_stock_operational_authority_v1.json').read_bytes())
    for owner in (market,stocks):
        if owner['trade_date']!=day or owner['input_data_head']['sha256']!=ctx['data_head_digest']:raise SourceInvalid('FORWARD_OWNER_DATE_HEAD_MISMATCH')
    inputs=path_inputs(ROOT,dict(sources=dict(market_operational=market['market'],stock_series=stocks['series'])))
    paths=AcceptedPaths(ROOT,inputs)
    kernel={}
    for p in ('src/workbench_analysis/v4_15_settlement.py','src/workbench_analysis/v4_15_settlement_successor.py','src/workbench_service/forward_daily.py'):
        raw=(ROOT/p).read_bytes();dest=ROOT/'data/v4/r2_forward/implementations'/digest(raw)/Path(p).name
        if dest.exists() and dest.read_bytes()!=raw:raise SourceInvalid('FORWARD_KERNEL_IMMUTABILITY')
        if not dest.exists():write(dest,raw)
        kernel[p]=ref(dest)
    store=ForwardStore(ROOT,'data/v4/r2_forward/journal_v1')
    legacy=ProductionV4ResearchReader(ROOT).manifest['domain_features']['forward'];prior_freezes={}
    for old in legacy['outcomes']:
        if old.get('frozen_t0'):prior_freezes[old['enrollment_id']]=old['frozen_t0']
    for b in store.refs('t0_freezes'):prior_freezes[store.read(b)['enrollment_id']]=b
    snapshots={store.read(b)['T0']:store.read(b)['snapshot'] for b in prior_freezes.values()}
    outcomes=[];plans=[];enrollments=[];freezes=[];read_count=0;coordinate_cache={}
    sources=dict(projection_adapter=ref('scripts/build_fp10_forward_v2.py'),kernel=kernel,evaluation_inputs=inputs,
        accepted_data_head=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json'))
    for row,binding in current._rows(contract,'cohort'):
        t0=row['T0'];frozen_calendar=current._read(row['calendar_identity']);sessions=frozen_calendar.get('session_dates',frozen_calendar.get('sessions'))
        if sessions and isinstance(sessions[0],dict):sessions=[r['trade_date'] for r in sessions]
        accepted=json.loads(checked_path(ROOT,inputs['calendar']).read_bytes())['session_dates']
        if accepted and isinstance(accepted[0],dict):accepted=[r['trade_date'] for r in accepted]
        calendar=calendar_extension(sessions,accepted,t0,day)
        authority=OperationalForwardAuthority(ROOT,calendar,dict(contract_id=CONTRACT,accepted_data_head=sources['accepted_data_head'],calendar=inputs['calendar'],kernel=kernel,
            historical_stage_permissions_unchanged=True,strict_pit=False,knowledge_lineage='RECONSTRUCTED_CORRECTED'))
        runtime=SettlementRuntime(authority,store)
        frozen=prior_freezes.get(row['enrollment_id'])
        if frozen is None:
            snap=snapshots.get(t0)
            if snap is None:raise SourceInvalid('FORWARD_ORIGINAL_T0_SNAPSHOT_UNAVAILABLE')
            snapshot=store.read(snap)
            if snapshot['source']!=row['comparison_reference_source']:raise SourceInvalid('FORWARD_T0_SOURCE_MISMATCH')
            frozen=runtime.freeze_t0(binding,snap)
        freeze=store.read(frozen)
        if freeze['enrollment_id']!=row['enrollment_id'] or freeze['comparison_reference']!=row['comparison_reference']:raise SourceInvalid('FORWARD_FROZEN_REFERENCE_CHANGED')
        snapshot=store.read(freeze['snapshot'])
        coordinate=row.get('t0_transform')
        if not coordinate:raise SourceInvalid('FORWARD_NATIVE_T0_COORDINATE_UNAVAILABLE')
        source_key=snapshot['source']['sha256']
        if source_key not in coordinate_cache:
            actual=store.read(snapshot['source'])
            coordinate_cache[source_key]={u['security_id']:dict(qfq_mul=u['qfq_mul'],qfq_add=u['qfq_add'],
                adjustment_identity=u['adjustment_source_revision'],reference=float(u['close'])) for u in actual['rows'] if u['adjustment_readiness']=='READY'}
        coords=coordinate_cache[source_key]
        if row['entity_id'] not in coords or any(coords[row['entity_id']][k]!=coordinate[k] for k in ('qfq_mul','qfq_add')):
            raise SourceInvalid('FORWARD_FROZEN_COORDINATE_SOURCE_MISMATCH')
        if coords[row['entity_id']]['reference']!=freeze['comparison_reference'] or any(
            u['security_id'] not in coords or coords[u['security_id']]['reference']!=u['close'] for u in snapshot['universe']):
            raise SourceInvalid('FORWARD_T0_REFERENCE_OR_UNIVERSE_SOURCE_MISMATCH')
        source=LocalForwardPriceSource(ROOT,inputs,t0,day,coords,kernel,accepted_paths=paths)
        # The source bundle includes cutoff and accepted calendar, so PENDING
        # cannot mask the first real maturity even if price bytes are unchanged.
        refs=runtime.settle(frozen,source,day)
        for b in refs:
            o=store.read(b);outcomes.append(dict(o,source=b,adapter_contract_id=CONTRACT,strict_pit=False,AS_RECORDED=False,
                knowledge_lineage='RECONSTRUCTED_CORRECTED',t0_degradation=dict(market_quality=freeze['market']['quality'],sector_quality=freeze['sector']['quality'],
                    hard_safety_quality=snapshot.get('hard_safety_quality'),research_universe_quality=snapshot.get('research_universe_quality'))))
        for plan in due_plan(calendar,t0,day):
            plan.update(enrollment_id=row['enrollment_id'],entity_id=row['entity_id'],T0=t0,source=binding,
                due_reason='FUTURE_SESSION_OUTSIDE_ACCEPTED_CALENDAR' if plan['due_date'] is None else 'NOT_YET_DUE' if plan['outcome_status']=='PENDING' else 'ACTUAL_OWNER_SETTLEMENT_ATTEMPTED',
                kind='DUE_PLAN_ONLY_NOT_OUTCOME',calendar_extension=inputs['calendar'],frozen_calendar=row['calendar_identity'])
            plans.append(plan)
        enrollments.append(dict(row,source=binding));freezes.append(frozen);read_count+=len(source.read_log)
    old_fep=legacy['fep'];status=collections.Counter(o['outcome_status'] for o in outcomes)
    publication=dict(contract_id='FP10_FORWARD_READ_PROJECTION_V2',adapter_contract_id=CONTRACT,trade_date=day,
        enrollments=enrollments,plans=plans,outcomes=outcomes,sources=sources,t0_freezes=freezes,
        legacy_outcomes=legacy.get('legacy_outcomes',legacy['outcomes']),fep=old_fep,
        statistics=dict(enrollment_denominator=len(enrollments),planned_horizon_denominator=len(plans),published_outcomes=len(outcomes),
            published_enrollment_count=len(enrollments),state_counts=dict(status),mature_eligible_count=0,win_rate=None,return_quantiles=None,
            reason='STRICT_T0_ELIGIBILITY_NOT_GRANTED',failure_and_censored_not_dropped=True),
        knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,strict_pit=False)
    due=verify_due_settlement(publication,day)
    publication['settlement_gate']=dict(contract_id=CONTRACT,result='NO_REAL_DUE' if not due else 'DUE_PROCESSED',due_count=due,
        actual_price_reads=read_count,t0_frozen_count=len(freezes),historical_permissions_unchanged=True)
    path=ROOT/'data/v4/fp10_forward'/digest(canonical(publication))/'forward.json';write(path,publication)
    write(operational_path('v4_forward_operational_authority_v1.json',for_write=True),dict(contract_id='FP10_FORWARD_READ_AUTHORITY_V1',trade_date=day,
        input_data_head=sources['accepted_data_head'],publication=ref(path)))
    write(out/'REAL_SOURCE_READBACK.json',dict(statistics=publication['statistics'],settlement_gate=publication['settlement_gate'],sources=sources,t0_freezes=freezes))
    return publication

if __name__=='__main__':print(json.dumps(build()['settlement_gate']))

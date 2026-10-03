"""Reproducible capability-scoped accepted source settlement, plus local gate."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_15_persistence import Store
from workbench_analysis.v4_15_settlement import AcceptedPriceSource,SettlementRuntime
from scripts.r20_io import ROOT,atomic,ref
from scripts.validate_r20d_settlement import validate

def run():
    authority=CurrentStageAuthority(ROOT)
    store=Store(ROOT,'reports/v4_15_runtime_r20/r20d_accepted_source_r2')
    # This exact projection reads the accepted T0 dated artifact, not future data.
    source=AcceptedPriceSource(authority,authority.data['component_artifacts']['ADJUSTED_DAILY'])
    t0='2026-09-30';universe=[]
    for sid,dates in sorted(source.rows.items()):
        r=dates[t0]
        if r['close'] is not None and r['verified_identity']:
            universe.append({'security_id':sid,'close':r['close'],'adjustment_identity':r['adjustment_identity'],'research_eligible':True,'hard_safety':False,'prewatch_final_eligible':False,'primary_industry':None})
    selected=universe[0]
    enrollment={'enrollment_id':'r20d_real_reconstructed_source','entity_type':'STOCK','entity_id':selected['security_id'],'T0':t0,'cohort_namespace':'RECONSTRUCTED_ASOF','comparison_reference':selected['close'],'source_binding':source.binding,'HISTORICAL_PIT_EFFECTIVENESS':'NOT_GRANTED'}
    enref=store.append('enrollments',enrollment['enrollment_id'],enrollment)
    snapshot=store.append('snapshots','accepted_t0',{'trade_date':t0,'source_asof':t0,'available_at':None,'available_at_unknown':True,'evidence_class':'RECONSTRUCTED_ASOF','universe':universe,'accepted_source':source.binding,'quality':'HARD_SAFETY_NOT_PROJECTED_CONTROLS_UNAVAILABLE'})
    runtime=SettlementRuntime(authority,store);frozen=runtime.freeze_t0(enref,snapshot,event_count=0)
    # All accepted-calendar horizons lie beyond Data Head. No future quote opens.
    outcomes=runtime.settle(frozen,source,t0)
    readback=store.append('readbacks','accepted_readback',runtime.readback(frozen,t0))
    assert not source.read_log
    oracle=validate(ROOT,store.namespace)
    gate={'R20D_V4_15_SETTLEMENT_RUNTIME':'PASS_LOCAL','DUE_PLANNER_RUNTIME':'IMPLEMENTED_ENGINEERING','BENCHMARK_CONTROL_RUNTIME':'IMPLEMENTED_ENGINEERING','SETTLEMENT_RUNTIME':'IMPLEMENTED_ENGINEERING','REAL_ACCEPTED_SOURCE_SETTLEMENT':'PASS_CAPABILITY_SCOPED','real_scope':'ACCEPTED_CURRENT_T0_RECONSTRUCTED_PROJECTION_AND_FIVE_PENDING_HORIZONS_NO_ACCEPTED_FUTURE_BEYOND_DATA_HEAD','numerical_forward_scope':'ENGINEERING_VECTORS_ONLY','HISTORICAL_PIT_EFFECTIVENESS':'NOT_GRANTED','V4_15_ACCEPTED_HEAD':'NOT_CREATED','Production':False,'Shadow':False,'Focus':False,'NEXT':'R20E_AFTER_R20C_AND_R20B','authority':authority.bindings(),'frozen_t0':frozen,'outcomes':outcomes,'readback':readback,'independent_oracle':oracle,'future_read_count':0}
    atomic(ROOT/'reports/r20d/SETTLEMENT_GATE.json',gate)
    return gate

if __name__=='__main__':print(json.dumps(run(),indent=2))

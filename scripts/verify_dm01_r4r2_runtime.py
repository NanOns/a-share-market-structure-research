"""Atomic engineering gates and read-only protected/future runtime readback."""
import json
from pathlib import Path
from datetime import datetime,timezone
import pytest
from workbench_analysis import dm01_runtime_r4 as r
from scripts import r25_bridge_oracle_r4r2 as o
from scripts.build_r25_bridge_r4r2 import produce_bridge
from scripts.validate_r25_preflight import selection,protected
from tests.v4_dm01_r4r2.test_bridge import vector,test_R4R2_11_engineering_producer,test_R4R2_12_real_shaped_parity

ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'reports/dm01_r4r2'
    def write(name,value):return r.atomic(ROOT,folder/(name+'.json'),value)
    contract=o.binding(ROOT,o.CONTRACT_PATH);deps=o.binding(ROOT,'config/v4_16_runtime_dependencies_v4.json')
    # Fixture ZIP bytes carry a creation timestamp. Every explicit audit run
    # gets a fresh engineering namespace; producers remain deterministic for
    # their exact supplied inputs and immutable within that namespace.
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    engineering=folder/'engineering'/(o.digest([contract,deps])[:8]+'_'+run)
    v=vector.__wrapped__(engineering/'engineering_bridge')
    test_R4R2_11_engineering_producer(v)
    shaped=vector.__wrapped__(engineering/'real_shaped_vector')
    with pytest.MonkeyPatch.context() as patch:test_R4R2_12_real_shaped_parity(shaped,patch)
    write('DAILY_INPUT_SCHEMA_GATE',dict(status='PASS_LOCAL_REPAIRED',contract=contract,predecessor=o.exact(ROOT,contract)['predecessor'],bridge_required=True,bridge_in_daily_and_packet_digest=True,old_V1='HISTORICAL_COMPATIBILITY_ONLY'))
    write('BRIDGE_PRODUCER_GATE',dict(status='PASS_LOCAL_REPAIRED',engineering_bridge=r.ref(ROOT,engineering/'engineering_bridge/produced.json'),engineering_daily=r.ref(ROOT,engineering/'engineering_bridge/produced_daily.json'),real_bridge_created=False,real_target_session_package='NOT_CREATED',real_grant=False))
    packet=r.ref(ROOT,engineering/'real_shaped_vector/reports/r25/activation_candidate/engineering_packet.json')
    write('R25_PREFLIGHT_PARITY_GATE',dict(status='PASS_LOCAL_REPAIRED',contract=contract,runtime_dependencies=deps,engineering_packet=packet,oracle='scripts/r25_bridge_oracle_r4r2.py',oracle_read_only=True,imports_runtime_execution=False,no_implicit_discovery=True,real_ready=False,scope='EXPLICIT_TEST_ONLY_SYNTHETIC_NOT_REAL'))
    write('RUNTIME_CONSUMER_PARITY_GATE',dict(status='PASS_LOCAL_REPAIRED',contract=contract,runtime_dependencies=deps,consumer='scripts/v4_16_go_forward_input_authority_r4r2.py',runtime='scripts/v4_16_go_forward_shadow_runtime_r4r2.py',frozen_constructor_bytecode_reused=True,real_authority_disabled=True,engineering_constructor_disclosure='Exact bridge/daily checks executed; external/native acceptance and immutable algorithm view supplied by explicit test seams. No controller grant or DB is opened.'))
    wait=produce_bridge(ROOT,parent=None,child=None,candidate=None,source=None,receipts=None,observation=None,target='2026-10-08',observed_at=datetime.now(timezone.utc).isoformat(),output='reports/r25/target_session_bridge/not_created.json')
    assert wait['status']=='WAIT_MARKET_CLOSE' and wait['source_requests']==0 and not (ROOT/'reports/r25/target_session_bridge/not_created.json').exists()
    write('FUTURE_SESSION_WAIT_READBACK',dict(wait,selection=selection(ROOT),real_target_session_package='NOT_CREATED',R25='WAIT_ACCEPTED_DAILY_INPUT'))
    entry=json.loads((folder/'ENTRY_BASELINE.json').read_bytes())
    allowed={'.gitattributes','scripts/validate_r25_preflight.py','tests/test_r25_packet.py'}
    changed={p:dict(before=h,after=r.sha(ROOT/p)) for p,h in entry['tracked'].items() if r.sha(ROOT/p)!=h}
    assert set(changed)<=allowed,changed
    assert all(r.sha(ROOT/p)==h for p,h in entry['unrelated'].items())
    state=protected(ROOT)
    write('PROTECTED_STATE',dict(status='PASS',protected=state,declared_existing_source_changes=changed,unrelated_preserved=True,
        unchanged_R4R1_core=[r.ref(ROOT,ROOT/p) for p in ['src/workbench_analysis/dm01_runtime_r4.py','src/workbench_analysis/dm01_lineage_r4r1.py','src/workbench_analysis/dm01_incremental_component_builders_r3_3.py','src/workbench_analysis/dm01_independent_postcheck_r3_3.py','config/dm01_go_forward_runtime_contract_r4r1.json','config/dm01_v2_promotion_policy_r4r1.json','data/v4/DM01_R4_CALENDAR_HEAD_V1.json']],
        real_target_session_package='NOT_CREATED',R25='WAIT_ACCEPTED_DAILY_INPUT',real_shadow_execution='NOT_STARTED',real_shadow_observations=0,PIT_OBSERVED_REAL_SAMPLES=0,tdx_root_write_count=0,source_requests=0,permissions=r.PERMISSIONS))
    print(dict(status='PASS_R4R2_ENGINEERING_GATES',next='STOP_WAIT_DM01_R4R2_INDEPENDENT_EXTERNAL_AUDIT'))
if __name__=='__main__':main()

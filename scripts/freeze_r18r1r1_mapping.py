"""Explicit field/interface mapping; never derived from execution receipts."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_replay_io import publish,ref
from scripts.v4_14_independent_edge_oracle_r18r1 import EdgeOracle

def run():
    o=EdgeOracle(ROOT)
    mappings={
        ('F0','A','base_seed_primitives'):('/base_seed_primitives','/seed_facts'),
        ('F0','C','stock_core'):('/stock_core','/stock_core'),
        ('A','C','base_seed_raw'):('/base_seed_state','/base_seed_raw'),
        ('C','D0','stock_prewatch_raw'):('/raw_qualification','/projection/replay_prewatch_lineage/value'),
        ('F0','D1','core_facts'):('/core_facts','/core_facts'),
        ('D1','D1','frozen_anchor_event'):('/event','/prior_anchor_event'),
        ('D0','D2','confirmation'):('/rows/0/confirmation_status','/values/CONFIRMED'),
        ('C','D2','stock_raw'):('/raw_qualification','/values/PREWATCH'),
        ('D2','D2','frozen_prior_state'):('/rows/0','/prior_state'),
        ('D0','EVENT_DIFF','confirmation_facts'):('/rows/0','/confirmation_facts'),
        ('D2','EVENT_DIFF','final_state'):('','/d2_publication'),
        ('D2','EVENT_DIFF','frozen_prior_final_state'):('','/prior_d2_publication'),
        ('D3_CONTEXT','D3','context_fields'):('','/context'),
        ('D2','GATE_B_OBSERVATION','state_readback'):('','/state'),
        ('D3','GATE_B_OBSERVATION','profile_context_readback'):('','/profile')}
    degraded={
        ('F0','B0','sector_native'):'/sector_native',('A','B0','base_seed_aggregates'):'/base_seed_state',
        ('B0','B1','rotation_core_state'):'',('B0','B2','sector_raw_qualification'):'/output_state',
        ('D1','D2','structure'):'/observation/support',('B0','D3_CONTEXT','non_target_sector_raw'):'/output_state',
        ('B1','D3_CONTEXT','loo_rotation_history'):'',('B2','D3_CONTEXT','non_target_sector_raw'):'',
        ('D1','D3','structure_projection'):'/observation/support',('D1','D3','rotation_structure_enrichment'):'/observation/support',
        ('MEMBERSHIP','D3_CONTEXT','date_valid_membership'):'',('F0','D3_CONTEXT','non_target_core_facts'):'/stock_core',
        ('F0','D3_CONTEXT','non_target_native_facts'):'/sector_native',('A','D3_CONTEXT','non_target_base_seed_raw'):'/base_seed_state',
        ('B1','D3_CONTEXT','rotation_core_state_read_only_for_enrichment'):''}
    rows=[]
    for e in o.expected_edges.values():
        key=(e['producer'],e['consumer'],e['field'])
        if key in mappings:projection,arg=mappings[key];mode='EXACT_ARGUMENT'
        else:projection=degraded[key];arg='/capabilities/'+e['edge_id'];mode='ACCEPTED_CAPABILITY_GATE'
        if key in [('C','D0','stock_prewatch_raw'),('D1','D1','frozen_anchor_event'),('D0','EVENT_DIFF','confirmation_facts'),('D3_CONTEXT','D3','context_fields')]:mode='PRECALL_READ_ONLY_VALIDATION'
        rows.append(dict(e,producer_projection=projection,consumer_argument_path=arg,binding_mode=mode))
    return publish(ROOT,'config/v4_14_precall_consumption_mapping_r18r1r1_v1.json',dict(contract_id='V4_14_PRECALL_FIELD_CONSUMPTION_MAPPING_V1',version='1.0.0',frozen_dag=ref(ROOT,'config/v4_14_temporal_non_edge_registry_v1_1.json'),fixture_package=ref(ROOT,'config/v4_14_edge_producer_fixtures_r18r1_v1.json'),owner_interfaces=[ref(ROOT,p) for p in ['src/v4/base_seed.py','src/v4/stock_prewatch.py','src/v4/confirmation_events.py','src/v4/confirmation_d2_bridge.py','src/workbench_analysis/v4_12_structure_engine.py','src/workbench_analysis/v4_13_profile_runtime.py']],mappings=rows,event_interface_resolution='Read-only D0 row validation against actual D2 CONFIRMED/scenario provenance; accepted verify_d2_publication and state_events retain their rules. No new direct predicate.',structure_fixture_resolution='F0 core_facts is exact defaults plus selected frozen V4-12 vector and exact persisted separated-session counter; ledger.observe consumes this dictionary.',degraded_rule='Pre-call UNKNOWN capability gate; upstream reference is evidence, never a fabricated argument or whole-node EXECUTED substitute.',runtime_artifacts_are_append_only=True))
if __name__=='__main__':print(json.dumps(run()))

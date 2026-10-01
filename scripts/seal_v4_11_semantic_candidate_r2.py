"""Final R2 lineage, vector and validation bindings; keep first attempt immutable."""
from collections import Counter
import gzip,json
from scripts.next_round_bundle_r2 import ROOT,read,write,bind,verify_protected

def main():
    base='reports/v4_11/candidate_r2/'
    c=read('config/v4_11_confirmation_detector_contract_r2.json')
    head=read(c['accepted_data_head']['path'])
    native_head=bind('data/v4/V4_03_ACCEPTED_HEAD.json')
    representations=read('reports/next_round_r1/BATCH_PROTECTED_REPRESENTATIONS_R1.json')['representations']
    original_native=next((r for r in representations if r['original_binding']==native_head),None)
    if original_native:native_head=original_native['git_representation']
    lineage=write(base+'REAL_STOCK_AMR20_SOURCE_AVAILABILITY_R1.json',dict(
        contract_id='STOCK_AMR20_TARGET_SOURCE_AVAILABILITY_R2',field='amr20_mean_prior',
        producer='TODAY_RESEARCH_FACTOR_V3_3_CANDIDATE_01',native_family='STOCK_AMOUNT_VOLUME_STATE_V1',
        numerator_field='RAW_DAILY.amount',numerator_unit='raw_CNY',output_unit='dimensionless_ratio',
        wire_unit='fraction',target_trade_date='2026-09-30',prior_window_end='2026-09-29',
        prior_window_master_sessions=20,target_in_denominator=False,
        actual_source_input_digest=head['component_artifacts']['RAW_DAILY']['sha256'],
        target_accepted_raw_source=head['component_artifacts']['RAW_DAILY'],
        accepted_calendar=head['calendar'],accepted_source_chain=head['accepted_chain'],
        source_formula=read(c['semantic_erratum']['path'])['source'],
        target_AMR20_accepted_publication=None,accepted_AMR20_input_digest=None,
        raw_source_accepted=True,derived_target_AMR20_accepted=False,
        reason='STOCK_AMR20_TARGET_ACCEPTED_PRODUCER_PUBLICATION_UNAVAILABLE',
        native_amount_ratio20_prior_window_contract=bind('config/v4_03_algorithm_contracts_v1.json'),
        native_accepted_head=native_head,native_original_bytes_representation=original_native,native_accepted_head_target='2026-09-24',
        native_head_does_not_accept_20260930_AMR20=True,AS_RECORDED=False))
    summary=read(base+'FULL_MARKET_SUMMARY_R1.json')
    payload=json.loads(gzip.decompress((ROOT/summary['confirmation_publication']['path']).read_bytes()))
    summary['scenario_status_counts']={s:dict(Counter(e['status'] for r in payload['rows'] for e in r['scenario_evidence'] if e['scenario']==s)) for s in summary['scenario_counts']}
    summary['stock_AMR20_source_availability']=lineage
    sb=write(base+'FULL_MARKET_SUMMARY_R2.json',summary)
    golden=read(base+'ACTIVE_GOLDEN_EXPECTATIONS_R2.json')
    value=golden['active_expected'].pop('SECTOR_AMOUNT_A_STATUS_IRRELEVANT')
    golden['active_expected']['SECTOR_AMOUNT_A_STATUS_IRRELEVANT_TO_STOCK_CONFIRMATION']=value
    golden['semantic_vector_scope']='AMR20_PREDICATES; OTHER_SCENARIOS_KEEP_THEIR_OWN_REQUIRED_FACTS'
    golden['active_tests']=[bind(p) for p in ['tests/v4_11/test_confirmation.py','tests/v4_11/test_semantic_r2.py','tests/v4_11/test_persistence.py','tests/v4_a04_r3/test_stock_confirmation_independence.py']]
    gb=write(base+'ACTIVE_GOLDEN_EXPECTATIONS_R3.json',golden)
    handoff=read(base+'V4_11_SEMANTIC_REPAIR_EXTERNAL_REAUDIT_HANDOFF_R1.json')
    handoff.update(full_market=sb,active_golden=gb,source_availability=lineage,
        supersedes=bind(base+'V4_11_SEMANTIC_REPAIR_EXTERNAL_REAUDIT_HANDOFF_R1.json'),
        targeted_persistence_and_semantic=bind(base+'TARGETED_PERSISTENCE_SEMANTIC_R2.xml'))
    write(base+'V4_11_SEMANTIC_REPAIR_EXTERNAL_REAUDIT_HANDOFF_R2.json',handoff)
    verify_protected()

if __name__=='__main__':main()

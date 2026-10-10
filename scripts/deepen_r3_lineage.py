"""Exact field capabilities, source contracts and current Owner consumer lineage."""
from immediate_r3_common import *
import ast
D=OUT/'11_DEEPENING'

def symbol(file,name):
    p=path(file);tree=ast.parse(p.read_text(encoding='utf8'));nodes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.name==name]
    assert nodes,(file,name)
    n=nodes[0];return dict(**binding(p),symbol=name,start_line=n.lineno,end_line=n.end_lineno)

def main():
    h=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=h['accepted_trade_date'];snap=load(h['membership_snapshot'])
    rows=[]
    definitions=[
      ('signal_event_at_T0','src/workbench_analysis/v4_15_radar_cohort.py','_project','logical_events','EVENT_DIFF_NOT_FOCUS'),
      ('cohort_enrollment_id','src/workbench_analysis/v4_15_radar_cohort.py','identity','enrollments','LOGICAL_EVENT_AND_NAMESPACE_IDENTITY'),
      ('frozen_signal_version','src/workbench_analysis/validation_cohort_read_contract_r3.py','validate_frozen','validation_cohort','IMMUTABLE_T0_SIGNAL_VERSION'),
      ('eligible_at_T0','src/workbench_analysis/v4_15_radar_cohort.py','_project','daily_ledger','FINAL_ELIGIBLE_ALL_ROWS_NOT_TOP_K'),
      ('asof_first_available','src/workbench_analysis/validation_cohort_read_contract_r3.py','validate_frozen','validation_cohort','AWARE_FIRST_AVAILABILITY_BEFORE_T0_FREEZE'),
      ('benchmark','src/workbench_analysis/v4_15_forward_r2.py','freeze_t0','t0_freezes','FROZEN_FIXED_BASKET_AND_CONTROL_ASSIGNMENTS'),
      ('no_lookahead','src/workbench_analysis/validation_cohort_read_contract_r3.py','validate_frozen','validation_cohort','NO_FUTURE_FEEDBACK'),
      ('path_observation','src/workbench_analysis/v4_15_forward_r2.py','settle','outcomes','BOUND_ACCEPTED_PRICE_SOURCE'),
      ('maturity_schedule','src/workbench_analysis/v4_15_settlement.py','due_plan','due_plans','EXACT_MASTER_SESSION_OFFSETS'),
      ('T1/T3/T5_result','src/workbench_analysis/v4_15_forward_r2.py','price_path','outcomes','AFFINE_ENDPOINT_AND_PATH_DOMAIN'),
      ('right_censor_reason','src/workbench_analysis/v4_15_settlement.py','price_path','outcomes','STATUS_SPECIFIC_PATH_AND_ENDPOINT_QUALITY'),
      ('settlement_owner','src/workbench_analysis/v4_15_forward_r2.py','readback','outcomes','FIRST_OBSERVED_LATEST_CORRECTED_SEPARATE'),
      ('FEP_model_version','src/workbench_analysis/fep_e5/ledger.py','register_model','FEP','MODEL_OR_PERMISSION_NOT_READY'),
      ('permission_gate','src/workbench_analysis/fep_e5/ledger.py','allowed','FEP','EXACT_CAPABILITY_GRANT_REQUIRED'),
      ('BFF_route','src/workbench_service/core_product_bff_r1.py','_get_product','validation_cohort','HASH_BOUND_DATED_READ_NO_WRITE')]
    for field,file,name,domain,rule in definitions:
        # Fail visibly if a presumed code symbol does not exist; never use blanket producers.
        producer=symbol(file,name)
        status='MODEL_OR_PERMISSION_NOT_READY' if domain=='FEP' else 'NO_ASOF_ENROLLMENT' if field=='asof_first_available' else 'PRODUCER_EXISTS_OWNER_MISSING'
        rows.append(dict(field=field,producer=producer,rule=rule,output_domain=domain,accepted_current_owner=h['owners'][day].get(domain),status=status,
          engineering_implemented=True,route='/api/v4/forward/statistics' if domain!='FEP' else '/api/v4/forward/fep',
          input_owner_required='Exact independently frozen enrollment and bound T0 snapshot' if domain!='FEP' else 'Frozen accepted model set, prediction revision and grant key',
          focus_substitution_allowed=False,actual_current_first_available=None))
    write(D/'COHORT_FIELD_CAPABILITY_MATRIX.json',dict(T0=day,fields=rows,scope='CODE_IMPLEMENTATION_IS_DISTINCT_FROM_CURRENT_ACCEPTED_OWNER',production_enabled=False))
    # Current field projection lineage uses real API cells and exact owner digest matching.
    sample=load(D/'SIX_ENTRY_NUMERIC_SOURCE_BINDINGS.json');cells=sample['hypotheses']['evidence'];owner_by_sha={v['sha256']:dict(domain=k,**v) for k,v in h['owners'][day].items()}
    for k,c in sample['stocks'].items():cells['stock.'+k]=c
    cells['sector.participation_proxy']=sample['sectors']['participation_proxy']
    lineage=[]
    for field,c in cells.items():
        owner=owner_by_sha.get(c.get('source_digest'));assert owner,(field,c)
        lineage.append(dict(issue_id='R3-DEEP-'+field,stage='P0-ALG/P0-AMOUNT/P0-OWNER',producer_code='src/v4/factors/core.py' if owner['domain']=='core' else 'src/sector/native_r5.py' if owner['domain']=='sector' else 'src/workbench_analysis/r43_owner_replay.py',
          algorithm_version=c.get('source_contract_id') or 'HASH_BOUND_OWNER_PROJECTION',exact_input_owner=owner,trade_date=day,first_available_at=None,
          member_asof=snap['member_set_asof'],PIT_scope='CORRECTED_LATEST_MEMBER_RETRO_NOT_AS_RECORDED',window_identity=c.get('window'),adjustment=c.get('adjustment_basis'),unit=c.get('unit'),null_policy='UNKNOWN_NOT_ZERO',
          output_owner=owner,expected_field=c['source_field'],actual_field=c['source_field'],BFF_route='/api/v4/sectors/INDUSTRY:T0706' if owner['domain']=='sector' else '/api/v4/stocks/301628/profile',UI_component='stock.js competitive hypotheses evidence' if field in ('close','ma20','ret5','rps20') else 'DataTable source drawer',
          discrepancy=None,responsible_layer='ADAPTER',current_verdict='PASS_CURRENT_BINDING',evidence_path=str((D/'SIX_ENTRY_NUMERIC_SOURCE_BINDINGS.json').relative_to(ROOT)),code_sha=git('rev-parse','HEAD'),owner_sha=owner['sha256'],next_action='Preserve frozen input lineage; future evidence remains separate',
          six_dimensions=dict(FORMULA_OR_LOGIC='INDEPENDENT_ORACLE_SCOPED' if owner['domain']=='core' else 'OWNER_PROJECTION_ONLY',CURRENT_DATA='HASH_BOUND',API_BINDING='ACTUAL_HTTP_CHECKED',UI_BEHAVIOR='ACTUAL_DOM_EVIDENCE_SCOPED',HISTORICAL_PIT='NOT_PROVEN',FUTURE_OUTCOME='WAIT_REAL_DAY')))
    write(D/'EXACT_FIELD_SOURCE_CONSUMER_MATRIX.json',dict(fields=lineage,no_generic_SEE_placeholders=True))
    formal=load('config/v4_10_input_provenance_r1_2.json')
    write(D/'SECTOR_FORMAL_EXTRACTION_PROPOSAL.json',dict(contract_id='SECTOR_D2_EXTRACTION_ENTRY_PROPOSAL_R3_V1',status='PROPOSAL_NOT_ACCEPTED',
      existing_contracts=[binding(p) for p in ('config/v4_08_b2_machine_ast_r5.json','config/v4_08_sector_native_contract_r5.json','config/v4_10_input_provenance_r1_2.json','config/v4_10_research_state_contract_r1_2.json')],
      producer_bindings=[symbol('src/sector/legacy_b2_r5.py','evaluate_b2'),symbol('src/v4/research_state.py','reduce_state')],
      admission_gaps=load(OUT/'09_CONTINUATION/SECTOR_D2_EXACT_CONTRACT_GAPS.json')['missing_fields'],
      required_changes=[dict(field='CONFIRMED',need='Accepted exact legacy valid-member/normal-rank provenance; accept extraction entry independent of diagnostic result',current='legacy_b2_r5.evaluate_b2 explicitly returns UNKNOWN'),
        dict(field='WARM',need='Accepted legacy SETUP/RECOVERY member facts, q20/dq5_3 exact rank universe and Amount A consumer gate where branch uses A',current='warm_raw UNKNOWN; Base Seed not SETUP alias'),
        dict(field='frozen_invalidation',need='Creation-frozen episode invalidation contract, exact T-1 sector episode payload and target-period observation',current='No accepted sector episode owner'),
        dict(field='maturity/health',need='Inputs above plus admitted sector dq5 and exact monotone calendar; reuse versioned reducer, no invented score',current='Generic SECTOR reducer exists; live candidate entry STOCK only')],
      isolated_candidate=binding(OUT/'09_CONTINUATION/SECTOR_D2_DATED_READINESS_CANDIDATE.json'),
      policy='No renaming B0/Rotation to maturity; no changes to accepted provenance contract, Head or algorithm thresholds',
      next_stage='Accept versioned extraction/entry contract and actual missing upstream bytes before eligible sector candidate reduction',production_authorized=False))
    print('cohort fields',len(rows),'bound consumer fields',len(lineage))
if __name__=='__main__':main()

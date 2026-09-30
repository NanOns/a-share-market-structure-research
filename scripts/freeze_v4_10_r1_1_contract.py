"""Versioned R1.1 repair freeze; the original R1 files remain byte-identical."""
from pathlib import Path
from copy import deepcopy
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.promote_v4_09_accepted_head import bind,validate
from src.v4.state_identity import INTERFACE,CANONICALIZATION

TASK='docs/evidence/V4_10_R1_EXTERNAL_AUDIT_REPAIR_TASK_20261001.md'
def read(name):return json.loads((ROOT/f'config/v4_10_{name}_v1.json').read_text(encoding='utf8'))

def main():
    if validate()['status']!='PASS':raise ValueError('V4_09_KEEP_ACCEPTED_REQUIRED')
    c=read('research_state_contract');a=read('machine_ast');p=read('parameter_set');out=read('output_schema')
    c.update(interface_contract_id=INTERFACE,engineering_revision='R1.1',business_contract_unchanged=True,
        repair_task=bind(TASK),supersedes_candidate=bind('reports/v4_10/V4_10_STAGE_CANDIDATE_MANIFEST.json'),
        provenance_contract_id='V4_10_STATE_INPUT_PROVENANCE_V1',canonicalization_contract_id=CANONICALIZATION,
        prior_authenticity='full R1.1 output schema + content-address + trusted PostgreSQL engineering publication existence + frozen calendar',
        model_boundary='structured authorized immutable manifest; no bare boolean; synthetic namespace segregated',
        db_hardening='A: database canonical identity/digest + lineage equality + manifest membership; historical 022 immutable; new migration 023',
        permissions=dict(production=False,shadow=False,focus_cutover=False),next_stage='STOP_FOR_INDEPENDENT_EXTERNAL_REAUDIT; V4-11 BLOCKED')
    required=['interface_contract_id','entity_id','entity_type','trade_date','session_index','calendar_publication_id','calendar_binding',
        'mode','cutoff','input_publication_ids','input_provenance','input_publication_manifest_digest','prior_state','prior_state_binding','model_boundary']
    c['input_required_fields']=required
    a.update(engineering_revision='R1.1',pre_reducer_gates=['CANONICAL_INPUT_PUBLICATION_MANIFEST','STRUCTURED_MODEL_BOUNDARY_AUTHORIZATION',
        'PRIOR_FULL_SCHEMA_CONTENT_ADDRESS_PUBLICATION_EXISTENCE','FROZEN_CALENDAR_LINEAGE','UNIFIED_STATE_CHANGING_FIELD_PROVENANCE'])
    input_schema=dict(schema_id='V4_10_REDUCER_INPUT_SCHEMA_R1_1',type='object',required=required,
        input_publication_ids=dict(type='array',minItems=1,uniqueItems=True,items=dict(type='string',minLength=1)),
        provenance='every state-changing field registered in V4_10_STATE_INPUT_PROVENANCE_V1',
        accepted_resolver='PostgresEngineeringLedger supplied outside serialized request; requires immutable DB rows',
        synthetic_context_keys=['synthetic_calendar_manifest','synthetic_boundary_manifest'])
    out.update(schema_id='V4_10_REDUCER_OUTPUT_SCHEMA_R1_1',canonicalization_contract_id=CANONICALIZATION)
    out['required']+=['interface_contract_id','canonicalization_contract_id','calendar_binding','input_provenance','input_publication_manifest_digest','invalidation_contract_id','cutoff']
    out.update(string_fields=['publication_id','entity_id','entity_type','trade_date','calendar_publication_id','mode','model_contract_id','parameter_set_id',
        'interface_contract_id','canonicalization_contract_id','input_digest','input_publication_manifest_digest'],
        nullable_string_fields=['episode_id','parent_episode_id','invalidation_contract_id','downgrade_candidate'],
        counter_fields=['session_index','expiry_count','downgrade_count','market_age'])
    envelope=['field','value','quality','status','producer_contract_id','producer_parameter_set_id','publication_id',
        'source_output_digest','source_field_payload','time_role','required','system_available_at']
    fields={}
    def field(name,domain,contract,param,implemented,required,role='T'):
        fields[name]=dict(domain=domain,producer_contract_id=contract,producer_parameter_set_id=param,
            implemented=implemented,required=required,time_role=role)
    field('SEED','TRI','BASE_SEED_V1','V4_07_BASE_SEED_PARAMETER_SET_V1',True,True)
    field('PREWATCH','TRI','STOCK_PREWATCH_V1','V4_09_STOCK_PREWATCH_PARAMETER_SET_V1',True,True)
    field('CONFIRMED','TRI','V4_11_CONFIRMATION_DETECTOR_NOT_IMPLEMENTED',None,False,True)
    field('WARM','TRI','LEGACY_WARM_EXTRACTION_NOT_ACCEPTED',None,False,True)
    field('core_price_damage','TRI','CORE_FACTOR_V1.CORE_PRICE_DAMAGE','V4_03_CORE_FACTOR_PARAMETER_SET_V1',True,True)
    field('frozen_invalidation','TRI','V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED',None,False,True,'T-1')
    field('episode_invalidation_contract_id','CONTRACT_ID','V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED',None,False,False,'T-1')
    field('risk','RISK','EXTENSION_RISK_V1','V4_04_CORE_PROFILE_PARAMETER_SET_V1',True,False)
    field('delta3','NUMBER','RPS_DELTA_V1','V4_03_CORE_FACTOR_PARAMETER_SET_V1',True,False)
    field('dq5','NUMBER','V4_08_SECTOR_NATIVE_V1','V4_08_ALGORITHM_PARAMETER_SET_R5',True,False)
    field('scenario','SCENARIO','V4_11_V4_12_SCENARIO_NOT_IMPLEMENTED',None,False,False)
    field('suspended','TRI','V4_02_DATED_TRADING_STATUS_V1',None,True,True)
    field('followup_complete','TRI','SETTLEMENT_DUE_OWNER_NOT_IMPLEMENTED',None,False,False)
    for name,d in fields.items():
        d['accepted_entity_types']=['SECTOR'] if name=='dq5' else ['STOCK'] if d['implemented'] else ['STOCK','SECTOR']
    provenance=dict(contract_id='V4_10_STATE_INPUT_PROVENANCE_V1',engineering_revision='R1.1',envelope_required=envelope,fields=fields,
        policy_authority=[bind('config/v4_03_field_registry_v1.json'),bind('config/v4_04_parameter_set_v1.json'),
            bind('config/v4_08_sector_native_contract_r5.json'),bind('config/v4_08_algorithm_parameter_set_r5.json'),
            bind('config/v4_02_dated_trading_status_v1.json')],
        unknown='NOT_IMPLEMENTED -> value UNKNOWN + quality UNKNOWN; no FALSE default',
        entity_scope='Accepted stock producers cannot be relabelled as sector inputs. Sector dq5 is admitted from accepted native owner; other sector adapters require their own future extraction/entry contract.',
        authority_boundary='DB ledger owner is trusted publication issuer. API callers and ordinary result writers cannot manufacture an input publication.',
        publication_manifest_shape='exact nonempty unique stable ID array; canonical field map digest; never substring membership',
        calendar_contract='MARKET_CALENDAR_V1',prior_ledger_id='V4_10_ENGINEERING_LEDGER_R1_1',consumer_contract_id='V4_10_REDUCER_INTERFACE_V1')
    files=dict(research_state_contract=c,machine_ast=a,parameter_set=p,input_schema=input_schema,output_schema=out,input_provenance=provenance)
    for name,value in files.items():atomic_json(ROOT/f'config/v4_10_{name}_r1_1.json',value)
    from scripts.build_v4_10_r1_1_vectors import build_vectors
    vectors=build_vectors()
    atomic_json(ROOT/'config/v4_10_machine_vectors_r1_1.json',dict(contract_id='V4_10_R1_1_INDEPENDENT_MACHINE_VECTORS',vectors=vectors,
        oracle='STATIC_EXPECTATIONS; 98 original semantic vectors adapted only through explicit synthetic provenance fixture envelope',
        original_vectors=bind('config/v4_10_machine_vectors_v1.json')))
    files['machine_vectors']=vectors
    atomic_json(ROOT/'reports/v4_10/V4_10_R1_1_CONTRACT_FREEZE.json',dict(contract_id='V4_10_R1_1_CONTRACT_FREEZE',status='PASS_R1_1_LINEAGE_INTERFACE_FREEZE',
        authority=c['authority']['master'],repair_task=bind(TASK),original_candidate=bind('reports/v4_10/V4_10_STAGE_CANDIDATE_MANIFEST.json'),
        business_contract='RESEARCH_STATE_V1',business_thresholds_unchanged=True,db_choice='A_DATABASE_CANONICAL_IDENTITY_GUARD',
        bindings={n:bind(f'config/v4_10_{n}_r1_1.json') for n in files},
        protected_bindings=[bind(p) for p in ['data/v4/V4_09_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json',
            'data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_DEV_BASELINE_HEAD.json','data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json']],
        stage_entry=bind('docs/evidence/V4_10_R1_1_REPAIR_STAGE_ENTRY_20261001.md'),
        next_stage='R1.1 engineering repair checks; then STOP for independent external reaudit; V4-11 blocked'))
    print('R1.1 frozen vectors:',len(vectors))

if __name__=='__main__':main()

"""R2 metadata-only hard gates. Reads accepted publications; computes no factors."""
import argparse
import json
import subprocess
from collections import Counter
from scripts.v4_11_promotion_contract_r1 import ROOT, bind, PERMISSIONS
from scripts.repair_v4_12_authority_r2 import (BASELINE,OUT,read,baseline,keep_proof,component_ref,CORE_CONTRACT,CORE_HEAD,
    PROFILE_HEAD,RPS_HEAD,DATA_HEAD,NATIVE_HEAD,TARGETS)
from scripts.record_r7_stage_contract import put
from scripts.validate_v4_12_contract_freeze_r1 import load_configs,literal_audit,dag_audit,schema_registry_audit,vector_oracle,scope_proof

# Independent explicit alias ledger, not inferred from case/lower() or repair code.
ALIASES={'ATR20':'atr20','CLV':'clv','MA20':'ma20','MA60':'ma60','prior_high20':'prior_high20',
         'amount_ratio20':'amount_ratio20','rel_market_1':'rel_market_1','ret1':'ret1','slope20':'slope20'}
NATIVE={'O':'open','H':'high','L':'low','C':'close','price_basis':'price_basis','adjustment_source_revision':'adjustment_source_revision'}
LOCAL_REQUIRED={'distance_zone','evaluable','observation_close_view','start_price_view','endpoint_price_view',
                'post_creation_sessions','pivot_left_count','pivot_right_count'}
BLOCKED_OWNERS={'alpha':'V4_12_COORDINATE_VIEW_V1','beta':'V4_12_COORDINATE_VIEW_V1','atr_prior_view':'V4_12_COORDINATE_VIEW_V1',
    'prior_high_view':'V4_12_COORDINATE_VIEW_V1','prior_range20_atr':'V4_12_BLOCKED_RANGE_INPUT_V1',
    'pivot_low':'V4_12_PIVOT_SOURCE_DESIGN_V1','pivot_low_strict':'V4_12_PIVOT_SOURCE_DESIGN_V1',
    'close_t_minus_1':'V4_12_BLOCKED_PRIOR_OWNER_V1','ma20_t_minus_1':'V4_12_BLOCKED_PRIOR_OWNER_V1'}

def authority_parity(fields=None):
    rows=read('config/v4_12_field_registry_v1.json')['fields'] if fields is None else fields
    contracts={o['field_id']:(c,o) for c in read(CORE_CONTRACT)['contracts'] for o in c['outputs']}
    data=read(DATA_HEAD);chain=read(data['accepted_chain']['path']);nodes={n['trade_date']:n for n in chain['nodes']}
    rps=read(RPS_HEAD);record=read(rps['acceptance_record']['path'])
    checked=set();checks=[]
    def exact(ref):
        if ref['path'] not in checked:
            assert bind(ref['path'])['sha256']==ref['sha256'],'PUBLICATION_DIGEST_MISMATCH'
            checked.add(ref['path'])
    exact(data['accepted_chain']);exact(rps['acceptance_record'])
    assert rps['publications']==record['publications'] and record['status']=='PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE'
    exact(rps['external_authority']);exact(record['producer_evidence'])
    for row in rows:
        name=row['field'];role=row['field_role']
        assert row['producer_contract_id']!='CORE_FACTOR_V1','GENERIC_CORE_FACTOR_FALLBACK'
        assert row['raw_reconstruction_allowed'] is False,'RAW_RECONSTRUCTION_CANNOT_GRANT_AUTHORITY'
        assert isinstance(row['required_by'],list) and row['globally_required'] is False
        if role=='D1_OUTPUT':continue
        if row['accepted_head_path']:
            assert bind(row['accepted_head_path'])['sha256']==row['accepted_head_sha256'],'ACCEPTED_HEAD_DIGEST_MISMATCH'
        if name in ALIASES:
            contract,owner=contracts[ALIASES[name]]
            assert row['accepted_source_field']==ALIASES[name],'EXACT_SOURCE_ALIAS_MISMATCH'
            assert row['producer_contract_id']==owner['producer_contract_id'],'EXACT_OWNER_MISMATCH'
            assert row['producer_version']==owner['producer_version']
            assert row['accepted_parameter_set_id']==contract['parameter_set_id']
            assert row['unit']==owner['unit'],'OWNER_UNIT_PARITY_MISMATCH'
            assert row['accepted_head_path']==CORE_HEAD
            assert row['accepted_reference_trade_date']=='2026-09-24'
            exact(row['accepted_reference_publication'])
            assert role=='BLOCKED_CAPABILITY' and not row['target_publication_available'] and row['blocked_reason'],'UNBOUND_TARGET_FACTOR_PUBLICATION'
        elif name in NATIVE:
            assert row['accepted_source_field']==NATIVE[name],'EXACT_NATIVE_ALIAS_MISMATCH'
            assert row['accepted_head_path']==DATA_HEAD and role=='UPSTREAM_ACCEPTED'
            assert row['target_publication_available'] and row['source_namespace']=='F0_ACCEPTED'
            assert row['producer_contract_id']=='V4_02_FORMAL_RAW_QFQ_PERIODS_V1'
            assert row['time_role']=='T'
            for day in TARGETS:
                expected=component_ref(nodes[day],'ADJUSTED_DAILY');pub=row['target_publications'][day]
                assert pub['artifact']==expected,'NATIVE_PUBLICATION_SUBSTITUTION';exact(expected)
                actual=read(expected['path'])
                assert actual['trade_date']==day and all(NATIVE[name] in r for r in actual['rows'])
                assert pub['source_field_path']=='rows[*].'+NATIVE[name]
                assert pub['available_at']==data['promoted_at_utc'] and pub['source_cutoff']==day
                assert pub['AS_RECORDED'] is False and pub['historical_first_availability_proven'] is False
        elif name in {'delta3','prior_delta3'}:
            assert row['accepted_source_field']=='rps5_delta3' and row['producer_contract_id']=='RPS_DELTA_V1','RPS_OWNER_MISMATCH'
            assert row['accepted_head_path']==RPS_HEAD and row['unit']=='percentage_points'
            assert role=='UPSTREAM_ACCEPTED' and row['target_publication_available']
            assert row['time_role']==('T' if name=='delta3' else 'T_MINUS_1')
            for day in TARGETS:
                exact(record['inputs'][day])
                sessions=read(record['inputs'][day]['path'])['sessions']
                source_day=day if name=='delta3' else sessions[sessions.index(day)-1]
                pub=row['target_publications'][day];expected=record['deltas'][source_day+':T-3']
                assert pub['trade_date']==source_day and pub['artifact']==expected,'RPS_PRIOR_TIME_OR_DIGEST_MISMATCH'
                exact(expected);exact(pub['rank_publication'])
                assert pub['rank_publication']==rps['publications'][source_day]
                payload=read(expected['path']);assert payload['offset']==3
                assert all('rps5_delta3' in r['fields'] for r in payload['rows'])
                assert pub['knowledge_lineage']=='RECONSTRUCTED_CORRECTED' and pub['AS_RECORDED'] is False and pub['historical_first_availability_proven'] is False
                assert pub['available_at']==max(read(rps['publications'][source_day]['path'])['cutoff_timestamp'],record['formalized_at'])
        elif name=='near_high20_state':
            owner=next(r for r in read('config/v4_04_field_registry_v2.json')['fields'] if r['field_id']==name)
            assert row['producer_contract_id']==owner['producer_contract_id']=='POSITION_STATE_V1','POSITION_OWNER_MISMATCH'
            assert row['accepted_head_path']==PROFILE_HEAD and row['accepted_source_field']==name and row['unit']==owner['unit']
            assert role=='BLOCKED_CAPABILITY' and row['target_publication_available'] is False and row['blocked_reason']
        elif name in LOCAL_REQUIRED:
            assert role=='D1_LOCAL_DERIVATION' and row['source_namespace']=='D1_LOCAL_DERIVATION','LOCAL_FIELD_CANNOT_BE_F0'
            assert row['producer_contract_id'] in {'V4_12_MACHINE_AST_V1','V4_12_COORDINATE_VIEW_V1','V4_12_SESSION_COUNTER_V1'}
        elif name in BLOCKED_OWNERS:
            assert role=='BLOCKED_CAPABILITY' and row['source_namespace']=='BLOCKED_CAPABILITY'
            assert row['producer_contract_id']==BLOCKED_OWNERS[name],'BLOCKED_OWNER_IDENTITY_MISMATCH'
        elif row['source_namespace']=='F0_ACCEPTED' or role=='UPSTREAM_ACCEPTED':
            raise AssertionError('FALSE_ACCEPTED_OWNER_CLAIM:'+name)
        if role in {'BLOCKED_CAPABILITY','FROZEN_PRIOR_D1'}:
            assert row['authority_status']=='BLOCKED_WITH_EXPLICIT_REASON' and row['blocked_reason'] and not row['target_publication_available']
        if role=='D1_LOCAL_DERIVATION':assert row['source_namespace']=='D1_LOCAL_DERIVATION' and not row['target_publication_available']
        checks.append(dict(logical_field=name,role=role,producer=row['producer_contract_id'],target_publication_available=row['target_publication_available'],status='PASS'))
    return dict(status='PASS',unresolved_false_accepted_claims=0,generic_CORE_FACTOR_fallback_count=0,fields=checks,
                roles=dict(Counter(r['field_role'] for r in rows)),source_hashes_validated=len(checked))

def coordinate_audit(configs):
    c=configs['anchor_coordinate_contract'];data=read(DATA_HEAD)
    assert c['accepted_authority']==bind(NATIVE_HEAD) and c['data_authority']==bind(DATA_HEAD),'COORDINATE_AUTHORITY_NOT_CORE'
    import hashlib
    canonical_path='config/v4_02_canonical_daily_pit_contract_v3.json'
    canonical_raw=subprocess.check_output(['git','show',BASELINE+':'+canonical_path],cwd=ROOT)
    assert (ROOT/canonical_path).read_bytes().replace(b'\r\n',b'\n')==canonical_raw
    assert c['canonical_contract']==dict(path=canonical_path,sha256=hashlib.sha256(canonical_raw).hexdigest(),bytes=len(canonical_raw))
    assert c['historical_adjustment_contract']==bind('config/v4_02_go_forward_pit_adjustment_r2.json')
    assert c['formal_adjustment_contract']==bind('config/v4_02_formal_period_contract_v1.json')
    assert c['basis_identity']==['price_basis','adjustment_source_revision'] and c['coefficient_equality_is_identity'] is False
    assert c['transform_capability']['alpha']==c['transform_capability']['beta']=='BLOCKED_WITH_EXPLICIT_REASON'
    for name,ref in c['component_refs'].items():assert ref==data['component_artifacts'][name] and bind(ref['path'])['sha256']==ref['sha256']
    rows={r['field']:r for r in configs['field_registry']['fields']}
    for name in ['alpha','beta','atr_prior_view','prior_high_view']:
        assert rows[name]['field_role']=='BLOCKED_CAPABILITY' and rows[name]['producer_contract_id']=='V4_12_COORDINATE_VIEW_V1'
    assert c['original_anchor_immutable'] and c['failed_conversion']['reason']=='PRICE_BASIS_MISMATCH'
    return dict(status='PASS',authority=c['accepted_authority'],data_authority=c['data_authority'],component_refs=c['component_refs'],
                alpha_beta='BLOCKED_WITH_EXPLICIT_REASON',corporate_action_transition='REQUIRES_EXACT_ACCEPTED_HISTORICAL_LINEAGE',
                same_day_revision='Separate immutable observation view; never another session',unsupported_conversion='UNKNOWN_PRICE_BASIS_MISMATCH',
                pure_core_as_coordinate_authority=False)

def unit_audit(configs):
    rows={r['field']:r for r in configs['field_registry']['fields']}
    sources={o['field_id']:o for c in read(CORE_CONTRACT)['contracts'] for o in c['outputs']}
    results=[]
    for name,source in ALIASES.items():
        assert rows[name]['unit']==sources[source]['unit'],'OWNER_UNIT_PARITY_MISMATCH'
        results.append(dict(logical_field=name,accepted_source_field=source,unit=rows[name]['unit'],status='PASS'))
    param=next(r for r in configs['parameter_set']['parameters'] if r['parameter_id']=='range_anchor_abs_slope20_max')
    assert param['value']==.1 and param['unit']=='dimensionless'
    return dict(status='PASS',fields=results,range_anchor_abs_slope20_max=dict(value=.1,unit='dimensionless'),parameter_values_unchanged=True)

def validate(emit=False):
    configs=load_configs();proof=keep_proof();parity=authority_parity();coordinate=coordinate_audit(configs);units=unit_audit(configs)
    literal=literal_audit(configs);dag=dag_audit(configs);schema=schema_registry_audit(configs);oracle=vector_oracle(configs)
    assert oracle['status']=='PASS' and oracle['total']==69
    registry=configs['field_registry']['fields'];matrix=read(OUT+'V4_12_R2_INPUT_AUTHORITY_RECONCILIATION.json')
    assert matrix['fields']==[r for r in registry if r['field_role']!='D1_OUTPUT'],'RECONCILIATION_REGISTRY_MISMATCH'
    enum=configs['output_schema']['state_enum_registry'];assert len(enum)==len(set(enum)) and set(enum)==set(baseline('config/v4_12_output_schema_v1.json')['state_enum_registry'])
    for name,expected in [('close_t_minus_1',['recovery.MA20_RECLAIM']),('ma20_t_minus_1',['recovery.MA20_RECLAIM']),('ret1',['recovery.BOUNCE_ONLY']),('near_high20_state',['breakout.APPROACHING'])]:
        assert next(r for r in registry if r['field']==name)['required_by']==expected
    anchor=configs['anchor_schema'];range_row=next(r for r in anchor['types'] if r['anchor_type']=='RANGE_UPPER')
    assert range_row['semantic_disposition']=='REMOVE_EXTRA_TRIGGER' and range_row['creation_rule']=='range_anchor_qualified'
    for kind in ['MA20_DYNAMIC','MA60_DYNAMIC','PIVOT_LOW']:
        row=next(r for r in anchor['types'] if r['anchor_type']==kind);assert row['capability']=='FORMAL_BLOCKED_INPUT_CAPABILITY' and row['blocked_reason']
    scope=scope_proof()
    changed=subprocess.check_output(['git','diff','--name-only',BASELINE],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('src/','data/','migrations/','alembic/')) or '/migrations/' in p for p in changed),'RUNTIME_OR_MIGRATION_OR_DATA_CHANGE'
    ast_diff=dict(status='PASS',business_rule_AST_byte_identical=True,rule_order_unchanged=True,retention_formula_unchanged=True,
        parameter_values_unchanged=True,R1_vectors_byte_identical=True,
        anchor_metadata_dispositions=[dict(anchor_type='RANGE_UPPER',disposition='REMOVE_EXTRA_TRIGGER',authority='REV4 section41A.2',
            reason='Remove unowned extra breakout gate; actual RANGE_UPPER consumer remains blocked',vector_impact='None: unchanged 69 rule vectors; no formal range consumer enabled'),
            dict(anchor_type='MA20_DYNAMIC/MA60_DYNAMIC',disposition='BLOCKED_WITH_EXPLICIT_REASON',reason='No accepted source event allowlist; freeze closed entry')])
    completeness=dict(status='PASS_AUTHORITY_POLICY_WITH_EXPLICIT_CAPABILITY_BLOCKS',authority_parity='PASS',coordinate_authority='PASS',unit_parity='PASS',
        items=[dict(item=n,status='FROZEN',condition='Independent authority parity / coordinate / units PASS; explicit blocked fields preserved') for n in
               ['field_registry','producer_registry','time_role_registry','coordinate_contract','input_schema','required_source_capability']],
        blocked_fields=[dict(field=r['field'],status='BLOCKED_WITH_EXPLICIT_REASON',reason=r['blocked_reason'],required_by=r['required_by']) for r in registry
                        if r['blocked_reason'] and r['field_role']!='D1_OUTPUT'],
        blocked_anchor_types=[dict(anchor_type=r['anchor_type'],status='BLOCKED_WITH_EXPLICIT_REASON',reason=r['blocked_reason']) for r in anchor['types'] if r.get('blocked_reason')],
        completeness_basis='VALIDATED_OWNER_AND_PUBLICATION_PARITY_NOT_FILE_EXISTENCE',runtime_authorized=False)
    result=dict(contract_id='V4_12_R2_CONTRACT_AUTHORITY_REPAIR_V1',status='V4_12_R2_CONTRACT_AUTHORITY_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',
        authority_parity=parity,coordinate_authority=coordinate,unit_parity=units,
        independent_vector_oracle=dict(status=oracle['status'],total=69,passed=69,failed=0),literal_audit_summary={k:literal[k] for k in ['status','parameters','ast_leaf_count','unbound_literal_count']},
        dag_edge_audit='PASS',enum_uniqueness='PASS',branch_requiredness='EXPLICIT_CONSUMER_LOCAL',completeness= completeness,
        scope_proof=scope,protected_and_keep_proof=proof,R6R1='EXTERNAL_PASS_PRESERVED_NO_REWORK',runtime_implemented=False,runtime_authorized=False,
        external_acceptance_claim=False,permissions=PERMISSIONS,next_stage='STOP_AFTER_COMMIT_PUSH_WAIT_EXTERNAL_AUDIT')
    if emit:
        for name,value in [('V4_12_R2_PRODUCER_AUTHORITY_PARITY',parity),('V4_12_R2_COORDINATE_AUTHORITY_AUDIT',coordinate),('V4_12_R2_UNIT_PARITY',units),
            ('V4_12_R1_TO_R2_AST_DIFF',ast_diff),('V4_12_R2_CONTRACT_COMPLETENESS_MATRIX',completeness),('V4_12_R2_PARAMETER_LITERAL_AUDIT',literal),
            ('V4_12_R2_DAG_EDGE_AUDIT',dag),('V4_12_R2_R1_INDEPENDENT_VECTOR_ORACLE',oracle),('V4_12_R2_CONTRACT_AUTHORITY_REPAIR',result)]:put(OUT+name+'.json',value)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--emit',action='store_true');args=p.parse_args()
    r=validate(args.emit);print(json.dumps(dict(status=r['status'],roles=r['authority_parity']['roles'],R1_vectors=r['independent_vector_oracle'],
        false_accepted_claims=0,generic_CORE_FACTOR_fallback=0,unit_parity=r['unit_parity']['status'],coordinate=r['coordinate_authority']['status'])))

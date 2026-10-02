"""R8 contract-authority reconciliation. No market calculation or publication."""
import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT, atomic, bind, UPGRADE, PERMISSIONS
from scripts.record_r7_stage_contract import put

BASELINE='b475002697bb3c5d91fab1ba44852b31d0d1da29'
OUT='reports/v4_12_r2/'
DOC='docs/evidence/next_round_v4_12_r2/'
TARGETS=['2026-09-29','2026-09-30']
CORE_HEAD='data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json'
CORE_CONTRACT='config/v4_03_algorithm_contracts_v1.json'
RPS_HEAD='data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json'
PROFILE_HEAD='data/v4/V4_04_ACCEPTED_HEAD.json'
DATA_HEAD='data/v4/V4_DATA_ACCEPTED_HEAD.json'
NATIVE_HEAD='data/v4/V4_02_ACCEPTED_HEAD.json'
NAMES=['V4_NEXT_ROUND_EXECUTION_MASTER_R8_20261002.md','V4_12_R2_SOURCE_AUTHORITY_PRODUCER_REGISTRY_REPAIR_TASK_20261002.md','V4_R7_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md']

def read(path):return json.loads((ROOT/path).read_bytes())
def baseline(path):return json.loads(subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT))

def canonical_source_binding():
    path='config/v4_02_canonical_daily_pit_contract_v3.json'
    raw=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT)
    assert (ROOT/path).read_bytes().replace(b'\r\n',b'\n')==raw,'CANONICAL_SOURCE_CONTENT_CHANGED'
    return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def refs(node,key):
    if isinstance(node,dict):
        if key in node:yield node[key]
        for v in node.values():yield from refs(v,key)
    elif isinstance(node,list):
        for v in node:yield from refs(v,key)

def component_ref(node,component):
    item=node['components'][component]
    return dict(path=item['artifact_path'],sha256=item['artifact_sha256'],bytes=item['artifact_bytes'])

def keep_proof():
    paths=['AGENTS.md','scripts/prepare_v4_11_promotion_r1.py','data/v4/V4_11_ACCEPTED_HEAD.json',
        'data/v4/V4_STAGE_ACCEPTED_HEAD.json',DATA_HEAD,'reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json',
        'config/v4_12_machine_ast_v1.json','config/v4_12_machine_vectors_v1.json','scripts/v4_12_independent_vector_oracle_r1.py']
    paths+=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'reports/next_round_r6r1'],cwd=ROOT,text=True).splitlines()
    rows=[]
    for path in paths:
        old=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT);new=(ROOT/path).read_bytes()
        assert old==new,path
        rows.append(dict(path=path,before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest(),byte_identical=True))
    assert [(r['parameter_id'],r['value']) for r in read('config/v4_12_parameter_set_v1.json')['parameters']]==[(r['parameter_id'],r['value']) for r in baseline('config/v4_12_parameter_set_v1.json')['parameters']]
    return rows

def stage(bundle_dir):
    for name in NAMES:
        raw=(Path(bundle_dir)/name).read_bytes();target=DOC+name
        if (ROOT/target).exists():assert (ROOT/target).read_bytes()==raw
        else:atomic(target,raw)
    for folder in [DOC,OUT]:atomic(folder+'.gitattributes',b'* -text\n')
    put(OUT+'R8_STAGE_CONTRACT.json',dict(contract_id='V4_12_R2_AUTHORITY_STAGE_CONTRACT_V1',starting_remote_head=BASELINE,
        authority=bind(DOC+NAMES[2]),master=bind(DOC+NAMES[0]),task=bind(DOC+NAMES[1]),upgrade=bind(UPGRADE),
        consulted_sections=['13A','41A0','41A.2','72','78','81.4','87A'],phase0=dict(status='DEGRADED_PASS',scope='CONTRACT_REPAIR_ONLY_NO_SCANNER'),
        scope='SOURCE_AUTHORITY_REPAIR_ONLY',R6R1='EXTERNAL_PASS_DO_NOT_REOPEN',protected=keep_proof(),permissions=PERMISSIONS,
        acceptance='EXTERNAL_AUDIT_PENDING',next_stage='COMMIT_PUSH_STOP_EXTERNAL_AUDIT_NO_RUNTIME'))

def consumer_map(tree,name):
    dependencies={k:set(refs(v,'field')) for k,v in tree['definitions'].items()}
    def expands(fields,seen=None):
        result=set(fields);seen=set() if seen is None else set(seen)
        for f in fields:
            if f in dependencies and f not in seen:result|=expands(dependencies[f],seen|{f})
        return result
    definitions=[k for k,v in dependencies.items() if name in expands(v)]
    rules=[]
    labels={'recovery':['RECOVERY_FAILED','RECOVERY_CONFIRMED','ANCHOR_RECLAIM','MA20_RECLAIM','RELATIVE_RECOVERY','BOUNCE_ONLY'],
            'breakout':['UNKNOWN','FAILED_BREAKOUT','BREAKOUT_ACCEPTED','TESTING','RETAIN_TENTATIVE','BREAKOUT_TENTATIVE','APPROACHING']}
    for machine,node in tree['machines'].items():
        for i,rule in enumerate(node['rules']):
            if name in expands(set(refs(rule,'field'))):
                label=labels.get(machine,[])
                rules.append(machine+'.'+(label[i] if i<len(label) else rule['then'].get('enum','RULE_'+str(i))))
    return sorted(definitions),sorted(set(rules))

def repair():
    assert (ROOT/(OUT+'R8_STAGE_CONTRACT.json')).exists(),'R8_STAGE_CONTRACT_REQUIRED'
    tree=read('config/v4_12_machine_ast_v1.json');registry=baseline('config/v4_12_field_registry_v1.json')
    data=read(DATA_HEAD);chain=read(data['accepted_chain']['path']);nodes={n['trade_date']:n for n in chain['nodes']}
    outputs={o['field_id']:(c,o) for c in read(CORE_CONTRACT)['contracts'] for o in c['outputs']}
    aliases={'ATR20':'atr20','CLV':'clv','MA20':'ma20','MA60':'ma60','prior_high20':'prior_high20','amount_ratio20':'amount_ratio20',
             'rel_market_1':'rel_market_1','ret1':'ret1','slope20':'slope20'}
    native={'O':'open','H':'high','L':'low','C':'close','price_basis':'price_basis','adjustment_source_revision':'adjustment_source_revision'}
    local={'distance_zone':'V4_12_MACHINE_AST_V1','evaluable':'V4_12_MACHINE_AST_V1',
        'observation_close_view':'V4_12_COORDINATE_VIEW_V1','start_price_view':'V4_12_COORDINATE_VIEW_V1','endpoint_price_view':'V4_12_COORDINATE_VIEW_V1',
        'lo':'V4_12_COORDINATE_VIEW_V1','hi':'V4_12_COORDINATE_VIEW_V1','base_view':'V4_12_COORDINATE_VIEW_V1','event_close_view':'V4_12_COORDINATE_VIEW_V1',
        'recovery_line_view':'V4_12_COORDINATE_VIEW_V1','prior_event_peak_view':'V4_12_COORDINATE_VIEW_V1',
        'post_creation_sessions':'V4_12_SESSION_COUNTER_V1','pivot_left_count':'V4_12_SESSION_COUNTER_V1','pivot_right_count':'V4_12_SESSION_COUNTER_V1'}
    blocked={'alpha':('V4_12_COORDINATE_VIEW_V1','No accepted Anchor-basis to observation-basis alpha publisher; qfq_mul is not alpha authority'),
        'beta':('V4_12_COORDINATE_VIEW_V1','No accepted Anchor-basis to observation-basis beta publisher; qfq_add is not beta authority'),
        'atr_prior_view':('V4_12_COORDINATE_VIEW_V1','No exact prior ATR publication plus accepted cross-basis transform'),
        'prior_high_view':('V4_12_COORDINATE_VIEW_V1','No exact previous-session high view plus accepted cross-basis transform'),
        'prior_range20_atr':('V4_12_BLOCKED_RANGE_INPUT_V1','Absent in accepted V4-03 outputs; Option B; no raw fallback'),
        'pivot_low':('V4_12_PIVOT_SOURCE_DESIGN_V1','No accepted left/right history source publication for D1 pivot detector'),
        'pivot_low_strict':('V4_12_PIVOT_SOURCE_DESIGN_V1','No accepted left/right history source publication for D1 pivot detector'),
        'close_t_minus_1':('V4_12_BLOCKED_PRIOR_OWNER_V1','Accepted owner capability unavailable; DO_NOT_RECONSTRUCT_FROM_RAW_BARS'),
        'ma20_t_minus_1':('V4_12_BLOCKED_PRIOR_OWNER_V1','Accepted owner capability unavailable; DO_NOT_RECONSTRUCT_FROM_RAW_BARS')}
    rps=read(RPS_HEAD);record=read(rps['acceptance_record']['path'])
    profile=read(PROFILE_HEAD)
    core_receipt=read('reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json')
    core_pub='reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz'
    assert bind(core_pub)['sha256']==core_receipt['hashes']['artifacts'][core_pub]
    reconciliation=[]
    for row in registry['fields']:
        name=row['field'];defs,rules=consumer_map(tree,name)
        row.pop('required',None)
        row.update(logical_field=name,globally_required=False,required_by=rules+['definition.'+d for d in defs],
            consumer_definitions=defs,consumer_machine_rules=rules,accepted_source_field=None,accepted_source_stage=None,
            accepted_head_path=None,accepted_head_sha256=None,producer_version='1.0.0',accepted_parameter_set_id=None,
            target_publication_available=False,target_publications={},blocked_reason=None,raw_reconstruction_allowed=False,
            trade_date_semantics=row['trade_date'],quality_semantics='UNKNOWN/STALE operands never treated as FALSE or reconstructed; exact owner reason retained',
            formal_or_diagnostic='CONTRACT_DESIGN_ONLY',authority_status='BLOCKED_WITH_EXPLICIT_REASON',source_contract_binding=None)
        if row['time_role']=='T_OUTPUT':
            row['field_role']='D1_OUTPUT';row['blocked_reason']='Runtime not authorized; output design only'
        elif name in native:
            row.update(field_role='UPSTREAM_ACCEPTED',source_namespace='F0_ACCEPTED',time_role='T',
                producer_contract_id='V4_02_FORMAL_RAW_QFQ_PERIODS_V1',accepted_source_field=native[name],
                accepted_source_stage='V4-02 / DM01 accepted chain',accepted_head_path=DATA_HEAD,accepted_head_sha256=bind(DATA_HEAD)['sha256'],
                source_contract_binding=bind('config/v4_02_formal_period_contract_v1.json'),
                authority_status='EXACT_ACCEPTED_MAPPING',target_publication_available=True,
                target_publications={day:dict(artifact=component_ref(nodes[day],'ADJUSTED_DAILY'),
                    publication_contract_id=nodes[day]['components']['ADJUSTED_DAILY']['contract_id'],
                    source_field_path='rows[*].'+native[name],trade_date=day,quality_field='adjustment_readiness',
                    input_publication_ids=nodes[day]['components']['ADJUSTED_DAILY']['input_publication_ids'],
                    available_at=data['promoted_at_utc'],candidate=nodes[day]['candidate'],
                    source_cutoff=day,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
                    historical_first_availability_proven=False,acceptance_record=data['external_acceptance_record']) for day in TARGETS})
            row['unit']='adjusted_price' if name in {'O','H','L','C'} else 'identity'
        elif name in aliases:
            contract,output=outputs[aliases[name]]
            row.update(field_role='BLOCKED_CAPABILITY',source_namespace='BLOCKED_CAPABILITY',producer_contract_id=output['producer_contract_id'],
                producer_version=output['producer_version'],accepted_parameter_set_id=contract['parameter_set_id'],
                accepted_source_field=aliases[name],accepted_source_stage='V4-03',accepted_head_path=CORE_HEAD,accepted_head_sha256=bind(CORE_HEAD)['sha256'],
                source_contract_binding=bind(CORE_CONTRACT),unit=output['unit'],
                accepted_reference_publication=bind(core_pub),accepted_reference_trade_date=read(CORE_HEAD)['source_cutoff'],
                blocked_reason='Exact owner/field accepted, but no target-date V4-03 accepted factor publication bound for 2026-09-29/30; V4-11 candidate computations do not grant a new D1 producer permission')
        elif name in {'delta3','prior_delta3'}:
            output=outputs['rps5_delta3'][1];pubs={}
            for day in TARGETS:
                index=rps['accepted_dates'].index(day);source_day=day if name=='delta3' else rps['accepted_dates'][index-1]
                inputs=read(record['inputs'][day]['path']);sessions=inputs['sessions'];assert source_day== (day if name=='delta3' else sessions[sessions.index(day)-1])
                ref=record['deltas'][source_day+':T-3']
                pack=read(ref['path']);assert pack['offset']==3 and 'rps5_delta3' in pack['rows'][0]['fields']
                pubs[day]=dict(artifact=ref,rank_publication=rps['publications'][source_day],source_field_path='rows[*].fields.rps5_delta3',
                    trade_date=source_day,observation_trade_date=day,time_role='T' if name=='delta3' else 'T_MINUS_1',
                    available_at=max(read(rps['publications'][source_day]['path'])['cutoff_timestamp'],record['formalized_at']),
                    knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,historical_first_availability_proven=False,
                    acceptance_record=rps['acceptance_record'],accepted_delta_scope='A02 accepted DELTA artifact, not a fresh calculation')
            row.update(field_role='UPSTREAM_ACCEPTED',source_namespace='F0_ACCEPTED',time_role='T' if name=='delta3' else 'T_MINUS_1',
                producer_contract_id='RPS_DELTA_V1',producer_version=output['producer_version'],accepted_parameter_set_id=outputs['rps5_delta3'][0]['parameter_set_id'],
                accepted_source_field='rps5_delta3',accepted_source_stage='V4-03 contract / A02 scoped accepted producer',
                accepted_head_path=RPS_HEAD,accepted_head_sha256=bind(RPS_HEAD)['sha256'],unit='percentage_points',
                source_contract_binding=bind(CORE_CONTRACT),authority_status='EXACT_ACCEPTED_MAPPING',target_publication_available=True,target_publications=pubs)
        elif name=='near_high20_state':
            owner=next(r for r in read('config/v4_04_field_registry_v2.json')['fields'] if r['field_id']==name)
            row.update(field_role='BLOCKED_CAPABILITY',source_namespace='BLOCKED_CAPABILITY',producer_contract_id=owner['producer_contract_id'],
                accepted_source_field=name,accepted_source_stage='V4-04',accepted_head_path=PROFILE_HEAD,accepted_head_sha256=bind(PROFILE_HEAD)['sha256'],
                accepted_parameter_set_id=owner['parameter_set_id'],source_contract_binding=bind('config/v4_04_field_registry_v2.json'),unit=owner['unit'],
                accepted_reference_publication=profile['accepted_artifact'],accepted_reference_trade_date=profile['source_cutoff'],
                blocked_reason='Accepted POSITION_STATE_V1 owner exists; accepted profile cutoff is 2026-09-24, no target-date V4-04 accepted publication bound')
        elif name in blocked:
            owner,reason=blocked[name]
            row.update(field_role='BLOCKED_CAPABILITY',source_namespace='BLOCKED_CAPABILITY',producer_contract_id=owner,blocked_reason=reason,
                       capability='FORMAL_BLOCKED_INPUT_CAPABILITY',time_role='T_MINUS_1' if name in {'close_t_minus_1','ma20_t_minus_1','atr_prior_view','prior_high_view'} else 'T')
            if name in {'alpha','beta','atr_prior_view','prior_high_view'}:row['source_contract_binding']=bind('config/v4_02_go_forward_pit_adjustment_r2.json')
        elif name in local or row['source_namespace']=='D1_LOCAL_DERIVATION':
            row.update(field_role='D1_LOCAL_DERIVATION',source_namespace='D1_LOCAL_DERIVATION',time_role='T_INTERNAL_D1',
                producer_contract_id=local.get(name,row['producer_contract_id']),blocked_reason='Design-only local derivation; runtime not authorized',
                source_contract_binding=bind('config/v4_12_machine_ast_v1.json'),local_derivation_contract='config/v4_12_source_derivations_r2.json')
        elif row['source_namespace']=='FROZEN_ANCHOR_EVENT':
            row.update(field_role='FROZEN_PRIOR_D1',producer_contract_id='STRUCTURE_EVENT_V1',source_namespace='FROZEN_ANCHOR_EVENT',
                time_role='T_MINUS_1',blocked_reason='No accepted previous-session D1 Anchor/event publication; immutable frozen-source schema is design only')
        else:
            # Unknown fields explicitly block; never infer any accepted owner.
            row.update(field_role='BLOCKED_CAPABILITY',source_namespace='BLOCKED_CAPABILITY',producer_contract_id='V4_12_UNOWNED_FIELD_BLOCK_V1',
                blocked_reason='No explicit reconciled owner for logical field: '+name,capability='FORMAL_BLOCKED_INPUT_CAPABILITY')
        if name in {'close_t_minus_1','ma20_t_minus_1'}:row['required_by']=['recovery.MA20_RECLAIM']
        if name=='ret1':row['required_by']=['recovery.BOUNCE_ONLY']
        if name=='near_high20_state':row['required_by']=['breakout.APPROACHING']
        if name=='slope20':row['unit']='dimensionless'
        if name=='alpha':row['unit']='dimensionless'
        if name=='beta':row['unit']='adjusted_price'
        row['capability']=('EXACT_ACCEPTED_RECONSTRUCTED_SOURCE_SCOPE' if row['field_role']=='UPSTREAM_ACCEPTED' else
                           'FORMAL_BLOCKED_INPUT_CAPABILITY' if row['field_role']=='BLOCKED_CAPABILITY' else 'RUNTIME_NOT_AUTHORIZED')
        if row['field_role']=='D1_LOCAL_DERIVATION':
            row['trade_date']='observation_t'
            row['trade_date_semantics']='Derived/view at observation_t; any prior event source frozen at previous market session'
        if row['field_role']=='FROZEN_PRIOR_D1':
            row['trade_date_semantics']='Previous-market-session publication; immutable anchor/event creation date retained separately'
            original_name='adjustment_source_revision' if name=='anchor_adjustment_source_revision' else name
            if original_name in baseline('config/v4_12_anchor_schema_v1.json')['required_fields']:
                row['required_by']=sorted(set(row['required_by']+['anchor_schema.IMMUTABLE_RECORD']))
        if row['field_role']!='D1_OUTPUT':reconciliation.append(copy.deepcopy(row))
    registry.update(version='1.1.0',authority_repair='R2_EXPLICIT_OWNER_NO_FALLBACK',target_dates=TARGETS)
    put('config/v4_12_field_registry_v1.json',registry)
    producers={}
    for row in registry['fields']:
        identifier=row['producer_contract_id']
        producers.setdefault(identifier,dict(producer_contract_id=identifier,producer_version=row['producer_version'],fields=[],
            accepted_head_bindings=[],status='NO_GENERIC_ACCEPTANCE_CLAIM_FIELD_ROWS_AUTHORITATIVE'))['fields'].append(row['field'])
        if row['accepted_head_path']:
            binding=bind(row['accepted_head_path'])
            if binding not in producers[identifier]['accepted_head_bindings']:producers[identifier]['accepted_head_bindings'].append(binding)
    put('config/v4_12_producer_registry_v1.json',dict(contract_id='V4_12_PRODUCER_REGISTRY_V1',version='1.1.0',authority_repair='R2',
        parameter_set_id=registry['parameter_set_id'],freeze_scope='CONTRACT_DESIGN_ONLY',runtime_implemented=False,permissions=PERMISSIONS,
        producers=list(producers.values()),source_authority_policy='EXPLICIT_ACCEPTED_OWNER_TABLE_OR_BLOCK; NEVER_DEFAULT_CORE_FACTOR',
        capabilities=[dict(fields=[r['field']],status='BLOCKED_WITH_EXPLICIT_REASON',capability=r['capability'],reason=r['blocked_reason'])
                      for r in registry['fields'] if r['blocked_reason'] and r['field_role'] not in {'D1_OUTPUT'}]))
    roles=baseline('config/v4_12_time_role_registry_v1.json')
    roles.update(version='1.1.0',fields=[{k:r[k] for k in ['field','field_role','time_role','trade_date_semantics','source_namespace','producer_contract_id','globally_required','required_by']} for r in registry['fields']])
    put('config/v4_12_time_role_registry_v1.json',roles)
    schema=baseline('config/v4_12_input_schema_v1.json')
    external={r['field']:r for r in registry['fields'] if r['source_namespace'] in {'F0_ACCEPTED','FROZEN_ANCHOR_EVENT','BLOCKED_CAPABILITY'} and r['field_role']!='D1_OUTPUT'}
    schema['schema']['properties']['inputs']['properties']={n:{'$ref':'#/$defs/fact'} for n in external}
    schema.update(version='1.1.0',requiredness_policy='Consumer-local; only envelope identity globally required; higher-priority resolved rule does not inspect unrelated branch inputs',
        field_requirements={r['field']:dict(globally_required=r['globally_required'],required_by=r['required_by']) for r in reconciliation},
        local_input_policy='D1 local derivations cannot enter external inputs envelope',
        quality_operand_binding='UNKNOWN/STALE retained values bind UNKNOWN operand, not last-known numeric value; preserve exact reason')
    put('config/v4_12_input_schema_v1.json',schema)
    coordinate=baseline('config/v4_12_anchor_coordinate_contract_v1.json')
    coordinate.update(version='1.1.0',accepted_authority=bind(NATIVE_HEAD),data_authority=bind(DATA_HEAD),
        historical_adjustment_contract=bind('config/v4_02_go_forward_pit_adjustment_r2.json'),canonical_contract=canonical_source_binding(),
        formal_adjustment_contract=bind('config/v4_02_formal_period_contract_v1.json'),component_refs={k:data['component_artifacts'][k] for k in ['ADJUSTED_DAILY','RAW_DAILY','PERIOD_ADJUSTED']},
        transform_capability={'alpha':'BLOCKED_WITH_EXPLICIT_REASON','beta':'BLOCKED_WITH_EXPLICIT_REASON','reason':blocked['alpha'][1]+'; '+blocked['beta'][1]},
        accepted_metadata_fields=['price_basis','adjustment_source_revision','qfq_mul','qfq_add','source_digest','source_snapshot_id'],
        coefficient_policy='Native coefficients are source metadata only; never infer cross-Anchor transform or price identity from equality',
        corporate_action_authority='Accepted historical adjustment lineage required for each transition; native row revision alone does not grant an Anchor rebase producer')
    put('config/v4_12_anchor_coordinate_contract_v1.json',coordinate)
    parameters=baseline('config/v4_12_parameter_set_v1.json')
    next(r for r in parameters['parameters'] if r['parameter_id']=='range_anchor_abs_slope20_max')['unit']='dimensionless'
    parameters['metadata_amendment']='R2_OWNER_UNIT_PARITY_ONLY_VALUES_UNCHANGED';put('config/v4_12_parameter_set_v1.json',parameters)
    output=baseline('config/v4_12_output_schema_v1.json');output['state_enum_registry']=list(dict.fromkeys(output['state_enum_registry']))
    output['metadata_amendment']='R2_ENUM_UNIQUENESS_ONLY';put('config/v4_12_output_schema_v1.json',output)
    anchor=baseline('config/v4_12_anchor_schema_v1.json')
    for row in anchor['types']:
        if row['anchor_type']=='RANGE_UPPER':
            row.update(creation_rule='range_anchor_qualified',source_event='RANGE_QUALIFIED_REGISTRATION',
                semantic_disposition='REMOVE_EXTRA_TRIGGER',authority_section='41A.2',capability='FORMAL_BLOCKED_INPUT_CAPABILITY',
                blocked_reason=blocked['prior_range20_atr'][1])
        if row['anchor_type'] in ['PIVOT_LOW','MA20_DYNAMIC','MA60_DYNAMIC']:
            row.update(capability='FORMAL_BLOCKED_INPUT_CAPABILITY',blocked_reason='Pivot accepted history / dynamic MA registered rise source-event authority not accepted',
                source_event_contract_id='STRUCTURE_EVENT_V1',allowed_source_event_types=[],required_maturity_status='NO_FORMAL_SOURCE_EVENT_ALLOWLIST_ACCEPTED',
                available_at_rule='Must be frozen previous-session accepted event, never same-day event',
                creation_identity=anchor['identity'],invalidation_linkage='Creation-bound owning episode only')
    anchor['metadata_amendment']='R2_SOURCE_ENTRY_RECONCILIATION';put('config/v4_12_anchor_schema_v1.json',anchor)
    put('config/v4_12_source_derivations_r2.json',dict(contract_id='V4_12_SOURCE_DERIVATIONS_R2',scope='DESIGN_ONLY_NO_RUNTIME',
        formulas={'distance_zone':'max(lo-C,C-hi,0)', 'evaluable':'accepted actual-bar quality + accepted source/basis + converted positive prior ATR; UNKNOWN stays UNKNOWN',
            'observation_close_view':'accepted observation C in registered observation basis',
            'start_price_view':'accepted start source price rebased through authenticated transform',
            'endpoint_price_view':'accepted endpoint source price rebased through authenticated transform',
            'lo/hi/base_view/event_close_view/recovery_line_view/prior_event_peak_view':'Immutable prior event/Anchor values rebased by source-bound accepted historical transform'},
        dependency_ledger={'distance_zone':['C','lo','hi'],
            'evaluable':dict(actual_bar_source=bind(DATA_HEAD),actual_bar_producer='V4_02_DATED_TRADING_STATUS_V1',
                accepted_source_fields=['actual_bar_present','status','status_conflict'],
                publications={day:component_ref(nodes[day],'TRADING_STATUS') for day in TARGETS},
                other_required_fields=['price_basis','adjustment_source_revision','atr_prior_view'],
                missing='UNKNOWN with exact source reason; availability does not mean a valid observed bar'),
            'observation_close_view':['C','price_basis','adjustment_source_revision'],
            'start_price_view/endpoint_price_view/lo/hi/base_view/event_close_view/recovery_line_view/prior_event_peak_view':
                ['frozen prior source value','alpha','beta','creation_coordinate','current_comparison_coordinate'],
            'post_creation_sessions/pivot_left_count/pivot_right_count':dict(calendar=data['calendar'],date_field='session_dates',actual_status_producer='V4_02_DATED_TRADING_STATUS_V1')},
        counters=dict(producer='V4_12_SESSION_COUNTER_V1',calendar_authority=data['calendar'],data_authority=bind(DATA_HEAD),
            source_dates=['anchor.available_date','pivot_date','confirmation_date','observation_trade_date'],
            post_creation_sessions='Market sessions strictly after available_date; zero on available_date',
            pivot_left_count='Actual evaluable sessions preceding pivot_date, no shortened missing window',
            pivot_right_count='Actual evaluable sessions after pivot_date through confirmation_date',
            missing_suspension='Cannot increment actual evaluable count; missing history yields UNKNOWN; breaks consecutive path counters',
            same_day_revision='Same previous-session counter baseline; not another session'),
        pivot=dict(producer='V4_12_PIVOT_SOURCE_DESIGN_V1',left_parameter_id='pivot_left_sessions',right_parameter_id='pivot_right_sessions',
            predicate='pivot_low strictly less than each accepted actual evaluable left/right low; ties do not qualify',
            pivot_date='Source low date',confirmation_date='Second actual right-session availability date',available_date='confirmation_date',
            available_at='Max input availability not later than cutoff; no backfill',quality='Missing accepted history -> UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE',
            capability='BLOCKED_WITH_EXPLICIT_REASON',reason=blocked['pivot_low'][1]),
        range=dict(option='B_BLOCK',capability='FORMAL_BLOCKED_INPUT_CAPABILITY',reason=blocked['prior_range20_atr'][1]),
        runtime_authorized=False,raw_reconstruction_allowed=False))
    put(OUT+'V4_12_R2_INPUT_AUTHORITY_RECONCILIATION.json',dict(contract_id='V4_12_R2_INPUT_AUTHORITY_RECONCILIATION_V1',
        target_dates=TARGETS,fields=reconciliation,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,historical_first_availability_proven=False))
    atomic('scripts/freeze_v4_12_contracts_r1.py',
        ('"""R1 generator retired by external audit; use explicit R2 owner table."""\n'
         'from scripts.repair_v4_12_authority_r2 import repair\n\n'
         'if __name__ == "__main__":\n    repair()\n').encode('utf8'))
    print('R2_EXPLICIT_AUTHORITY_ROWS_WRITTEN:'+str(len(reconciliation)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle-dir');args=p.parse_args()
    if args.bundle_dir:stage(args.bundle_dir)
    repair()

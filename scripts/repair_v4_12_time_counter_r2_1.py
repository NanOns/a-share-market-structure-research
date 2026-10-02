"""R9 contract-only time-domain repair; no market detector or publisher."""
import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT, atomic, bind, UPGRADE, PERMISSIONS
from scripts.record_r7_stage_contract import put
from scripts.repair_v4_12_authority_r2 import consumer_map

BASELINE='5267c9e482268dfaaf06d1c752e1bb3d09e33b6f'
OUT='reports/v4_12_r2_1/'
DOC='docs/evidence/next_round_v4_12_r2_1/'
OLD='post_creation_sessions'
MARKET='post_creation_market_sessions'
EVAL='post_creation_evaluable_sessions'
def old(path):return json.loads(subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT))
def config(name):return old('config/v4_12_'+name+'_v1.json')

def stage(bundle):
    names=['V4_NEXT_ROUND_EXECUTION_MASTER_R9_20261002.md','V4_12_R2_1_SESSION_COUNTER_SEMANTICS_REPAIR_TASK_20261002.md','V4_R8_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md']
    for name in names:atomic(DOC+name,(Path(bundle)/name).read_bytes())
    for folder in [DOC,OUT]:atomic(folder+'.gitattributes',b'* -text\n')
    put(OUT+'R9_STAGE_CONTRACT.json',dict(starting_remote_head=BASELINE,master=bind(DOC+names[0]),task=bind(DOC+names[1]),authority=bind(DOC+names[2]),
        upgrade=bind(UPGRADE),consulted_sections=['13A','41C','41D'],phase0='DEGRADED_PASS_CONTRACT_ONLY_NO_SCANNER',
        R2_authority='EXTERNAL_PASS_KEEP_NO_REWORK',scope='COUNTER_TIME_DOMAIN_AND_UNIT_METADATA_ONLY',permissions=PERMISSIONS,
        acceptance='EXTERNAL_AUDIT_PENDING',next_stage='COMMIT_PUSH_STOP_WAIT_EXTERNAL_AUDIT_NO_RUNTIME'))

def repair():
    tree=config('machine_ast')
    def migrate(node):
        if isinstance(node,dict):
            if node.get('field')==OLD:node['field']=MARKET
            for value in node.values():migrate(value)
        elif isinstance(node,list):
            for value in node:migrate(value)
    migrate(tree)
    tree['machines']['acceptance']['rules'][3]['when']['args'][0]={'field':EVAL}
    tree['version']='1.1.0'
    tree['semantic_amendment']='R2.1_SPLIT_MARKET_AGE_AND_EVALUABLE_COUNT_ONLY'
    put('config/v4_12_machine_ast_v1.json',tree)
    fields=config('field_registry');row=next(r for r in fields['fields'] if r['field']==OLD)
    fields['fields'].remove(row)
    for name,unit,dimension in [(MARKET,'market_sessions_after_available_date','market_session_age'),(EVAL,'evaluable_sessions','evaluable_session_count')]:
        r=copy.deepcopy(row);r.update(field=name,logical_field=name,unit=unit,semantic_dimension=dimension,producer_contract_id='V4_12_SESSION_COUNTER_V2',producer_version='2.0.0')
        fields['fields'].append(r)
    units={
        'pivot_left_count':('actual_evaluable_sessions','actual_evaluable_window_count'),
        'pivot_right_count':('actual_evaluable_sessions','actual_evaluable_window_count'),
        'body_atr':('dimensionless_ATR_multiple','dimensionless_ATR_multiple'),
        'range_atr':('dimensionless_ATR_multiple','dimensionless_ATR_multiple'),
        'prior_range20_atr':('dimensionless_ATR_multiple','dimensionless_ATR_multiple')}
    for name in ['held_count','prior_held_count','breach_count','prior_breach_count','recovery_held_count','prior_recovery_held_count']:
        units[name]=('consecutive_evaluable_sessions','consecutive_evaluable_count')
    for name in ['separated_sessions','prior_separated_sessions']:
        units[name]=('actual_session_separation_count','actual_session_separation_count')
    for r in fields['fields']:
        if r['field'] in units:r['unit'],r['semantic_dimension']=units[r['field']]
        if r['field_role']=='D1_LOCAL_DERIVATION':
            defs,rules=consumer_map(tree,r['field'])
            r['consumer_definitions']=defs;r['consumer_machine_rules']=rules
            r['required_by']=sorted(set(rules+['definition.'+d for d in defs]))
            if r.get('source_contract_binding',{}).get('path')=='config/v4_12_machine_ast_v1.json':r['source_contract_binding']=bind('config/v4_12_machine_ast_v1.json')
    fields['time_counter_amendment']='R2.1';put('config/v4_12_field_registry_v1.json',fields)
    producers=config('producer_registry')
    for r in producers['producers']:
        if OLD in r['fields']:r['fields'].remove(OLD)
        if r['producer_contract_id']=='V4_12_SESSION_COUNTER_V1':
            r['producer_contract_id']='V4_12_SESSION_COUNTER_V2';r['producer_version']='2.0.0';r['fields'] += [MARKET,EVAL]
    for r in fields['fields']:
        if r['field'] in ['pivot_left_count','pivot_right_count']:r['producer_contract_id']='V4_12_SESSION_COUNTER_V2';r['producer_version']='2.0.0'
    put('config/v4_12_field_registry_v1.json',fields)
    # Capabilities are explicit design-only field entries; accepted owner rows stay intact.
    for cap in producers['capabilities']:
        if cap.get('field')==OLD:cap['field']=MARKET
        if isinstance(cap.get('fields'),list) and OLD in cap['fields']:cap['fields']=[MARKET if x==OLD else x for x in cap['fields']]+[EVAL]
    producers['time_counter_amendment']='R2.1';put('config/v4_12_producer_registry_v1.json',producers)
    roles=config('time_role_registry');template=next(r for r in roles['fields'] if r['field']==OLD);roles['fields'].remove(template)
    for name in [MARKET,EVAL]:
        r=copy.deepcopy(template);r['field']=name;roles['fields'].append(r)
    registry={r['field']:r for r in fields['fields']}
    for r in roles['fields']:
        if 'required_by' in r:r['required_by']=registry[r['field']]['required_by']
        if r['field'] in [MARKET,EVAL,'pivot_left_count','pivot_right_count']:r['producer_contract_id']='V4_12_SESSION_COUNTER_V2'
    roles['time_counter_amendment']='R2.1';put('config/v4_12_time_role_registry_v1.json',roles)
    schema=config('input_schema');schema['field_requirements'].pop(OLD,None)
    for r in fields['fields']:schema['field_requirements'][r['field']]=dict(globally_required=False,required_by=r['required_by'])
    schema['cross_field_rules']=[s for s in schema['cross_field_rules'] if OLD not in s]
    schema['cross_field_rules'] += ['Market age and evaluable observation count are independent local counters; external input forbidden; exact calendar and frozen observation lineage required']
    schema['time_counter_amendment']='R2.1';put('config/v4_12_input_schema_v1.json',schema)
    params=config('parameter_set')
    dimensions={'earliest_anchor_test_sessions':('market_sessions_after_available_date','market_session_age'),
        'acceptance_consecutive_sessions':('evaluable_sessions','evaluable_session_threshold'),
        'support_break_consecutive_sessions':('consecutive_evaluable_sessions','consecutive_evaluable_count'),
        'support_tentative_hold_sessions':('consecutive_evaluable_sessions','consecutive_evaluable_count'),
        'support_separated_retest_sessions':('actual_session_separation_count','actual_session_separation_count'),
        'pivot_left_sessions':('actual_evaluable_sessions','actual_evaluable_window_count'),
        'pivot_right_sessions':('actual_evaluable_sessions','actual_evaluable_window_count')}
    for n in ['impulse_body_atr_min','impulse_range_atr_min','range_anchor_range_atr_max']:dimensions[n]=('dimensionless_ATR_multiple','dimensionless_ATR_multiple')
    for n in ['breakout_atr_buffer','support_touch_atr_buffer','support_close_breach_atr','support_deep_breach_atr','support_approach_atr']:
        dimensions[n]=('dimensionless_ATR_multiple','dimensionless_ATR_multiple')
    for r in params['parameters']:
        if r['parameter_id'] in dimensions:r['unit'],r['semantic_dimension']=dimensions[r['parameter_id']]
    params['time_counter_amendment']='R2.1_METADATA_ONLY_ALL_VALUES_KEEP';put('config/v4_12_parameter_set_v1.json',params)
    deriv=old('config/v4_12_source_derivations_r2.json');c=deriv['counters'];c.pop(OLD)
    c['producer']='V4_12_SESSION_COUNTER_V2'
    c[MARKET]=dict(definition='Count unique accepted calendar session_dates in (anchor.available_date, observation_trade_date]',
        increment='Each market session including security suspension/missing',reset='New immutable Anchor only',missing='Unavailable calendar -> UNKNOWN',same_day_revision='Same date, same count',
        unit='market_sessions_after_available_date',uses=['old_anchor','earliest test','same-day self-confirmation prevention'])
    c[EVAL]=dict(definition='Count unique sessions after available_date with a qualifying evaluable D1 observation through observation_trade_date',
        increment='One per qualifying distinct date',reset='New immutable Anchor only; NOT reset by missing',missing='Suspension/missing/required coordinate unavailable adds zero; unavailable frozen count/history -> UNKNOWN',
        same_day_revision='Recompute date membership against same frozen t-1 baseline; never accumulate revisions; quality correction replaces membership',
        unit='evaluable_sessions',uses=['acceptance.PENDING'],consecutive=False)
    c['consecutive_path']=dict(missing='Reset held/breach/recovery held chain to zero; prior_adjacent_evaluable false',
        same_day_revision='Same t-1 baseline; replace observation; held and breach never repeatedly increment')
    ledger=deriv['dependency_ledger'];ledger[MARKET+'/pivot_left_count/pivot_right_count']=ledger.pop(OLD+'/pivot_left_count/pivot_right_count')
    ledger[EVAL]=['frozen prior D1 evaluable count','unique observation market date','accepted current required source quality','available_date']
    deriv['time_counter_amendment']='R2.1';put('config/v4_12_source_derivations_r2.json',deriv)
    for name in ['support_state_contract','retention_contract']:
        contract=config(name);contract['time_counter_contract']='config/v4_12_source_derivations_r2.json#/counters'
        contract['time_counter_amendment']='R2.1'
        if name=='retention_contract':contract['acceptance_order']=['BROKEN hard invalidated','UNKNOWN current required observation unavailable','ACCEPTED old_anchor and consecutive held >= threshold','PENDING cumulative evaluable count < threshold','NOT_ACCEPTED otherwise evaluable']
        put('config/v4_12_'+name+'_v1.json',contract)
    # Independent amended oracle keeps every unaffected expected value.
    from scripts.v4_12_time_counter_oracle_r2_1 import amended_vectors,sequence_book,compatibility_vectors
    put('config/v4_12_time_counter_contract_v2.json',dict(contract_id='V4_12_SESSION_COUNTER_V2',version='2.0.0',scope='CONTRACT_DESIGN_ONLY',
        definitions=c,producer_runtime_available=False,runtime_authorized=False,permissions=PERMISSIONS,
        identity=['anchor_id','anchor.available_date','observation_trade_date','observation_revision'],
        unique_count_key=['anchor_id','observation_trade_date'],source_lineage='Accepted calendar + frozen prior D1 observations; no raw reconstruction',
        unknown_semantics='Unknown history/calendar/required source remains UNKNOWN; never FALSE or synthesized'))
    put('config/v4_12_time_counter_vectors_r2_1.json',dict(contract_id='V4_12_TIME_COUNTER_INDEPENDENT_VECTORS_R2_1',
        independent_oracle_source=bind('scripts/v4_12_time_counter_oracle_r2_1.py'),scope='SYNTHETIC_CONTRACT_ONLY_NO_RUNTIME',
        sequences=sequence_book(),time_domain_vectors=compatibility_vectors()))
    pack=config('machine_vectors');defaults=pack['defaults'];value=defaults.pop(OLD);defaults[MARKET]=value;defaults[EVAL]=value
    pack['vectors']=amended_vectors();pack['independent_oracle_source']=bind('scripts/v4_12_time_counter_oracle_r2_1.py')
    pack['time_counter_amendment']='R2.1_B03_MISSING_NORMATIVE_CORRECTION';put('config/v4_12_machine_vectors_v1.json',pack)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle-dir');a=p.parse_args()
    if a.bundle_dir:stage(a.bundle_dir)
    repair();print('R2.1_CONTRACT_COUNTERS_SPLIT_NO_RUNTIME')

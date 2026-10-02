"""Serialize research contracts only. No detector, publisher, DB or D2 integration."""
import json
from scripts.v4_11_promotion_contract_r1 import ROOT, PERMISSIONS, bind
from scripts.record_r7_stage_contract import put

PARAMETER_SET='V4_12_ENGINEERING_CANDIDATE_R1'
PARAMETERS={
 'breakout_atr_buffer':(.1,'ATR','10J'), 'breakout_clv_min':(.7,'ratio','10J'),
 'acceptance_consecutive_sessions':(2,'evaluable_sessions','10J/41D'),
 'impulse_body_atr_min':(1.,'ATR','41B'),'impulse_range_atr_min':(1.,'ATR','41B'),
 'impulse_clv_min':(.7,'ratio','41B'),'impulse_amount_ratio20_min':(1.2,'ratio','41B'),
 'support_touch_atr_buffer':(.25,'ATR','41C'),'support_close_breach_atr':(.5,'ATR','41C'),
 'support_deep_breach_atr':(1.5,'ATR','41C'),'support_approach_atr':(1.,'ATR','41C'),
 'support_reclaim_clv_min':(.5,'ratio','41C'),'support_break_consecutive_sessions':(2,'evaluable_sessions','41C'),
 'support_separated_retest_sessions':(1,'actual_sessions_fully_outside_touch_band','41C'),
 'support_tentative_hold_sessions':(1,'actual_sessions','41C'),
 'range_anchor_window':(20,'actual_bars','41A'),'range_anchor_range_atr_max':(4,'ATR','41A'),
 'range_anchor_abs_slope20_max':(.1,'ATR','41A'),'pivot_left_sessions':(2,'actual_evaluable_sessions','41A'),
 'pivot_right_sessions':(2,'actual_evaluable_sessions','41A'),'recovery_delta3_threshold':(3,'percentage_points','10L'),
 'earliest_anchor_test_sessions':(1,'market_sessions_after_available_date','13A/41A'),
 'retention_horizon_one':(1,'post_event_market_sessions','41D'),'retention_horizon_three':(3,'post_event_market_sessions','41D')}

def f(name): return {'field':name}
def p(name): return {'parameter_id':name}
def m(name): return {'math_constant':name}
def e(value): return {'enum':value}
def op(name,*args): return {'op':name,'args':list(args)}
def ALL(*args): return op('and',*args)
def ANY(*args): return op('or',*args)
def eq(a,b): return op('eq',a,b)
def ge(a,b): return op('ge',a,b)
def gt(a,b): return op('gt',a,b)
def lt(a,b): return op('lt',a,b)
def le(a,b): return op('le',a,b)
def add(a,b): return op('add',a,b)
def sub(a,b): return op('sub',a,b)
def mul(a,b): return op('mul',a,b)
def div(a,b): return op('div',a,b)
def NOT(a): return op('not',a)
def isin(a,values): return ANY(*(eq(a,e(v)) for v in values))
def select(rules,otherwise): return {'op':'ordered_select','rules':[{'when':a,'then':b} for a,b in rules],'otherwise':otherwise,'unknown':'STOP_WITH_UNKNOWN_BEFORE_LOWER_PRIORITY'}

def ast():
    terminal=isin(f('prior_support_state'),['BROKEN','INVALIDATED'])
    old=ge(f('post_creation_sessions'),p('earliest_anchor_test_sessions'))
    definitions={
      'old_anchor':old,
      'touch':ALL(le(f('L'),add(f('hi'),mul(p('support_touch_atr_buffer'),f('atr_prior_view')))),
                  ge(f('H'),sub(f('lo'),mul(p('support_touch_atr_buffer'),f('atr_prior_view'))))),
      'close_breach':lt(f('C'),sub(f('lo'),mul(p('support_close_breach_atr'),f('atr_prior_view')))),
      'deep_breach':lt(f('C'),sub(f('lo'),mul(p('support_deep_breach_atr'),f('atr_prior_view')))),
      'eod_reclaim':ALL(f('touch'),ge(f('C'),f('hi')),ge(f('CLV'),p('support_reclaim_clv_min'))),
      'breach_count':select([(NOT(f('evaluable')),m('ZERO')),
                             (f('close_breach'),add(select([(f('prior_adjacent_evaluable'),f('prior_breach_count'))],m('ZERO')),m('ONE')))],m('ZERO')),
      'separated_retest':ALL(gt(f('prior_test_count'),m('ZERO')),
                            ANY(ge(f('prior_separated_sessions'),p('support_separated_retest_sessions')),
                                ALL(eq(f('prior_support_state'),e('RETESTING')),f('prior_retest_qualified'),f('prior_adjacent_evaluable'))),f('touch')),
      'fully_outside_test_band':NOT(f('touch')),
      'next_test_count':select([(ALL(f('evaluable'),f('eod_reclaim'),ANY(eq(f('prior_test_count'),m('ZERO')),f('separated_retest'))),add(f('prior_test_count'),m('ONE')))],f('prior_test_count')),
      'separated_sessions':select([(NOT(f('evaluable')),m('ZERO')),(f('touch'),m('ZERO')),
                                   (gt(f('prior_test_count'),m('ZERO')),add(f('prior_separated_sessions'),m('ONE')))],m('ZERO')),
      'held_count':select([(ALL(f('evaluable'),f('old_anchor'),ge(f('C'),f('hi'))),add(select([(f('prior_adjacent_evaluable'),f('prior_held_count'))],m('ZERO')),m('ONE')))],m('ZERO')),
      'recovery_held_count':select([(ALL(f('evaluable'),f('old_anchor'),ge(f('C'),f('recovery_line_view'))),add(select([(f('prior_adjacent_evaluable'),f('prior_recovery_held_count'))],m('ZERO')),m('ONE')))],m('ZERO')),
      'post_peak_drawdown':lt(f('C'),f('prior_event_peak_view')),
      'body':sub(f('C'),f('O')), 'body_mid':div(add(f('O'),f('C')),m('TWO')),
      'body_atr':div(f('body'),f('atr_prior_view')), 'range_atr':div(sub(f('H'),f('L')),f('atr_prior_view')),
      'impulse':ALL(ge(f('body_atr'),p('impulse_body_atr_min')),ge(f('range_atr'),p('impulse_range_atr_min')),
                    ge(f('CLV'),p('impulse_clv_min')),ge(f('amount_ratio20'),p('impulse_amount_ratio20_min')),gt(f('rel_market_1'),m('ZERO'))),
      'breakout_trigger':ALL(gt(f('C'),add(f('prior_high20'),mul(p('breakout_atr_buffer'),f('ATR20')))),ge(f('CLV'),p('breakout_clv_min'))),
      'ma20_reclaim':op('require_known',f('close_t_minus_1'),f('ma20_t_minus_1'),
                        ALL(le(f('close_t_minus_1'),f('ma20_t_minus_1')),gt(f('C'),f('MA20')))),
      'relative_recovery':ALL(le(f('prior_delta3'),m('ZERO')),gt(f('delta3'),p('recovery_delta3_threshold')),gt(f('rel_market_1'),m('ZERO'))),
      'retention_denominator':sub(f('event_close_view'),f('base_view')),
      'retention_value':select([(le(f('retention_denominator'),m('ZERO')),e('NOT_APPLICABLE'))],div(sub(f('observation_close_view'),f('base_view')),f('retention_denominator'))),
      'range_anchor_qualified':ALL(le(f('prior_range20_atr'),p('range_anchor_range_atr_max')),le(op('abs',f('slope20')),p('range_anchor_abs_slope20_max'))),
      'gap_qualified':gt(f('L'),f('prior_high_view')),
      'pivot_available':ALL(ge(f('pivot_left_count'),p('pivot_left_sessions')),ge(f('pivot_right_count'),p('pivot_right_sessions')),f('pivot_low_strict')),
      'anchor_price_view':add(mul(f('alpha'),f('anchor_original_price')),f('beta')),
      'anchor_atr_view':mul(f('alpha'),f('anchor_original_atr')),
      'common_coordinate_return':sub(div(f('endpoint_price_view'),f('start_price_view')),m('ONE')),
      'episode_invalidated':ALL(f('episode_owns_anchor'),ANY(f('deep_breach'),ge(f('breach_count'),p('support_break_consecutive_sessions')))),
      'hard_invalidated':ANY(f('prior_hard_invalidated'),f('episode_invalidated'))}
    machines={
      'support':select([(terminal,f('prior_support_state')),(NOT(old),e('IDLE')),(NOT(f('evaluable')),e('UNKNOWN')),
        (ANY(f('deep_breach'),ge(f('breach_count'),p('support_break_consecutive_sessions'))),e('BROKEN')),
        (f('close_breach'),e('BREACHED_SHALLOW')),(ALL(f('separated_retest'),f('eod_reclaim')),e('HELD_CONFIRMED')),
        (ALL(f('eod_reclaim'),ANY(isin(f('prior_support_state'),['TESTING','BREACHED_SHALLOW']),eq(f('prior_test_count'),m('ZERO')))),e('RECLAIMED')),
        (ALL(eq(f('prior_support_state'),e('RECLAIMED')),ge(f('held_count'),p('support_tentative_hold_sessions')),NOT(f('close_breach'))),e('HELD_TENTATIVE')),
        (ALL(isin(f('prior_support_state'),['HELD_TENTATIVE','HELD_CONFIRMED']),f('touch'),NOT(f('eod_reclaim'))),e('RETESTING')),
        (f('touch'),e('TESTING')),(le(f('distance_zone'),mul(p('support_approach_atr'),f('atr_prior_view'))),e('APPROACHING'))],f('prior_support_state')),
      'breakout':select([(NOT(f('evaluable')),e('UNKNOWN')),
        (ALL(f('prior_breakout_exists'),terminal),e('FAILED_BREAKOUT')),
        (ALL(f('prior_breakout_exists'),old,ANY(eq(f('support_today'),e('HELD_CONFIRMED')),ge(f('held_count'),p('acceptance_consecutive_sessions')))),e('BREAKOUT_ACCEPTED')),
        (ALL(f('prior_breakout_exists'),old,f('touch')),e('TESTING')),
        (f('prior_breakout_exists'),e('BREAKOUT_TENTATIVE')),(f('breakout_trigger'),e('BREAKOUT_TENTATIVE')),
        (eq(f('near_high20_state'),e('NEAR')),e('APPROACHING'))],e('NO_BREAKOUT')),
      'pullback':select([(NOT(f('prior_valid_event')),e('NOT_PULLBACK')),(terminal,e('PULLBACK_FAILED')),
        (NOT(f('evaluable')),e('UNKNOWN')),(eq(f('support_today'),e('HELD_CONFIRMED')),e('PULLBACK_HELD')),
        (isin(f('support_today'),['RECLAIMED','HELD_TENTATIVE']),e('PULLBACK_RECLAIMED')),
        (ALL(f('touch'),isin(f('anchor_type'),['MA20_DYNAMIC','MA60_DYNAMIC'])),e('PULLBACK_TO_MA')),
        (ALL(f('touch'),isin(f('anchor_type'),['BULLISH_IMPULSE_BODY','BULLISH_IMPULSE_LOW'])),e('PULLBACK_TO_IMPULSE')),
        (f('touch'),e('PULLBACK_TO_BREAKOUT')),(f('post_peak_drawdown'),e('PULLBACK_IN_PROGRESS'))],e('NOT_PULLBACK')),
      'recovery':select([(f('prior_recovery_failed'),e('RECOVERY_FAILED')),
        (ALL(f('prior_recovery_exists'),old,ge(f('recovery_held_count'),p('acceptance_consecutive_sessions'))),e('RECOVERY_CONFIRMED')),
        (ALL(f('prior_valid_event'),old,f('eod_reclaim')),e('ANCHOR_RECLAIM')),
        (f('ma20_reclaim'),e('MA20_RECLAIM')),(f('relative_recovery'),e('RELATIVE_RECOVERY')),
        (gt(f('ret1'),m('ZERO')),e('BOUNCE_ONLY'))],e('NONE')),
      'acceptance':select([(f('hard_invalidated'),e('BROKEN')),(NOT(f('evaluable')),e('UNKNOWN')),
        (ALL(old,ge(f('held_count'),p('acceptance_consecutive_sessions'))),e('ACCEPTED')),
        (lt(f('post_creation_sessions'),p('acceptance_consecutive_sessions')),e('PENDING'))],e('NOT_ACCEPTED'))}
    return dict(contract_id='V4_12_MACHINE_AST_V1',definitions=definitions,machines=machines,
       parameter_set_id=PARAMETER_SET,math_constants={'ZERO':{'value':0,'reason':'additive identity / zero comparison / empty count'},
       'ONE':{'value':1,'reason':'unit count increment / multiplicative identity'},'TWO':{'value':2,'reason':'arithmetic midpoint divisor'}},
       grammar={'leaf':['field','parameter_id','math_constant','enum'],'operations':['and','or','not','eq','ge','gt','lt','le','add','sub','mul','div','abs','require_known','ordered_select']},
       unknown_semantics='KLEENE; ordered UNKNOWN stops before lower priority; missing numerator/denominator stays UNKNOWN; division <=0 UNKNOWN except retention NOT_APPLICABLE',
       unknown_reason='EXACT_SOURCE_REASON_OR_UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE',tooling_only=True)

def references(value,key):
    if isinstance(value,dict):
        if key in value: yield value[key]
        for v in value.values(): yield from references(v,key)
    elif isinstance(value,list):
        for v in value: yield from references(v,key)

def freeze():
    stage=json.loads((ROOT/'reports/v4_12_r1/R7_STAGE_CONTRACT.json').read_bytes())
    assert stage['scope']=='CONTRACT_DESIGN_FREEZE_ONLY'
    configs=[]
    def config(name,value):
        value={'version':'1.0.0','freeze_scope':'CONTRACT_DESIGN_ONLY','runtime_implemented':False,
               'parameter_set_id':PARAMETER_SET,'permissions':PERMISSIONS,**value}
        path='config/v4_12_'+name+'_v1.json';put(path,value);configs.append(path)
    config('parameter_set',dict(contract_id='V4_12_PARAMETER_SET_V1',parameters=[dict(parameter_id=k,value=v,unit=u,
        contract_scope=s,min=0,max=1 if 'clv' in k else None,min_inclusive=False,max_inclusive=True,
        status='ENGINEERING_CANDIDATE',reason='REV4 candidate default; no effectiveness claim',introduced_version='V4.2.2/R7',
        approved_at=None,supersedes=None,profitability_validated=False,statistically_optimal=False,production_proven=False)
        for k,(v,u,s) in PARAMETERS.items()],parameter_change='NEW_PARAMETER_SET_AND_MODEL_ID; preserve old observations'))
    tree=ast(); config('machine_ast',tree)
    fields=sorted((set(references(tree,'field'))-set(tree['definitions']))|{'MA60','pivot_low','price_basis','adjustment_source_revision'})
    unavailable={'close_t_minus_1','ma20_t_minus_1'}
    previous={'lo','hi','prior_support_state','prior_breakout_exists','prior_valid_event','prior_event_peak_view',
              'prior_test_count','prior_breach_count','prior_held_count','prior_adjacent_evaluable','prior_separated_sessions',
              'prior_recovery_failed','prior_recovery_exists','anchor_type','episode_owns_anchor','prior_hard_invalidated',
              'anchor_original_price','anchor_original_atr','event_close_view','base_view','prior_retest_qualified',
              'prior_recovery_held_count','recovery_line_view'}
    bools={'evaluable','prior_breakout_exists','prior_valid_event','prior_adjacent_evaluable','prior_recovery_failed',
           'prior_recovery_exists','episode_owns_anchor','prior_hard_invalidated','pivot_low_strict','prior_retest_qualified'}
    enums={'prior_support_state','anchor_type','near_high20_state','support_today','price_basis','adjustment_source_revision'}
    counts={x for x in fields if x.endswith('_count') or x.endswith('_sessions')}
    registry=[]
    metadata_types={'anchor_id':'string','security_id':'string','anchor_trade_date':'string','available_date':'string','available_at':'string',
        'anchor_type':'string','anchor_raw_lower':'number','anchor_raw_upper':'number','anchor_price_basis':'string',
        'adjustment_contract_id':'string','adjustment_source_identity':'string','adjustment_source_revision':'string','adjustment_asof':'string',
        'anchor_basis_trade_date':'string','frozen_transform_coefficients':'object','source_event_id':'string','source_fact_digest':'string',
        'creation_coordinate':'object','current_comparison_coordinate':'object','rebase_lineage':'array','corporate_action_transition':'array'}
    for name in fields:
        role='T_MINUS_1' if name in previous or name in unavailable else 'T'
        source='FROZEN_ANCHOR_EVENT' if name in previous else 'F0_ACCEPTED'
        if name=='support_today': source='D1_LOCAL_DERIVATION'
        producer='STRUCTURE_EVENT_V1' if name in previous else 'CORE_FACTOR_V1'
        if name=='support_today': producer='SUPPORT_STATE_V1'
        if name in {'O','H','L','C','price_basis','adjustment_source_revision'}:producer='V4_CANONICAL_DAILY_PIT_PERIODS_V3'
        if name in {'prior_delta3','atr_prior_view','prior_high_view'}: role='T_MINUS_1'
        if name in {'post_creation_sessions','pivot_left_count','pivot_right_count'}:
            producer='CROSS_SECTION_SESSION_WINDOW_V1'
        registry.append(dict(field=name,data_type='boolean' if name in bools else 'string' if name in enums else 'integer' if name in counts else 'number',
            unit='state_or_identity' if name in enums else 'predicate' if name in bools else 'evaluable_sessions' if name in counts else
                 'percentage_points' if name in {'delta3','prior_delta3'} else 'return_fraction' if name in {'ret1','rel_market_1'} else
                 'dimensionless_ratio' if name in {'CLV','amount_ratio20','alpha','prior_range20_atr'} else
                 'ATR_per_actual_session' if name=='slope20' else 'CNY_per_share_in_declared_common_coordinate',
            producer_contract_id=producer,parameter_set_id=PARAMETER_SET,source_namespace=source,trade_date='observation_t' if role=='T' else 'previous_market_session',
            time_role=role,required=True,publication_identity=['contract_id','parameter_set_digest','publication_id','publication_digest','source_revision','security_id','trade_date','available_at'],
            quality=['KNOWN','UNKNOWN','STALE','NOT_APPLICABLE'],unknown_reason_family=['MISSING_REQUIRED_FACT','PRICE_BASIS_MISMATCH','UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'],
            output_digest='SHA256_CANONICAL_FIELD_VALUE_AND_METADATA',formal_or_diagnostic='FORMAL_DESIGN_ONLY',
            capability='FORMAL_BLOCKED_INPUT_CAPABILITY' if name in unavailable else 'ACCEPTED_BINDING_REQUIRED_BEFORE_RUNTIME',
            raw_reconstruction_allowed=False))
    # Internal current D1 fields are derived, never supplied by downstream publications.
    for row in registry:
        if row['field']=='support_today': row['time_role']='T_INTERNAL_D1'
        if row['field']=='adjustment_source_revision':row['time_role']='T';row['source_namespace']='F0_ACCEPTED'
    for name,dtype in metadata_types.items():
        # Observation adjustment_source_revision is distinct from frozen Anchor's revision.
        registered_name='anchor_adjustment_source_revision' if name=='adjustment_source_revision' else name
        if registered_name in {r['field'] for r in registry}:continue
        registry.append(dict(field=registered_name,data_type=dtype,unit='immutable_anchor_metadata',producer_contract_id='STRUCTURE_EVENT_V1',
            parameter_set_id=PARAMETER_SET,source_namespace='FROZEN_ANCHOR_EVENT',trade_date='previous_market_session',time_role='T_MINUS_1',required=True,
            publication_identity=['anchor_id','source_event_id','source_fact_digest','available_at'],quality=['KNOWN','UNKNOWN','STALE'],
            unknown_reason_family=['MISSING_REQUIRED_FACT','PRICE_BASIS_MISMATCH'],output_digest='SHA256_IMMUTABLE_ANCHOR_AND_LINEAGE',
            formal_or_diagnostic='FORMAL_DESIGN_ONLY',capability='RUNTIME_NOT_AUTHORIZED',raw_reconstruction_allowed=False))
    for name in tree['definitions']:
        derived_predicates={'old_anchor','touch','close_breach','deep_breach','eod_reclaim','separated_retest','fully_outside_test_band','post_peak_drawdown',
                            'impulse','breakout_trigger','ma20_reclaim','relative_recovery','range_anchor_qualified','gap_qualified','pivot_available','episode_invalidated','hard_invalidated'}
        registry.append(dict(field=name,data_type='boolean' if name in derived_predicates else 'integer' if name in {'breach_count','held_count','recovery_held_count','next_test_count','separated_sessions'} else 'number_or_UNKNOWN_NOT_APPLICABLE',
            unit='predicate' if name in derived_predicates else 'actual_evaluable_sessions' if name in {'breach_count','held_count','recovery_held_count','next_test_count','separated_sessions'} else
                 'dimensionless_ratio' if name in {'body_atr','range_atr','retention_value','common_coordinate_return'} else 'CNY_per_share_in_common_coordinate',producer_contract_id='V4_12_MACHINE_AST_V1',
            parameter_set_id=PARAMETER_SET,source_namespace='D1_LOCAL_DERIVATION',trade_date='observation_t',time_role='T_INTERNAL_D1',required=True,
            publication_identity=['contract_id','parameter_set_digest','source_publication_bindings'],quality=['KNOWN','UNKNOWN'],
            unknown_reason_family=['EXACT_SOURCE_REASON','PRICE_BASIS_MISMATCH','UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'],
            output_digest='SHA256_CANONICAL_DERIVED_VALUE_AND_INPUT_BINDINGS',formal_or_diagnostic='FORMAL_DESIGN_ONLY',capability='RUNTIME_NOT_AUTHORIZED',raw_reconstruction_allowed=False))
    outputs={'active_anchor_id':'string','anchor_view_asof_t':'object','basic_breakout_state':'string','basic_pullback_state':'string',
             'basic_recovery_state':'string','structure_health':'string','structure_events':'array','support_state':'string',
             'acceptance_state':'string','impulse_retention_1':'number','impulse_retention_3':'number','retest_count':'integer',
             'unknown_reasons':'array','stale':'boolean','last_known_support_state':'string','invalidation_facts':'array'}
    for name,dtype in outputs.items():
        registry.append(dict(field=name,data_type=dtype,unit='ratio_unbounded' if 'retention' in name else 'test_count' if name=='retest_count' else
            'predicate' if name=='stale' else 'coordinate_view' if name=='anchor_view_asof_t' else 'event_fact_list' if dtype=='array' else 'enum_or_identity',
            producer_contract_id='RETENTION_V1' if 'retention' in name or name=='acceptance_state' else 'SUPPORT_STATE_V1' if 'support' in name or name=='retest_count' else 'STRUCTURE_EVENT_V1',
            parameter_set_id=PARAMETER_SET,source_namespace='D1_CONTRACT_OUTPUT',trade_date='observation_t',time_role='T_OUTPUT',required=True,
            publication_identity=['contract_id','parameter_set_digest','publication_id','publication_digest','trade_date','available_at'],
            quality=['KNOWN','UNKNOWN','STALE','NOT_APPLICABLE'],unknown_reason_family=['EXACT_SOURCE_REASON','UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE','PRICE_BASIS_MISMATCH'],
            output_digest='SHA256_CANONICAL_FIELD_VALUE_AND_METADATA',formal_or_diagnostic='FORMAL_DESIGN_ONLY',capability='RUNTIME_NOT_AUTHORIZED',raw_reconstruction_allowed=False))
    config('field_registry',dict(contract_id='V4_12_FIELD_REGISTRY_V1',fields=registry,
        unit_rules={'prices':'CNY per share in common comparison coordinate','ATR':'CNY difference; positive scale only','returns':'fraction; recompute common coordinate',
        'delta3':'percentage_points','CLV':'dimensionless [0,1] or UNKNOWN when H=L','counts':'actual/evaluable sessions per counter contract'}))
    config('time_role_registry',dict(contract_id='V4_12_TIME_ROLE_REGISTRY_V1',fields=[{k:r[k] for k in ['field','time_role','trade_date','source_namespace','producer_contract_id']} for r in registry],
        allowed_external_edges=['F0[t] -> D1[t]','Frozen Anchor/event[t-1] -> D1[t]'],allowed_internal_edge='SUPPORT_STATE_V1[t] -> STRUCTURE_EVENT_V1[t]',
        forbidden_edges=['D2[t] -> D1[t]','Final State[t] -> D1[t]','Event[t] -> D1[t]','Focus -> D1[t]','UI -> D1[t]','Supplemental feedback -> D1[t]','future outcome -> D1[t]'],
        cutoff='ALL external source available_at <= observation cutoff; prior Anchor/event available_date <= previous_market_session',
        new_anchor_rule='EMIT_NEW_EVENT_ONLY; NO_SELF_SUPPORT_ACCEPTANCE_CONFIRMATION; earliest available_date+1 market session',
        historical_F0='Previous-session factor/price must be explicitly published as an accepted F0[t] field with frozen lineage; never infer availability from local raw bars'))
    config('producer_registry',dict(contract_id='V4_12_PRODUCER_REGISTRY_V1',producers=[
        dict(producer_contract_id='V4_CANONICAL_DAILY_PIT_PERIODS_V3',namespace='F0_ACCEPTED',status='ACCEPTED_NATIVE_OHLC_AND_ADJUSTMENT_BINDING_REQUIRED',
             authority=bind('data/v4/V4_02_ACCEPTED_HEAD.json'),current_data_authority=bind('data/v4/V4_DATA_ACCEPTED_HEAD.json'),
             contract=bind('config/v4_02_canonical_daily_pit_contract_v3.json'),field_aliases={'O':'open','H':'high','L':'low','C':'close'},
             price_rule='OHLC must use same accepted adjusted observation basis; alias never changes owner quality/source digest'),
        dict(producer_contract_id='CORE_FACTOR_V1',namespace='F0_ACCEPTED',status='ACCEPTED_OWNER_AUTHORITY_REQUIRED',authority=bind('data/v4/V4_03_ACCEPTED_HEAD.json'),
             rule='Consume exact accepted field publication; daily t availability does not authorize reconstructing missing t-1 field',missing='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'),
        dict(producer_contract_id='CROSS_SECTION_SESSION_WINDOW_V1',namespace='F0_ACCEPTED',status='ACCEPTED_CALENDAR_AND_EXPLICIT_WINDOW_BINDING_REQUIRED',
             fields=[r['field'] for r in registry if r['producer_contract_id']=='CROSS_SECTION_SESSION_WINDOW_V1']),
        *[dict(producer_contract_id=x,namespace='D1_CONTRACT_DESIGN_ONLY',status='CONTRACT_FROZEN_RUNTIME_NOT_AUTHORIZED',fields=[r['field'] for r in registry if r['producer_contract_id']==x])
          for x in ['STRUCTURE_EVENT_V1','SUPPORT_STATE_V1','RETENTION_V1','V4_12_MACHINE_AST_V1']]],
        owner_parity_authority=bind('reports/v4_11_r5a/OWNER_INPUT_AUTHORITY_MATRIX.json'),
        derived_input_bindings={'evaluable':'Accepted actual bar AND valid source/basis AND positive converted prior ATR; missing required source is UNKNOWN',
           'distance_zone':'max(lo-C, C-hi, mathematical_zero) in observation coordinate',
           'post_creation_sessions':'Accepted market calendar session distance from Anchor available_date; zero on creation day; revision is not session',
           'prior_adjacent_evaluable':'Previous observation matches immediately preceding market session and was evaluable; false after missing/suspension',
           'prior_event_peak_view':'Frozen event path peak through previous session, rebased as view; never today/future peak',
           'recovery_line_view':'Creation-bound prior recovery line in current comparison coordinate',
           'prior_retest_qualified':'Frozen retest evidence records prior separated actual session; no raw bar reconstruction',
           'alpha/beta':'Accepted historical adjustment source-bound transform; positive alpha; coefficients are not identity'},
        capabilities=[dict(fields=sorted(unavailable),status='BLOCKED_WITH_EXPLICIT_REASON',capability='FORMAL_BLOCKED_INPUT_CAPABILITY',
            reason='Accepted owner lacks close_t_minus_1 and ma20_t_minus_1',policy='DO_NOT_RECONSTRUCT_FROM_RAW_BARS',result='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'),
          dict(fields=['t-1 frozen Anchor/event'],status='BLOCKED_WITH_EXPLICIT_REASON',capability='RUNTIME_NOT_AUTHORIZED',reason='D1 publication producer is contract design only; no accepted Anchor/event runtime publication'),
          dict(fields=['atr_prior_view','prior_high_view','prior_delta3','pivot_low_strict'],status='BLOCKED_WITH_EXPLICIT_REASON',capability='UNBOUND_REQUIRED_F0_INPUT',
               reason='Historical field authority must be explicitly published in F0[t]; this design does not grant new accepted producer capability')]))
    enumvalues=sorted(set(references(tree,'enum')))
    config('input_schema',dict(contract_id='V4_12_INPUT_SCHEMA_V1',schema={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object',
        'additionalProperties':False,'required':['contract_id','parameter_set_digest','observation_trade_date','cutoff','security_id','inputs'],
        'properties':{'contract_id':{'const':'V4_12_INPUT_V1'},'parameter_set_digest':{'type':'string','pattern':'^[0-9a-f]{64}$'},
        'observation_trade_date':{'type':'string','format':'date'},'cutoff':{'type':'string','format':'date-time'},'security_id':{'type':'string'},
        'inputs':{'type':'object','additionalProperties':False,'properties':{r['field']:{'$ref':'#/$defs/fact'} for r in registry if r['time_role'] not in ['T_OUTPUT','T_INTERNAL_D1']}}},
        '$defs':{'fact':{'type':'object','additionalProperties':False,'required':['value','quality','unknown_reason','producer_contract_id','publication_id','publication_digest','trade_date','available_at','source_namespace','time_role','output_digest','price_basis','adjustment_source_revision'],
        'properties':{'value':{'type':['number','string','boolean','object','array','null']},'quality':{'enum':['KNOWN','UNKNOWN','STALE','NOT_APPLICABLE']},'unknown_reason':{'type':['string','null']},
        **{k:{'type':'string'} for k in ['producer_contract_id','publication_id','publication_digest','trade_date','available_at','source_namespace','time_role','output_digest','price_basis','adjustment_source_revision']}}}}},
        cross_field_rules=['Missing required field -> UNKNOWN, not FALSE','KNOWN requires correct registered type, digest and accepted capability',
        'Foreign namespace/time role/late source rejected','Price/ATR/breach/support share observation basis identity','atr_prior_view > 0; H >= L; CLV UNKNOWN if H=L',
        'support_today is computed internally; external input forbidden','post_creation_sessions computed from available_date and market calendar; cannot be supplied without lineage']))
    output_metadata=['contract_id','parameter_set_digest','source_publication_bindings','output_digest','observation_date','cutoff','price_basis','adjustment_source_revision']
    config('output_schema',dict(contract_id='V4_12_OUTPUT_SCHEMA_V1',schema={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object',
        'additionalProperties':False,'required':list(outputs)+output_metadata,
        'properties':{**{k:{'type':[v,'null']} for k,v in outputs.items()},**{k:{'type':'array' if k=='source_publication_bindings' else 'string'} for k in output_metadata}}},
        state_enum_registry=enumvalues+['UNKNOWN','INVALIDATED','RETESTING','HELD_TENTATIVE','HELD_CONFIRMED'],
        metadata_required=output_metadata,
        publication_policy='No publishing authorized; immutable revision/output digest contract only',
        structure_health_mapping={'BROKEN':'DAMAGED','INVALIDATED':'DAMAGED','BREACHED_SHALLOW':'WEAKENING','HELD_CONFIRMED':'STABLE','RECLAIMED':'IMPROVING','UNKNOWN':'UNKNOWN','default':'STABLE'},
        null_value='Only with explicit UNKNOWN/NOT_APPLICABLE quality and reason',active_anchor_sort=['not invalidated','distance_to_C / ATR ascending','anchor_date descending','anchor_id ascending']))
    anchor_fields=['anchor_id','security_id','anchor_trade_date','available_date','available_at','anchor_type','anchor_raw_lower','anchor_raw_upper','anchor_price_basis',
        'adjustment_contract_id','adjustment_source_identity','adjustment_source_revision','adjustment_asof','anchor_basis_trade_date','frozen_transform_coefficients',
        'source_event_id','source_fact_digest','creation_coordinate','current_comparison_coordinate','rebase_lineage','corporate_action_transition']
    specs=[('PRIOR_HIGH','BREAKOUT','prior_high20','prior_high20','fixed',['prior_high20']),
        ('BREAKOUT_LEVEL','BREAKOUT','prior_high20','prior_high20','fixed',['prior_high20']),
        ('RANGE_UPPER','RANGE_BREAKOUT','prior_high20','prior_high20','fixed',['prior_high20','prior_range20_atr','slope20']),
        ('BULLISH_IMPULSE_BODY','BULLISH_IMPULSE','O','body_mid','fixed',['O','C','H','L','CLV','atr_prior_view','amount_ratio20','rel_market_1']),
        ('BULLISH_IMPULSE_LOW','BULLISH_IMPULSE','L','L','fixed',['O','C','H','L','CLV','atr_prior_view','amount_ratio20','rel_market_1']),
        ('MA20_DYNAMIC','FROZEN_REGISTERED_RISE','MA20','MA20','dynamic',['MA20']),('MA60_DYNAMIC','FROZEN_REGISTERED_RISE','MA60','MA60','dynamic',['MA60']),
        ('PIVOT_LOW','PIVOT_CONFIRMED','pivot_low','pivot_low','fixed',['pivot_left_count','pivot_right_count','pivot_low_strict','pivot_low']),
        ('GAP_ZONE','GAP_REGISTERED','prior_high_view','L','fixed',['prior_high_view','L'])]
    config('anchor_schema',dict(contract_id='V4_12_ANCHOR_SCHEMA_V1',required_fields=anchor_fields,
        schema={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','additionalProperties':False,'required':anchor_fields,
                'properties':{k:{'type':dtype} for k,dtype in metadata_types.items()}},
        identity='SHA256(contract_id, security_id, source_event_id, anchor_type, anchor_trade_date, source_fact_digest, price_basis, adjustment_source_revision)',
        types=[dict(anchor_type=t,source_event=event,creation_rule={'PRIOR_HIGH':'breakout_trigger','BREAKOUT_LEVEL':'breakout_trigger','RANGE_UPPER':'range_anchor_qualified AND breakout_trigger',
            'BULLISH_IMPULSE_BODY':'impulse','BULLISH_IMPULSE_LOW':'impulse','MA20_DYNAMIC':'prior registered rise event; accepted MA20 current view',
            'MA60_DYNAMIC':'prior registered rise event; accepted MA60 current view','PIVOT_LOW':'pivot_available; pivot low strictly below all left/right actual low bars',
            'GAP_ZONE':'gap_qualified'}[t],lower=lo,upper=hi,fixed_or_dynamic=mode,required_fields=req,
            price_basis='price_basis + adjustment_source_revision',available_date='confirmation_date' if t=='PIVOT_LOW' else 'creation_date',
            available_time='source publication available_at no later than cutoff',earliest_test_date='first market session AFTER available_date',
            unknown='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE_OR_EXACT_SOURCE_REASON',invalidation_relation='own frozen episode invalid_if only; never another Anchor') for t,event,lo,hi,mode,req in specs],
        original_immutable=True,observation_view_storage='Separate immutable view record per observation/revision; never update original Anchor current_comparison_coordinate/rebase_lineage; original stores creation identity only',
        dynamic_view='new view per observation date; preserve original event/formula and old values',
        historical_high_storage='Inverse accepted affine transform to anchor_basis_trade_date raw; not highest historical raw number',
        pivot_ties='Strictly lower than left/right actual-session lows; equal lows do not qualify',
        event_identity='Immutable source event ID plus contract/parameter/source digest; same-day revision keeps previous_session predecessor, no backdating'))
    config('anchor_coordinate_contract',dict(contract_id='V4_12_ANCHOR_COORDINATE_V1',accepted_authority=bind('data/v4/V4_03_ACCEPTED_HEAD.json'),
        basis_identity=['price_basis','adjustment_source_revision'],coefficient_equality_is_identity=False,original_anchor_immutable=True,
        level_transform='alpha * original + beta; alpha>0; source-bound deterministic accepted historical adjustment',
        difference_transform='alpha * difference; no beta for ATR',return_transform='endpoint_view/start_view - 1; start_view>0',
        compare_fields=['anchor','current_price','ATR','return','breach_depth','support_zone'],
        same_day_revision='New observation view/output revision against t-1 frozen event; never overwrite original or count revision as new session',
        lineage_required=['from_basis_identity','to_basis_identity','adjustment_source_digest','asof','alpha','beta','corporate_action_transition'],
        failed_conversion={'state':'UNKNOWN','reason':'PRICE_BASIS_MISMATCH','stale':True,'preserve_prior_state':True},
        corporate_action_cases=['cash_dividend','bonus_shares','rights_issue','same_day_revision','cross_corporate_action_support']))
    config('support_state_contract',dict(contract_id='SUPPORT_STATE_V1',machine='support',definitions=['touch','close_breach','deep_breach','eod_reclaim','breach_count','separated_retest'],
        ordered_ast_ref='config/v4_12_machine_ast_v1.json#/machines/support',counter_ast_refs=['breach_count','held_count','next_test_count','separated_sessions'],
        counter_rules={'missing':'Reset consecutive breach/held/separation counters; preserve prior state/test_count; stale true; does not restore',
        'same_day_revision':'Replace observation view against same t-1 counter baseline; no increment of market-session counts',
        'separation':'At least one actual fully non-touch session after prior test; UNKNOWN cannot qualify; consume separation when touch; qualified RETESTING episode may reclaim on next adjacent evaluable touch session',
        'first_test':'first EOD reclaim increments test_count=1; later qualified separated retest increments once',
        'terminal':'BROKEN/INVALIDATED retained; new recovery requires new event; no resurrection'},
        missing={'observation_state':'UNKNOWN','preserve_prior_state':True,'stale':True},invalidation='BROKEN price-path state; INVALIDATED administrative terminal of owning episode; distinct meanings',
        intraday_order_claim=False,episode_binding='creation-bound anchor; never switch with active_anchor display selection'))
    config('retention_contract',dict(contract_id='RETENTION_V1',formula_ast_ref='config/v4_12_machine_ast_v1.json#/definitions/retention_value',
        horizons=['retention_horizon_one','retention_horizon_three'],availability='Append observation only when target market session arrived and source cutoff visible',
        denominator_nonpositive='NOT_APPLICABLE',missing='UNKNOWN',epsilon_allowed=False,value_range='UNBOUNDED_REAL_NOT_PROBABILITY',
        coordinate='All event close, base and observation close transformed to same observation identity',event_facts_immutable=True,
        acceptance_ast_ref='config/v4_12_machine_ast_v1.json#/machines/acceptance',acceptance_support_distinct=True))
    config('structure_event_contract',dict(contract_id='STRUCTURE_EVENT_V1',authority_sections=['10J','10K','10L','13A','31','34A','41A0','41A','41B','41C','41D','87A'],
        machines={k:'config/v4_12_machine_ast_v1.json#/machines/'+k for k in ['breakout','pullback','recovery']},
        impulse_ast_ref='config/v4_12_machine_ast_v1.json#/definitions/impulse',
        recovery_missing_prior_policy='DO_NOT_RECONSTRUCT_FROM_RAW_BARS',recovery_missing_reason='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE',
        current_ma20_branch_capability='FORMAL_BLOCKED_INPUT_CAPABILITY',
        event_required_fields=['event_id','security_id','event_type','created_trade_date','available_at','contract_id','parameter_set_digest','source_fact_digest','anchor_id','prior_session_event_id','frozen_invalidation_ast'],
        unknown_priority='Earlier UNKNOWN prevents claiming later rule; MA20_RECLAIM requires prior owner fields known before evaluating Kleene predicate; missing authority cannot be defeated by current-price FALSE',
        no_prior_event='Known absence is distinct from missing prior publication',
        invalidation_ast_ref='config/v4_12_machine_ast_v1.json#/definitions/episode_invalidated',
        impulse_saved_fields=['open','body_mid','close','low','high'],supplemental_turnover_formal_input=False,
        new_anchor_same_day='Can emit event; cannot self support/accept/confirm',
        downstream_interface='D1 invalidation facts available as design output to RESEARCH_STATE_V1; no D2 implementation/integration',
        structure_events='Append immutable per-anchor event/revision; prior_session predecessor, not same_day_revision parent'))
    put('reports/v4_12_r1/V4_12_R1_CONFIG_MANIFEST.json',dict(contract_id='V4_12_R1_CONFIG_MANIFEST_V1',files=[bind(path) for path in configs]))
    print('V4_12_DESIGN_CONTRACTS_SERIALIZED_NO_RUNTIME')

if __name__=='__main__': freeze()

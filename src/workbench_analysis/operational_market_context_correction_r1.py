"""Strict target Market context correction; never generic numeric source admission."""
import ast,json,copy,hashlib
from .r43_owner_replay import checked
KEY='market_context_correction_preparation_r1'
CONTRACT='V4_MARKET_CONTEXT_CORRECTION_R1'
DRIVERS={'src/workbench_analysis/r43_market_replay.py':'materialize_market','src/workbench_analysis/operational_owner_adapter_v1.py':'replay'}


def driver_scope(before,after,function):
    # Entire approved AST pairs: excluding a function is never sufficient.
    approved={
        'materialize_market':('ae74dd5a3076fcd4c40622fd29ea4ef20f99c003023c5afd48b1b3eb86cbfa5a','7e8d24471509688e87a8431041348d1cd1ab81affa72ff68504c08d2ebeaab43'),
        'replay':('191c71be31b129f7b6d1e8d79cf6c5b4f65ae1ab9427573cd93bfa77bcdf5b36','2ef6669f0c6b2947c4d1066d84ef5678c37e8f856295a8bee456aff66e707010'),
    }
    old=ast.parse(before);new=ast.parse(after)
    actual=(hashlib.sha256(ast.dump(old).encode()).hexdigest(),hashlib.sha256(ast.dump(new).encode()).hexdigest())
    if actual!=approved.get(function):raise ValueError('MARKET_EXACT_APPROVED_DRIVER_AST_REQUIRED')
    def normalized(tree):
        targets=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==function]
        if len(targets)!=1:raise ValueError('MARKET_DRIVER_FUNCTION_REQUIRED')
        tree.body.remove(targets[0]);return ast.dump(tree),targets[0]
    a,_=normalized(old);b,current=normalized(new)
    if a!=b:raise ValueError('MARKET_UNRELATED_DRIVER_SOURCE_CHANGED')
    text=ast.unparse(current)
    if function=='materialize_market' and any(x not in text for x in ('predecessor_profiles','predecessor_markets','market_axis_primitives','market_trend_axis','project')):raise ValueError('MARKET_EXPLICIT_PRIOR_CONTEXT_REQUIRED')
    if function=='replay' and any(x not in text for x in ('predecessor_profiles','predecessor_markets','materialize_market')):raise ValueError('MARKET_ADAPTER_CONTEXT_REQUIRED')


def verify(root,candidate,policy=None):
    receipt=json.loads(checked(root,candidate[KEY]).read_bytes())
    if receipt.get('contract_id')!=CONTRACT:raise ValueError('MARKET_CORRECTION_RECEIPT_REQUIRED')
    original=json.loads(checked(root,receipt['generation_candidate']).read_bytes())
    result=json.loads(checked(root,receipt['patch_result']).read_bytes())
    day=candidate['accepted_trade_date']
    if result.get('acceptance')!='PASS' or result.get('compute_sessions')!=[day] or result.get('history_owners_changed') is not False or result.get('original_failure_preserved') is not True:raise ValueError('MARKET_TARGET_ONLY_RESULT_REQUIRED')
    g3=result.get('G3',{})
    if g3.get('status')!='PASS' or any(g3.get(k) is not True for k in ('actual_input_digest_recomputed','all_input_binding_hashes_verified','predecessor_is_exact_accepted_A')):raise ValueError('MARKET_INDEPENDENT_G3_REQUIRED')
    if candidate['owners'][day]['market']!=result['market_binding']:raise ValueError('MARKET_PATCH_OWNER_MISMATCH')
    if set(candidate['owners'])!=set(original['owners']):raise ValueError('MARKET_CORRECTION_DATE_CHANGED')
    for d,owners in original['owners'].items():
        for domain,binding in owners.items():
            if (d,domain)!=(day,'market') and candidate['owners'][d][domain]!=binding:raise ValueError('MARKET_UNRELATED_OWNER_CHANGED')
    allowed={'owners','registry','day_receipt','native_pg_owner_authority','native_product_read_authority','native_membership_reference','sealed_numeric_preparation','component_source_conservation','release_policy','accepted_algorithm_bindings',KEY,'runtime_acceptance_preparation_r1_1'}
    if any(candidate.get(k)!=v for k,v in original.items() if k not in allowed) or set(candidate)-set(original)-allowed:raise ValueError('MARKET_UNRELATED_CANDIDATE_CHANGED')
    market=json.loads(checked(root,result['market_binding']).read_bytes());reference=json.loads(checked(root,result['reference']).read_bytes())
    def business(value):
        value=copy.deepcopy(value);value.pop('input_bindings',None)
        for name in ('axes','trend'):
            value[name].pop('input_digest',None);value[name].pop('output_digest',None)
            for key in ('input_source_digest','market_snapshot_id','adjustment_basis_id'):value[name]['identity'].pop(key,None)
        return value
    if business(market)!=business(reference):raise ValueError('MARKET_FULL_BUSINESS_PARITY_FAILED')
    original_market=json.loads(checked(root,original['owners'][day]['market']).read_bytes())
    for name in ('axes','trend'):
        if market[name]['identity']['market_snapshot_id']!=original_market[name]['identity']['market_snapshot_id'] or market[name]['identity']['adjustment_basis_id']!=original_market[name]['identity']['adjustment_basis_id']:raise ValueError('MARKET_ORIGINAL_CORE_IDENTITY_CHANGED')
        payload=dict(market[name]);claimed=payload.pop('output_digest')
        if hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()!=claimed:raise ValueError('MARKET_OUTPUT_DIGEST_RECOMPUTATION_FAILED')
    for binding in market['input_bindings']:checked(root,binding)
    from workbench_db.v4_operational_predecessor_pg_v1 import read_predecessor
    prior=read_predecessor(root,original)
    if result['predecessor_market_bindings']!={d:o['market'] for d,o in prior['owners'].items()}:raise ValueError('MARKET_ACCEPTED_PREDECESSOR_CHANGED')
    for binding in g3['parameter_bindings'].values():checked(root,binding)
    for key in ('producer','current_limit','accepted_prior_limit'):checked(root,g3[key])
    actual_digest=hashlib.sha256(json.dumps(dict(core_owner=market['axes']['identity']['market_snapshot_id'],current_limits=g3['current_limit'],prior_limits=g3['accepted_prior_limit'],producer=g3['producer']),sort_keys=True).encode()).hexdigest()
    if any(market[name]['identity']['input_source_digest']!=actual_digest for name in ('axes','trend')):raise ValueError('MARKET_INPUT_DIGEST_RECOMPUTATION_FAILED')
    old_policy=json.loads(checked(root,original['release_policy']).read_bytes())
    old={b.get('module_path',b['path']):b for b in old_policy['accepted_algorithm_bindings']}
    for name,function in DRIVERS.items():
        binding=receipt['driver_bindings'][name]
        driver_scope(checked(root,old[name]).read_text(encoding='utf-8'),checked(root,binding).read_text(encoding='utf-8'),function)
        if policy:
            new=next(b for b in policy['accepted_algorithm_bindings'] if b.get('module_path',b['path'])==name)
            if new['sha256']!=binding['sha256']:raise ValueError('MARKET_RUNTIME_DRIVER_BINDING_MISMATCH')
    if receipt['driver_bindings']['src/workbench_analysis/r43_market_replay.py']['sha256']!=g3['producer']['sha256']:raise ValueError('MARKET_ACTUAL_DRIVER_MISMATCH')
    return receipt

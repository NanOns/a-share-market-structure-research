"""Versioned Pure-Core Stock PREWATCH raw qualification and priority primitives."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path

from .base_seed import (_load_accepted_source_context, _verify_file_binding, _logical_digest,
                        canonical_json, sha256_file, atomic_write_gzip_jsonl)

MODEL = 'STOCK_PREWATCH_V1'
PARAMETER_SET = 'V4_09_STOCK_PREWATCH_PARAMETER_SET_V1'

def digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()

def load_package(root):
    freeze = json.loads((root/'reports/v4_09/V4_09_CONTRACT_FREEZE.json').read_text(encoding='utf8'))
    if freeze['status'] != 'PASS_CONTRACT_FREEZE_CANDIDATE': raise ValueError('CONTRACT_NOT_FROZEN')
    package = {}
    for binding in freeze['frozen_bindings']:
        path, _ = _verify_file_binding(root, binding, 'V4-09 frozen package')
        package[path.name.removeprefix('v4_09_').removesuffix('_v1.json')] = json.loads(path.read_text(encoding='utf8'))
    for binding in freeze['authority'].values():
        if isinstance(binding, dict) and 'path' in binding: _verify_file_binding(root, binding, 'V4-09 authority')
    return package

def parameter_values(params):
    if params.get('parameter_set_id') != PARAMETER_SET: raise ValueError('PARAMETER_ID_MISMATCH')
    entries = params.get('parameters', [])
    if len(entries) != 2 or {e['parameter_id'] for e in entries} != {'delta3_medium','delta3_high'}:
        raise ValueError('PARAMETER_FIELDS_MISMATCH')
    values = {}
    for entry in entries:
        value = entry['value']
        if entry.get('unit') != 'percentage_points' or entry.get('comparison') != 'GTE' or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('PARAMETER_UNIT_OR_VALUE_INVALID')
        values[entry['parameter_id']] = value
    if values['delta3_medium'] >= values['delta3_high']: raise ValueError('PARAMETER_ORDER_INVALID')
    return values

def evaluate(facts, package):
    """Only the six declared inputs can influence rule output; no entity branches."""
    ast = package['machine_ast']
    params = parameter_values(package['parameter_set'])
    seed = facts.get('base_seed_state','UNKNOWN')
    quality = facts.get('mandatory_core_quality_ready','UNKNOWN')
    if seed not in ['TRUE','FALSE','UNKNOWN'] or quality not in ['TRUE','UNKNOWN']:
        raise ValueError('INVALID_TRI_STATE_OR_UNCONTRACTED_QUALITY_FALSE')
    if ast['raw'] != dict(op='UNKNOWN_DOMINANT_AND',fields=['base_seed_state','mandatory_core_quality_ready']):
        raise ValueError('UNSUPPORTED_RAW_AST')
    raw = 'UNKNOWN' if 'UNKNOWN' in [seed,quality] else seed
    delta = facts.get('delta3')
    emergence = 'UNKNOWN'
    if not isinstance(delta,bool) and isinstance(delta,(float,int)) and math.isfinite(delta):
        emergence = next((rule['result'] for rule in ast['emergence'] if delta >= params[rule['parameter']]),'LOW')
    structure = 'UNKNOWN'
    compression, ma = facts.get('compression_state','UNKNOWN'), facts.get('ma_structure_state','UNKNOWN')
    for rule in ast['structure']:
        value = compression if rule['field']=='compression_state' else ma
        if value in [None,'UNKNOWN']: break  # Earlier unresolved HIGH outranks a known MEDIUM.
        if value == rule['equals']:
            structure = rule['result']; break
    else: structure = 'LOW'
    risk = facts.get('core_extension_risk')
    if risk not in ast['enum_order']['risk_axis']: risk = 'UNKNOWN'
    axes = dict(emergence_axis=emergence,structure_quality_axis=structure,risk_axis=risk)
    matched, unknown = [], []
    for field,value in dict(base_seed_state=seed, mandatory_core_quality_ready=quality, **axes).items():
        (unknown if value=='UNKNOWN' else matched).append(dict(predicate=field,value=value))
    bucket = 'NOT_ELIGIBLE' if raw=='FALSE' else 'UNKNOWN_BUCKET'
    if raw=='TRUE' and 'UNKNOWN' not in axes.values():
        bucket = ast['fallback_bucket']
        for rule in ast['bucket_rules']:
            def predicate(item):
                field,op,expected = item
                actual = axes[field]
                if op=='EQ': return actual==expected
                order = ast['enum_order'][field]
                return order.index(actual)>=order.index(expected) if op=='GE' else order.index(actual)<=order.index(expected)
            if all(predicate(item) for item in rule['all']):
                bucket = rule['bucket']; matched.append(dict(predicate='bucket_'+bucket,value='TRUE')); break
    order = ast['enum_order']
    # Numeric tuple, unknown separate and last. No score aggregation.
    sort_key = [order['bucket'].index(bucket) if bucket in order['bucket'] else len(order['bucket']),
                -order['emergence_axis'].index(emergence) if emergence in order['emergence_axis'] else 1,
                -order['structure_quality_axis'].index(structure) if structure in order['structure_quality_axis'] else 1,
                order['risk_axis'].index(risk) if risk in order['risk_axis'] else len(order['risk_axis'])]
    return dict(raw_qualification=raw,**axes,priority_bucket=bucket,matched_predicates=matched,
                unknown_predicates=unknown,priority_sort_key=sort_key)

def _timestamp(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))

def project(core, factor, seed, context, package):
    """Whitelist source projection, including only required provenance and independent axes."""
    reasons = []
    quality_contract = package['mandatory_core_quality_contract']
    required = {r['field']: r for r in quality_contract['required_fields']}
    if set(required) != {'base_seed_state','core_price_damage'} or quality_contract['false_quality_rule'] is not None:
        raise ValueError('UNSUPPORTED_MANDATORY_QUALITY_CONTRACT')
    date = context['trade_date']; cutoff = _timestamp(context['knowledge_cutoff'])
    security = core.get('security_id')
    valid_identity = security in context['identity_ids'] and all(row.get('security_id')==security and row.get('trade_date')==date for row in [core,factor,seed])
    if not valid_identity: reasons.append('IDENTITY_OR_SAME_SESSION_MISMATCH')
    if core.get('publication_id')!=context['profile_row_publication_id'] or seed.get('publication_id')!=context['source_publication_id'] or seed.get('source_publication_id')!=context['profile_row_publication_id'] or seed.get('source_core_logical_digest')!=context['core_logical_digest']:
        reasons.append('ACCEPTED_PUBLICATION_LINEAGE_MISMATCH')
    for row in [core,factor]:
        if row.get('coordinate_basis')!='T0_CURRENT_COORDINATE' or row.get('historical_as_recorded_claim') is not False:
            reasons.append('PRICE_BASIS_OR_AS_RECORDED_CLAIM_INVALID')
        try:
            if row.get('max_source_trade_date',date.replace('-','')) and str(row.get('max_source_trade_date',date.replace('-',''))).replace('-','')>date.replace('-','') or _timestamp(row['formal_publication_at'])>cutoff:
                reasons.append('SOURCE_DATE_OR_AVAILABILITY_AFTER_CONTEXT')
        except (ValueError,KeyError,TypeError): reasons.append('SOURCE_TIME_UNKNOWN')
    fields = factor.get('fields',{})
    def number_field(name):
        item = fields.get(name,{})
        value = item.get('value')
        try:
            provenance = item['target_trade_date']==date and item['source_asof']==date and str(item['max_source_trade_date']).replace('-','')<=date.replace('-','') and _timestamp(item['available_at'])<=cutoff and item['contract_id']=='CORE_FACTOR_V1'
        except (KeyError,ValueError,TypeError): provenance=False
        known = provenance and item.get('quality_state')=='OBSERVED' and item.get('unknown_reason') is None
        return item, value if known else None
    damage_item,damage = number_field('core_price_damage')
    if not isinstance(damage,bool) or damage_item.get('quality_state') not in required['core_price_damage']['quality_allowlist']:
        reasons.append('core_price_damage:'+str(damage_item.get('unknown_reason') or 'REQUIRED_CORE_UNKNOWN'))
    state = seed.get('base_seed_state','UNKNOWN')
    if state not in required['base_seed_state']['value_allowlist'] or seed.get('quality') not in required['base_seed_state']['quality_allowlist'] or seed.get('model_contract_id')!='BASE_SEED_V1':
        reasons.append('base_seed_state:ACCEPTED_SEED_UNKNOWN')
        state = 'UNKNOWN'
    delta_item, delta = number_field('rps5_delta3')
    def state_field(name):
        item = core.get('states',{}).get(name,{})
        return item.get('value','UNKNOWN') if item.get('unknown_reason') is None and item.get('value') is not None else 'UNKNOWN'
    facts = dict(base_seed_state=state, mandatory_core_quality_ready='UNKNOWN' if reasons else 'TRUE', delta3=delta,
                 compression_state=state_field('compression_state'), ma_structure_state=state_field('ma_structure_state'),
                 core_extension_risk=state_field('core_extension_risk'))
    # Digests consume the same whitelist as the formula; forbidden inputs do not alter bytes.
    provenance = dict(security_id=security,trade_date=date,profile_publication=core.get('publication_id'),
        seed_publication=seed.get('publication_id'),source_core_logical_digest=seed.get('source_core_logical_digest'),
        coordinate_basis=core.get('coordinate_basis'),factor_coordinate_basis=factor.get('coordinate_basis'),
        core_price_damage=damage,damage_quality=damage_item.get('quality_state'),delta_quality=delta_item.get('quality_state'))
    return facts, sorted(set(reasons)), provenance

def build(core_rows, factor_rows, seed_rows, context, package):
    expected = set(context['identity_ids'])
    indexes = []
    for rows in [core_rows,factor_rows,seed_rows]:
        index = {row['security_id']:row for row in rows}
        if len(index)!=len(rows) or set(index)!=expected: raise ValueError('EXACT_UNIVERSE_COVERAGE_MISMATCH')
        indexes.append(index)
    if len(expected)!=context['expected_identity_count']: raise ValueError('IDENTITY_COUNT_CONTEXT_MISMATCH')
    boards = Counter(row['board'] for row in core_rows)
    if dict(boards)!=context['expected_board_counts']: raise ValueError('BOARD_SCOPE_CONTEXT_MISMATCH')
    bindings = context['source_bindings']
    publication = 'V4_09:'+digest(dict(context_id=context['context_id'],source_bindings=bindings,package_digest=digest(package)))
    results=[]
    for security in sorted(expected):
        core,factor,seed = [index[security] for index in indexes]
        facts,reasons,provenance = project(core,factor,seed,context,package)
        evaluated = evaluate(facts,package)
        waiting = [{'field_id':p['predicate'], 'reason':'UPSTREAM_PRIORITY_OR_REQUIRED_UNKNOWN'} for p in evaluated['unknown_predicates']]
        waiting += [{'field_id':'mandatory_core_quality_ready','reason':r} for r in reasons]
        results.append(dict(security_id=security,trade_date=context['trade_date'],publication_id=publication,
            base_seed_state=facts['base_seed_state'],mandatory_core_quality_ready=facts['mandatory_core_quality_ready'],
            **evaluated,waiting_for=waiting,quality='PARTIAL_UNKNOWN' if waiting else 'READY',
            input_digest=digest(dict(facts=facts,provenance=provenance,source_bindings=bindings)),
            parameter_set_id=package['parameter_set']['parameter_set_id'],model_contract_id=MODEL,
            source_publication_id=context['source_publication_id'],source_core_logical_digest=context['core_logical_digest']))
    return results

def load_accepted(root):
    """Resolve authoritative target from accepted heads, not from a source-code date."""
    package = load_package(root)
    old_context, core_rows, factor_rows = _load_accepted_source_context(root)
    global_head = json.loads((root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_text(encoding='utf8'))
    if global_head.get('v4_09_entry')!='AUTHORIZED_AFTER_V4_08_PROMOTION_VALIDATION': raise ValueError('V4_09_ENTRY_NOT_AUTHORIZED')
    seed_path,_ = _verify_file_binding(root,global_head['v4_07_binding'],'accepted V4-07 head')
    seed_head=json.loads(seed_path.read_text(encoding='utf8'))
    if seed_head.get('external_acceptance')!='EXTERNALLY_ACCEPTED': raise ValueError('SEED_NOT_ACCEPTED')
    artifact=seed_head['candidate_artifact']; path,_ = _verify_file_binding(root,artifact,'accepted V4-07 artifact')
    with gzip.open(path,'rt',encoding='utf8') as stream: seeds=[json.loads(line) for line in stream]
    seed_manifest_path,_ = _verify_file_binding(root,seed_head['evidence_bindings']['candidate_manifest'],'accepted Seed manifest')
    manifest=json.loads(seed_manifest_path.read_text(encoding='utf8'))
    seed_source=manifest['source_bindings'] if 'source_bindings' in manifest else None
    if seed_source is None:
        receipt_path,_ = _verify_file_binding(root,seed_head['evidence_bindings']['pre_final_candidate_receipt'],'accepted Seed source receipt')
        seed_source=json.loads(receipt_path.read_text(encoding='utf8'))['source_bindings']
    if _logical_digest(seeds,seed_source)!=artifact['logical_digest']: raise ValueError('SEED_LOGICAL_DIGEST_MISMATCH')
    if seed_head['accepted_input']['trade_date']!=old_context['trade_date'] or seed_head['accepted_input']['core_logical_digest']!=old_context['core_logical_digest']:
        raise ValueError('ACCEPTED_CORE_SEED_SESSION_MISMATCH')
    identity_path,_ = _verify_file_binding(root,global_head['bindings']['v4_01_identity_map'],'accepted identity map')
    identity=json.loads(identity_path.read_text(encoding='utf8'))
    target=old_context['trade_date']
    valid_ids={r['security_id'] for r in identity['records'] if r.get('security_type')=='A_STOCK' and r.get('list_date') and r['list_date']<=target and (not r.get('delist_date') or r['delist_date']>target)}
    ids={r['security_id'] for r in core_rows}
    if not ids<=valid_ids: raise ValueError('ACCEPTED_IDENTITY_DATE_MEMBERSHIP_MISMATCH')
    accepted_core_head=json.loads((root/'data/v4/V4_05_ACCEPTED_HEAD.json').read_text(encoding='utf8'))
    source_bindings=dict(core_profile=accepted_core_head['accepted_artifact'],factors=accepted_core_head['accepted_artifacts']['full_scope_factors'],
        seed_artifact=artifact,identity_map=global_head['bindings']['v4_01_identity_map'],
        core_logical_digest=old_context['core_logical_digest'],seed_logical_digest=artifact['logical_digest'])
    context=dict(context_id='ACCEPTED_CORE_SEED:'+digest(source_bindings), trade_date=target,
        source_publication_id=old_context['publication_id'],profile_row_publication_id=old_context['profile_row_publication_id'],
        core_logical_digest=old_context['core_logical_digest'], expected_identity_count=old_context['expected_identity_count'],
        expected_board_counts=old_context['expected_board_counts'],identity_ids=sorted(ids),source_bindings=source_bindings,
        knowledge_cutoff=seed_head['accepted_at_date']+'T23:59:59+08:00',
        universe_authority='Exact accepted V4-05 full-scope research universe, validated against date-effective accepted V4-01 identities',
        capability=seed_head['capabilities']['REAL_BASE_SEED_SIGNAL'])
    return context,core_rows,factor_rows,seeds,package

def materialize(root, output):
    context,cores,factors,seeds,package=load_accepted(root)
    rows=build(cores,factors,seeds,context,package)
    atomic_write_gzip_jsonl(output,rows)
    return dict(contract_id='V4_09_FULL_MARKET_CANDIDATE_V1',status='ENGINEERING_CANDIDATE',
        run_context=context, artifact=dict(path=output.relative_to(root).as_posix(),sha256=sha256_file(output),
        byte_count=output.stat().st_size,logical_digest=digest(rows)),row_count=len(rows),
        raw_counts={k:sum(r['raw_qualification']==k for r in rows) for k in ['TRUE','FALSE','UNKNOWN']},
        bucket_counts={k:sum(r['priority_bucket']==k for r in rows) for k in ['A','B','C','D','UNKNOWN_BUCKET','NOT_ELIGIBLE']},
        board_counts=context['expected_board_counts'],production_permission=False)

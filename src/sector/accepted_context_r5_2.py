"""V4_08_ACCEPTED_INPUT_CONTEXT_R5_2; three-head reader, never a head writer."""
import copy
import json
from datetime import datetime
from pathlib import Path
from v4.canonical_governance_hash import canonical_json_file_sha256, canonical_json_sha256

CONTRACT_ID = 'V4_08_ACCEPTED_INPUT_CONTEXT_R5_2'
PERMITTED = {'FULL_PASS', 'DEGRADED_PASS'}


def validate_context(root, context, *, target, cutoff):
    from sector.accepted_input_r5_1 import bound_file
    result = copy.deepcopy(context)
    if result.get('contract_id') != CONTRACT_ID or not result.get('context_id'):
        raise ValueError('ACCEPTED_CONTEXT_CONTRACT_REQUIRED')
    scope = result.get('scope')
    if scope not in {'DAILY_ACCEPTED_DATA', 'ENGINEERING_REPLAY_ONLY'}:
        raise ValueError('ACCEPTED_CONTEXT_SCOPE_INVALID')
    if result.get('daily_production_authority') is not (scope == 'DAILY_ACCEPTED_DATA'):
        raise ValueError('ACCEPTED_CONTEXT_AUTHORITY_SCOPE_MISMATCH')
    governance = result.get('governance', {})
    head_path = governance.get('source_head_path')
    path = (Path(root).resolve()/str(head_path)).resolve()
    if not path.is_relative_to(Path(root).resolve()) or canonical_json_file_sha256(path) != governance.get('source_head_digest'):
        raise ValueError('ACCEPTED_CONTEXT_HEAD_DIGEST_MISMATCH')
    if scope == 'DAILY_ACCEPTED_DATA':
        head = json.loads(path.read_text(encoding='utf8'))
        if head.get('contract_id') != 'V4_DATA_ACCEPTED_HEAD_V1' or head.get('accepted_trade_date') != result.get('accepted_trade_date'):
            raise ValueError('DAILY_ACCEPTED_HEAD_CONTEXT_MISMATCH')
        expected = dict(path=head['manifest_path'], sha256=head['manifest_sha256'])
        if (governance.get('manifest_binding') != expected or governance.get('parent_identity') != head.get('parent_head_sha256')
                or governance.get('source_revision') != head.get('source_revision') or governance.get('canonical_data_revision') != head.get('canonical_data_revision')):
            raise ValueError('DAILY_ACCEPTED_CONTEXT_LINEAGE_MISMATCH')
        manifest = json.loads(bound_file(root, expected).read_text(encoding='utf8'))
        # Ready contexts must be exactly the immutable publication's bindings;
        # caller-supplied paths cannot impersonate the accepted daily authority.
        if result['accepted_trade_date'] <= target:
            accepted = manifest.get('accepted_input_context')
            if accepted is None and any(result.get(k,{}).get('capability') in PERMITTED for k in ('raw_daily','adjusted_price')):
                raise ValueError('DAILY_CONTEXT_NOT_BOUND_BY_ACCEPTED_MANIFEST')
            if accepted is not None and any(result.get(k) != accepted.get(k) for k in ('raw_daily','adjusted_price')):
                raise ValueError('DAILY_CONTEXT_NOT_BOUND_BY_ACCEPTED_MANIFEST')
            for key, capability in [('raw_daily','RAW_DAILY'),('adjusted_price','ADJUSTED_DAILY')]:
                head_status = head['component_permissions'][capability]['status']
                if result[key]['capability'] in PERMITTED and head_status not in PERMITTED:
                    raise ValueError('DAILY_CONTEXT_CAPABILITY_OVERCLAIM')
    date = result['accepted_trade_date']
    if date > target:
        raise ValueError('FUTURE_ACCEPTED_CONTEXT_DATE')
    if date < target:
        result['availability'] = 'TARGET_ACCEPTED_DATA_UNAVAILABLE'
        return result
    limit = datetime.fromisoformat(cutoff.replace('Z', '+00:00'))
    for key in ('raw_daily','adjusted_price'):
        item = result.get(key)
        if not isinstance(item, dict) or item.get('capability') not in {'FULL_PASS','DEGRADED_PASS','BLOCKED','NOT_APPLICABLE'}:
            raise ValueError('ACCEPTED_CONTEXT_CAPABILITY_INVALID')
        if item['capability'] not in PERMITTED:
            continue
        if not all(item.get(k) for k in ('path','sha256','source_digest','available_at','revision_semantics')):
            raise ValueError('ACCEPTED_CONTEXT_SOURCE_IDENTITY_REQUIRED')
        if key == 'adjusted_price' and not all(item.get(k) for k in ('logical_digest','coordinate_identity')):
            raise ValueError('ACCEPTED_CONTEXT_PRICE_IDENTITY_REQUIRED')
        if datetime.fromisoformat(item['available_at'].replace('Z', '+00:00')) > limit:
            raise ValueError('FUTURE_ACCEPTED_CONTEXT_REVISION')
    result['availability'] = 'TARGET_ACCEPTED_DATA_CONTEXT'
    return result


def resolve_daily_context(root, *, target, head_path='data/v4/V4_DATA_ACCEPTED_HEAD.json'):
    """Read existing moving authority. Stale head never falls back to stage IO."""
    from sector.accepted_input_r5_1 import bound_file
    root = Path(root)
    head = json.loads((root/head_path).read_text(encoding='utf8'))
    if head.get('contract_id') != 'V4_DATA_ACCEPTED_HEAD_V1':
        raise ValueError('DAILY_DATA_HEAD_CONTRACT_INVALID')
    manifest_binding = dict(path=head['manifest_path'], sha256=head['manifest_sha256'])
    manifest = json.loads(bound_file(root, manifest_binding).read_text(encoding='utf8'))
    accepted = manifest.get('accepted_input_context', {})
    unavailable = dict(capability='BLOCKED', reason='TARGET_ACCEPTED_DATA_UNAVAILABLE')
    context = dict(contract_id=CONTRACT_ID, context_id='DAILY_DATA_CONTEXT:'+canonical_json_file_sha256(root/head_path),
                   scope='DAILY_ACCEPTED_DATA', daily_production_authority=True, accepted_trade_date=head['accepted_trade_date'],
                   raw_daily=copy.deepcopy(accepted.get('raw_daily',unavailable)), adjusted_price=copy.deepcopy(accepted.get('adjusted_price',unavailable)),
                   governance=dict(source_head_path=head_path, source_head_digest=canonical_json_file_sha256(root/head_path),
                                   parent_identity=head.get('parent_head_sha256'), manifest_binding=manifest_binding,
                                   source_revision=head['source_revision'], canonical_data_revision=head['canonical_data_revision']))
    if head['accepted_trade_date'] == target and not accepted:
        # Bootstrap metadata has no sector-compatible immutable source pair.
        # It remains unavailable, without reading its static parent heads.
        context['raw_daily']=copy.deepcopy(unavailable)
        context['adjusted_price']=copy.deepcopy(unavailable)
    return context


def static_engineering_context(root):
    """Explicit caller-only replay context, never daily production authority."""
    from sector.accepted_input_r5_1 import bound_file
    root=Path(root)
    head_path='data/v4/V4_02_ACCEPTED_HEAD.json'
    price_head_path='data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json'
    head=json.loads((root/head_path).read_text(encoding='utf8'))
    price_head=json.loads((root/price_head_path).read_text(encoding='utf8'))
    if any(h.get('external_acceptance')!='EXTERNALLY_ACCEPTED' for h in (head,price_head)):
        raise ValueError('UNACCEPTED_STATIC_ENGINEERING_AUTHORITY')
    manifest_binding=dict(path=head['manifest_path'],sha256=head['manifest_sha256'])
    manifest=json.loads(bound_file(root,manifest_binding).read_text(encoding='utf8'))
    daily=manifest['components']['DAILY_R7']
    # Explicitly freeze baseline cutoff; 9/28 price never makes 9/24 raw daily
    # a later same-session authority. The replay is unavailable at later targets.
    return dict(contract_id=CONTRACT_ID,context_id='STATIC_ENGINEERING_BASELINE_CONTEXT',scope='ENGINEERING_REPLAY_ONLY',daily_production_authority=False,
                accepted_trade_date=head.get('source_cutoff',head.get('accepted_trade_date')),
                raw_daily=dict(**daily,source_digest=daily['sha256'],available_at=head['accepted_at_utc'],capability='FULL_PASS',revision_semantics='PER_ROW_adjustment_source_revision'),
                adjusted_price=dict(**price_head['accepted_candidate'],source_digest=price_head['logical_digest'],logical_digest=price_head['logical_digest'],
                                    available_at=head['accepted_at_utc'],capability='DEGRADED_PASS',revision_semantics='adjustment_snapshot_digest',coordinate_identity='coordinate_basis:adjustment_snapshot_id'),
                governance=dict(source_head_path=head_path,source_head_digest=canonical_json_file_sha256(root/head_path),parent_identity=None,
                                manifest_binding=manifest_binding,price_head_path=price_head_path,price_head_digest=canonical_json_file_sha256(root/price_head_path)))

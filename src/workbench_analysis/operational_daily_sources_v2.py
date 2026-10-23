"""日更来源解析 V2：前态、当日冻结与显式历史复现分开。"""
from pathlib import Path

from .r43_owner_replay import checked, load, ref

CONTRACT = 'V4_DAILY_OWNER_SOURCE_CONTEXT_V2'
AUTHORITY = 'config/operational_daily_source_authority_v2.json'


def dependency_sessions(sessions, targets, offsets=(1, 3, 4, 5)):
    """不足窗口必须阻断；Python 负索引不能成为历史来源。"""
    if sessions != sorted(set(sessions)):
        raise ValueError('SOURCE_CALENDAR_NOT_UNIQUE_SORTED')
    result = set(targets)
    for day in targets:
        if day not in sessions:
            raise ValueError('SOURCE_CALENDAR_SESSION_MISSING:' + day)
        index = sessions.index(day)
        for offset in offsets:
            if index < offset:
                raise ValueError('SOURCE_CALENDAR_WINDOW_MISSING:' + day + ':' + str(offset))
            result.add(sessions[index - offset])
    return sorted(result)


def resolve(root, parent, freeze, *, historical_manifest=None):
    """所有输入有确定身份；不搜索目录或取任意历史第一项。

    historical_manifest 仅供明确历史复现，必须绑定目标日和前态摘要。
    正常新增日从当日前态的数值收据、seed 和 source_registry 解析。
    """
    import hashlib, json
    root = Path(root).resolve()
    day = freeze['target_session']
    previous = parent['accepted_trade_date']
    manifest=None
    if historical_manifest is not None:
        manifest=load(checked(root,historical_manifest))
        parent_digest=hashlib.sha256(json.dumps(parent,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if (manifest.get('contract_id')!='V4_EXPLICIT_HISTORICAL_OWNER_REPLAY_V1'
                or manifest.get('target_session')!=day or manifest.get('parent_digest')!=parent_digest):
            raise ValueError('SOURCE_HISTORICAL_REPLAY_SCOPE_MISMATCH')
    authority_binding = freeze.get('owner_source_authority')
    authority_path = checked(root, authority_binding) if authority_binding else root / AUTHORITY
    if not authority_path.is_file():
        raise ValueError('SOURCE_OWNER_AUTHORITY_MISSING')
    authority = load(authority_path)
    if authority.get('contract_id') != CONTRACT or authority.get('version') != '2.0.0':
        raise ValueError('SOURCE_OWNER_AUTHORITY_INVALID')
    evidence = {}
    for name in ('phase0', 'upgrade_document', 'task_contract', 'runtime_contract'):
        if not isinstance(authority.get(name), dict):
            raise ValueError('SOURCE_' + name.upper() + '_MISSING')
        evidence[name] = checked(root, authority[name])
    if load(evidence['phase0']).get('phase0_status') not in ('FULL_PASS', 'DEGRADED_PASS'):
        raise ValueError('SOURCE_PHASE0_BLOCKED')
    roots = load(evidence['runtime_contract']).get('read_only_tdx_roots', [])
    if not roots:
        raise ValueError('SOURCE_TDX_ROOT_MISSING')
    roots = list(dict.fromkeys(Path(path).resolve() for path in roots))
    selected = freeze.get('read_only_tdx_root')
    if selected:
        tdx_root = Path(selected).resolve()
        if tdx_root not in roots:
            raise ValueError('SOURCE_TDX_ROOT_NOT_CONFIGURED')
    else:
        candidates = roots if manifest else [path for path in roots if (path / 'T0002/hq_cache/gbbq').is_file()]
        if not candidates:
            raise ValueError('SOURCE_GBBQ_MISSING')
        if len(candidates) != 1:
            raise ValueError('SOURCE_TDX_ROOT_AMBIGUOUS')
        tdx_root = candidates[0]
    lifecycle_binding = freeze.get('lifecycle') or parent.get('source_registry', {}).get(previous, {}).get('lifecycle') or parent['owners'][previous].get('lifecycle')
    if not lifecycle_binding:
        raise ValueError('SOURCE_LIFECYCLE_MISSING')
    lifecycle = load(checked(root, lifecycle_binding))
    identity = freeze.get('identity') or lifecycle.get('identity')
    if not identity:
        raise ValueError('SOURCE_IDENTITY_MISSING')
    checked(root, identity)
    membership = freeze.get('membership_snapshot') or parent.get('source_registry', {}).get(previous, {}).get('membership') or parent.get('membership_snapshot')
    if not membership:
        raise ValueError('SOURCE_MEMBERSHIP_MISSING')
    snapshot = load(checked(root, membership))
    gbbq_path=tdx_root/'T0002/hq_cache/gbbq'
    if manifest:
        # Historical replay uses the explicitly frozen bytes, never today's
        # local actions or a newly observed member set.
        identity=manifest['identity'];checked(root,identity)
        snapshot=load(checked(root,manifest['membership']))
        gbbq_path=checked(root,manifest['gbbq'])
    # The predecessor receipt is authoritative for the exact predecessor date.
    if not parent.get('day_receipt'):
        raise ValueError('SOURCE_PREDECESSOR_RECEIPT_MISSING')
    receipt = load(checked(root, parent['day_receipt']))
    core_binding = receipt.get('numeric_core_oracle')
    if not core_binding:
        raise ValueError('SOURCE_PREDECESSOR_CORE_MISSING')
    cores = load(checked(root, core_binding)).get('owners', [])
    matches = [row for row in cores if row.get('trade_date') == previous]
    if len(matches) != 1:
        raise ValueError('SOURCE_PREDECESSOR_CORE_MISSING' if not matches else 'SOURCE_PREDECESSOR_CORE_AMBIGUOUS')
    oldcore = matches[0]
    if oldcore.get('core') != parent['owners'][previous]['core']:
        raise ValueError('SOURCE_PREDECESSOR_CORE_IDENTITY_MISMATCH')
    checked(root, oldcore['sources']['gbbq'])
    registry = load(checked(root, parent['registry']))
    trace_binding = registry.get('source_adapter_trace')
    trace = load(checked(root, trace_binding)) if trace_binding else {'dates': []}
    acquisition = {'contract_id': CONTRACT, 'queries': []}
    seed_registry = {'contract_id': CONTRACT, 'owners': [
        {'trade_date': date, 'seed': owner['seed']} for date, owner in sorted(parent['owners'].items()) if owner.get('seed')]}
    if historical_manifest is not None:
        acquisition = load(checked(root, manifest['acquisition']))
        seed_registry = load(checked(root, manifest['seed_registry']))
        trace = load(checked(root, manifest['trace']))
    return dict(contract_id=CONTRACT, authority=ref(root, authority_path), evidence=evidence,
                tdx_root=tdx_root, read_only_roots=roots, identity=identity, snapshot=snapshot,
                gbbq_path=gbbq_path,
                oldcore=oldcore, acquisition=acquisition, trace=trace, seed_registry=seed_registry,
                historical_manifest=historical_manifest)

"""R9 来源解析：换日/切源、哈希身份、缺失及日历边界。"""
import hashlib
import json
from pathlib import Path

import pytest

from workbench_analysis.operational_daily_sources_v2 import resolve, dependency_sessions


def _write(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf8')
    return dict(path=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


def _fixture(root, previous='2026-03-03', target='2026-03-04'):
    tdx = root / 'source_tdx'
    gbbq = tdx / 'T0002/hq_cache/gbbq'
    gbbq.parent.mkdir(parents=True)
    gbbq.write_bytes(b'actions')
    oldgb = _write(root, 'prior/actions.json', {})
    core = _write(root, 'prior/core.json', {'value': 12})
    identity = _write(root, 'prior/identity.json', {'rows': []})
    lifecycle = _write(root, 'prior/lifecycle.json', {'trade_date': previous, 'identity': identity})
    member = _write(root, 'prior/member.json', {'memberships': {}, 'sources': []})
    seed = _write(root, 'prior/seed.json', {})
    prior_core = dict(trade_date=previous, core=core, sources={'gbbq': oldgb})
    replay = _write(root, 'prior/replay.json', {'owners': [prior_core]})
    receipt = _write(root, 'prior/receipt.json', {'numeric_core_oracle': replay})
    registry = _write(root, 'prior/registry.json', {})
    evidence = {
        'phase0': _write(root, 'phase.json', {'phase0_status': 'DEGRADED_PASS'}),
        'upgrade_document': _write(root, 'upgrade.json', {}),
        'task_contract': _write(root, 'task.json', {}),
        'runtime_contract': _write(root, 'runtime.json', {'read_only_tdx_roots': [str(tdx)]}),
    }
    _write(root, 'config/operational_daily_source_authority_v2.json',
           dict(contract_id='V4_DAILY_OWNER_SOURCE_CONTEXT_V2', version='2.0.0', **evidence))
    parent = dict(accepted_trade_date=previous, day_receipt=receipt, registry=registry,
                  membership_snapshot=member, owners={previous: dict(core=core, lifecycle=lifecycle, seed=seed)})
    return parent, {'target_session': target}, tdx


@pytest.mark.parametrize('previous,target', [('2026-03-03', '2026-03-04'), ('2027-02-10', '2027-02-11')])
def test_sources_follow_exact_predecessor_and_current_freeze(tmp_path, previous, target):
    parent, freeze, tdx = _fixture(tmp_path, previous, target)
    result = resolve(tmp_path, parent, freeze)
    assert result['oldcore']['trade_date'] == previous
    assert result['tdx_root'] == tdx
    assert result['acquisition']['queries'] == []
    assert result['seed_registry']['owners'][0]['trade_date'] == previous
    # New identities and membership are supplied by this freeze, not the prior day.
    identity = _write(tmp_path, 'new/identity.json', {'rows': [{'security_id': 'SYN-NEW'}]})
    membership = _write(tmp_path, 'new/member.json', {'revision': 'new-member', 'sources': []})
    freeze.update(identity=identity, membership_snapshot=membership)
    changed = resolve(tmp_path, parent, freeze)
    assert changed['identity'] == identity
    assert changed['snapshot']['revision'] == 'new-member'


def test_ambiguous_source_root_and_bad_digest_fail_closed(tmp_path):
    parent, freeze, tdx = _fixture(tmp_path)
    other = tmp_path / 'second_tdx'
    p = other / 'T0002/hq_cache/gbbq'
    p.parent.mkdir(parents=True)
    p.write_bytes(b'other actions')
    runtime = _write(tmp_path, 'runtime.json', {'read_only_tdx_roots': [str(tdx), str(other)]})
    authority = json.loads((tmp_path / 'config/operational_daily_source_authority_v2.json').read_bytes())
    authority['runtime_contract'] = runtime
    _write(tmp_path, 'config/operational_daily_source_authority_v2.json', authority)
    with pytest.raises(ValueError, match='SOURCE_TDX_ROOT_AMBIGUOUS'):
        resolve(tmp_path, parent, freeze)
    freeze['read_only_tdx_root'] = str(other)
    assert resolve(tmp_path, parent, freeze)['tdx_root'] == other
    parent['day_receipt']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='DIGEST_MISMATCH'):
        resolve(tmp_path, parent, freeze)


def test_missing_or_ambiguous_predecessor_never_selects_first(tmp_path):
    parent, freeze, _ = _fixture(tmp_path)
    receipt = json.loads((tmp_path / parent['day_receipt']['path']).read_bytes())
    replay = json.loads((tmp_path / receipt['numeric_core_oracle']['path']).read_bytes())
    replay['owners'] *= 2
    receipt['numeric_core_oracle'] = _write(tmp_path, 'prior/replay.json', replay)
    parent['day_receipt'] = _write(tmp_path, 'prior/receipt.json', receipt)
    with pytest.raises(ValueError, match='SOURCE_PREDECESSOR_CORE_AMBIGUOUS'):
        resolve(tmp_path, parent, freeze)


def test_calendar_boundaries_and_holiday_offsets():
    sessions = ['2026-02-12', '2026-02-13', '2026-02-24', '2026-02-25', '2026-02-26', '2026-02-27']
    assert dependency_sessions(sessions, [sessions[-1]]) == [sessions[i] for i in (0, 1, 2, 4, 5)]
    with pytest.raises(ValueError, match='SOURCE_CALENDAR_WINDOW_MISSING'):
        dependency_sessions(sessions, [sessions[0]])
    with pytest.raises(ValueError, match='SOURCE_CALENDAR_SESSION_MISSING'):
        dependency_sessions(sessions, ['2026-02-23'])


def test_core_cannot_fall_back_to_a_historical_default(tmp_path):
    from workbench_analysis.r43_owner_replay import materialize_core
    with pytest.raises(ValueError,match='SOURCE_CORE_INPUT_CONTEXT_REQUIRED'):
        materialize_core(tmp_path,dates=['2026-03-03'])
    assert list(tmp_path.iterdir())==[]


def test_explicit_historical_manifest_freezes_actions_and_members(tmp_path):
    parent, freeze, tdx = _fixture(tmp_path)
    identity=_write(tmp_path,'frozen/identity.json',{'rows':[]})
    membership=_write(tmp_path,'frozen/member.json',{'revision':'frozen-member','sources':[]})
    actions=_write(tmp_path,'frozen/actions.json',{'revision':'frozen-action'})
    manifest=dict(contract_id='V4_EXPLICIT_HISTORICAL_OWNER_REPLAY_V1',target_session=freeze['target_session'],
        parent_digest=hashlib.sha256(json.dumps(parent,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        acquisition=_write(tmp_path,'frozen/acquisition.json',{'queries':[]}),
        seed_registry=_write(tmp_path,'frozen/seeds.json',{'owners':[]}),
        trace=_write(tmp_path,'frozen/trace.json',{'dates':[]}),identity=identity,membership=membership,gbbq=actions)
    binding=_write(tmp_path,'frozen/manifest.json',manifest)
    result=resolve(tmp_path,parent,freeze,historical_manifest=binding)
    (tdx/'T0002/hq_cache/gbbq').write_bytes(b'new company action')
    replay=resolve(tmp_path,parent,freeze,historical_manifest=binding)
    assert result['gbbq_path']==replay['gbbq_path']==tmp_path/actions['path']
    assert replay['snapshot']['revision']=='frozen-member'
    with pytest.raises(ValueError,match='HISTORICAL_REPLAY_SCOPE_MISMATCH'):
        resolve(tmp_path,parent,dict(freeze,target_session='2026-03-05'),historical_manifest=binding)

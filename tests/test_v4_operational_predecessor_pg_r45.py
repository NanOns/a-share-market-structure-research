import json

import pytest

from workbench_db import v4_operational_predecessor_pg_v1 as predecessor


def test_pg_predecessor_read_uses_bound_owner_reader_without_file_fallback(tmp_path, monkeypatch):
    source = {'path': 'data/v4/predecessors/old.json', 'sha256': 'a' * 64, 'bytes': 12}
    old = {'contract_id': predecessor.OPERATIONAL_CONTRACT, 'dates': ['2026-10-16']}
    candidate = {
        'accepted_trade_date': '2026-10-17',
        'predecessor': source,
        predecessor.KEY: {
            'contract_id': predecessor.CONTRACT,
            'T0': '2026-10-17',
            'source_binding': source,
            'descriptor': {'path': 'locator'},
            'fact_key': predecessor._fact_key('2026-10-17', source),
        },
    }
    calls = []

    def pg_read(root, descriptor, fact_key, day, domain, binding, *, workspace_root=None):
        calls.append((descriptor, fact_key, day, domain, binding, workspace_root))
        return [old]

    monkeypatch.setattr(predecessor, 'read_owner_fact', pg_read)
    monkeypatch.setattr(predecessor, 'checked', lambda *_: pytest.fail('PG path attempted file fallback'))
    assert predecessor.read_predecessor(tmp_path, candidate, workspace_root=tmp_path) == old
    assert calls == [({'path': 'locator'}, candidate[predecessor.KEY]['fact_key'],
                      '2026-10-17', predecessor.DOMAIN, source, tmp_path)]


def test_pg_predecessor_rejects_source_binding_change_before_read(tmp_path, monkeypatch):
    source = {'path': 'old.json', 'sha256': 'a' * 64, 'bytes': 12}
    candidate = {
        'accepted_trade_date': '2026-10-17',
        'predecessor': {'path': 'other.json', 'sha256': 'b' * 64, 'bytes': 12},
        predecessor.KEY: {
            'contract_id': predecessor.CONTRACT,
            'T0': '2026-10-17',
            'source_binding': source,
            'descriptor': {'path': 'locator'},
            'fact_key': predecessor._fact_key('2026-10-17', source),
        },
    }
    monkeypatch.setattr(predecessor, 'read_owner_fact', lambda *a, **k: pytest.fail('unexpected PG read'))
    with pytest.raises(ValueError, match='PREDECESSOR_HEAD_SOURCE_BINDING_MISMATCH'):
        predecessor.read(tmp_path, candidate)


def test_prepare_binds_exact_legacy_head_as_migration_ingress(tmp_path, monkeypatch):
    source_path = tmp_path / 'data' / 'v4' / 'predecessors' / 'old.json'
    source_path.parent.mkdir(parents=True)
    old = {'contract_id': predecessor.OPERATIONAL_CONTRACT, 'dates': ['2026-10-16']}
    raw = json.dumps(old, separators=(',', ':')).encode()
    source_path.write_bytes(raw)
    source = {'path': 'data/v4/predecessors/old.json', 'sha256': predecessor.digest(raw), 'bytes': len(raw)}
    candidate = {'accepted_trade_date': '2026-10-17', 'predecessor': source}
    writes = []

    class Checked:
        def read_bytes(self):
            return raw

    monkeypatch.setattr(predecessor, 'checked', lambda root, binding: Checked())

    def append(root, fact_key, day, domain, binding, rows):
        writes.append((fact_key, day, domain, binding, rows))
        return {'path': 'data/v4/operational_owner_pg_closeout_r1/predecessor_head/key.pg.json'}

    monkeypatch.setattr(predecessor, 'append_owner_fact', append)
    monkeypatch.setattr(predecessor, 'read_owner_fact', lambda *args, **kwargs: [old])
    result = predecessor.prepare(tmp_path, candidate)
    assert result['publication'] is False
    assert candidate[predecessor.KEY]['source_binding'] == source
    assert writes == [(predecessor._fact_key('2026-10-17', source), '2026-10-17',
                       predecessor.DOMAIN, source, [old])]

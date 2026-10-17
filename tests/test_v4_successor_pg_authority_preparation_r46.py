from workbench_db import v4_successor_pg_authority_preparation_v1 as preparation


def test_publisher_completion_prepares_remaining_head_facts(tmp_path, monkeypatch):
    from workbench_db import (
        v4_operational_predecessor_pg_v1 as predecessor,
        v4_operational_registry_pg_v1 as registry,
        v4_operational_daily_evidence_pg_v1 as evidence,
        v4_operational_period_artifact_pg_v1 as period_artifact,
    )

    candidate = {'accepted_trade_date': '2026-10-17'}
    calls = []

    def prep(name, key):
        def run(root, value):
            calls.append(name)
            value[key] = {'contract_id': name, 'T0': value['accepted_trade_date']}
            return {'publication': False, 'kind': name}
        return run

    monkeypatch.setattr(predecessor, 'prepare', prep('predecessor', predecessor.KEY))
    monkeypatch.setattr(registry, 'prepare', prep('registry', registry.KEY))
    monkeypatch.setattr(evidence, 'prepare', prep('daily_evidence', evidence.KEY))
    monkeypatch.setattr(period_artifact, 'prepare', prep('period_artifacts', period_artifact.KEY))
    receipt = preparation.prepare_remaining(tmp_path, candidate)
    assert calls == ['predecessor', 'registry', 'daily_evidence', 'period_artifacts']
    assert receipt['T0'] == '2026-10-17' and receipt['publication'] is False
    assert all(key in candidate for key in (predecessor.KEY, registry.KEY, evidence.KEY, period_artifact.KEY))

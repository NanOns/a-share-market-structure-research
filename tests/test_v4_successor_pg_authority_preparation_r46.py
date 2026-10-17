from workbench_db import v4_successor_pg_authority_preparation_v1 as preparation


def test_publisher_completion_prepares_remaining_head_facts(tmp_path, monkeypatch):
    from workbench_analysis.r43_owner_replay import ref
    from workbench_db import (
        v4_operational_predecessor_pg_v1 as predecessor,
        v4_operational_registry_pg_v1 as registry,
        v4_operational_daily_evidence_pg_v1 as evidence,
        v4_operational_period_artifact_pg_v1 as period_artifact,
    )
    from workbench_service import native_product_catalog_v3 as product

    candidate = {'accepted_trade_date': '2026-10-17', 'published_sessions': ['2026-10-17']}
    local_catalog = tmp_path / 'product-catalog.json'
    local_catalog.write_text('{"dates":{}}', encoding='utf-8')
    candidate[product.KEY] = ref(tmp_path, local_catalog)
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
    def prepare_product(root, value, authority):
        calls.append('product_catalog')
        value[product.PG_KEY] = {'contract_id': product.PG_CONTRACT}
        return {'publication': False}
    monkeypatch.setattr(product, 'prepare_pg', prepare_product)
    monkeypatch.setattr(product, 'load', lambda root, value: {'dates': {'2026-10-17': {}}})
    receipt = preparation.prepare_remaining(tmp_path, candidate)
    assert calls == ['predecessor', 'registry', 'daily_evidence', 'period_artifacts', 'product_catalog']
    assert receipt['T0'] == '2026-10-17' and receipt['publication'] is False
    assert all(key in candidate for key in (predecessor.KEY, registry.KEY, evidence.KEY,
        period_artifact.KEY, product.PG_KEY))

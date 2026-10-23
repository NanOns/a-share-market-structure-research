import json

import pytest

from workbench_analysis.operational_product_pack_v3 import index_benchmark_contract, previous_date_bindings


def _candidate(tmp_path):
    predecessor_path = tmp_path / 'predecessor.json'
    predecessor_path.write_text('{}', encoding='utf-8')
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/core_product_read_authority_r1.json').write_text(
        json.dumps({'contract_id': 'CORE_PRODUCT_READ_AUTHORITY_R1'}), encoding='utf-8'
    )
    return {
        'predecessor': {'path': 'predecessor.json', 'bytes': predecessor_path.stat().st_size,
                        'sha256': __import__('hashlib').sha256(predecessor_path.read_bytes()).hexdigest()},
        'published_sessions': ['2026-10-08', '2026-10-09', '2026-10-12'],
    }


def test_legacy_product_bootstrap_requires_exact_dated_corrections_and_predecessors(tmp_path):
    candidate = _candidate(tmp_path)
    with pytest.raises(ValueError, match='INITIAL_HISTORICAL_EXACT_CORRECTION_ADMISSION_REQUIRED'):
        previous_date_bindings(tmp_path, candidate, {}, previous_dates={'2026-10-08': {}, '2026-10-09': {}})

    corrections = {'2026-10-08': {'T0': '2026-10-08'}, '2026-10-09': {'T0': '2026-10-09'}}
    previous = {'2026-10-08': {'path': 'older/2026-10-08/MANIFEST.json'},
                '2026-10-09': {'path': 'older/2026-10-09/MANIFEST.json'}}
    assert previous_date_bindings(tmp_path, candidate, {}, historical_indices=corrections,
                                  previous_dates=previous) == previous


def test_legacy_product_bootstrap_rejects_incomplete_date_denominators(tmp_path):
    candidate = _candidate(tmp_path)
    corrections = {'2026-10-08': {'T0': '2026-10-08'}}
    previous = {'2026-10-08': {'path': 'older/2026-10-08/MANIFEST.json'},
                '2026-10-09': {'path': 'older/2026-10-09/MANIFEST.json'}}
    with pytest.raises(ValueError, match='ALL_HISTORICAL_CORRECTION_INDICES_REQUIRED'):
        previous_date_bindings(tmp_path, candidate, {}, historical_indices=corrections,
                               previous_dates=previous)


def test_legacy_product_bootstrap_rejects_unversioned_dated_catalog(tmp_path):
    candidate = _candidate(tmp_path)
    (tmp_path / 'config/core_product_read_authority_r1.json').write_text(
        json.dumps({'contract_id': 'OTHER'}), encoding='utf-8'
    )
    with pytest.raises(ValueError, match='LEGACY_DATED_PRODUCT_CATALOG_REQUIRED'):
        previous_date_bindings(tmp_path, candidate, {}, historical_indices={'2026-10-08': {}},
                               previous_dates={'2026-10-08': {}, '2026-10-09': {}})


def test_market_index_symbols_are_read_from_versioned_benchmark_contract(tmp_path):
    from pathlib import Path
    config=tmp_path/'config';config.mkdir()
    source=Path(__file__).resolve().parents[2]/'config'
    for name in ('core_product_index_benchmark_v1.json','v4_market_reference_instruments_v1_1.json'):
        (config/name).write_bytes((source/name).read_bytes())
    value,binding=index_benchmark_contract(tmp_path)
    assert value['benchmarks'][0]['instrument_type']=='MARKET_INDEX'
    assert binding['path']=='config/core_product_index_benchmark_v1.json'
    assert len(binding['sha256'])==64


def test_market_index_contract_rejects_stock_selection_or_duplicate_entries(tmp_path):
    test_market_index_symbols_are_read_from_versioned_benchmark_contract(tmp_path)
    config=tmp_path/'config'
    path=config/'core_product_index_benchmark_v1.json'
    value=json.loads(path.read_bytes())
    value['benchmarks'].append(dict(value['benchmarks'][0]))
    path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(ValueError,match='INDEX_BENCHMARK_CONTRACT_INVALID'):
        index_benchmark_contract(tmp_path)

"""R9 指数：类别、来源包、逐序列摘要与交易日必须一致。"""
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile

import pytest

from workbench_analysis.operational_product_pack_v3 import index_series, index_benchmark_contract


def _series():
    benchmark = dict(symbol='sh000001', display_name='上证指数')
    blob = struct.pack('<IIIIIfII', 20260303, 100, 120, 90, 110, 1000.0, 100, 0)
    member = 'sh/lday/sh000001.day'
    source = dict(symbol='sh000001', instrument_type='MARKET_INDEX', role='MARKET_BENCHMARK',
                  source_kind='TDX_INDEX_DAY', price_basis='RAW_INDEX_POINTS', trade_date='2026-03-03',
                  member=member, sha256=hashlib.sha256(blob).hexdigest())
    catalog = dict(contract_id='V4_TDX_INDEX_SOURCE_CATALOG_V1', version='1.0.0',
                   package_sha256='a'*64, instruments=[source])
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr(member, blob)
    return benchmark, catalog, output


def test_typed_index_points_have_exact_source_and_date():
    benchmark, catalog, output = _series()
    with zipfile.ZipFile(output) as z:
        row = index_series(z, benchmark, '2026-03-03', catalog, 'a'*64)
    assert row['instrument_type'] == 'MARKET_INDEX'
    assert row['bars'][-1]['close'] == 1.1
    assert row['source_sha256'] == catalog['instruments'][0]['sha256']


@pytest.mark.parametrize('field,value', [
    ('instrument_type','STOCK'), ('source_kind','TDX_STOCK_DAY'), ('role','STOCK_SELECTION'),
    ('price_basis','RAW_STOCK_PRICE'), ('trade_date','2026-03-02'), ('sha256','b'*64),
])
def test_same_filename_does_not_authorize_untyped_or_changed_stock_data(field, value):
    benchmark, catalog, output = _series()
    catalog['instruments'][0][field] = value
    with zipfile.ZipFile(output) as z, pytest.raises(ValueError, match='INDEX_SOURCE_'):
        index_series(z, benchmark, '2026-03-03', catalog, 'a'*64)


@pytest.mark.parametrize('change', ['missing','duplicate','package'])
def test_catalog_missing_duplicate_and_other_package_are_rejected(change):
    benchmark, catalog, output = _series()
    if change == 'missing': catalog['instruments'] = []
    if change == 'duplicate': catalog['instruments'] *= 2
    if change == 'package': catalog['package_sha256'] = 'b'*64
    with zipfile.ZipFile(output) as z, pytest.raises(ValueError, match='INDEX_SOURCE_'):
        index_series(z, benchmark, '2026-03-03', catalog, 'a'*64)


def test_unknown_stock_shape_and_catalog_digest_cannot_be_used(tmp_path):
    config = tmp_path/'config'
    config.mkdir()
    source = Path(__file__).resolve().parents[2]/'config'
    for name in ('core_product_index_benchmark_v1.json','v4_market_reference_instruments_v1_1.json'):
        (config/name).write_bytes((source/name).read_bytes())
    path=config/'core_product_index_benchmark_v1.json'
    contract=json.loads(path.read_bytes())
    contract['benchmarks'][0]['symbol']='bj123456'
    path.write_text(json.dumps(contract),encoding='utf8')
    with pytest.raises(ValueError,match='INDEX_BENCHMARK_TYPE_OR_SOURCE_INVALID'):
        index_benchmark_contract(tmp_path)
    contract['reference_instruments']['sha256']='0'*64
    path.write_text(json.dumps(contract),encoding='utf8')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):
        index_benchmark_contract(tmp_path)


def test_source_catalog_cannot_borrow_new_benchmark_contract_digest():
    from workbench_analysis.operational_product_pack_v3 import validate_index_catalog_contract
    benchmark={'path':'benchmark.json','sha256':'a'*64}
    reference={'path':'reference.json','sha256':'b'*64}
    catalog={'benchmark_contract':benchmark,'reference_instruments':reference}
    validate_index_catalog_contract(catalog,benchmark,reference)
    with pytest.raises(ValueError,match='INDEX_SOURCE_CONTRACT_REVISION_MISMATCH'):
        validate_index_catalog_contract(catalog,dict(benchmark,sha256='c'*64),reference)

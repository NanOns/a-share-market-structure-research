import hashlib
import json
import pytest
from workbench_service.core_product_bff_r1 import dated_product_manifest


def bind(root, name, value):
    raw=json.dumps(value).encode();path=root/name;path.write_bytes(raw)
    return dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def test_exact_date_catalog_and_r1_compatibility(tmp_path):
    one=bind(tmp_path,'one.json',dict(T0='2026-10-08'))
    two=bind(tmp_path,'two.json',dict(T0='2026-10-09'))
    authority=dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R2',dates={'2026-10-08':one,'2026-10-09':two})
    assert dated_product_manifest(tmp_path,authority,'2026-10-08')['T0']=='2026-10-08'
    assert dated_product_manifest(tmp_path,authority,'2026-10-09')['T0']=='2026-10-09'
    assert dated_product_manifest(tmp_path,authority,'2026-10-12') is None
    legacy=dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R1',manifest=two)
    assert dated_product_manifest(tmp_path,legacy,'2026-10-09')['T0']=='2026-10-09'
    assert dated_product_manifest(tmp_path,legacy,'2026-10-08') is None


def test_date_catalog_never_substitutes_another_date(tmp_path):
    binding=bind(tmp_path,'wrong.json',dict(T0='2026-10-09'))
    with pytest.raises(ValueError,match='DATE_MISMATCH'):
        dated_product_manifest(tmp_path,dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R2',dates={'2026-10-08':binding}),'2026-10-08')


def test_manifest_tamper_fails_hash_verification(tmp_path):
    binding=bind(tmp_path,'one.json',dict(T0='2026-10-08'))
    (tmp_path/'one.json').write_text('{}')
    with pytest.raises(ValueError):
        dated_product_manifest(tmp_path,dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R2',dates={'2026-10-08':binding}),'2026-10-08')

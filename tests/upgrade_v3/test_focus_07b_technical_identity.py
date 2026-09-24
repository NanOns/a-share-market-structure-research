from datetime import date

import pytest

from src.focus_tracker.technical_identity import canonical_technical_identity
from workbench_analysis.technical import TECHNICAL_RESULT_COLUMNS


def row(*, quality_codes, basis_json):
    result = {column: None for column in TECHNICAL_RESULT_COLUMNS}
    result.update(security_id="SH.600000", trade_date=date(2026, 9, 23),
                  contract_id="TECHNICAL_HISTORY_V2_1_PREVIEW",
                  price_basis="TDX_NATIVE_QFQ", adj_close=10.0,
                  quality_codes=quality_codes, basis_json=basis_json)
    return result


def test_json_text_and_decoded_json_have_same_canonical_identity():
    text = row(quality_codes='["A", "B"]', basis_json='{"z":1,"a":{"b":2}}')
    decoded = row(quality_codes=["A", "B"], basis_json={"a": {"b": 2}, "z": 1})
    assert canonical_technical_identity([text]) == canonical_technical_identity([decoded])


def test_canonical_identity_rejects_semantic_change_and_invalid_json():
    baseline = row(quality_codes=[], basis_json={"basis": "original"})
    changed = row(quality_codes=[], basis_json={"basis": "changed"})
    assert canonical_technical_identity([baseline])[0] != canonical_technical_identity([changed])[0]
    with pytest.raises(ValueError):
        canonical_technical_identity([row(quality_codes="not-json", basis_json={})])

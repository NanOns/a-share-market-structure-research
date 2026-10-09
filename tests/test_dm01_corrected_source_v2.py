import pytest
from workbench_analysis.dm01_corrected_source_capture_v2 import normalize_factor_schema, dated_daily_metadata


def test_native_factor_alias_preserves_values_and_original():
    native=[dict(code='sh.600000',adjustFacto='11.051912')]
    result=normalize_factor_schema(native)
    assert result==[dict(code='sh.600000',adjustFactor='11.051912')]
    assert 'adjustFacto' in native[0]


def test_alias_conflict_fails_closed():
    with pytest.raises(ValueError,match='FACTOR_ALIAS_CONFLICT'):
        normalize_factor_schema([dict(adjustFactor='1',adjustFacto='2')])


def test_actual_row_dates_prove_missing_sdk_date_only():
    assert dated_daily_metadata([dict(date='2026-10-08')],{'provider_date':None},'2026-10-08')['provider_date']=='2026-10-08'
    with pytest.raises(ValueError,match='DATE_MISMATCH'):
        dated_daily_metadata([dict(date='2026-09-30')],{},'2026-10-08')

"""Independent original pandas predicate and versioned adapter comparisons."""
import ast
import re
from pathlib import Path
import pandas as pd
import pytest
from sector.legacy_valid_member_a05_v1 import exact_value
from sector.valid_member_qualification_v3 import compare
from sector.phase2 import prepare, validity

DAY = '2026-10-09'
CASES = [
    ('SH.688349', 'BAR', 'ACTUAL_TRADED', True, True),
    ('SZ.001235', 'SUSPENDED', 'SUSPENDED', True, True),
    ('BJ.920229', 'NOT_LISTED_YET', 'NOT_LISTED_YET', True, False),
    ('SH.600000', 'DELISTED_OR_INACTIVE', 'DELISTED_OR_INACTIVE', False, False),
    ('SH.600001', 'FILE_MISSING', 'ACTUAL_TRADED', False, True),
    ('SH.600002', None, 'ACTUAL_TRADED', False, True),
    ('SH.600003', 'RENAMED', 'ACTUAL_TRADED', True, True),
    ('SH.600004', 'BOUNDARY_UNKNOWN', 'BOUNDARY_UNKNOWN', True, None),
    ('688349', 'BAR', 'ACTUAL_TRADED', False, False),
    ('SH.68834', 'BAR', 'ACTUAL_TRADED', False, False),
    (r'SH\\688349', 'BAR', 'ACTUAL_TRADED', False, False),
]


def patterns(path):
    tree = ast.parse(Path(path).read_bytes())
    return [n.args[0].value for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == 'fullmatch' and n.args and isinstance(n.args[0], ast.Constant)]


@pytest.mark.parametrize('key,missing,status,expected,mapped', CASES)
def test_original_python_pandas_and_v3_pair(key, missing, status, expected, mapped):
    factors = pd.DataFrame([dict(security_id=key, MA20=1., MA60=1., AMOUNT_MA5=1., AMOUNT_MA20=1.)])
    latest = pd.DataFrame([dict(security_id=key, missing_state=missing, aligned_close=1.)])
    assert bool(prepare(factors, latest).valid_member.iloc[0]) == expected
    assert exact_value(key, missing) == expected
    result = compare(dict(source_security_key=key, missing_state=missing, status=status, trade_date=DAY),
        trade_date=DAY, normal_universe=True)
    assert result['original_A05_expected'] == expected and result['V2_actual'] == mapped
    assert result['comparison'] == ('UNKNOWN' if mapped is None else 'PASS' if mapped == expected else 'DIFFERENCE')


@pytest.mark.parametrize('key', ['SH.688349', 'SZ.001235', 'BJ.920229'])
def test_four_current_source_patterns_match(key):
    root = Path(__file__).resolve().parents[1]
    for path in ('phase2.py', 'legacy_valid_member_a05_v1.py', 'operational_candidate_v1.py', 'operational_candidate_v2.py'):
        assert all(re.fullmatch(p, key) for p in patterns(root/'src/sector'/path))


@pytest.mark.parametrize('missing_field', ['missing_state', 'source_security_key'])
def test_absent_evidence_is_unknown(missing_field):
    row = dict(source_security_key='SH.688349', missing_state='BAR', status='ACTUAL_TRADED', trade_date=DAY)
    del row[missing_field]
    result = compare(row, trade_date=DAY)
    assert result['value'] is None and result['comparison'] == 'UNKNOWN'
    assert result['market_denominator'] is None


def test_market_scope_sector_scope_and_date_are_separate():
    row = dict(source_security_key='SH.688349', missing_state='BAR', status='ACTUAL_TRADED', trade_date=DAY)
    result = compare(row, trade_date=DAY, normal_universe=False)
    assert result['value'] is True and result['market_denominator'] is False
    assert validity(8, 5, 'THEME')[0] is False
    assert validity(8, 6, 'THEME')[0] is True
    assert validity(8, 8, 'EXCLUDE_FROM_THEME_RANK')[0] is False
    with pytest.raises(ValueError, match='DATED_VALIDITY_SCOPE_REQUIRED'):
        compare(row, trade_date='2026-10-12')

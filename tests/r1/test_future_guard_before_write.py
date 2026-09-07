import hashlib
import inspect

import pandas as pd
import pytest

import phase1_runner


def test_future_guard_blocks_before_any_staged_canonical_write(tmp_path):
    normalized=tmp_path/'adjusted.parquet';factors=tmp_path/'factors.parquet'
    pd.DataFrame({'date':[20260903,20260904],'value':[1,2]}).to_parquet(normalized)
    pd.DataFrame({'date':[20260903],'value':[1]}).to_parquet(factors)
    before={path:hashlib.sha256(path.read_bytes()).hexdigest() for path in (normalized,factors)}
    with pytest.raises(ValueError,match='FUTURE_SNAPSHOT'):
        phase1_runner.validate_canonical_dates_before_write(normalized,factors,20260903)
    assert before=={path:hashlib.sha256(path.read_bytes()).hexdigest() for path in (normalized,factors)}
    assert not list(tmp_path.glob('*.tmp'))


def test_guard_call_precedes_staged_path_creation():
    source=inspect.getsource(phase1_runner.run)
    assert source.index('validate_canonical_dates_before_write')<source.index("staged=normalized.with_name")

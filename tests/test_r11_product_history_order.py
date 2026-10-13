import gzip
import hashlib
import json

import pytest

from workbench_analysis.operational_product_pack_v3 import canonical_history_rows
from workbench_db.v4_forward_pg_r1 import canonical


def write(path, rows):
    with gzip.open(path, 'wt', encoding='utf8') as stream:
        for row in rows:
            stream.write(json.dumps(row) + '\n')


def test_appended_new_security_keeps_values_and_canonical_digest(tmp_path):
    rows = [dict(security_id=sid, bars=[dict(trade_date='2026-10-13',
        raw_ohlc=[1, 3, 1, 2], qfq_ohlc=[2, 6, 2, 4], amount=20, volume=10)])
        for sid in ('Z', 'A')]
    path = tmp_path / 'history.gz'
    write(path, rows)
    digest = hashlib.sha256()
    assert list(canonical_history_rows(path, digest)) == rows[::-1]
    assert digest.hexdigest() == hashlib.sha256(
        b''.join(canonical(row) + b'\n' for row in rows[::-1])).hexdigest()


def test_duplicate_security_fails_closed(tmp_path):
    path = tmp_path / 'history.gz'
    write(path, [dict(security_id='A', bars=[])] * 2)
    with pytest.raises(ValueError, match='PRODUCT_HISTORY_DUPLICATE_SECURITY'):
        list(canonical_history_rows(path, hashlib.sha256()))

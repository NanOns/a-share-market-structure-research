from pathlib import Path

import pytest

from workbench_db.v4_job_migration_r1 import _require_fixed_receipts


class _Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _Pg:
    def __init__(self, relation, guard_count):
        self.relation = relation
        self.guard_count = guard_count
        self.calls = 0

    def execute(self, query, params=()):
        self.calls += 1
        return _Result((self.relation,) if self.calls == 1 else (self.guard_count,))


def test_fixed_job_migration_receipts_require_relation_and_guard():
    _require_fixed_receipts(_Pg('v4.jobs_frozen_oracle_migration_receipts_r1', 1))
    with pytest.raises(ValueError, match='NOT_MIGRATED'):
        _require_fixed_receipts(_Pg(None, 0))


def test_job_oracle_importer_has_no_runtime_persistent_ddl():
    source = Path(__file__).resolve().parents[1] / 'src/workbench_db/v4_job_migration_r1.py'
    text = source.read_text(encoding='utf-8')
    assert 'CREATE TABLE' not in text
    assert 'v4.jobs_frozen_oracle_migration_receipts_r1' in text

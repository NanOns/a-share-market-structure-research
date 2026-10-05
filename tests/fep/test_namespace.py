import json
import re
from .conftest import ROOT


def test_explicit_fep_only_namespace_contract():
    contract=json.loads((ROOT/'config/fep_namespace_contract_v1.json').read_bytes())
    source=ROOT/'src/workbench_db/migrations/v4_postgres/028_fep_schema_v1.sql'
    declared=set(re.findall(r'CREATE TABLE (fep\.\w+)',source.read_text(encoding='utf8')))
    rows=contract['tables']
    assert len(declared)==33 and declared=={r['table'] for r in rows}
    assert all(r['production_write_target'] is None and r['scope']=='FEP_ONLY' for r in rows)
    assert contract['new_regression_failure']=='tests.test_v4_18_migration_contract::test_all_declared_tables_have_explicit_namespace_rules'

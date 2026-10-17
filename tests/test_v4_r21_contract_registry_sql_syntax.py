from pathlib import Path

from pglast import parse_sql

ROOT = Path(__file__).resolve().parents[1]


def test_contract_registry_sql_drafts_parse_as_postgresql():
    drafts = {
        'forward': ROOT / 'docs/upgrade/R21R3_V4_CONTRACT_REGISTRY_MIGRATION_DRAFT_20261017.sql',
        'rollback': ROOT / 'docs/upgrade/R21R4_V4_CONTRACT_REGISTRY_ROLLBACK_DRAFT_20261017.sql',
        'readonly_preflight': ROOT / 'docs/upgrade/R21R4_V4_CONTRACT_REGISTRY_PREFLIGHT_READONLY_20261017.sql',
    }
    statements = {name: parse_sql(path.read_text(encoding='utf-8')) for name, path in drafts.items()}
    assert len(statements['forward']) == 16
    assert len(statements['rollback']) == 19
    assert len(statements['readonly_preflight']) == 7

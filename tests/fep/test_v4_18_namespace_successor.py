"""Active post-FEP inventory; immutable pre-FEP test is retained separately."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def test_all_current_sql_declarations_are_explicit_successor_inventory():
    c=json.loads((ROOT/'config/v4_18_migration_replay_contract_v1_1.json').read_bytes())
    ref=c['supersedes'];raw=(ROOT/ref['path']).read_bytes()
    assert c['contract_id']=='V4_18_MIGRATION_REPLAY_CONTRACT_V1_1'
    assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
    assert raw==subprocess.check_output(['git','show','e4ea913:'+ref['path']],cwd=ROOT)
    original=json.loads(raw)
    assert c['permissions']==original['permissions']
    assert c['namespace_matrix'][:len(original['namespace_matrix'])]==original['namespace_matrix']
    paths=list((ROOT/'src/workbench_db').rglob('*.sql'))+[ROOT/'migrations/v4_16_r24_real_shadow_v1.sql']
    actual={(p.relative_to(ROOT).as_posix(),name) for p in paths for name in
            re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)',p.read_text(encoding='utf8'),re.I)}
    registered={(r['declaration'],r['state_or_table']) for r in c['namespace_matrix']
                if r['declaration']!='DESIGN_ONLY_NOT_CREATED'}
    assert actual==registered
    fep=[r for r in c['namespace_matrix'] if r['state_or_table'].startswith('fep.')]
    assert len(fep)==33
    assert all(r['read_source']=='FEP_E1_ENGINEERING' and r['disposition']=='REFERENCE'
               and r['write_target'] is None and not r['production_cutover']
               and r['migration_replay_pass']=='NOT_GRANTED' for r in fep)
    assert c['permissions']['migration_replay_pass']=='NOT_GRANTED'
    assert not any(c['permissions'][k] for k in ('migration_execution','production_writer','production_focus_cutover'))
    assert c['permissions']['v4_18_accepted_head'] is None
    assert not (ROOT/'data/v4/V4_18_ACCEPTED_HEAD.json').exists()


def test_protected_v1_test_is_exact_historical_blob():
    raw=(ROOT/'tests/test_v4_18_migration_contract.py').read_bytes()
    assert raw==subprocess.check_output(['git','cat-file','blob','26369110c8ea35b9c1d216df17d11f981047fcef'],cwd=ROOT)

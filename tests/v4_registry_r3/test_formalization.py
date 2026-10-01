import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf8'))

def exact(binding):
    assert hashlib.sha256((ROOT / binding['path']).read_bytes()).hexdigest() == binding['sha256']

def test_external_dispositions_and_protected_bytes():
    r = read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3.json')
    exact(r['external_authority']['document'])
    assert r['external_authority']['audited_head'] == '1655f84d1a47faca43c281d66e7704f2fa56b1b8'
    entries = {e['work_package']: e for e in r['entries']}
    for wp in ['WP-A08-V4-09-N01', 'WP-A09-V4-09-N02', 'WP-A11-V4-01-IDENTITY-AUTHORITY']:
        assert entries[wp]['status'] == 'ACCEPTED'
        t = entries[wp]['transition']
        assert t['previous_status'] == 'OPEN' and t['new_status'] == 'ACCEPTED'
        for b in t['evidence_bindings']:
            exact(b)
    expected = {'WP-A10-SOURCE-AUTHORITY-GOVERNANCE': 'BLOCKED_R2_OWNER_ACCEPTANCE_GATE',
        'WP-A12-V4-02-STATUS-ST-AUTHORITY': 'BLOCKED_R2_REAL_DATED_OWNER_SEMANTICS',
        'WP-A01-DM01': 'PARTIAL_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED'}
    for wp, status in expected.items():
        assert entries[wp]['status'] == 'OPEN' and entries[wp]['implementation_status'] == status
        assert entries[wp]['external_acceptance'] == 'BLOCKED'
    assert entries['WP-A01-DM01']['depends_on'] == ['A10-R2_EXTERNAL_ACCEPTANCE', 'A12-R2_EXTERNAL_ACCEPTANCE']
    assert not r['accepted_source_authority_owners'] and not any(r['permissions'].values())
    for b in read('reports/audits/R3_STAGE_ENTRY_R1.json')['protected_bindings']:
        if 'git_sha256' in b:
            import subprocess
            baseline = subprocess.check_output(['git', 'show', b['git_baseline_commit'] + ':' + b['path']], cwd=ROOT)
            current = (ROOT / b['path']).read_bytes()
            assert hashlib.sha256(baseline).hexdigest() == b['git_sha256']
            assert current.replace(b'\r\n', b'\n') == baseline.replace(b'\r\n', b'\n')
            assert hashlib.sha256(current).hexdigest() in (b['sha256'], b['git_sha256'])
        else:
            exact(b)

def test_accepted_sidecar_scopes_and_identity_equivalence():
    n1 = read('reports/audits/V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json')
    assert n1['historical_validation_scope'] == 'ACCEPTED_PUBLICATION_HISTORY_ONLY'
    assert n1['current_runtime_accepted'] is False
    exact(n1['accepted_artifact']); exact(n1['historical_implementation'])
    n2 = read('reports/audits/V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1.json')
    assert n2['acceptance_scope'] == 'ACCEPTED_FUTURE_SCHEMA_HARDENING'
    assert n2['production_database_deployed'] is False
    assert all(n2['legacy_exact_readback_and_rollback'].values())
    exact(n2['migration']); exact(n2['rollback'])
    a = read('config/V4_01_HISTORICAL_IDENTITY_AUTHORITY_AMENDMENT_R1.json')
    assert a['external_acceptance'] == 'PASS_RESULT_C_WITH_CAPABILITY_DOWNGRADE'
    assert a['business_identity_bytes_unchanged'] and a['security_id_unchanged']
    assert a['go_forward_official_identity_authority_unchanged']
    assert not a['AS_RECORDED'] and not a['local_tdx_legal_lifecycle_authority']
    assert not a['downstream_business_rebuild_required']
    assert a['capability_limitations'] == ['HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED']
    exact(a['identity_equivalence'])
    d = read(a['identity_equivalence']['path'])
    assert d['canonical_candidate_sha256'] == d['canonical_old_sha256']
    assert d['identity_rows_changed'] == d['security_ids_renumbered'] == 0

def test_accepted_historical_prewatch_replay_is_exact():
    from src.v4.stock_prewatch import load_accepted, build, immutable_gzip_bytes, digest
    c, cores, factors, seeds, package = load_accepted(ROOT)
    records = build(cores, factors, seeds, c, package)
    artifact = read('reports/audits/V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json')['accepted_artifact']
    assert len(records) == 5222
    assert immutable_gzip_bytes(records) == (ROOT / artifact['path']).read_bytes()
    assert digest(records) == artifact['logical_digest']

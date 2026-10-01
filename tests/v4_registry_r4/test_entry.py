import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))

def test_r4_exact_dispositions_and_empty_owners():
    r=read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R4.json')
    entries={e['work_package']:e for e in r['entries']}
    a=entries['WP-A10-SOURCE-AUTHORITY-GOVERNANCE']
    assert a['status']=='ACCEPTED_INFRASTRUCTURE_SCOPE' and a['external_acceptance']=='PASS_INFRASTRUCTURE_SCOPE'
    assert a['formal_consumer_authorization'] is False and a['acceptance_scope']=='INFRASTRUCTURE_ONLY'
    a12=entries['WP-A12-V4-02-STATUS-ST-AUTHORITY']
    assert a12['status']=='OPEN' and a12['implementation_status']=='A12_R2_IMPLEMENTATION_ENTRY_AUTHORIZED'
    assert a12['external_acceptance']=='BLOCKED' and a12['formal_consumer_authorization'] is False
    dm=entries['WP-A01-DM01']
    assert dm['implementation_status']=='PARTIAL_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED'
    assert dm['depends_on']==['A12-R2_EXTERNAL_ACCEPTANCE','A12_ACCEPTED_OWNER_REGISTRATION']
    for wp in ['WP-A08-V4-09-N01','WP-A09-V4-09-N02','WP-A11-V4-01-IDENTITY-AUTHORITY']:assert entries[wp]['status']=='ACCEPTED'
    assert read('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json')['owners']==[]
    assert not r['global_mandatory_adoption_authorized'] and not any(r['permissions'].values())

def test_independent_acceptance_exact_evidence():
    for path in ['reports/audits/SOURCE_AUTHORITY_REGISTRY_R3_EXTERNAL_CONFIRMATION_R1.json',
                 'reports/audits/A10_R2_EXTERNAL_ACCEPTANCE_RECORD_R1.json']:
        record=read(path)
        assert record['external_authority']['audited_head']=='699d3503d2d8ddbd37997441eec59308aec1990f'
        for b in [record['external_authority']['document'],*record['evidence_bindings']]:
            assert hashlib.sha256((ROOT/b['path']).read_bytes()).hexdigest()==b['sha256']
    for b in read('reports/audits/R4_STAGE_ENTRY_R1.json')['protected_bindings']:
        assert hashlib.sha256((ROOT/b['path']).read_bytes()).hexdigest() in (b['sha256'],b.get('git_sha256'))

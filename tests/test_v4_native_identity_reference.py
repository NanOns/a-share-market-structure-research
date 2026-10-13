"""New identity extension control; existing membership PASS checks retained."""
from workbench_db.v4_membership_reference_pg_v1 import prepare,prepare_identity,read_identity,KEY
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref

def test_identity_extension_preserves_member_fact_and_uses_native_reader(tmp_path,monkeypatch):
    members=tmp_path/'members.json';atomic_json(tmp_path,members,dict(rows=[dict(sector_id='S',security_id='FIXTURE')]))
    identities=tmp_path/'identity.json';atomic_json(tmp_path,identities,dict(rows=[dict(security_id='FIXTURE',source_security_key='FIXTURE.CURRENT')]))
    snapshot=tmp_path/'snapshot.json';atomic_json(tmp_path,snapshot,dict(memberships=ref(tmp_path,members),identity_source=ref(tmp_path,identities)))
    candidate=dict(accepted_trade_date='2026-10-12',membership_snapshot=ref(tmp_path,snapshot));prepare(tmp_path,candidate)
    import json
    previous=json.loads((tmp_path/candidate[KEY]['path']).read_bytes());receipt=prepare_identity(tmp_path,candidate)
    current=json.loads((tmp_path/candidate[KEY]['path']).read_bytes())
    assert current['descriptor']==previous['descriptor'] and current['fact_token']==previous['fact_token']
    from workbench_analysis import r43_operational_publication
    def forbidden(*args):raise AssertionError('ARCHIVE_IDENTITY_READ')
    monkeypatch.setattr(r43_operational_publication,'rows',forbidden)
    assert read_identity(tmp_path,candidate)==[dict(security_id='FIXTURE',source_security_key='FIXTURE.CURRENT')]
    assert receipt['membership_fact_recomputed'] is False

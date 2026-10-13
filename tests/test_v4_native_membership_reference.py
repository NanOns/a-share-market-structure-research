"""New business-reference PG controls, no prior fixture suite rerun."""
import json
import pytest
from workbench_db.v4_membership_reference_pg_v1 import KEY,prepare,read
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref

def candidate(root):
    source=root/'members.json';atomic_json(root,source,dict(rows=[dict(sector_id='SECTOR',security_id='FIXTURE')]))
    snapshot=root/'snapshot.json';atomic_json(root,snapshot,dict(memberships=ref(root,source)))
    return dict(accepted_trade_date='2026-10-12',membership_snapshot=ref(root,snapshot))

def test_membership_consumer_reads_pg_when_archive_row_loader_is_forbidden(tmp_path,monkeypatch):
    data=candidate(tmp_path);receipt=prepare(tmp_path,data)
    from workbench_analysis import r43_operational_publication
    def forbidden(*args):raise AssertionError('BUSINESS_ARCHIVE_READ')
    monkeypatch.setattr(r43_operational_publication,'rows',forbidden)
    assert read(tmp_path,data)==[dict(sector_id='SECTOR',security_id='FIXTURE')]
    assert receipt['rows']==1

def test_membership_wrong_actual_pg_fact_token_never_falls_back_to_relation_json(tmp_path):
    data=candidate(tmp_path);prepare(tmp_path,data)
    authority=json.loads((tmp_path/data[KEY]['path']).read_bytes());authority['fact_token']='a'*64
    other=tmp_path/'other-authority.json';atomic_json(tmp_path,other,authority);data[KEY]=ref(tmp_path,other)
    with pytest.raises(ValueError,match='PG_OPERATIONAL_OWNER_CONTEXT_MISMATCH'):read(tmp_path,data)

def test_missing_membership_authority_fails_closed(tmp_path):
    with pytest.raises(ValueError,match='REFERENCE_REQUIRED_NO_FALLBACK'):read(tmp_path,candidate(tmp_path))

"""New business-reference PG controls, no prior fixture suite rerun."""
import pytest
from workbench_db.v4_membership_reference_pg_v1 import KEY,prepare,read,context_metadata
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

def test_membership_wrong_pg_authority_key_never_falls_back_to_relation_json(tmp_path):
    data=candidate(tmp_path);prepare(tmp_path,data)
    data[KEY]['fact_key']='a'*64
    with pytest.raises(ValueError,match='PG_AUTHORITY_DIGEST_MISMATCH'):read(tmp_path,data)

def test_missing_membership_authority_fails_closed(tmp_path):
    with pytest.raises(ValueError,match='REFERENCE_REQUIRED_NO_FALLBACK'):read(tmp_path,candidate(tmp_path))


def test_membership_context_metadata_requires_exact_head_scope_and_non_pit_lineage(monkeypatch,tmp_path):
    data=candidate(tmp_path);data['membership_snapshot_id']='SNAP-1'
    metadata={key:'value' for key in ('membership_mode','taxonomy','membership_observed_at','member_set_asof',
        'knowledge_lineage','production_eligible_scope','survivorship_bias_risk')}
    metadata.update(membership_snapshot_id='SNAP-1',AS_RECORDED=False,PIT_ELIGIBLE=False,
        HISTORICAL_FIRST_AVAILABLE_PROVEN=False)
    authority=dict(contract_id='V4_NATIVE_MEMBERSHIP_REFERENCE_AUTHORITY_R1',T0=data['accepted_trade_date'],
        membership_snapshot=data['membership_snapshot'],membership_snapshot_id='SNAP-1',snapshot_metadata=dict(
            contract_id='V4_NATIVE_MEMBERSHIP_CONTEXT_METADATA_R1',version='1.0.0',fields=metadata),
        AS_RECORDED=False,PIT_ELIGIBLE=False)
    monkeypatch.setattr('workbench_db.v4_membership_reference_pg_v1._load_authority',lambda root,candidate:authority)
    assert context_metadata(tmp_path,data)==metadata
    authority['snapshot_metadata']['fields']=dict(metadata,PIT_ELIGIBLE=True)
    with pytest.raises(ValueError,match='CONTEXT_LINEAGE_MISMATCH'):
        context_metadata(tmp_path,data)


def test_membership_prepare_pins_snapshot_context_into_pg_authority_fixture(monkeypatch,tmp_path):
    from workbench_db import v4_membership_reference_pg_v1 as module
    source=tmp_path/'members.json';atomic_json(tmp_path,source,dict(rows=[{'security_id':'S1'}]))
    source_binding=ref(tmp_path,source)
    snapshot={key:'value' for key in ('membership_mode','taxonomy','membership_observed_at','member_set_asof',
        'knowledge_lineage','production_eligible_scope','survivorship_bias_risk')}
    snapshot.update(membership_snapshot_id='SNAP-2',AS_RECORDED=False,PIT_ELIGIBLE=False,
        HISTORICAL_FIRST_AVAILABLE_PROVEN=False,memberships=source_binding)
    snapshot_path=tmp_path/'snapshot.json';atomic_json(tmp_path,snapshot_path,snapshot)
    data={'accepted_trade_date':'2026-10-12','membership_snapshot_id':'SNAP-2',
        'membership_snapshot':ref(tmp_path,snapshot_path)}
    content=[{'security_id':'S1'}];stored=[]
    monkeypatch.setattr('workbench_analysis.r43_operational_publication.rows',lambda root,binding:content)
    monkeypatch.setattr(module,'append',lambda *args,**kwargs:{'descriptor':'fixture'})
    monkeypatch.setattr(module,'read_fact',lambda *args,**kwargs:content)
    monkeypatch.setattr(module,'_persist_authority',lambda root,authority:stored.append(authority) or {'authority':'fixture'})

    module.prepare(tmp_path,data)

    assert stored[0]['snapshot_metadata']==dict(contract_id='V4_NATIVE_MEMBERSHIP_CONTEXT_METADATA_R1',version='1.0.0',
        fields={key:snapshot[key] for key in (
            'membership_mode','taxonomy','membership_snapshot_id','membership_observed_at','member_set_asof',
            'knowledge_lineage','AS_RECORDED','PIT_ELIGIBLE','HISTORICAL_FIRST_AVAILABLE_PROVEN',
            'production_eligible_scope','survivorship_bias_risk')})
    assert data[KEY]=={'authority':'fixture'}

from pathlib import Path
from sector.membership_snapshot import build_snapshot

def test_current_membership_snapshot_has_stable_keys():
    frame,_=build_snapshot(Path("D:/new_tdx"),"20260904")
    assert not frame.duplicated(["date","sector_id","security_id"]).any()
    assert set(frame.sector_type)=={"INDUSTRY","THEME","STYLE"}
    assert frame.membership_asof_date.eq(frame.date).all()
    assert not frame.pit_membership.any()

def test_industry_snapshot_materializes_audited_parent_memberships():
    frame,_=build_snapshot(Path("D:/new_tdx"),"20260904")
    copper=frame[(frame.sector_type=="INDUSTRY")&(frame.sector_code=="T020201")]
    parent=frame[(frame.sector_type=="INDUSTRY")&(frame.sector_code=="T0202")]
    assert not copper.empty and not parent.empty
    assert set(copper.security_id)<=set(parent.security_id)

from pathlib import Path
from sector.membership_snapshot import build_snapshot

def test_current_membership_snapshot_has_stable_keys():
    frame,_=build_snapshot(Path("D:/new_tdx"),"20260904")
    assert not frame.duplicated(["date","sector_id","security_id"]).any()
    assert set(frame.sector_type)=={"INDUSTRY","THEME","STYLE"}
    assert frame.membership_asof_date.eq(frame.date).all()
    assert not frame.pit_membership.any()

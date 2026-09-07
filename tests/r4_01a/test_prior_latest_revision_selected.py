from forward.live import latest_revision,next_revision_number
def test_latest_ignores_incomplete_revision(live_root):
 (live_root/"data/forward/observations/20260904/revision_2").mkdir();assert latest_revision(live_root,"20260904").name=="revision_1";assert next_revision_number(live_root,"20260904")==3

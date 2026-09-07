from forward.live import live_event,states_for_union
def test_revision():
 assert live_event("20260904","20260904","b","a")=="SAME_CUTOFF_SOURCE_REVISION"
 assert states_for_union([{"security_id":"x"}],[{"security_id":"x"}],same_cutoff_revision=True)[0]["candidate_state"]=="SOURCE_REVISED"

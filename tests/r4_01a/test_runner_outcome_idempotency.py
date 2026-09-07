from forward.live import append_outcomes
def test_idempotent(live_root):
 x={"signal_observation_id":"s","horizon":1,"target_revision":1};append_outcomes(live_root,[x]);assert append_outcomes(live_root,[x])["idempotent"]==1

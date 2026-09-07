from forward.live import outcome_replay
def test_idempotent():
 x={"signal_observation_id":"a","horizon":1,"target_revision":1};assert outcome_replay(x,x)=="VERIFIED_IDEMPOTENT"

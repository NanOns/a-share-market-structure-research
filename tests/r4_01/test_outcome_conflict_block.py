from forward.live import outcome_replay
def test_conflict():
 a={"signal_observation_id":"a","horizon":1,"target_revision":1,"value":1};b={**a,"value":2};assert outcome_replay(a,b)=="CONFLICT_BLOCKED"

from forward.live import states_for_union
def test_model_guard():assert states_for_union([{"security_id":"x"}],[{"security_id":"x"}],model_identity_same=False)[0]["candidate_state"]=="SOURCE_REVISED"

from forward.observation import OUTCOME_FIELDS
def test_schema():assert {"signal_observation_id","horizon","target_trading_date","forward_return","outcome_status"}<=set(OUTCOME_FIELDS)

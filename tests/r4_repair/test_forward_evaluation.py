import pandas as pd
import pytest
from forward.evaluation import bind_outcomes,evaluate

def sample(n=30,dates=5):
    obs=[];out=[]
    for i in range(n):
        sid=f"SH.{600000+i:06d}";oid=f"o{i}";day=f"202609{10+i%dates:02d}"
        obs.append({"security_id":sid,"observation_id":oid,"observation_date":day,"steady_queue_tier":"CORE"})
        out.append({"security_id":sid,"signal_observation_id":oid,"signal_date":day,"horizon":5,"target_revision":1,"outcome_status":"OBSERVED","forward_return":i/1000,"max_high_return":i/900,"max_drawdown":-i/2000})
    return pd.DataFrame(obs),pd.DataFrame(out)

def test_metrics_hidden_until_both_sample_gates_pass():
    obs,out=sample(29,5);row=evaluate(bind_outcomes(obs,out)).iloc[0]
    assert row.sample_status=="DATA_INSUFFICIENT" and pd.isna(row.median_forward_return)
    obs,out=sample(30,5);row=evaluate(bind_outcomes(obs,out)).iloc[0]
    assert row.sample_status=="SUFFICIENT_FOR_DESCRIPTION" and row.observed_count==30 and row.signal_date_count==5

def test_outcome_must_bind_to_original_signal():
    obs,out=sample(1,1);out.loc[0,"signal_observation_id"]="wrong"
    with pytest.raises(RuntimeError,match="UNBOUND_OUTCOME_SIGNAL"):bind_outcomes(obs,out)

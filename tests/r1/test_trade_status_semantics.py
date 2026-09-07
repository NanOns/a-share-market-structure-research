import numpy as np

from normalize.phase1 import normalize


def test_trade_and_data_status_are_separate(gap_rows):
    table,_,_=normalize('SH.600001',gap_rows,np.array([20260901,20260902,20260903]),[])
    actual,gap=table.to_pandas().iloc[[0,1]].itertuples(index=False)
    assert actual.has_actual_bar and actual.data_observed and actual.has_positive_amount
    assert not actual.trade_status_known
    assert actual.tradable
    assert not gap.has_actual_bar and not gap.data_observed and not gap.has_positive_amount
    assert not gap.trade_status_known and not gap.tradable

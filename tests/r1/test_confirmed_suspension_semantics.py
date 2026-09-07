import numpy as np

from normalize.phase1 import normalize


def test_confirmed_suspension_requires_explicit_local_evidence(gap_rows):
    table,context,stats=normalize('SH.600001',gap_rows,np.array([20260901,20260902,20260903]),[],
        confirmed_suspension_dates={20260902})
    row=table.to_pandas().iloc[1]
    assert row.missing_state=='CONFIRMED_SUSPENSION'
    assert row.trade_status_known and row.is_synthetic_fill and not row.has_actual_bar
    assert context.iloc[1].close==10 and context.iloc[1].amount==0
    assert stats['confirmed_suspension']==1

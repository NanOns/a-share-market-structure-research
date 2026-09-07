import numpy as np

from normalize.phase1 import normalize


def test_unknown_internal_gap_is_inferred_not_confirmed(gap_rows):
    table,context,stats=normalize('SH.600001',gap_rows,np.array([20260901,20260902,20260903]),[])
    row=table.to_pandas().iloc[1]
    assert row.missing_state=='INFERRED_GAP'
    assert row.missing_state!='CONFIRMED_SUSPENSION'
    assert not row.is_synthetic_fill and stats['inferred_gap']==1
    assert context.iloc[1].state=='INFERRED_GAP'

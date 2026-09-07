import numpy as np
import pandas as pd

from normalize.phase1 import normalize


def test_inferred_gap_raw_and_derived_observations_remain_null(gap_rows):
    table,context,_=normalize('SH.600001',gap_rows,np.array([20260901,20260902,20260903]),[])
    row=table.to_pandas().iloc[1]
    fields=['raw_open','raw_high','raw_low','raw_close','raw_volume','raw_amount',
        'adj_open','adj_high','adj_low','adj_close','aligned_close','aligned_volume','aligned_amount']
    assert all(pd.isna(row[field]) for field in fields)
    assert pd.isna(context.iloc[1]['close']) and pd.isna(context.iloc[1]['amount'])

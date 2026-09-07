from candidates.research_priority import pool_gate
def test_outside(row):row.update(steady_trend=False,scanner_hits='');assert not pool_gate(row)

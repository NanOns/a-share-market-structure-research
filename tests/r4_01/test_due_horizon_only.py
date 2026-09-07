from forward.live import due_horizons
def test_due():assert due_horizons(0,5)==[1,5] and due_horizons(0,4)==[1]

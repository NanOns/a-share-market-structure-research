from forward.live import due_horizons
def test_exited_still_due():assert due_horizons(0,5,settled=(1,))==[5]

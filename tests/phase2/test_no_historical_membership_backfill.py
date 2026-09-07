from sector.phase2 import snapshot_guard
import pytest

def test_dates_bound_to_membership():
    snapshot_guard([20260904],20260904,20260904)
    with pytest.raises(ValueError):snapshot_guard([20100101],20260904,20260904)
    with pytest.raises(ValueError):snapshot_guard([20260905],20260904,20260904)
    with pytest.raises(ValueError):snapshot_guard([20260904],20260904,20260905)

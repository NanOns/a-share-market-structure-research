import pytest

from workbench_online.collector import (
    HotRankCaptureDisabled,
    collect_eastmoney_hot_rank,
    collect_ths_hot_rank,
)


@pytest.mark.parametrize("capture", [collect_ths_hot_rank, collect_eastmoney_hot_rank])
def test_legacy_capture_fails_before_creating_storage(tmp_path, capture):
    target = tmp_path / "hot-rank"
    with pytest.raises(HotRankCaptureDisabled, match="REQUEST_TIME_ONLY"):
        capture(target)
    assert not target.exists()

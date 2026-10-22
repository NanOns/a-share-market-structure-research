from pathlib import Path


def test_missing_or_zero_first_capture_is_presented_as_wait_not_published():
    source = (Path(__file__).parents[1] / "src/workbench_service/static/core-product-r1/app.js").read_text(
        encoding="utf-8"
    )

    assert "liveCount==null||liveCount===0?'WAIT_REAL_FIRST_CAPTURE'" in source
    assert "WAIT_REAL_FIRST_CAPTURE：当前没有符合条件的真实首次捕获" in source
    assert "缺少首次捕获证据时不生成 Lane L 观察" in source

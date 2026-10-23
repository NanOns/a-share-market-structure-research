from pathlib import Path
from types import SimpleNamespace

from workbench_service.core_product_bff_r1 import CoreProductBFFR1


def test_chart_and_market_fact_roots_are_retained_from_constructor(tmp_path: Path) -> None:
    api = SimpleNamespace(candidate={}, root=tmp_path, token="candidate-token")
    chart_root = tmp_path / "chart-index"
    market_root = tmp_path / "market-index"
    extension = {"contract_id": "chart-history-extension-test"}

    bff = CoreProductBFFR1(
        api,
        None,
        chart_history_index_root=chart_root,
        chart_history_extension_binding=extension,
        market_fact_index_root=market_root,
    )

    assert bff.chart_history_index_root == chart_root.resolve()
    assert bff.chart_history_extension_binding is extension
    assert bff.market_fact_index_root == market_root.resolve()
    assert bff.isolated_history is None

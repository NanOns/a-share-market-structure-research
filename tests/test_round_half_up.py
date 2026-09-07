from decimal import Decimal

from adjustment.tdx_adjustment import round_half_up_price


def test_round_half_up_boundaries() -> None:
    assert round_half_up_price("5.765") == Decimal("5.77")
    assert round_half_up_price("5.7649") == Decimal("5.76")
    assert round_half_up_price("-260.975") == Decimal("-260.98")


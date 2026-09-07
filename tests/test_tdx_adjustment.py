from decimal import Decimal

from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors


def test_single_xrxd_affine_formula() -> None:
    event = XrxdEvent(
        "SZ.000001",
        20250102,
        cash_dividend_per_10=Decimal("2"),
        rights_price=Decimal("8"),
        bonus_transfer_per_10=Decimal("3"),
        rights_ratio_per_10=Decimal("1"),
    )
    m, c = event.mc()
    assert m == Decimal("1.4")
    assert c == Decimal("-0.6")
    factors = build_affine_factors([20241231, 20250102], [event])
    assert factors[20241231].qfq_price("20") == Decimal("14.71")
    assert factors[20250102].qfq_price("20") == Decimal("20.00")


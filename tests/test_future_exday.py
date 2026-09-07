from decimal import Decimal

from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors


def test_future_exday_is_ignored() -> None:
    event = XrxdEvent(
        "SH.600887", 20160605, cash_dividend_per_10=Decimal("9")
    )
    factors = build_affine_factors([20160104, 20160105], [event])
    assert factors[20160104].qfq_price("15.17") == Decimal("15.17")
    assert factors[20160105].qfq_price("15.49") == Decimal("15.49")
    assert factors[20160105].qfq_mul == Decimal("1")
    assert factors[20160105].qfq_add == Decimal("0")


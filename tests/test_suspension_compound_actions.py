from decimal import Decimal

from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors


def test_600519_two_events_in_one_suspension_gap_are_both_applied() -> None:
    events = [
        XrxdEvent(
            "SH.600519",
            20060519,
            cash_dividend_per_10=Decimal("3"),
            bonus_transfer_per_10=Decimal("10"),
            source_record_index=1,
        ),
        XrxdEvent(
            "SH.600519",
            20060524,
            cash_dividend_per_10=Decimal("5.91"),
            bonus_transfer_per_10=Decimal("1.2"),
            source_record_index=2,
        ),
    ]
    factors = build_affine_factors([20060425, 20060525, 20060526], events)
    # 2006-04-25 lies before both ex-days; 2006-05-25 lies after both.
    assert abs(factors[20060425].qfq_mul * Decimal("2.24") - Decimal("1")) < Decimal("1e-38")
    assert factors[20060525].qfq_mul == Decimal("1")
    assert factors[20060526].qfq_mul == Decimal("1")

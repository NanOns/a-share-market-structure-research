from decimal import Decimal

from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors


def test_000651_rights_issue_and_large_bonus_reference_cases() -> None:
    rights = XrxdEvent(
        "SZ.000651",
        19980421,
        rights_price=Decimal("22"),
        rights_ratio_per_10=Decimal("3"),
    )
    bonus = XrxdEvent(
        "SZ.000651",
        20150703,
        cash_dividend_per_10=Decimal("30"),
        bonus_transfer_per_10=Decimal("10"),
    )
    assert rights.mc() == (Decimal("1.3"), Decimal("-6.6"))
    assert bonus.mc() == (Decimal("2"), Decimal("3"))


def test_hfq_is_derived_consistently_from_qfq_anchor() -> None:
    event = XrxdEvent("SZ.000651", 20150703, cash_dividend_per_10=Decimal("30"), bonus_transfer_per_10=Decimal("10"))
    factors = build_affine_factors([20150702, 20150703, 20150706], [event])
    first = factors[20150702]
    for factor in factors.values():
        raw = Decimal("58.49")
        expected = ((factor.qfq_mul * raw + factor.qfq_add - first.qfq_add) / first.qfq_mul)
        assert factor.hfq_price(raw) == expected.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")


def _cash_events(security_id: str, rows: list[tuple[int, str]]) -> list[XrxdEvent]:
    return [
        XrxdEvent(security_id, day, cash_dividend_per_10=Decimal(cash), source_record_index=index)
        for index, (day, cash) in enumerate(rows)
    ]


def test_locked_reference_tdx_price_assertions() -> None:
    # Minimal dates are sufficient because affine coefficients are constant
    # between ex-days. Values are ported from the locked reference test fixture.
    moutai_events = [
        XrxdEvent("SH.600519", 20060519, Decimal("3"), bonus_transfer_per_10=Decimal("10"), source_record_index=0),
        XrxdEvent("SH.600519", 20060524, Decimal("5.91"), bonus_transfer_per_10=Decimal("1.2"), source_record_index=1),
        XrxdEvent("SH.600519", 20110701, Decimal("23"), bonus_transfer_per_10=Decimal("1"), source_record_index=2),
        XrxdEvent("SH.600519", 20140625, Decimal("43.74"), bonus_transfer_per_10=Decimal("1"), source_record_index=3),
        XrxdEvent("SH.600519", 20150717, Decimal("43.74"), bonus_transfer_per_10=Decimal("1"), source_record_index=4),
    ] + _cash_events("SH.600519", [
        (20070713, "7"), (20080616, "8.36"), (20090701, "11.56"), (20100705, "11.85"),
        (20120705, "39.97"), (20130607, "64.19"), (20160701, "61.71"), (20170707, "67.87"), (20180615, "109.99"),
        (20190628, "145.39"), (20200624, "170.25"), (20210625, "192.93"), (20220630, "216.75"),
        (20221227, "219.1"), (20230630, "259.11"), (20231220, "191.06"), (20240619, "308.76"),
        (20241220, "238.82"), (20250626, "276.73"), (20251219, "239.57"),
    ])
    mf = build_affine_factors([20060425, 20060526, 20250626, 20260602], moutai_events)
    assert [mf[20060425].qfq_price(x) for x in ("89", "93.2", "87.61", "91.41")] == [
        Decimal("-261.29"), Decimal("-259.88"), Decimal("-261.76"), Decimal("-260.48")
    ]
    assert mf[20060526].qfq_price("39.49") == Decimal("-260.97")
    assert mf[20060526].qfq_price("40.02") == Decimal("-260.58")
    assert mf[20250626].qfq_price("1420") == Decimal("1396.04")

    gree_events = [
        XrxdEvent("SZ.000651", 20150703, Decimal("30"), bonus_transfer_per_10=Decimal("10"), source_record_index=0)
    ] + _cash_events("SZ.000651", [
        (20160707, "15"), (20170705, "18"), (20190225, "6"), (20190806, "15"),
        (20200611, "12"), (20201112, "10"), (20210823, "30"), (20220408, "10"),
        (20220805, "20"), (20230227, "10"), (20230809, "10"), (20240828, "23.8"),
        (20250515, "10"), (20250829, "20"), (20260123, "10"),
    ])
    gf = build_affine_factors([20150702, 20150703, 20260601], gree_events)
    assert gf[20150702].qfq_price("58.49") == Decimal("5.77")
    assert gf[20150703].qfq_price("24.98") == Decimal("3.00")

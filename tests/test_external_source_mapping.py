from validation.external_qfq import eastmoney_secid, tencent_symbol


def test_external_security_mappings() -> None:
    assert eastmoney_secid("SH.600519") == "1.600519"
    assert eastmoney_secid("SZ.000001") == "0.000001"
    assert eastmoney_secid("BJ.920000") == "0.920000"
    assert tencent_symbol("SH.600519") == "sh600519"
    assert tencent_symbol("BJ.920000") == "bj920000"


from v4.contracts.source_overlap import classify_asset, compare_day_values, core_gate


def test_asset_types_and_non_a_stock_differences_do_not_block_core():
    a_ids={"SH.600000","SZ.000001","BJ.920001"}
    assert classify_asset("SH","600000",a_ids)=="A_STOCK"
    assert classify_asset("SH","000001",a_ids)=="INDEX"
    assert classify_asset("SH","510050",a_ids)=="ETF_LOF"
    assert classify_asset("SH","113001",a_ids)=="BOND_CONVERTIBLE"
    assert classify_asset("SH","204001",a_ids)=="REPO"
    assert core_gate({"A_STOCK":{"acceptance":"ACCEPTED_SOURCE_PACKAGE"},"REPO":{"acceptance":"BLOCKED"}})=="ACCEPTED_SOURCE_PACKAGE"


def test_identity_mismatch_or_unexplained_a_stock_difference_blocks_core():
    assert core_gate({"A_STOCK":{"acceptance":"BLOCKED"},"INDEX":{"acceptance":"ACCEPTED_SOURCE_PACKAGE"}})=="BLOCKED"


def test_overlap_comparator_requires_field_specific_explanation():
    package=(100,110,90,105,100000.0,1000)
    assert compare_day_values(package,package)==("EXACT",None,[])
    one_price_unit=(101,110,90,105,100000.0,1000)
    assert compare_day_values(package,one_price_unit)==("NORMALIZED","TOLERATED_PRICE_ROUNDING",["open"])
    refreshed=(100,110,90,105,100000.0,1001)
    assert compare_day_values(package,refreshed,source_refresh_eligible=True)[1]=="TOLERATED_SOURCE_REFRESH_VOLUME_REVISION"
    assert compare_day_values(package,refreshed,source_refresh_eligible=False)[0]=="UNEXPLAINED_MISMATCH"
    substantive=(105,110,90,105,100000.0,1000)
    assert compare_day_values(package,substantive,source_refresh_eligible=True)[0]=="UNEXPLAINED_MISMATCH"
    amount=(100,110,90,105,100001.0,1000)
    assert compare_day_values(package,amount,source_refresh_eligible=True)[0]=="UNEXPLAINED_MISMATCH"

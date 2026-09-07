from production.daily import STAGE_ORDER
def test_order():assert STAGE_ORDER[0]=='PRECHECK' and STAGE_ORDER[-1]=='FINAL_RECEIPT' and STAGE_ORDER.index('REPORTING')<STAGE_ORDER.index('END_TO_END_VERIFY')

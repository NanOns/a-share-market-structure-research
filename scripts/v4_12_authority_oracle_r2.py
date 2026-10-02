"""Independent handwritten authority expectations from the R8 task/audit.

No imports from repair, validators, AST interpreters or future implementation.
"""
def vectors():
    return [
        {'id':'A01','subject':'delta3','expected':['rps5_delta3','RPS_DELTA_V1','data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json'],'reason':'Task6: scoped accepted RPS delta only'},
        {'id':'A02','subject':'near_high20_state','expected':['POSITION_STATE_V1',False,'BLOCKED_CAPABILITY'],'reason':'Task7: correct V4-04 owner; no target-date accepted profile'},
        {'id':'A03','subject':'unknown_f0','expected':'FALSE_ACCEPTED_OWNER_CLAIM','reason':'Task1/18: unknown F0 never defaults to any accepted Core'},
        {'id':'A04','subject':'distance_zone','expected':['D1_LOCAL_DERIVATION','V4_12_MACHINE_AST_V1'],'reason':'Task8: internal derivation, no F0 source'},
        {'id':'A05','subject':'alpha_beta','expected':['V4_12_COORDINATE_VIEW_V1','BLOCKED_CAPABILITY','BLOCKED_WITH_EXPLICIT_REASON'],'reason':'Task4: historical transform authority unavailable; never Core'},
        {'id':'A06','subject':'prior_range20_atr','expected':['BLOCKED_CAPABILITY','FORMAL_BLOCKED_INPUT_CAPABILITY'],'reason':'Task10: Option B; no accepted output and no raw fallback'},
        {'id':'A07','subject':'pivot','expected':['BLOCKED_CAPABILITY','V4_12_PIVOT_SOURCE_DESIGN_V1'],'reason':'Task11: both pivot fields blocked pending exact accepted history'},
        {'id':'A08','subject':'slope_unit','expected':['dimensionless','dimensionless',0.1],'reason':'Task13: unit parity; numeric candidate unchanged'},
        {'id':'A09','subject':'explicit_aliases','expected':{'ATR20':'atr20','CLV':'clv','MA20':'ma20','MA60':'ma60'},'reason':'Task5: exact aliases, no runtime casing guesses'},
        {'id':'A10','subject':'branch_local','expected':'RECOVERY_CONFIRMED','reason':'Task14: earlier resolved confirmed rule ignores missing MA/bounce branch inputs; synthetic design fixture only'},
        {'id':'A11','subject':'missing_owner','expected':'UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE','reason':'Task7/18: cannot forge known near-high output when target publication absent'},
        {'id':'A12','subject':'raw_bars','expected':['BLOCKED_CAPABILITY',False],'reason':'Task10/11: existence of raw bars cannot confer range/pivot authority'}]

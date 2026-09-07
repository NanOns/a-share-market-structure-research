from shadow_v2.diagnostics import nonoverlap_ranges
def test_nonoverlap_contraction():
 c=[10]*20;h=[15]*10+[11]*10;l=[5]*10+[9]*10;assert nonoverlap_ranges(c,h,l)[2]<1

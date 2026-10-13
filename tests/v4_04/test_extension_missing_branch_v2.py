"""New previously uncovered branch masking cases, not old passed vectors."""
from v4.profile_core import extension_risk

def test_known_false_amount_resolves_missing_return():
    assert extension_risk(dict(bias20_atr=2.1,amount_ratio20=1.5,ret5=None,atr20=1,close=10,ret1=-.1)).value=='MEDIUM'

def test_known_positive_ret1_resolves_missing_ret5():
    assert extension_risk(dict(bias20_atr=1,amount_ratio20=3,ret5=None,atr20=1,close=10,ret1=.1)).value=='LOW'

def test_unresolved_high_branch_stays_unknown():
    assert extension_risk(dict(bias20_atr=2.1,amount_ratio20=3,ret5=None,atr20=1,close=10,ret1=-.1)).value=='UNKNOWN'

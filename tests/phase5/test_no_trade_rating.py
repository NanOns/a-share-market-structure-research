import candidates.research_priority as m
def test_no_trade_fields():assert not {'buy','sell','watch'}&set(m.__dict__)

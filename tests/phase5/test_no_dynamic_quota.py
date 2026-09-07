from candidates.research_priority import rating
def test_rating_is_threshold_only():assert rating(.95)=='A+' and rating(.1)=='C'

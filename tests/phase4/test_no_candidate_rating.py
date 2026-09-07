import scanner.stock_scanner as s
def test_no_rating_or_score(): assert 'rating' not in s.__dict__ and 'score' not in s.__dict__

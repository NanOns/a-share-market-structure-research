import pytest
from candidates.research_priority import rating
@pytest.mark.parametrize('p,g',[(.95,'A+'),(.949999,'A'),(.85,'A'),(.849999,'B'),(.65,'B'),(.649999,'C')])
def test_boundaries(p,g):assert rating(p)==g

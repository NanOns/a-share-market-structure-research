import pytest
from tests.forward_p1_vectors import sector_vector

@pytest.mark.parametrize('number', range(1,13))
def test_required_sector_vector(number):
    sector_vector(number)

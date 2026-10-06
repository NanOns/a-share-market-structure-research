import pytest
from tests.forward_p1_vectors import stock_vector

@pytest.mark.parametrize('number', range(1,13))
def test_required_stock_vector(number):
    stock_vector(number)

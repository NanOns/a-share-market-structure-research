from datetime import date
import pytest
from production.daily import guard_no_future
def test_future_blocks():
 with pytest.raises(RuntimeError,match='FUTURE_SNAPSHOT'):guard_no_future([date(2026,9,5)],date(2026,9,4))

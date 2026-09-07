import pytest
from production.daily import require_hash
def test_receipt_hash_mismatch_blocks():
 with pytest.raises(RuntimeError,match='HASH_MISMATCH'):require_hash('actual','receipt')

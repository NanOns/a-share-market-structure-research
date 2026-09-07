import pytest
from forward.live import assert_target_in_sequence
def test_sequence_only():
 with pytest.raises(RuntimeError,match="NOT_SEALED"):assert_target_in_sequence("20260908",["20260904","20260907"])

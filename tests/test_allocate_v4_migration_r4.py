import pytest

from scripts.allocate_v4_migration_r4 import _next_number


def test_allocator_fills_only_unreserved_physical_gap_before_later_migration():
    physical = [*range(1, 72), 73]
    assert _next_number(physical, [33, 44, 46, 47, 73]) == 72


def test_allocator_rejects_missing_file_for_reserved_migration_number():
    with pytest.raises(ValueError, match="MIGRATION_ALLOCATION_RESERVED_FILE_MISSING:2"):
        _next_number([1, 3], [2])

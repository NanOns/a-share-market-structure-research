import pytest
from candidates.research_priority import quality_points
@pytest.mark.parametrize('w,n',[('',10),('LATE_EXTENSION_WARNING',7),('HIGH_CONCENTRATION_SECTOR_CONTEXT',8),('LOW_SECTOR_COVERAGE_CONTEXT',7),('LATE_EXTENSION_WARNING|HIGH_CONCENTRATION_SECTOR_CONTEXT|LOW_SECTOR_COVERAGE_CONTEXT',2),('LATE_EXTENSION_WARNING|LATE_EXTENSION_WARNING',7)])
def test_deductions(w,n):assert quality_points(w)==n

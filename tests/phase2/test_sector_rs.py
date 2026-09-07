import statistics
import pytest

def test_translation_median_equivalence():
    values=[-.4,.1,.8,.9];benchmark=.03
    assert statistics.median(values)-benchmark==pytest.approx(statistics.median([v-benchmark for v in values]))

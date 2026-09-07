from decimal import Decimal as D
import pytest
from validation.phase0_2b import fit_ab, FIELDS

def test_exact_affine_and_residuals():
    raw = dict(zip(FIELDS, ['10','12','9','11']))
    qfq = {f: D(v)*D('.5')-D('3') for f,v in raw.items()}
    fit = fit_ab(raw, qfq)
    assert (fit['fit_A'], fit['fit_B'], fit['fit_max_abs_residual']) == (D('.5'), D('-3'), 0)

def test_flat_day_cannot_identify_a_b():
    assert fit_ab(dict.fromkeys(FIELDS, 10), dict.fromkeys(FIELDS, 7))['fit_A'] is None

def test_nonfinite_rejected():
    with pytest.raises(ValueError):
        fit_ab(dict.fromkeys(FIELDS, 'NaN'), dict.fromkeys(FIELDS, 7))

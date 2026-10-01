from copy import deepcopy
import json
from pathlib import Path
import pytest
from workbench_analysis.forward_pit_ledger_r2 import atomic,canonical,reference
from workbench_analysis.amount_a_source_binding_r3_1 import validate_roots

ROOT=Path(__file__).resolve().parents[2]


def test_current_source_roots_are_verified_against_actual_accepted_scope():
    result=validate_roots(ROOT,reference(ROOT,ROOT/"data/v4/V4_DATA_ACCEPTED_HEAD.json"),reference(ROOT,ROOT/"data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json"))
    assert result["data_head_validation"].startswith("PASS")


def test_self_declared_accepted_membership_replica_not_admitted(tmp_path):
    # Preserve actual data root and source artifacts; only inject an alternate
    # JSON head path inside the actual project temporary namespace.
    from tempfile import TemporaryDirectory
    (ROOT/"tmp").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT/"tmp") as directory:
        path=Path(directory)/"self_declared_membership.json"
        actual=json.loads((ROOT/"data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json").read_text(encoding="utf8"))
        atomic(path,canonical(actual))
        with pytest.raises(ValueError,match="MEMBERSHIP_NOT_EXACT_ACCEPTED_V4_08_SOURCE"):
            validate_roots(ROOT,reference(ROOT,ROOT/"data/v4/V4_DATA_ACCEPTED_HEAD.json"),reference(ROOT,path))

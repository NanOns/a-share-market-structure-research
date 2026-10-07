import json
from pathlib import Path
import pytest
from scripts.full_chain_repair_io import ROOT
from workbench_analysis.v4_legacy_release_scope import release_scope


def test_current_authority_separates_immutable_historical_release():
    result = release_scope(ROOT)
    assert result['historical_role'] == 'HISTORICAL_V1_RELEASE_DIAGNOSTIC_ONLY'
    assert result['current_head']['path'] == 'data/v4/V4_15_ACCEPTED_HEAD.json'
    assert result['historical_replay_is_current_acceptance'] is False
    assert result['runtime_permission'] is False


def test_historical_pointer_drift_rejected_before_current_acceptance(tmp_path):
    contract = json.loads((ROOT / 'config/v4_legacy_release_scope_v1.json').read_bytes())
    path = tmp_path / 'config/v4_legacy_release_scope_v1.json'
    path.parent.mkdir()
    path.write_text(json.dumps(contract), encoding='utf8')
    pointer = tmp_path / contract['historical_pointer']['path']
    pointer.parent.mkdir(parents=True)
    pointer.write_bytes(b'{}')
    with pytest.raises(ValueError, match='LEGACY_RELEASE_SCOPE_BINDING_CHANGED:historical_pointer'):
        release_scope(tmp_path)

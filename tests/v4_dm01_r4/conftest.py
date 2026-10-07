"""Legacy assertion executes an explicit historical authority profile only."""
from types import FunctionType
import json,hashlib
from scripts.full_chain_repair_io import ROOT
import pytest
from tests.runtime_isolation import create

@pytest.fixture(autouse=True)
def legacy_pre_acceptance_profile(request,tmp_path,monkeypatch):
    if request.node.name!='test_current_real_v2_parent_and_future_wait':return
    from workbench_analysis import dm01_runtime_r4 as r
    root=create(tmp_path/'historical_pre_acceptance')
    profile=json.loads((ROOT/'reports/forward_r2_remainder_consolidated_20261007/DM01_LEGACY_TEST_SUPERSESSION_PROOF.json').read_bytes())
    for row in profile['historical_pre_acceptance']['profile']:
        raw=(ROOT/row['archive']['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['archive']['sha256']
        target=root/row['original_path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    original=r.accepted_envelope
    gate=r.session_gate
    historical=FunctionType(gate.__code__,dict(gate.__globals__,accepted_envelope=lambda ignored:original(root)),gate.__name__,gate.__defaults__)
    monkeypatch.setattr(r,'session_gate',historical)

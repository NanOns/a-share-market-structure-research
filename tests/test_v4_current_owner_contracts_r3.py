"""Current V4 descendant entry cannot borrow corrupted or escalated authority."""
import json
from pathlib import Path
import pytest
from workbench_analysis.v4_13_accepted_contract_package import current_contracts
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('mutation',['production','changed_owner','unaccepted_stage'])
def test_current_owner_rejects_escalation_and_changed_predecessor(monkeypatch,mutation):
    path=ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json'
    original=Path.read_bytes
    stage=json.loads(original(path))
    if mutation=='production':stage['production_permission']=True
    if mutation=='changed_owner':stage['v4_13_binding']['sha256']='0'*64
    if mutation=='unaccepted_stage':stage['accepted_stage_range']='V4_00_TO_V4_17_ACCEPTED'
    def altered(selected):
        return json.dumps(stage).encode() if selected.resolve()==path else original(selected)
    monkeypatch.setattr(Path,'read_bytes',altered)
    with pytest.raises(ValueError):current_contracts(ROOT)

def test_external_historical_git_cannot_be_enabled_in_normal_root(monkeypatch):
    from workbench_analysis.v4_13_descendant_contracts import DescendantContracts
    monkeypatch.setenv('R4_ENGINEERING_HISTORICAL_GIT_ROOT',str(ROOT))
    monkeypatch.setenv('R4_NATIVE_ISOLATION','1')
    with pytest.raises(ValueError,match='HISTORICAL_GIT_ROOT_REQUIRES_ISOLATED_ENGINEERING'):
        DescendantContracts(ROOT)

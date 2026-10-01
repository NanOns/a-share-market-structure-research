"""Pinned protection metadata never changes business source byte admission."""
from pathlib import Path
import json
import pytest
from workbench_analysis.dm01_accepted_chain_v1 import bound_path
from workbench_analysis.forward_pit_ledger_r2 import atomic
from workbench_analysis.parallel_scoped_consolidation_r3 import validate_scoped_protected_binding
from workbench_analysis.parallel_scoped_acceptance_r1 import PROTECTED_REPRESENTATIONS

ROOT=Path(__file__).resolve().parents[2]

def copied(tmp):
    raw=(ROOT/PROTECTED_REPRESENTATIONS['path']).read_bytes()
    atomic(tmp/PROTECTED_REPRESENTATIONS['path'],raw)
    rows=json.loads(raw)['representations']
    for row in rows:
        arc=row['original_bytes_archive']
        original=(ROOT/arc['path']).read_bytes()
        atomic(tmp/arc['path'],original)
        atomic(tmp/row['original_binding']['path'],original.replace(b'\r\n',b'\n'))
    return rows

@pytest.mark.parametrize('index',[0,1])
def test_exact_registered_git_bytes_are_metadata_only(tmp_path,index):
    row=copied(tmp_path)[index]
    validate_scoped_protected_binding(tmp_path,row['original_binding'])
    with pytest.raises(ValueError):bound_path(tmp_path,row['original_binding'])

def test_real_content_drift_fails_protection(tmp_path):
    row=copied(tmp_path)[0]
    path=tmp_path/row['original_binding']['path']
    atomic(path,path.read_bytes()+b'\n')
    with pytest.raises(ValueError):validate_scoped_protected_binding(tmp_path,row['original_binding'])

def test_representation_map_cannot_be_reissued_by_caller(tmp_path):
    row=copied(tmp_path)[0]
    path=tmp_path/PROTECTED_REPRESENTATIONS['path']
    atomic(path,path.read_bytes()+b'\n')
    with pytest.raises(ValueError):validate_scoped_protected_binding(tmp_path,row['original_binding'])

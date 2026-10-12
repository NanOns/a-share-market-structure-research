import json
from pathlib import Path
import pytest
from workbench_service.engineering_pg_publication_r3 import attest, ADMISSION, CONTRACT
from workbench_service.current_v4_context import SourceInvalid

def test_production_root_refused_before_pg():
    with pytest.raises(SourceInvalid,match='DISPOSABLE_G_ROOT_REQUIRED'):
        attest(Path(__file__).resolve().parents[1])

@pytest.mark.parametrize('mutation',[dict(production_permission=True),dict(workspace_root='G:/codex_tmp/wrong')])
def test_isolated_admission_scope_refused_before_pg(tmp_path,mutation):
    path=tmp_path/ADMISSION;path.parent.mkdir(parents=True)
    record=dict(contract_id=CONTRACT,scope='ENGINEERING_ONLY',production_permission=False,workspace_root=str(tmp_path))
    record.update(mutation)
    path.write_text(json.dumps(record),encoding='utf8')
    with pytest.raises(SourceInvalid,match='ADMISSION_REQUIRED|WORKSPACE_IDENTITY_MISMATCH'):
        attest(tmp_path)

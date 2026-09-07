import hashlib
import inspect

import phase1_runner
from production.daily import _write_runtime_status


def test_runtime_status_writes_only_runtime_paths(tmp_path):
    protected=['PROJECT_SPEC.md','docs/FACTOR_CONTRACT_V1.md','docs/DAILY_PRODUCTION_CONTRACT_V1.md']
    for relative in protected:
        path=tmp_path/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(relative,encoding='utf8')
    before={name:hashlib.sha256((tmp_path/name).read_bytes()).hexdigest() for name in protected}
    _write_runtime_status(tmp_path,{'date':'20260903','run_id':'run-1','release_path':'release'},2)
    after={name:hashlib.sha256((tmp_path/name).read_bytes()).hexdigest() for name in protected}
    assert before==after
    assert (tmp_path/'reports/current/CURRENT_RELEASE.json').exists()
    assert (tmp_path/'reports/current/CURRENT_STATUS.md').exists()


def test_phase1_runtime_no_longer_rewrites_specification():
    source=inspect.getsource(phase1_runner.run)
    assert 'registry_documents(' not in source
    assert "PROJECT_SPEC.md" not in source
    assert "docs/PHASE1_REPORT.md" not in source

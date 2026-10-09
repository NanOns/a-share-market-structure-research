from types import SimpleNamespace
from scripts import run_v4_dm01_daily_increment as daily


def test_failed_child_without_json_retains_failure(monkeypatch):
    monkeypatch.setattr(daily.subprocess, 'run', lambda *a, **k:
        SimpleNamespace(returncode=1, stdout='', stderr="ModuleNotFoundError: No module named 'scripts'"))
    code, payload = daily._run_json_cli('scripts/build_dm01_r4_tdx_delta.py')
    assert code == 1
    assert payload['status'] == 'BLOCKED_CLI_EXECUTION_FAILED'
    assert 'ModuleNotFoundError' in payload['stderr']


def test_failed_child_json_keeps_specific_status(monkeypatch):
    monkeypatch.setattr(daily.subprocess, 'run', lambda *a, **k:
        SimpleNamespace(returncode=2, stdout='{"status":"BLOCKED_HASH"}\n', stderr='detail'))
    _, payload = daily._run_json_cli('example')
    assert payload['status'] == 'BLOCKED_HASH'
    assert payload['exit_code'] == 2


def test_non_object_child_is_invalid(monkeypatch):
    monkeypatch.setattr(daily.subprocess, 'run', lambda *a, **k:
        SimpleNamespace(returncode=0, stdout='[]', stderr=''))
    assert daily._run_json_cli('example')[1]['status'] == 'BLOCKED_CLI_OUTPUT_INVALID'

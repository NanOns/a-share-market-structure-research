from types import SimpleNamespace
from workbench_service.diagnostic_views import diagnostic

def test_retired_database_never_restored():
    r=SimpleNamespace(manifest={},envelope=lambda **x:x)
    d=diagnostic(r,'legacy')
    assert d['legacy_database']=='RETIRED_NOT_RESTORED'
    assert len(d['items'])==7
    assert diagnostic(r,'shadow')['scope']=='INDEPENDENT_SHADOW_CONTEXT_NOT_DEFAULT_PRODUCTION'

def test_missing_job_is_valid_and_no_raw_errors(tmp_path):
    r=SimpleNamespace(root=tmp_path,manifest={},envelope=lambda **x:x)
    d=diagnostic(r,'jobs')
    assert d['status']=='READY' and d['items']==[]
    assert d['log_policy']=='BOUNDED_STATUS_ONLY_NO_RAW_SHELL_OR_CREDENTIAL_PATHS'

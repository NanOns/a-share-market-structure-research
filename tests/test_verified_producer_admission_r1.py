import json
import sys
import pytest
from workbench_desktop import storage
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis import operational_daily_exact_policy_v2 as policy


def policy_file(tmp_path):
    p=tmp_path/'config/operational_daily_exact_release_policy_v2.json';p.parent.mkdir();p.write_text(json.dumps(dict(publication_ready=True)))
    return p,ref(tmp_path,p)


def test_source_worker_admitted_only_after_strict_verified_policy_without_lease(tmp_path,monkeypatch):
    p,binding=policy_file(tmp_path);checks=[]
    monkeypatch.setattr(sys,'frozen',False,raising=False)
    monkeypatch.setattr(policy,'verify',lambda root,verify_loaded: (checks.append(verify_loaded) or {},binding))
    with pytest.raises(ValueError,match='PRODUCER_ADMISSION_REQUIRED'):storage.require_producer(tmp_path)
    storage.activate_workspace_sources(tmp_path,producer_worker=True)
    storage.require_producer(tmp_path)
    assert checks==[True]
    with pytest.raises(ValueError,match='WORKSPACE_LEASE_REQUIRED'):storage.require_owned(tmp_path)
    p.write_text('{}')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):storage.require_producer(tmp_path)


def test_failed_actual_source_verification_never_records_worker_authorization(tmp_path,monkeypatch):
    policy_file(tmp_path);monkeypatch.setattr(sys,'frozen',False,raising=False)
    def reject(*args,**kwargs):raise ValueError('EXACT_V2_LOADED_ALGORITHM_VERSION_MISMATCH')
    monkeypatch.setattr(policy,'verify',reject)
    with pytest.raises(ValueError,match='VERSION_MISMATCH'):storage.activate_workspace_sources(tmp_path,producer_worker=True)
    with pytest.raises(ValueError,match='PRODUCER_ADMISSION_REQUIRED'):storage.require_producer(tmp_path)


def test_source_adapter_rejects_unverified_worker_before_any_source_import(tmp_path):
    from workbench_desktop.source_adapter import executor,tdx_capture
    with pytest.raises(ValueError,match='PRODUCER_ADMISSION_REQUIRED'):executor(tmp_path,producer_worker=True)
    with pytest.raises(ValueError,match='PRODUCER_ADMISSION_REQUIRED'):tdx_capture(tmp_path,producer_worker=True)


def test_tdx_capture_verified_producer_needs_no_desktop_lease(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import scripts
    from workbench_analysis import operational_owner_adapter_v1 as adapter
    from workbench_desktop.source_adapter import tdx_capture
    _,binding=policy_file(tmp_path);monkeypatch.setattr(sys,'frozen',False,raising=False)
    monkeypatch.setattr(policy,'verify',lambda root,verify_loaded: ({},binding))
    storage.activate_workspace_sources(tmp_path,producer_worker=True)
    capture=SimpleNamespace();binding_module=SimpleNamespace()
    monkeypatch.setattr(scripts,'capture_dm01_a01_r3_tdx_package',capture,raising=False)
    monkeypatch.setattr(scripts,'enter_source_authority_remediation_r2',binding_module,raising=False)
    calls=[]
    def private(module,values):
        assert values['ROOT']==tmp_path
        if module is binding_module:return {'bind':lambda:None}
        assert module is capture
        return {'main':lambda:calls.append('verified-capture') or 'CAPTURED'}
    monkeypatch.setattr(adapter,'private_scope',private)
    assert tdx_capture(tmp_path,producer_worker=True)=='CAPTURED' and calls==['verified-capture']
    with pytest.raises(ValueError,match='WORKSPACE_LEASE_REQUIRED'):storage.require_owned(tmp_path)

import json
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock


def test_accepted_reader_checks_archive_without_loaded_producer(monkeypatch,tmp_path):
    from workbench_analysis import operational_successor_v1 as module
    from workbench_analysis import operational_successor_release_v1 as release
    candidate=dict(contract_id=module.CONTRACT)
    head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head.parent.mkdir(parents=True);head.write_text(json.dumps(candidate))
    verify=Mock();monkeypatch.setattr(release,'verify_policy',verify)
    monkeypatch.setattr(module,'OperationalSuccessorReaderV1',lambda root,document:document)
    assert module.accepted_api(tmp_path)==candidate
    verify.assert_called_once_with(tmp_path,candidate,verify_loaded=False)


def test_current_joint_reader_retains_strict_default_for_producer(monkeypatch,tmp_path):
    from workbench_service import native_current_snapshot_v3 as module
    path=tmp_path/module.AUTHORITY;path.parent.mkdir(parents=True);path.write_text('{}')
    import inspect
    assert inspect.signature(module.validate_joint).parameters['verify_loaded'].default is True
    verify=Mock(return_value='checked');monkeypatch.setattr(module,'validate_joint',verify)
    assert module.current(tmp_path,{})=='checked'
    verify.assert_called_once_with(tmp_path,{}, {},verify_loaded=False)


def test_worker_activation_verifies_manifest_without_workspace_lease(monkeypatch,tmp_path):
    from workbench_desktop import storage
    from workbench_desktop import closeout_runtime_sources_r1 as source
    import sys
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    require=Mock(side_effect=AssertionError('worker must not claim desktop lease'))
    monkeypatch.setattr(storage,'require_owned',require)
    check=Mock(return_value={'resources':[],'module_locations':[]})
    monkeypatch.setattr(storage,'verify_resources',check)
    monkeypatch.setattr(storage,'g_path',lambda p:p)
    monkeypatch.setattr(source,'admitted',lambda p:{})
    storage.activate_workspace_sources(tmp_path,producer_worker=True)
    check.assert_called_once();require.assert_not_called()

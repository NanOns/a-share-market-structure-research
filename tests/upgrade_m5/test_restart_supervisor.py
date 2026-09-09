from workbench_ops import RestartSupervisor


def test_restart_happy_path_has_required_order():
    calls=[];call=lambda name: lambda: calls.append(name)
    result=RestartSupervisor().restart(drain=call("drain"),close_db=call("close"),release_owner_lock=call("release"),start_new=call("start"),health_check=lambda: True,restore_old=call("restore"))
    assert result["status"] == "READY"
    assert result["states"] == ["DRAINING","CLOSE_DB","RELEASE_OWNER_LOCK","START_NEW","HEALTH_CHECK","READY"]


def test_restart_failed_health_restores_old_config():
    calls=[];call=lambda name: lambda: calls.append(name)
    result=RestartSupervisor().restart(drain=call("drain"),close_db=call("close"),release_owner_lock=call("release"),start_new=call("start"),health_check=lambda: False,restore_old=call("restore"))
    assert result["status"] == "ROLLED_BACK" and calls[-1] == "restore"
    assert result["states"][-2:] == ["ROLLBACK_OLD_CONFIG","ROLLED_BACK"]

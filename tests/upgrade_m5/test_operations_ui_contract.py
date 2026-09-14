from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]


def test_operations_ui_exposes_every_m5_module_in_chinese():
    html=(ROOT/'src/workbench_service/static/operations.html').read_text('utf-8')
    for text in ('服务控制','立即重启服务','配置中心','存储与三日清理','备份与恢复演练','数据库迁移','活动任务','受管对象'):
        assert text in html


def test_every_operations_button_is_bound_to_a_real_api():
    html=(ROOT/'src/workbench_service/static/operations.html').read_text('utf-8')
    app=(ROOT/'src/workbench_service/app.py').read_text('utf-8')
    for endpoint in ('/api/operations/config/validate','/api/operations/config/apply','/api/operations/storage/preview','/api/operations/backup/create','/api/operations/backup/restore-drill','/api/operations/migration/prepare','/api/operations/restart'):
        assert endpoint in html and endpoint in app
    assert "'/api/operations/storage/'+action" in html
    for action in ('quarantine','restore','delete'):
        assert f"/api/operations/storage/{action}" in app
    assert "/api/operations/stop" in app


def test_windows_tray_exposes_service_controls():
    tray=(ROOT/'scripts/workbench_tray.ps1').read_text('utf-8')
    launcher=(ROOT/'START_WORKBENCH_TRAY.cmd').read_text('utf-8')
    for label in ('服务状态：','打开 V3 工作台','打开运维中心','启动服务','重启服务','停止服务','退出托盘'):
        assert label in tray
    assert "/api/operations/' + $action" in tray
    assert 'workbench_tray.ps1' in launcher


def test_raw_boolean_is_not_accepted_as_maintenance_authority():
    app=(ROOT/'src/workbench_service/app.py').read_text('utf-8')
    assert "body.get('maintenance_window')" not in app
    assert "body.get('confirmation')" in app
    i18n=(ROOT/'src/workbench_service/static/operations-i18n.js').read_text('utf-8')
    assert "api/operations/storage/" in i18n and "payload.confirmation" in i18n

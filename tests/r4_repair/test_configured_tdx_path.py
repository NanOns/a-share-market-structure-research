from pathlib import Path
from common.paths import (
    configured_path_source,
    resolve_baostock_cache_root,
    resolve_baostock_download_root,
    resolve_baostock_request_ledger,
    resolve_configured_path,
    resolve_tdx_root,
    resolve_tdx_snapshot_root,
)

def test_environment_tdx_root_overrides_config(tmp_path,monkeypatch):
    configured=tmp_path/"configured";configured.mkdir();environment=tmp_path/"environment";environment.mkdir()
    (tmp_path/"config").mkdir();(tmp_path/"config/paths.yaml").write_text(f'tdx:\n  root: "{configured.as_posix()}"\n',encoding="utf8")
    monkeypatch.setenv("TDX_ROOT",str(environment))
    assert resolve_tdx_root(tmp_path)==environment.resolve()

def test_explicit_tdx_root_overrides_environment_and_config(tmp_path,monkeypatch):
    configured=tmp_path/"configured";configured.mkdir();environment=tmp_path/"environment";environment.mkdir();explicit=tmp_path/"explicit";explicit.mkdir()
    (tmp_path/"config").mkdir();(tmp_path/"config/paths.yaml").write_text(f'tdx:\n  source_root: "{configured.as_posix()}"\n',encoding="utf8")
    monkeypatch.setenv("TDX_ROOT",str(environment))
    assert resolve_tdx_root(tmp_path,explicit)==explicit.resolve()

def test_configured_market_data_paths_use_environment_then_yaml(tmp_path,monkeypatch):
    configured=tmp_path/"yaml-download";environment=tmp_path/"env-download";explicit=tmp_path/"explicit-download"
    (tmp_path/"config").mkdir()
    (tmp_path/"config/paths.yaml").write_text(f"tdx:\n  daily_download_root: '{configured.as_posix()}'\n",encoding="utf8")
    monkeypatch.delenv("TDX_DAILY_DOWNLOAD_ROOT",raising=False)
    assert resolve_configured_path(tmp_path,"tdx.daily_download_root")==configured.resolve()
    monkeypatch.setenv("TDX_DAILY_DOWNLOAD_ROOT",str(environment))
    assert resolve_configured_path(tmp_path,"tdx.daily_download_root")==environment.resolve()
    assert configured_path_source(tmp_path,"tdx.daily_download_root")=="ENVIRONMENT:TDX_DAILY_DOWNLOAD_ROOT"
    assert resolve_configured_path(tmp_path,"tdx.daily_download_root",explicit=explicit)==explicit.resolve()

def test_missing_optional_ingest_path_is_not_invented(tmp_path,monkeypatch):
    monkeypatch.delenv("V4_INGEST_TEMP_ROOT",raising=False)
    assert resolve_configured_path(tmp_path,"ingest.temp_root",required=False) is None

def test_environment_is_used_when_config_has_no_root(tmp_path,monkeypatch):
    candidate=tmp_path/"environment";candidate.mkdir();monkeypatch.setenv("TDX_ROOT",str(candidate))
    assert resolve_tdx_root(tmp_path)==candidate.resolve()

def test_no_implicit_absolute_tdx_root_fallback(tmp_path,monkeypatch):
    monkeypatch.delenv("TDX_ROOT",raising=False)
    (tmp_path/"config").mkdir()
    (tmp_path/"config/paths.yaml").write_text("tdx:\n  root:\n",encoding="utf8")
    try:
        resolve_tdx_root(tmp_path)
    except FileNotFoundError as exc:
        assert str(exc)=="TDX_ROOT_NOT_CONFIGURED"
    else:
        raise AssertionError("TDX_ROOT_MUST_NOT_FALL_BACK_TO_CODED_ABSOLUTE_PATH")


def test_repository_tdx_and_baostock_input_output_paths_are_separated(monkeypatch):
    root=Path(__file__).resolve().parents[2]
    for key in ('TDX_ROOT','TDX_SNAPSHOT_ROOT','BAOSTOCK_CACHE_ROOT'):
        monkeypatch.delenv(key,raising=False)
    tdx=resolve_tdx_root(root)
    snapshot=resolve_tdx_snapshot_root(root)
    cache=resolve_baostock_cache_root(root)
    download=resolve_baostock_download_root(root)
    assert configured_path_source(root,'tdx.source_root')=='CONFIG:config/paths.yaml'
    assert configured_path_source(root,'tdx.snapshot_root')=='CONFIG:config/paths.yaml'
    assert configured_path_source(root,'baostock.cache_root')=='CONFIG:config/paths.yaml'
    assert configured_path_source(root,'baostock.download_root')=='CONFIG:config/paths.yaml'
    assert not snapshot.is_relative_to(tdx)
    assert not cache.is_relative_to(tdx)
    assert not download.is_relative_to(tdx)


def test_baostock_download_root_uses_explicit_environment_yaml_precedence(tmp_path,monkeypatch):
    configured=tmp_path/'yaml-download';environment=tmp_path/'env-download';explicit=tmp_path/'explicit-download'
    (tmp_path/'config').mkdir()
    (tmp_path/'config/paths.yaml').write_text(
        f'baostock:\n  download_root: "{configured.as_posix()}"\n',encoding='utf-8')
    monkeypatch.delenv('BAOSTOCK_DOWNLOAD_ROOT',raising=False)
    assert resolve_baostock_download_root(tmp_path)==configured.resolve()
    monkeypatch.setenv('BAOSTOCK_DOWNLOAD_ROOT',str(environment))
    assert resolve_baostock_download_root(tmp_path)==environment.resolve()
    assert resolve_baostock_download_root(tmp_path,explicit)==explicit.resolve()


def test_continuous_maintenance_capture_readers_use_configured_snapshot_roots(tmp_path,monkeypatch):
    import hashlib
    import json
    from scripts import run_v4_continuous_data_maintenance as maintenance

    tdx_root=tmp_path/'custom-tdx-snapshots'
    bao_root=tmp_path/'custom-bao-cache'
    (tmp_path/'config').mkdir()
    (tmp_path/'config/paths.yaml').write_text(
        f'tdx:\n  snapshot_root: "{tdx_root.as_posix()}"\n'
        f'baostock:\n  cache_root: "{bao_root.as_posix()}"\n',encoding='utf-8')
    monkeypatch.setattr(maintenance,'ROOT',tmp_path)
    day='2026-10-16'
    bao_folder=bao_root/'baostock'/day.replace('-','')/'sha256-configured'
    bao_folder.mkdir(parents=True)
    bao_record={'trade_date':day,'provider_date':day,'status':'BAOSTOCK_DAILY_SNAPSHOT_READY',
                'received_at':'2026-10-16T17:00:00+08:00','daily_rows':[{'code':'sh.600000'}],
                'adjustment_factor_rows':[]}
    (bao_folder/'daily_update.json').write_text(json.dumps(bao_record),encoding='utf-8')

    package=b'configured official TDX package'
    package_path=tdx_root/'tdx'/day.replace('-','')/'capture-1'/'package.zip'
    package_path.parent.mkdir(parents=True)
    package_path.write_bytes(package)
    tdx_receipt={'target_date':day,'observed_at':'2026-10-16T16:00:00+08:00',
                 'status':'TDX_PACKAGE_READY','download':{'path':str(package_path),
                 'sha256':hashlib.sha256(package).hexdigest()},'zip_validation':{'crc_integrity':'PASS'}}
    receipt_path=package_path.parent/'capture_receipt.json'
    receipt_path.write_text(json.dumps(tdx_receipt),encoding='utf-8')

    assert maintenance.discover_baostock_daily_capture(day)==bao_record
    assert maintenance.discover_official_tdx_capture(day)==tdx_receipt


def test_dm01_lifecycle_reader_selects_baostock_snapshot_from_configured_cache(tmp_path,monkeypatch):
    import json
    from scripts import build_v4_dm01_lifecycle_snapshot as lifecycle

    cache=tmp_path/'relocated-cache'
    (tmp_path/'config').mkdir()
    (tmp_path/'config/paths.yaml').write_text(
        f'baostock:\n  cache_root: "{cache.as_posix()}"\n',encoding='utf-8')
    monkeypatch.setattr(lifecycle,'ROOT',tmp_path)
    day='2026-10-16';snapshot_id='sha256-'+('a'*64)
    folder=cache/'baostock'/day.replace('-','')/snapshot_id
    folder.mkdir(parents=True)
    record={'trade_date':day,'provider_date':day,'status':'BAOSTOCK_DAILY_SNAPSHOT_READY',
            'daily_rows':[{'code':'sh.600000'}],'adjustment_factor_rows':[],
            'snapshot_id':snapshot_id}
    path=folder/'daily_update.json';path.write_text(json.dumps(record),encoding='utf-8')
    assert lifecycle.select_baostock_snapshot(day,snapshot_id)==(record,path)


def test_dm01_source_capture_entrypoints_resolve_central_roots(tmp_path):
    from scripts.capture_dm01_a01_r3_tdx_package import capture_roots
    from workbench_analysis.dm01_corrected_source_capture_v2 import resolve_source_paths

    configured_tdx=tmp_path/'read-only-tdx'
    configured_snapshot=tmp_path/'tdx-snapshots'
    configured_baostock=tmp_path/'baostock-cache'
    (tmp_path/'config').mkdir()
    (tmp_path/'config/paths.yaml').write_text(
        f'tdx:\n  source_root: "{configured_tdx.as_posix()}"\n'
        f'  snapshot_root: "{configured_snapshot.as_posix()}"\n'
        f'baostock:\n  cache_root: "{configured_baostock.as_posix()}"\n',
        encoding='utf-8')
    assert capture_roots(tmp_path)==(configured_tdx.resolve(),configured_snapshot.resolve())
    assert resolve_source_paths(tmp_path)==(configured_tdx.resolve(),configured_baostock.resolve())


def test_baostock_request_ledger_uses_configured_cache_without_legacy_history(tmp_path):
    configured=tmp_path/'cache-root'
    (tmp_path/'config').mkdir()
    (tmp_path/'config/paths.yaml').write_text(
        f'baostock:\n  cache_root: "{configured.as_posix()}"\n  request_ledger: "{(configured / "request_ledger.json").as_posix()}"\n',encoding='utf-8')
    assert resolve_baostock_request_ledger(tmp_path)==configured.resolve()/'request_ledger.json'


def test_baostock_request_ledger_requires_explicit_config_and_preserves_legacy(tmp_path):
    import pytest
    configured=tmp_path/'cache-root'
    (tmp_path/'config').mkdir()
    (tmp_path/'config/paths.yaml').write_text(
        f'baostock:\n  cache_root: "{configured.as_posix()}"\n',encoding='utf-8')
    legacy=tmp_path/'reports/v4_baostock/request_ledger.json'
    legacy.parent.mkdir(parents=True);legacy.write_text('{}',encoding='utf-8')
    with pytest.raises(FileNotFoundError,match='BAOSTOCK_REQUEST_LEDGER_NOT_CONFIGURED'):
        resolve_baostock_request_ledger(tmp_path)
    assert legacy.read_text(encoding='utf-8')=='{}'


def test_live_baostock_acceptance_adapter_uses_resolved_roots():
    source=(Path(__file__).resolve().parents[2]/'scripts/accept_dynamic_daily_baostock_v2.py').read_text(encoding='utf-8')
    assert "resolve_tdx_root(root)" in source
    assert "resolve_baostock_request_ledger(root)" in source
    assert "D:/new_tdx" not in source


def test_daily_increment_defaults_to_the_configured_tdx_root(tmp_path, monkeypatch):
    import json
    from workbench_analysis import daily_increment_builder as increment

    tdx = tmp_path / "configured-tdx"
    output = tmp_path / "staging" / "raw.jsonl"
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text(
        f'tdx:\n  source_root: "{tdx.as_posix()}"\n', encoding="utf-8")
    monkeypatch.setattr(increment, "PROJECT_ROOT", tmp_path)
    delta = {
        "status": "READY", "target_date": "2026-10-16", "current_snapshot_id": "snapshot-1",
        "target_bars": [{"trade_date": 20261016, "security_id": "SH.600000", "open": 10,
                          "high": 11, "low": 9, "close": 10, "amount": 20, "volume": 2}],
    }

    result = increment.build_raw_increment_staging(
        trade_date="2026-10-16", source_snapshot_id="snapshot-1", delta=delta, output_path=output)

    assert result["status"] == "STAGING_READY"
    assert output.is_file()
    assert not output.resolve().is_relative_to(tdx.resolve())


def test_dm01_component_artifact_guard_uses_central_tdx_root(tmp_path, monkeypatch):
    import pytest
    from workbench_analysis import dm01_incremental_component_builders as builders

    tdx = tmp_path / "configured-tdx"
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text(
        f'tdx:\n  source_root: "{tdx.as_posix()}"\n', encoding="utf-8")
    monkeypatch.setattr(builders, "ROOT", tmp_path)
    monkeypatch.setattr(builders, "_tdx_root", lambda: resolve_tdx_root(tmp_path))
    with pytest.raises(ValueError, match="OUTPUT_UNDER_TDX_ROOT_FORBIDDEN"):
        builders._write_immutable(tdx / "must-not-write.json", {"x": 1})
    output = tmp_path / "artifact" / "candidate.json"
    builders._write_immutable(output, {"x": 1})
    assert output.is_file()
    assert not output.resolve().is_relative_to(tdx.resolve())


def test_operational_owner_writer_uses_configured_tdx_root(tmp_path, monkeypatch):
    from workbench_analysis import operational_owner_adapter_v1 as adapter
    from workbench_analysis import operational_daily_exact_policy_v2 as policy

    configured = tmp_path / "configured-tdx"
    monkeypatch.setenv("TDX_ROOT", str(configured))
    assert resolve_tdx_root(tmp_path) == configured.resolve()
    assert "D:/new_tdx" not in Path(adapter.__file__).read_text(encoding="utf-8")
    assert "D:/new_tdx" not in Path(policy.__file__).read_text(encoding="utf-8")


def test_dm01_baostock_runtime_acceptance_uses_pg_calendar_and_configured_ledger(tmp_path):
    from scripts.accept_v4_dm01_baostock_runtime import _target_is_official_session
    assert _target_is_official_session(
        tmp_path, '2026-10-16', sessions_reader=lambda root: ['2026-10-15', '2026-10-16'],
    )
    assert not _target_is_official_session(
        tmp_path, '2026-09-24', sessions_reader=lambda root: ['2026-09-24'],
    )
    source=(Path(__file__).resolve().parents[2]/'scripts/accept_v4_dm01_baostock_runtime.py').read_text(encoding='utf-8')
    assert 'resolve_baostock_request_ledger(ROOT, args.ledger)' in source
    assert '_target_is_official_session(ROOT, args.target_date)' in source
    assert 'reports/v4_dm01/2026-09-28/calendar_bridge_receipt.json' not in source


def test_dm01_runtime_entrypoints_resolve_tdx_root_from_central_config():
    root=Path(__file__).resolve().parents[2]
    source=(root/'scripts/run_dm01_a01_next_session_r1.py').read_text(encoding='utf-8')
    assert 'resolve_tdx_root' in source
    assert 'D:/new_tdx' not in source
    probe=(root/'src/workbench_analysis/gbbq_source_revision_probe.py').read_text(encoding='utf-8')
    assert 'tdx_root: Path,' in probe
    assert 'Path("D:/new_tdx")' not in probe

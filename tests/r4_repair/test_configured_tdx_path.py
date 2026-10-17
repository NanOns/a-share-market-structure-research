from pathlib import Path
from common.paths import (
    configured_path_source,
    resolve_baostock_cache_root,
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
    assert configured_path_source(root,'tdx.source_root')=='CONFIG:config/paths.yaml'
    assert configured_path_source(root,'tdx.snapshot_root')=='CONFIG:config/paths.yaml'
    assert configured_path_source(root,'baostock.cache_root')=='CONFIG:config/paths.yaml'
    assert not snapshot.is_relative_to(tdx)
    assert not cache.is_relative_to(tdx)


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

"""Invoke supported legacy provider surfaces inside a V4 native process."""
import importlib
import pytest

def exercise(tmp_path,monkeypatch,provider_name,entry,configuration):
    module=importlib.import_module('workbench_db.api_connection')
    monkeypatch.setenv('R4_NATIVE_ISOLATION','1')
    if configuration=='empty':monkeypatch.setenv('V4_NATIVE_PG_DSN','')
    elif configuration=='missing':monkeypatch.delenv('V4_NATIVE_PG_DSN',raising=False)
    attempts=[]
    def forbidden(*args,**kwargs):
        attempts.append((args,kwargs));raise AssertionError('DATABASE_ATTEMPT_BEFORE_V4_ADMISSION')
    monkeypatch.setattr(module.duckdb,'connect',forbidden)
    monkeypatch.setattr(module.psycopg,'connect',forbidden)
    provider=getattr(module,provider_name)(tmp_path/'legacy.duckdb' if provider_name.startswith('DuckDB') else 'host=127.0.0.1 port=1 dbname=forbidden')
    with pytest.raises(RuntimeError,match='V4_LEGACY_API_DATABASE_FORBIDDEN_NO_FALLBACK'):
        with getattr(provider,entry)():
            pytest.fail('LEGACY_BRIDGE_REACHED_IN_V4')
    assert not list(tmp_path.rglob('*'))
    assert attempts==[]

@pytest.mark.parametrize('provider_name',['DuckDBApiConnectionProvider','PostgresDuckDBApiConnectionProvider'])
@pytest.mark.parametrize('entry',['connect','memory'])
def test_v4_dynamic_legacy_api_fails_before_database_attempt(tmp_path,monkeypatch,provider_name,entry):
    exercise(tmp_path,monkeypatch,provider_name,entry,'configured')

@pytest.mark.parametrize('provider_name',['DuckDBApiConnectionProvider','PostgresDuckDBApiConnectionProvider'])
@pytest.mark.parametrize('entry',['connect','memory'])
@pytest.mark.parametrize('configuration',['empty','missing'])
def test_v4_missing_configuration_never_activates_bridge(tmp_path,monkeypatch,provider_name,entry,configuration):
    exercise(tmp_path,monkeypatch,provider_name,entry,configuration)

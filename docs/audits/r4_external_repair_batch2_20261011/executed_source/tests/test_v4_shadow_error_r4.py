"""R4-E01: exercise the error boundary, without production connections."""
from pathlib import Path

import psycopg
import pytest

from workbench_service.research_context import ResearchContextError
from workbench_service.shadow_context import COMPONENTS, PREFIX, ShadowContextReader


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('bundle', [{}, {'context': None}, {'context': {}}])
def test_malformed_source_preserves_underlying_error(bundle):
    reader = ShadowContextReader(ROOT, simulation_fixture=bundle)
    with pytest.raises(ResearchContextError, match='^SHADOW_SOURCE_INVALID$') as caught:
        reader._load()
    assert isinstance(caught.value.__cause__, (KeyError, TypeError))


@pytest.mark.parametrize('error', [psycopg.OperationalError, psycopg.ProgrammingError])
def test_pg_error_is_fail_closed(monkeypatch, error):
    reader = ShadowContextReader(ROOT)
    def fail():
        raise error('isolated injected database failure')
    monkeypatch.setattr(reader, '_real', fail)
    with pytest.raises(ResearchContextError, match='^SHADOW_PG_UNAVAILABLE$') as caught:
        reader._load()
    assert isinstance(caught.value.__cause__, error)


def test_contract_failure_is_preserved(monkeypatch):
    reader = ShadowContextReader(ROOT)
    def fail():
        raise ResearchContextError('READBACK_NOT_EXTERNALLY_ACCEPTED')
    monkeypatch.setattr(reader, '_real', fail)
    with pytest.raises(ResearchContextError, match='^READBACK_NOT_EXTERNALLY_ACCEPTED$'):
        reader._load()


def test_no_authorization_opens_no_database(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('unaccepted Shadow must not connect')
    monkeypatch.setattr(psycopg, 'connect', forbidden)
    reader = ShadowContextReader(tmp_path)
    for name in ('context', *COMPONENTS):
        status, data = reader.handle(PREFIX + name, {})
        assert status == 200
        assert data['status'] == 'NO_REAL_SHADOW_DATA'

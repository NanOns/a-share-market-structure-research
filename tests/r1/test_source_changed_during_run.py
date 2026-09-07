import json
import inspect
import pytest

from production import daily
from production.daily import assert_source_stable


def test_source_change_blocks_before_pointer_publication(tmp_path):
    pointer=tmp_path/'current.json';pointer.write_text(json.dumps({'run_id':'old'}),encoding='utf8')
    before=pointer.read_bytes()
    with pytest.raises(RuntimeError,match='SOURCE_CHANGED_DURING_RUN'):
        assert_source_stable({'sha256':'A'},{'sha256':'B'})
    assert pointer.read_bytes()==before


def test_unchanged_source_passes():
    assert assert_source_stable({'sha256':'A'},{'sha256':'A'})


def test_full_source_recheck_precedes_manifest_receipt_and_pointer():
    source=inspect.getsource(daily._run_daily_unlocked)
    report=source.index('build_reports(')
    recheck=source.index('source_after_full=source_fingerprint')
    gate=source.index('assert_source_stable(')
    manifest=source.index('manifest(stage')
    pointer=source.index('publish_generation(')
    assert report<recheck<gate<manifest<pointer

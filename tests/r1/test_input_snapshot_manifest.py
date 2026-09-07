import json
import inspect
import pytest

from common.input_snapshot import validate_input_snapshot_manifest,write_immutable_manifest
from production import daily
from production.release import RELEASE_FILES


def test_input_snapshot_manifest_is_complete_hashed_and_immutable(tmp_path,manifest_factory):
    value=manifest_factory()
    required={'run_id','cutoff_date','observed_at','source_revision_id','source_identity_version',
        'source_identity','day_source_summary','gbbq_sha256','gbbq_map_sha256','membership_hashes',
        'security_master_hashes','calendar_sha256','run_universe_generation','run_universe_sha256',
        'run_universe_count','adjustment_identity','price_basis','computation_identity','render_identity',
        'snapshot_manifest_sha256'}
    assert required<=set(value) and validate_input_snapshot_manifest(value)
    path=tmp_path/'INPUT_SNAPSHOT_MANIFEST.json';write_immutable_manifest(path,value)
    assert json.loads(path.read_text('utf8'))==value
    changed=dict(value);changed['run_id']='different'
    with pytest.raises((ValueError,FileExistsError)):
        write_immutable_manifest(path,changed)


def test_input_snapshot_is_release_required_and_built_before_manifest():
    source=inspect.getsource(daily._run_daily_unlocked)
    assert 'INPUT_SNAPSHOT_MANIFEST.json' in RELEASE_FILES
    assert 'INPUT_SNAPSHOT_MANIFEST.json' in daily.REQUIRED
    assert source.index('build_input_snapshot_manifest(')<source.index('manifest(stage')

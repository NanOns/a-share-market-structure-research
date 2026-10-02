"""Governance/replay tests; bundle operations use temporary directories only."""
import hashlib
import subprocess
from pathlib import Path
import pytest
from scripts.prepare_v4_11_promotion_r1 import ensure_bundle, EXPECTED_BUNDLE

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '2e3e811eb08d7e350e27c4c1e2767ba91160ef98'
PROTECTED = ['data/v4/V4_11_ACCEPTED_HEAD.json', 'data/v4/V4_STAGE_ACCEPTED_HEAD.json',
             'data/v4/V4_DATA_ACCEPTED_HEAD.json',
             'reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json']

def test_agents_exact_baseline():
    assert (ROOT/'AGENTS.md').read_bytes() == subprocess.check_output(
        ['git','show','1c46d6681ba1d0540551bcc0f75b35c545ff2769:AGENTS.md'], cwd=ROOT)

def populate(root):
    for p in EXPECTED_BUNDLE:
        (root/p).parent.mkdir(parents=True, exist_ok=True)
        (root/p).write_bytes((ROOT/p).read_bytes())

def test_prepare_repo_first(tmp_path):
    populate(tmp_path)
    before = {p: ((tmp_path/p).read_bytes(), (tmp_path/p).stat().st_mtime_ns) for p in EXPECTED_BUNDLE}
    assert ensure_bundle(tmp_path, tmp_path/'nonexistent')['copied_files'] == []
    assert before == {p: ((tmp_path/p).read_bytes(), (tmp_path/p).stat().st_mtime_ns) for p in EXPECTED_BUNDLE}
    assert not (tmp_path/'reports').exists()

def test_prepare_missing_bundle_fails_closed(tmp_path):
    with pytest.raises(ValueError, match='R6_EXTERNAL_BUNDLE_SOURCE_REQUIRED'):
        ensure_bundle(tmp_path)
    assert list(tmp_path.iterdir()) == []

def test_prepare_explicit_bundle_dir(tmp_path):
    bundle=tmp_path/'bundle'; bundle.mkdir()
    for p in EXPECTED_BUNDLE: (bundle/Path(p).name).write_bytes((ROOT/p).read_bytes())
    repo=tmp_path/'repo'
    assert len(ensure_bundle(repo,bundle)['copied_files']) == 3
    import json
    receipt=json.loads((repo/'reports/next_round_r6r1/R6_EXPLICIT_BUNDLE_SOURCE_PLAN.json').read_bytes())
    for item in receipt['sources']:
        raw=Path(item['source_path']).read_bytes()
        assert item['source_sha256']==hashlib.sha256(raw).hexdigest()
        assert item['source_bytes']==len(raw)
        assert (repo/item['destination']).read_bytes()==raw

def test_prepare_has_no_absolute_user_path():
    source=(ROOT/'scripts/prepare_v4_11_promotion_r1.py').read_text(encoding='utf8')
    for bad in ('D:/Users/', 'C:/Users/', '~/Desktop', 'rglob(', 'glob(', 'Desktop'):
        assert bad not in source

@pytest.mark.parametrize('path',PROTECTED)
def test_heads_byte_identical(path):
    assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT)

def test_invalid_existing_bundle_is_never_overwritten(tmp_path):
    populate(tmp_path); path=next(iter(EXPECTED_BUNDLE)); (tmp_path/path).write_bytes(b'tampered')
    with pytest.raises(ValueError,match='EXACT_MISMATCH'): ensure_bundle(tmp_path,tmp_path/'missing')
    assert (tmp_path/path).read_bytes()==b'tampered'

def test_bad_bootstrap_is_atomic_before_destination_writes(tmp_path):
    bundle=tmp_path/'bundle'; bundle.mkdir()
    for p in EXPECTED_BUNDLE: (bundle/Path(p).name).write_bytes((ROOT/p).read_bytes())
    (bundle/Path(next(iter(EXPECTED_BUNDLE))).name).write_bytes(b'bad')
    with pytest.raises(ValueError,match='EXACT_MISMATCH'): ensure_bundle(tmp_path/'repo',bundle)
    assert not (tmp_path/'repo').exists()

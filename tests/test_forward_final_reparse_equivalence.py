"""Portable negative proof in the original snapshot owners; real tests remain."""
from pathlib import Path
from types import SimpleNamespace
import stat
import pytest
from tests.v4_phase0.test_tdx_local_snapshot import fixture_root
from tests.v4_phase0.test_tdx_snapshot import build_fixture
from workbench_analysis.tdx_local_snapshot import build_local_snapshot, LocalSnapshotError
from workbench_analysis.tdx_snapshot import verify_zip_snapshot, SnapshotIntegrityError


def test_local_snapshot_original_owner_rejects_link_predicate(tmp_path, monkeypatch):
    source = fixture_root(tmp_path)
    link = source / 'vipdoc/sh/lday/sh600000.day'
    original = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda path: path == link or original(path))
    output = tmp_path / 'snapshot'
    with pytest.raises(LocalSnapshotError, match='TDX_INPUT_SYMLINK_REJECTED'):
        build_local_snapshot(source, output)
    assert not list(output.rglob('*.day'))


def test_extracted_snapshot_original_owner_rejects_reparse_attribute(tmp_path, monkeypatch):
    archive, extracted, inventory, digest = build_fixture(tmp_path)
    link = extracted / 'sh/lday/sh000001.day'
    original = Path.lstat
    def attributes(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path == link:
            return SimpleNamespace(st_mode=info.st_mode,
                                   st_file_attributes=getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))
        return info
    monkeypatch.setattr(Path, 'lstat', attributes)
    with pytest.raises(SnapshotIntegrityError, match='EXTRACTED_REPARSE_POINT_REJECTED'):
        verify_zip_snapshot(archive, extracted, inventory, 2, digest)

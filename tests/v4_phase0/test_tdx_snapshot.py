from __future__ import annotations

import hashlib
import os
import stat
import zipfile
from pathlib import Path

import pytest

from workbench_analysis.tdx_snapshot import SnapshotIntegrityError, verify_zip_snapshot


def build_fixture(root: Path):
    extracted = root / "extracted"
    extracted.mkdir()
    members = {"sh/lday/sh000001.day": b"index data", "sz/lday/sz000001.day": b"stock data"}
    inventory = {}
    digest = hashlib.sha256()
    archive = root / "source.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for relative, content in sorted(members.items(), key=lambda item: item[0].casefold()):
            path = extracted / Path(*relative.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            checksum = hashlib.sha256(content).hexdigest()
            inventory[relative] = {"byte_count": str(len(content)), "sha256": checksum}
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(str(len(content)).encode())
            digest.update(b"\0")
            digest.update(checksum.encode())
            digest.update(b"\n")
            output.writestr(relative, content)
    return archive, extracted, inventory, digest.hexdigest()


def test_zip_and_extracted_snapshot_are_matched_by_every_member_hash(tmp_path: Path):
    archive, extracted, inventory, expected_digest = build_fixture(tmp_path)
    result = verify_zip_snapshot(archive, extracted, inventory, 2, expected_digest)
    assert result["status"] == "PASS"
    assert result["member_count"] == 2
    assert result["expanded_bytes"] == 20


@pytest.mark.parametrize("mutation", ["extract", "inventory", "digest"])
def test_mutated_snapshot_fails_closed(tmp_path: Path, mutation: str):
    archive, extracted, inventory, expected_digest = build_fixture(tmp_path)
    if mutation == "extract":
        (extracted / "sh/lday/sh000001.day").write_bytes(b"mutated!!!")
    elif mutation == "inventory":
        inventory["sh/lday/sh000001.day"]["sha256"] = "0" * 64
    else:
        expected_digest = "0" * 64
    with pytest.raises(SnapshotIntegrityError):
        verify_zip_snapshot(archive, extracted, inventory, 2, expected_digest)


def test_archive_inventory_name_mismatch_fails_closed(tmp_path: Path):
    archive, extracted, inventory, expected_digest = build_fixture(tmp_path)
    inventory["bj/lday/bj000001.day"] = inventory.pop("sz/lday/sz000001.day")
    with pytest.raises(SnapshotIntegrityError, match="ZIP_INVENTORY_MEMBER_SET_MISMATCH"):
        verify_zip_snapshot(archive, extracted, inventory, 2, expected_digest)


def test_unsafe_zip_member_path_is_rejected_before_resolution(tmp_path: Path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../outside.day", b"x")
    with pytest.raises(SnapshotIntegrityError, match="ZIP_MEMBER_PATH_UNSAFE"):
        verify_zip_snapshot(archive, tmp_path, {"../outside.day": {"byte_count": "1", "sha256": "0" * 64}}, 1, "0" * 64)


@pytest.mark.parametrize("member", ["C:/outside.day", "SH/../escape.day", "/rooted.day"])
def test_windows_and_posix_path_escape_members_are_rejected(tmp_path: Path, member: str):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(member, b"x")
    with pytest.raises(SnapshotIntegrityError, match="ZIP_MEMBER_PATH_UNSAFE"):
        verify_zip_snapshot(archive, tmp_path, {member: {"byte_count": "1", "sha256": hashlib.sha256(b"x").hexdigest()}}, 1, "0" * 64)


def test_zip_symlink_member_is_rejected(tmp_path: Path):
    archive = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("sh/lday/sh000001.day")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(info, "target")
    with pytest.raises(SnapshotIntegrityError, match="ZIP_LINK_MEMBER_REJECTED"):
        verify_zip_snapshot(archive, tmp_path, {}, 1, "0" * 64)


def test_extracted_symlink_is_rejected(tmp_path: Path):
    archive, extracted, inventory, expected_digest = build_fixture(tmp_path)
    link = extracted / "sh/lday/sh000001.day"
    link.unlink()
    try:
        os.symlink(extracted / "sz/lday/sz000001.day", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this runner")
    with pytest.raises(SnapshotIntegrityError, match="EXTRACTED_REPARSE_POINT_REJECTED"):
        verify_zip_snapshot(archive, extracted, inventory, 2, expected_digest)

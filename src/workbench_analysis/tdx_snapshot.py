"""Content-addressed verification for project-managed TDX ZIP extractions."""
from __future__ import annotations

import hashlib
import stat
import zipfile
from pathlib import Path, PurePosixPath


class SnapshotIntegrityError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(name: str) -> str:
    posix = PurePosixPath(name.replace("\\", "/"))
    if (posix.is_absolute() or not posix.parts or ":" in posix.parts[0]
            or any(part in {"", ".", ".."} for part in posix.parts)):
        raise SnapshotIntegrityError("ZIP_MEMBER_PATH_UNSAFE")
    return posix.as_posix()


def _reject_reparse_components(root: Path, relative: str) -> None:
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            raise
        attributes = getattr(info, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if stat.S_ISLNK(info.st_mode) or (attributes & reparse_flag):
            raise SnapshotIntegrityError("EXTRACTED_REPARSE_POINT_REJECTED")


def verify_zip_snapshot(
    archive_path: Path,
    extracted_root: Path,
    inventory: dict[str, dict[str, str]],
    expected_entry_count: int,
    expected_content_digest: str,
) -> dict[str, object]:
    """Match every ZIP member to an extracted hash-bound inventory row.

    The digest is SHA256(sorted relative_path NUL byte_count NUL file_sha256 LF),
    matching the V4-01 extraction manifest. No TDX source root is accessed.
    """
    root = extracted_root.resolve(strict=True)
    with zipfile.ZipFile(archive_path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) != expected_entry_count:
            raise SnapshotIntegrityError("ZIP_ENTRY_COUNT_MISMATCH")
        members: dict[str, zipfile.ZipInfo] = {}
        folded_members: set[str] = set()
        for info in infos:
            relative = _safe_relative(info.filename)
            folded = relative.casefold()
            if relative in members or folded in folded_members:
                raise SnapshotIntegrityError("ZIP_DUPLICATE_MEMBER")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise SnapshotIntegrityError("ZIP_LINK_MEMBER_REJECTED")
            folded_members.add(folded)
            members[relative] = info
        if set(members) != set(inventory):
            raise SnapshotIntegrityError("ZIP_INVENTORY_MEMBER_SET_MISMATCH")

        digest = hashlib.sha256()
        total_bytes = 0
        for relative in sorted(members, key=str.casefold):
            expected = inventory[relative]
            _reject_reparse_components(root, relative)
            target = (root / Path(*PurePosixPath(relative).parts)).resolve(strict=True)
            if root not in target.parents:
                raise SnapshotIntegrityError("EXTRACTED_MEMBER_PATH_ESCAPE")
            info = members[relative]
            target_stat = target.stat()
            expected_size = int(expected["byte_count"])
            expected_sha = expected["sha256"].lower()
            if target_stat.st_size != expected_size or target_stat.st_size != info.file_size:
                raise SnapshotIntegrityError(f"EXTRACTED_MEMBER_SIZE_MISMATCH:{relative}")
            actual_sha = sha256_file(target)
            if actual_sha != expected_sha:
                raise SnapshotIntegrityError(f"EXTRACTED_MEMBER_HASH_MISMATCH:{relative}")
            archive_sha = hashlib.sha256()
            with archive.open(members[relative], "r") as member_stream:
                for block in iter(lambda: member_stream.read(1024 * 1024), b""):
                    archive_sha.update(block)
            if archive_sha.hexdigest() != actual_sha:
                raise SnapshotIntegrityError(f"ZIP_MEMBER_CONTENT_MISMATCH:{relative}")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(target_stat.st_size).encode("ascii"))
            digest.update(b"\0")
            digest.update(actual_sha.encode("ascii"))
            digest.update(b"\n")
            total_bytes += target_stat.st_size
        actual_digest = digest.hexdigest()
        if actual_digest != expected_content_digest:
            raise SnapshotIntegrityError("EXTRACTED_CONTENT_DIGEST_MISMATCH")
        return {
            "status": "PASS",
            "member_count": len(members),
            "expanded_bytes": total_bytes,
            "content_digest": actual_digest,
            "archive_sha256": sha256_file(archive_path),
        }

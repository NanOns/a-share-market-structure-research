"""Strict Git LFS pointer and restored-payload checks used by V4-05 R4 evidence."""
from __future__ import annotations

from hashlib import sha256
import re

_OID = re.compile(r"^oid sha256:([0-9a-f]{64})$")
_SIZE = re.compile(r"^size ([0-9]+)$")


def parse_pointer(data: bytes | str) -> dict[str, int | str]:
    text = data.decode("utf-8") if isinstance(data, bytes) else data
    rows = [line.strip() for line in text.splitlines() if line.strip()]
    if len(rows) != 3 or rows[0] != "version https://git-lfs.github.com/spec/v1":
        raise ValueError("INVALID_LFS_POINTER_HEADER")
    oid = _OID.fullmatch(rows[1])
    size = _SIZE.fullmatch(rows[2])
    if not oid or not size:
        raise ValueError("INVALID_LFS_POINTER_FIELDS")
    return {"oid_sha256": oid.group(1), "size": int(size.group(1))}


def verify_restored(pointer: dict[str, int | str], payload: bytes, expected_sha256: str) -> dict:
    restored_sha = sha256(payload).hexdigest()
    checks = {"pointer_oid_matches_expected": pointer["oid_sha256"] == expected_sha256,
              "pointer_size_matches_restored": pointer["size"] == len(payload),
              "restored_sha_matches_expected": restored_sha == expected_sha256}
    return {"pointer_oid_sha256": pointer["oid_sha256"], "pointer_size": pointer["size"],
            "restored_bytes": len(payload), "restored_sha256": restored_sha,
            "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"}

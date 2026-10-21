"""Atomic, content-addressed cache for read-only R8 candidate derivations."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile


CONTRACT_ID = "R8_CANDIDATE_DERIVED_SNAPSHOT_R1"


def cache_allowed(root):
    root=Path(root).resolve()
    approved=Path('G:/codex_tmp').resolve()
    return root==approved or approved in root.parents


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def cache_path(root, namespace, identity):
    root = Path(root).resolve()
    if not cache_allowed(root):
        raise ValueError("R8_DERIVED_CACHE_REQUIRES_G_CODEX_TMP_CANDIDATE_ROOT")
    target = (root / "runtime" / "r8_derived_cache" / namespace /
              (hashlib.sha256(canonical(identity)).hexdigest() + ".json")).resolve()
    if root not in target.parents:
        raise ValueError("R8_DERIVED_CACHE_PATH_ESCAPES_CANDIDATE_ROOT")
    return target


def read_snapshot(path, identity):
    """Return verified data, or a miss. A corrupt snapshot is never trusted."""
    try:
        envelope = json.loads(Path(path).read_bytes())
        payload = envelope["payload"]
        if (envelope.get("contract_id") != CONTRACT_ID or
                envelope.get("identity") != identity or
                envelope.get("payload_sha256") != hashlib.sha256(canonical(payload)).hexdigest()):
            return None
        return payload
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def write_snapshot(path, identity, payload):
    """Atomically publish only under the candidate root; never touches source Owners."""
    path = Path(path)
    body = canonical({"contract_id": CONTRACT_ID, "identity": identity,
                      "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest(),
                      "payload": payload})
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".r8-derived-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

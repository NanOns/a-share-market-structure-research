"""Content identity checks for immutable V4 source bundle descriptors."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def recompute_source_bundle_id(bundle: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in bundle.items() if key != "source_bundle_id"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_source_bundle_identity(bundle: dict[str, Any], expected_id: str | None = None) -> dict[str, str]:
    claimed = str(bundle.get("source_bundle_id", ""))
    actual = recompute_source_bundle_id(bundle)
    if not claimed or claimed != actual or (expected_id is not None and actual != expected_id):
        raise ValueError("SOURCE_BUNDLE_IDENTITY_MISMATCH")
    return {"source_bundle_id": actual, "status": "PASS"}

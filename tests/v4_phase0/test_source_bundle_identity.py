from __future__ import annotations

import pytest

from workbench_analysis.source_bundle_identity import recompute_source_bundle_id, verify_source_bundle_identity


def test_source_bundle_id_is_recomputed_from_canonical_unsigned_payload():
    bundle = {"contract": "source-bundle-v1", "package": {"sha256": "a" * 64},
              "target_trade_date": "2026-09-24"}
    bundle["source_bundle_id"] = recompute_source_bundle_id(bundle)
    assert verify_source_bundle_identity(bundle)["status"] == "PASS"
    changed = {**bundle, "target_trade_date": "2026-09-25"}
    with pytest.raises(ValueError, match="SOURCE_BUNDLE_IDENTITY_MISMATCH"):
        verify_source_bundle_identity(changed)


def test_source_bundle_id_expected_path_binding_is_enforced():
    bundle = {"contract": "source-bundle-v1", "package": {"sha256": "b" * 64}}
    bundle["source_bundle_id"] = recompute_source_bundle_id(bundle)
    with pytest.raises(ValueError, match="SOURCE_BUNDLE_IDENTITY_MISMATCH"):
        verify_source_bundle_identity(bundle, expected_id="0" * 64)

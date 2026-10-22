from __future__ import annotations

import pytest

from workbench_analysis.d0_source_seal_r2 import owner_version_from_binding


def test_content_address_is_owner_version_for_dated_archived_owner():
    sha = "a" * 64
    binding = {"path": f"archive/2026-10-20/core.jsonl.gz", "sha256": sha}
    assert owner_version_from_binding(binding, "2026-10-20") == sha


def test_run_token_in_dated_owner_path_has_precedence():
    token = "b" * 64
    binding = {"path": f"owners/2026-10-20/{token}/core.jsonl.gz", "sha256": "c" * 64}
    assert owner_version_from_binding(binding, "2026-10-20") == token


def test_content_address_fallback_requires_exact_target_date():
    binding = {"path": "archive/2026-10-19/core.jsonl.gz", "sha256": "d" * 64}
    with pytest.raises(ValueError, match="D0_OWNER_VERSION_TOKEN_NOT_BOUND"):
        owner_version_from_binding(binding, "2026-10-20")

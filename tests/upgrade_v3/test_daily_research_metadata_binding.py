import hashlib
import json
from pathlib import Path

import pytest

from workbench_service.research_builder import ResearchBuildError, _market_universe_metadata_path


def _write_bundle(root, bundle_id="bundle-1", content=b"industry-membership"):
    relative_root = "data/input_staging/metadata/20260916/meta-1"
    metadata_file = root / relative_root / "T0002/hq_cache/tdxhy.cfg"
    metadata_file.parent.mkdir(parents=True)
    metadata_file.write_bytes(content)
    bundle_dir = root / "data/source_bundles" / bundle_id
    bundle_dir.mkdir(parents=True)
    bundle = {
        "source_bundle_id": bundle_id,
        "metadata": {
            "root": relative_root,
            "files": {
                "T0002/hq_cache/tdxhy.cfg": {
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            },
        },
    }
    (bundle_dir / "source_bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    return metadata_file


def test_research_builder_uses_versioned_metadata_root_from_source_bundle(tmp_path):
    expected = _write_bundle(tmp_path)

    resolved = _market_universe_metadata_path(tmp_path, "bundle-1", "2026-09-16")

    assert resolved == expected.resolve()


def test_research_builder_fails_closed_on_metadata_hash_mismatch(tmp_path):
    metadata_file = _write_bundle(tmp_path)
    metadata_file.write_bytes(b"changed")

    with pytest.raises(ResearchBuildError, match="MARKET_UNIVERSE_SOURCE_HASH_MISMATCH"):
        _market_universe_metadata_path(tmp_path, "bundle-1", "2026-09-16")


def test_v3_page_renders_the_service_error_instead_of_generic_log_message():
    script = (Path(__file__).resolve().parents[2] / "src/workbench_service/static/v2/v3-unified.js").read_text(encoding="utf-8")

    assert "job.progress && job.progress.error" in script

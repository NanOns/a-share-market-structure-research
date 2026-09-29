"""Verify sealed Git/LFS artifact identities and unchanged accepted heads."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_CANDIDATE_MANIFEST_R2.json"
OUT = ROOT / "reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_SEAL_POSTCHECK_R2.json"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for path, ref in manifest["artifacts"].items():
        if "source_commit" in ref:
            data = subprocess.check_output(["git", "show", f"{ref['source_commit']}:{path}"], cwd=ROOT)
            assert sha256(data).hexdigest() == ref["git_blob_content_sha256"], path
            assert len(data) == ref["git_blob_bytes"], path
            if "lfs_object_sha256" in ref:
                assert f"oid sha256:{ref['lfs_object_sha256']}".encode() in data, path
                assert f"size {ref['lfs_object_bytes']}".encode() in data, path
                h = sha256()
                with (ROOT / path).open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(chunk)
                assert h.hexdigest() == ref["lfs_object_sha256"], path
        else:
            content = (ROOT / path).read_bytes()
            assert sha256(content).hexdigest() == ref["sha256"], path
            assert len(content) == ref["bytes"], path
    for path, expected in manifest["accepted_head_sha256"].items():
        assert sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert manifest["status"] == "V4_02_GO_FORWARD_PIT_ADJUSTMENT_AMENDMENT_CANDIDATE_R2"
    assert manifest["external_acceptance"] == "PENDING" and manifest["v4_05_r2"] == "NOT_STARTED"
    result = {"contract_id": "V4_02_GO_FORWARD_PIT_AMENDMENT_SEAL_POSTCHECK_R2", "status": "PASS",
              "artifact_count": len(manifest["artifacts"]),
              "manifest_sha256": sha256(MANIFEST.read_bytes()).hexdigest(),
              "lfs_package_oid_verified": manifest["package_sha256"],
              "accepted_heads_unchanged": True,
              "external_acceptance": "PENDING", "tdx_root_write_count": 0}
    OUT.write_bytes((json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())
    print("SEAL_POSTCHECK_PASS", result["artifact_count"])


if __name__ == "__main__":
    main()

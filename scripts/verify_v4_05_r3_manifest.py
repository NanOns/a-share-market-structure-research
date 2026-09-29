"""Verify every sealed R3 artifact byte identity before upload."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05"


def main():
    manifest = json.loads((OUT / "V4_05_R3_STAGE_CANDIDATE_MANIFEST.json").read_text(encoding="utf-8"))
    for name, ref in manifest["artifacts"].items():
        path = OUT / name
        if not path.is_file() or path.stat().st_size != ref["byte_count"]:
            raise ValueError(f"missing/size mismatch: {name}")
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
        if h.hexdigest() != ref["sha256"]:
            raise ValueError(f"SHA mismatch: {name}")
    if manifest["status"] != "V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R3" or manifest["external_acceptance"] != "PENDING":
        raise ValueError("candidate status mismatch")
    print("PASS", len(manifest["artifacts"]))


if __name__ == "__main__":
    main()

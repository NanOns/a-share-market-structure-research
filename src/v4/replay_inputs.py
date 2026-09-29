"""Hash-bound V4-05 inputs resolved through the promoted V4-04 Accepted Head."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path


@dataclass(frozen=True)
class ReplayInput:
    path: Path
    sha256: str
    contract_id: str


def _hash(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _verified(root: Path, ref: dict) -> Path:
    path = (root / ref["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or _hash(path) != ref["sha256"]:
        raise ValueError(f"accepted replay input identity mismatch: {ref['path']}")
    return path


def resolve(root: Path) -> tuple[dict[str, ReplayInput], dict]:
    root = root.resolve()
    stage = json.loads((root / "data/v4/V4_STAGE_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    if (stage.get("v4_04_status") != "FULL_PASS_REQUIRED_SCOPE" or
            stage.get("v4_04_external_acceptance") != "EXTERNALLY_ACCEPTED" or
            stage.get("v4_05_entry") != "AUTHORIZED_REPLAY_GATE_A"):
        raise ValueError("V4-05 entry authority missing")
    head_path = _verified(root, stage["v4_04_binding"])
    head = json.loads(head_path.read_text(encoding="utf-8"))
    if head["status"] != "FULL_PASS_REQUIRED_SCOPE" or head["external_acceptance"] != "EXTERNALLY_ACCEPTED":
        raise ValueError("V4-04 Accepted Head status mismatch")
    manifest = json.loads(_verified(root, head["accepted_manifest"]).read_text(encoding="utf-8"))
    production = json.loads(_verified(root, manifest["evidence"]["production"]).read_text(encoding="utf-8"))
    if production["artifact"] != head["accepted_artifact"]:
        raise ValueError("accepted profile and production receipt diverge")
    profile_path = _verified(root, head["accepted_artifact"])
    inputs = {name: ReplayInput(_verified(root, ref), ref["sha256"], ref["contract_id"])
              for name, ref in production["sources"].items()}
    archive_ref = stage["bindings"]["tdx_archive"]
    inputs["tdx_archive"] = ReplayInput(_verified(root, archive_ref), archive_ref["sha256"], "V4_00_ACCEPTED_TDX_ARCHIVE")
    inputs["profile"] = ReplayInput(profile_path, head["accepted_artifact"]["sha256"], "V4_04_ACCEPTED_FULL_MARKET_CORE_PROFILE")
    return inputs, {"global_head_sha256": _hash(root / "data/v4/V4_STAGE_ACCEPTED_HEAD.json"),
                    "v4_04_accepted_head_sha256": stage["v4_04_binding"]["sha256"],
                    "v4_04_implementation_commit": head["implementation_commit"],
                    "r4_manifest_sha256": head["accepted_manifest"]["sha256"],
                    "source_cutoff": head["source_cutoff"]}

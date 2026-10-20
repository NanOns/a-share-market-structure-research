from pathlib import Path
from copy import deepcopy
import hashlib, json
import pytest
from workbench_analysis import historical_stage_governance_r17 as governance

ROOT = Path(__file__).resolve().parents[1]
TARGET = {
    "path": "scripts/validate_v4_12_r11_chain.py",
    "bytes": 9383,
    "sha256": "ab76426fba950a58ba4a38ae144084801082d784e508c1985120f00a5c1a167d",
}


def test_old_accepted_validator_resolves_exact_archive_while_current_code_evolves():
    row = next(r for r in governance.registry(ROOT)["static_byte_archives"]
               if r["original_namespace"] == TARGET)
    resolved = governance.accepted_static_binding(ROOT, TARGET)
    assert resolved.read_bytes() == (ROOT / row["archive"]["path"]).read_bytes()
    current = (ROOT / TARGET["path"]).read_bytes()
    assert current != resolved.read_bytes()
    assert hashlib.sha256(resolved.read_bytes()).hexdigest() == TARGET["sha256"]


@pytest.mark.parametrize("mutation", ["archive", "origin", "registry"])
def test_r19_historical_static_archive_rejects_tampering_and_wrong_origin(tmp_path, monkeypatch, mutation):
    if mutation == "registry":
        registry_copy = tmp_path / governance.REGISTRY
        registry_copy.parent.mkdir(parents=True, exist_ok=True)
        registry_copy.write_bytes((ROOT / governance.REGISTRY).read_bytes() + b" ")
        with pytest.raises(governance.HistoricalBindingError):
            governance.registry(tmp_path)
        return
    book = deepcopy(governance.registry(ROOT))
    row = next(r for r in book["static_byte_archives"] if r["original_namespace"] == TARGET)
    destination = tmp_path / row["archive"]["path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes((ROOT / row["archive"]["path"]).read_bytes())
    monkeypatch.setattr(governance, "registry", lambda _root: book)
    original = governance.subprocess.check_output
    if mutation == "archive":
        destination.write_bytes(destination.read_bytes() + b"tamper")
    elif mutation == "origin":
        row["source_commit"] = "33b1949a1c05b0fe6c9068e6db9f219a9f113780"
    monkeypatch.setattr(governance.subprocess, "check_output", lambda args, **kwargs: original(args, cwd=ROOT))
    with pytest.raises(governance.HistoricalBindingError):
        governance.accepted_static_binding(tmp_path, TARGET)

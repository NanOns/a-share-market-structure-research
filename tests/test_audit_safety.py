from __future__ import annotations

from pathlib import Path

import pytest

from tdx.tdx_audit import atomic_write_json


def test_atomic_output_refuses_tdx_root(tmp_path: Path) -> None:
    tdx_root = tmp_path / "tdx"
    tdx_root.mkdir()
    with pytest.raises(ValueError, match="refusing to write"):
        atomic_write_json(tdx_root / "audit.json", {"ok": True}, tdx_root)


def test_atomic_output_outside_tdx_root(tmp_path: Path) -> None:
    tdx_root = tmp_path / "tdx"
    output = tmp_path / "project" / "audit.json"
    tdx_root.mkdir()
    atomic_write_json(output, {"ok": True}, tdx_root)
    assert output.read_text(encoding="utf-8").strip() == '{\n  "ok": true\n}'


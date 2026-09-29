from hashlib import sha256
import json
from pathlib import Path

import pytest

from src.v4 import accepted_input


ROOT = Path(__file__).resolve().parents[2]


def test_real_accepted_chain_resolves_expected_sources():
    sources = accepted_input.resolve(ROOT)
    assert set(sources) == {"daily", "weekly", "monthly", "calendar", "calendar_szse", "trading_status", "universe", "factors", "market_regime"}
    assert sources["factors"].sha256 == "9b6a1f16d90c2c5d08f1cc981edcceb737c29cab1792cad84bf25d62a7fd1e2e"


def test_hash_mismatch_fails_closed(tmp_path):
    path = tmp_path / "sample.json"
    path.write_text("{}", encoding="utf-8")
    good = sha256(path.read_bytes()).hexdigest()
    assert accepted_input._verify(tmp_path, "sample.json", good) == path
    path.write_text('{"changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        accepted_input._verify(tmp_path, "sample.json", good)


def test_cutoff_mismatch_fails_before_data_reads(monkeypatch):
    original = accepted_input._json

    def altered(root, relative, digest=None):
        payload = original(root, relative, digest)
        if relative == "data/v4/V4_02_ACCEPTED_HEAD.json":
            payload = dict(payload, source_cutoff="2026-09-25")
        return payload

    monkeypatch.setattr(accepted_input, "_json", altered)
    with pytest.raises(ValueError, match="cutoff mismatch"):
        accepted_input.resolve(ROOT)

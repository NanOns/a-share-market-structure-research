from __future__ import annotations

import hashlib
import json

from src.v4.canonical_governance_hash import (
    canonical_json_file_sha256,
    canonical_json_sha256,
    canonical_text_file_sha256,
)


def test_canonical_json_identity_ignores_lf_crlf_and_object_key_order(tmp_path):
    value = {"trade_date": "2026-09-28", "nested": {"b": 2, "a": 1}}
    lf = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    crlf = lf.replace("\n", "\r\n")
    a, b = tmp_path / "lf.json", tmp_path / "crlf.json"
    a.write_bytes(lf.encode("utf-8"))
    b.write_bytes(crlf.encode("utf-8"))

    assert hashlib.sha256(a.read_bytes()).hexdigest() != hashlib.sha256(b.read_bytes()).hexdigest()
    assert canonical_json_file_sha256(a) == canonical_json_file_sha256(b)
    assert canonical_json_file_sha256(a) == canonical_json_sha256(value)
    downstream_a = canonical_json_sha256({"accepted_head_sha256": canonical_json_file_sha256(a), "source": "frozen"})
    downstream_b = canonical_json_sha256({"accepted_head_sha256": canonical_json_file_sha256(b), "source": "frozen"})
    assert downstream_a == downstream_b


def test_canonical_text_identity_normalizes_crlf(tmp_path):
    lf, crlf = tmp_path / "lf.md", tmp_path / "crlf.md"
    lf.write_bytes("stage\nacceptance\n".encode())
    crlf.write_bytes("stage\r\nacceptance\r\n".encode())
    assert canonical_text_file_sha256(lf) == canonical_text_file_sha256(crlf)


def test_canonical_json_identity_rejects_non_json_numbers():
    try:
        canonical_json_sha256({"not_finite": float("nan")})
    except ValueError:
        pass
    else:
        raise AssertionError("canonical JSON identity accepted NaN")

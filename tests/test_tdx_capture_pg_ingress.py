import hashlib
import json

from scripts import capture_tdx_official_daily_package as capture
from workbench_db import v4_historical_source_ingress_pg_r1 as ingress


def test_capture_evidence_is_verified_and_read_back_from_pg(monkeypatch, tmp_path):
    capture_dir = tmp_path / "dynamic" / "tdx" / "20261008" / "capture-test"
    capture_dir.mkdir(parents=True)
    page = b"<html>tdx</html>"
    info = b'HSJDAY_SOFT_TIME="2026-10-16 15:58:46";'
    (capture_dir / "page.html").write_bytes(page)
    (capture_dir / "update_info.js").write_bytes(info)
    result = {
        "target_date": "2026-10-08",
        "receipt_path": str(capture_dir / "capture_receipt.json"),
        "page_html_path": str(capture_dir / "page.html"),
        "page_sha256": hashlib.sha256(page).hexdigest(),
        "update_info_path": str(capture_dir / "update_info.js"),
        "update_info_sha256": hashlib.sha256(info).hexdigest(),
    }
    (capture_dir / "capture_receipt.json").write_text(json.dumps(result), encoding="utf-8")
    captured = {}

    def ingest(root, path, raw, *, source_revision, source_origin):
        captured[path] = raw
        return {"source_path": path, "source_sha256": hashlib.sha256(raw).hexdigest(),
                "source_bytes": len(raw)}

    def read_bound(root, path, sha):
        raw = captured[path]
        assert hashlib.sha256(raw).hexdigest() == sha
        return {"raw": raw, "record": {"source_path": path,
                "source_sha256": sha, "source_bytes": len(raw)}}

    monkeypatch.setattr(ingress, "ingest_captured_bytes", ingest)
    monkeypatch.setattr(ingress, "read_bound", read_bound)
    bindings = capture._ingest_capture_evidence(result, root=tmp_path)

    assert set(bindings) == {"page.html", "update_info.js", "capture_receipt.json"}
    assert bindings["page.html"]["path"].endswith("/page.html")
    assert bindings["update_info.js"]["sha256"] == hashlib.sha256(info).hexdigest()
    assert bindings["capture_receipt.json"]["bytes"] > 0


def test_capture_evidence_rejects_page_digest_drift(tmp_path):
    capture_dir = tmp_path / "dynamic" / "capture-test"
    capture_dir.mkdir(parents=True)
    (capture_dir / "page.html").write_bytes(b"changed")
    (capture_dir / "update_info.js").write_bytes(b"info")
    (capture_dir / "capture_receipt.json").write_text("{}", encoding="utf-8")
    result = {"target_date": "2026-10-08", "receipt_path": str(capture_dir / "capture_receipt.json"),
              "page_html_path": str(capture_dir / "page.html"), "page_sha256": "0" * 64,
              "update_info_path": str(capture_dir / "update_info.js"),
              "update_info_sha256": hashlib.sha256(b"info").hexdigest()}

    try:
        capture._ingest_capture_evidence(result, root=tmp_path)
    except ValueError as exc:
        assert str(exc) == "TDX_CAPTURE_EVIDENCE_DIGEST_MISMATCH:page.html"
    else:
        raise AssertionError("changed TDX capture bytes must not enter SourceIngress")

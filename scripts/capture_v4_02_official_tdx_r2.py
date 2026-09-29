"""Bounded, diagnostic official TDX capture for the Sep-28 amendment."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.tdx_official_daily_source import (  # noqa: E402
    PAGE_URL, _request, _read_bounded, _zip_validate, discover_download_url,
    discover_update_info_url, parse_update_date, validate_official_url,
)

OUT = ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json"
BASE = ROOT / "data/v4/source_snapshots/tdx/20260928"
MAX_BYTES = 1024 * 1024 * 1024


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save(value: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, OUT)


def endpoints() -> tuple[str, bytes, bytes, str]:
    with _request(PAGE_URL, timeout=60) as response:
        page = _read_bounded(response, 4 * 1024 * 1024)
    package = discover_download_url(page)
    info_url = discover_update_info_url(page, package)
    with _request(info_url, timeout=60) as response:
        info = _read_bounded(response, 256 * 1024)
    update_date, update_time = parse_update_date(info)
    return package, page, info, f"{update_date} {update_time}"


def file_diag(path: Path) -> dict:
    if not path.exists():
        return {"actual_byte_count": 0, "sha256_if_complete": None,
                "first_64_bytes_hex": "", "last_128_bytes_hex": "",
                "zip_magic_check": False, "zip_is_zipfile": False}
    h = sha256()
    first = b""
    tail = b""
    total = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            if not first:
                first = chunk[:64]
            tail = (tail + chunk)[-128:]
            total += len(chunk)
            h.update(chunk)
    return {"actual_byte_count": total, "sha256_if_complete": h.hexdigest(),
            "first_64_bytes_hex": first.hex(), "last_128_bytes_hex": tail.hex(),
            "zip_magic_check": first.startswith(b"PK\x03\x04"),
            "zip_is_zipfile": zipfile.is_zipfile(path)}


def python_attempt(url: str, path: Path, number: int) -> dict:
    began = time.monotonic()
    record = {"attempt_id": f"python-{number}", "method": "PYTHON_URLLIB", "started_at": stamp(),
              "requested_url": url, "final_url": None, "http_status": None, "http_headers": {},
              "failure_reason": None}
    try:
        with _request(url, timeout=180) as response, path.open("wb") as stream:
            final = str(response.geturl())
            validate_official_url(final)
            record["final_url"] = final
            record["http_status"] = response.getcode()
            record["http_headers"] = {key: response.headers.get(key) for key in
                                      ("Content-Type", "Content-Length", "ETag", "Last-Modified", "Content-Disposition")}
            if record["http_status"] != 200:
                raise ValueError("HTTP_STATUS_NOT_200")
            total = 0
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError("PACKAGE_SIZE_LIMIT")
                stream.write(chunk)
        length = record["http_headers"].get("Content-Length")
        if length and length.isdigit() and int(length) != path.stat().st_size:
            raise ValueError("CONTENT_LENGTH_MISMATCH")
        if not zipfile.is_zipfile(path):
            raise ValueError("TDX_ZIP_INVALID")
        record["zip_validation"] = _zip_validate(path)
    except Exception as exc:
        record["failure_reason"] = f"{type(exc).__name__}:{exc}"
    record.update(file_diag(path))
    record["finished_at"] = stamp()
    record["elapsed_seconds"] = round(time.monotonic() - began, 3)
    if record["failure_reason"]:
        path.unlink(missing_ok=True)
    return record


def curl_attempt(url: str, path: Path) -> dict:
    began = time.monotonic()
    headers = path.with_suffix(".headers")
    command = ["curl.exe", "--fail", "--show-error", "--silent", "--retry", "5", "--retry-all-errors",
               "--retry-delay", "2", "--connect-timeout", "30", "--max-time", "1800",
               "--max-redirs", "0", "--proto", "=https", "--referer", PAGE_URL,
               "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
               "--dump-header", str(headers), "--output", str(path), "--write-out", "%{http_code} %{url_effective}", url]
    record = {"attempt_id": "curl-1", "method": "WINDOWS_CURL", "started_at": stamp(),
              "requested_url": url, "exact_command": command, "failure_reason": None}
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=1900)
        fields = done.stdout.strip().split(" ", 1)
        record["http_status"] = fields[0] if fields else None
        record["final_url"] = fields[1] if len(fields) == 2 else None
        if record["final_url"]:
            validate_official_url(record["final_url"])
        blocks = headers.read_text(encoding="iso-8859-1").split("\r\n\r\n") if headers.exists() else []
        lines = blocks[-1].splitlines() if blocks else []
        parsed = {line.split(":", 1)[0].lower(): line.split(":", 1)[1].strip() for line in lines if ":" in line}
        record["http_headers"] = {key: parsed.get(key.lower()) for key in
                                  ("Content-Type", "Content-Length", "ETag", "Last-Modified", "Content-Disposition")}
        if done.returncode or record["http_status"] != "200":
            raise ValueError(f"CURL_EXIT_{done.returncode}:HTTP_{record['http_status']}:{done.stderr[-250:]}")
        length = record["http_headers"].get("Content-Length")
        if length and length.isdigit() and int(length) != path.stat().st_size:
            raise ValueError("CONTENT_LENGTH_MISMATCH")
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("PACKAGE_SIZE_LIMIT")
        if not zipfile.is_zipfile(path):
            raise ValueError("TDX_ZIP_INVALID")
        record["zip_validation"] = _zip_validate(path)
    except Exception as exc:
        record["failure_reason"] = f"{type(exc).__name__}:{exc}"
    record.update(file_diag(path))
    record["finished_at"] = stamp()
    record["elapsed_seconds"] = round(time.monotonic() - began, 3)
    headers.unlink(missing_ok=True)
    if record["failure_reason"]:
        path.unlink(missing_ok=True)
    return record


def main() -> None:
    url, page, info, published = endpoints()
    BASE.mkdir(parents=True, exist_ok=True)
    snapshot = BASE / f"r2-metadata-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    snapshot.mkdir()
    (snapshot / "page.html").write_bytes(page)
    (snapshot / "update_info.js").write_bytes(info)
    result = {"contract_id": "V4_02_GO_FORWARD_TDX_CAPTURE_R2", "target_trade_date": "2026-09-28",
              "official_publication_time": published, "requested_url": url,
              "metadata_paths": [str((snapshot / name).relative_to(ROOT)).replace("\\", "/") for name in ("page.html", "update_info.js")],
              "metadata_sha256": {name: sha256(data).hexdigest() for name, data in (("page.html", page), ("update_info.js", info))},
              "attempts": [], "tdx_root_write_count": 0}
    if not published.startswith("2026-09-28 "):
        result["status"] = "V4_02_GO_FORWARD_BLOCKED_20260928_OFFICIAL_PACKAGE_ROLLED_FORWARD"
        save(result)
        print(result["status"])
        return
    for number in (1, 2):
        path = snapshot / f"python-{number}.part"
        attempt = python_attempt(url, path, number)
        result["attempts"].append(attempt)
        save(result)
        if not attempt["failure_reason"]:
            break
        time.sleep(2 ** (number - 1))
    if result["attempts"][-1]["failure_reason"]:
        path = snapshot / "curl-1.part"
        attempt = curl_attempt(url, path)
        result["attempts"].append(attempt)
        save(result)
    final = result["attempts"][-1]
    if final["failure_reason"]:
        result["status"] = "V4_02_GO_FORWARD_BLOCKED_OFFICIAL_DOWNLOAD_ENVIRONMENT"
    else:
        digest = final["sha256_if_complete"]
        store = BASE / f"sha256-{digest}"
        store.mkdir(exist_ok=True)
        frozen = store / "hsjday.zip"
        if frozen.exists():
            if file_diag(frozen)["sha256_if_complete"] != digest:
                raise ValueError("IMMUTABLE_PACKAGE_COLLISION")
            path.unlink(missing_ok=True)
        else:
            os.replace(path, frozen)
        for name, data in (("page.html", page), ("update_info.js", info)):
            target = store / name
            if target.exists() and sha256(target.read_bytes()).digest() != sha256(data).digest():
                raise ValueError(f"IMMUTABLE_METADATA_COLLISION:{name}")
            if not target.exists():
                target.write_bytes(data)
        result["status"] = "TDX_PACKAGE_READY"
        result["package_sha256"] = digest
        result["package_path"] = str((store / "hsjday.zip").relative_to(ROOT)).replace("\\", "/")
    save(result)
    if result["status"] == "TDX_PACKAGE_READY":
        store = BASE / f"sha256-{result['package_sha256']}"
        manifest = {"contract_id": "V4_02_GO_FORWARD_TDX_IMMUTABLE_PACKAGE_R2",
                    "snapshot_id": store.name, "target_trade_date": "2026-09-28",
                    "package_sha256": result["package_sha256"],
                    "package_bytes": final["actual_byte_count"],
                    "zip_validation": final["zip_validation"],
                    "official_publication_time": published,
                    "project_capture_available_at": final["finished_at"],
                    "tdx_root_write_count": 0}
        for name, payload in (("package_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"),
                              ("capture_receipt.json", OUT.read_bytes())):
            target = store / name
            if target.exists() and target.read_bytes() != payload:
                raise ValueError(f"IMMUTABLE_RECEIPT_COLLISION:{name}")
            if not target.exists():
                target.write_bytes(payload)
    print(result["status"])


if __name__ == "__main__":
    main()

from __future__ import annotations

"""Read-only capture of the official TDX daily package and its publication date."""

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Mapping

from workbench_analysis.daily_source_freeze import ensure_outside_tdx


PAGE_URL = "https://www.tdx.com.cn/article/vipdata.html"
ALLOWED_HOSTS = frozenset({"www.tdx.com.cn", "data.tdx.com.cn"})
DEFAULT_MAX_PAGE_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_INFO_BYTES = 256 * 1024
DEFAULT_MAX_PACKAGE_BYTES = 1024 * 1024 * 1024
MAX_ZIP_ENTRIES = 100_000
MAX_ZIP_ENTRY_BYTES = 128 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 5 * 1024 * 1024 * 1024
COPY_CHUNK_BYTES = 1024 * 1024


class TDXSourceError(ValueError):
    pass


class _AllowlistedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        validate_official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_official_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username
            or parsed.password or parsed.port not in (None, 443)):
        raise TDXSourceError("TDX_URL_OUTSIDE_OFFICIAL_ALLOWLIST")
    return url


def _request(url: str, *, timeout: int = 30) -> Any:
    validate_official_url(url)
    opener = urllib.request.build_opener(_AllowlistedRedirect())
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Referer": PAGE_URL,
        "Accept": "text/html,application/javascript,application/zip,*/*;q=0.5",
        "Cache-Control": "no-cache, max-age=0",
        "Pragma": "no-cache",
    })
    return opener.open(request, timeout=timeout)


def _read_bounded(response: Any, limit: int) -> bytes:
    chunks, total = [], 0
    while True:
        chunk = response.read(min(COPY_CHUNK_BYTES, limit + 1 - total))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise TDXSourceError("TDX_RESPONSE_SIZE_LIMIT_EXCEEDED")
        chunks.append(chunk)
    return b"".join(chunks)


def _header(response: Any, name: str) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    try:
        value = headers.get(name)
    except AttributeError:
        value = None
    return str(value) if value is not None else None


def discover_download_url(page_html: bytes, page_url: str = PAGE_URL) -> str:
    """Resolve the package link from the page markup; no package URL is embedded."""
    text = page_html.decode("utf-8", "replace")
    links = re.findall(r"\bhref\s*=\s*['\"]([^'\"]+\.zip(?:\?[^'\"]*)?)['\"]", text, re.I)
    candidates = []
    for link in links:
        absolute = urllib.parse.urljoin(page_url, html.unescape(link).strip())
        try:
            validate_official_url(absolute)
        except TDXSourceError:
            continue
        candidates.append(absolute)
    unique = list(dict.fromkeys(candidates))
    if len(unique) != 1:
        raise TDXSourceError("TDX_OFFICIAL_PACKAGE_LINK_NOT_UNIQUE")
    return unique[0]


def discover_update_info_url(page_html: bytes, package_url: str) -> str:
    """Find the page's update-info script reference, then resolve its base URL."""
    text = page_html.decode("utf-8", "replace")
    match = re.search(r"getScript\(\s*['\"]([^'\"]*_hsjdayinfo\.js)", text, re.I)
    if match:
        reference = match.group(1)
        if reference.startswith("//"):
            reference = "https:" + reference
        elif reference.startswith("/"):
            reference = urllib.parse.urljoin(PAGE_URL, reference)
        else:
            reference = urllib.parse.urljoin(PAGE_URL, reference)
    else:
        # Official markup can omit the inline JS temporarily. Resolve the
        # metadata file from the page-discovered package directory in that case.
        parsed = urllib.parse.urlparse(package_url)
        reference = urllib.parse.urlunparse((parsed.scheme, parsed.netloc,
                                             str(Path(parsed.path).parent).replace("\\", "/") + "/_hsjdayinfo.js",
                                             "", "", ""))
    validate_official_url(reference)
    return reference


def parse_update_date(info_js: bytes) -> tuple[str | None, str | None]:
    text = info_js.decode("ascii", "replace")
    match = re.search(r"HSJDAY_SOFT_TIME\s*=\s*['\"](\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}:\d{2}))?['\"]", text)
    if not match:
        raise TDXSourceError("TDX_UPDATE_DATE_MISSING_FROM_OFFICIAL_METADATA")
    try:
        date.fromisoformat(match.group(1))
    except ValueError as exc:
        raise TDXSourceError("TDX_UPDATE_DATE_INVALID") from exc
    return match.group(1), match.group(2)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(COPY_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, data: bytes, *, tdx_root: Path) -> None:
    ensure_outside_tdx(path, tdx_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except Exception:
        Path(name).unlink(missing_ok=True)
        raise


def _zip_validate(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                raise TDXSourceError("TDX_ZIP_ENTRY_COUNT_LIMIT_EXCEEDED")
            total = 0
            names: set[str] = set()
            day_markets: set[str] = set()
            for info in infos:
                name = info.filename.replace("\\", "/")
                parts = name.split("/")
                unix_mode = (info.external_attr >> 16) & 0xFFFF
                if (name.startswith("/") or re.match(r"^[a-zA-Z]:", name)
                        or any(part in {".", ".."} for part in parts)
                        or (unix_mode & 0o170000) == 0o120000):
                    raise TDXSourceError("TDX_ZIP_UNSAFE_ENTRY_PATH")
                if name.casefold() in names:
                    raise TDXSourceError("TDX_ZIP_DUPLICATE_ENTRY_PATH")
                names.add(name.casefold())
                if info.file_size > MAX_ZIP_ENTRY_BYTES:
                    raise TDXSourceError("TDX_ZIP_ENTRY_SIZE_LIMIT_EXCEEDED")
                if info.file_size > max(info.compress_size, 1) * 250:
                    raise TDXSourceError("TDX_ZIP_COMPRESSION_RATIO_LIMIT_EXCEEDED")
                total += info.file_size
                if total > MAX_ZIP_TOTAL_BYTES:
                    raise TDXSourceError("TDX_ZIP_TOTAL_SIZE_LIMIT_EXCEEDED")
                if name.lower().endswith(".day"):
                    market_parts = [part.lower() for part in parts if part]
                    if market_parts and market_parts[0] in {"sh", "sz", "bj"}:
                        day_markets.add(market_parts[0])
                    elif len(market_parts) >= 3 and market_parts[1] in {"sh", "sz", "bj"}:
                        day_markets.add(market_parts[1])
            if not {"sh", "sz"}.issubset(day_markets):
                raise TDXSourceError("TDX_ZIP_REQUIRED_MARKET_DAILY_ENTRIES_MISSING")
            bad_entry = archive.testzip()
            if bad_entry is not None:
                raise TDXSourceError("TDX_ZIP_CRC_FAILURE")
            return {
                "status": "PASS",
                "entry_count": len(infos),
                "uncompressed_bytes": total,
                "day_entry_markets": sorted(day_markets),
                "crc_integrity": "PASS",
            }
    except zipfile.BadZipFile as exc:
        raise TDXSourceError("TDX_ZIP_INVALID") from exc


def _stream_download(url: str, destination: Path, *, max_bytes: int, timeout: int,
                     tdx_root: Path) -> tuple[str, int, dict[str, str | None]]:
    digest = hashlib.sha256()
    total = 0
    ensure_outside_tdx(destination, tdx_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = _request(url, timeout=timeout)
    try:
        final_url = validate_official_url(str(response.geturl()))
        headers = {name: _header(response, name) for name in ("ETag", "Last-Modified", "Content-Disposition", "Content-Length")}
        expected_length = headers.get("Content-Length")
        if expected_length and expected_length.isdigit() and int(expected_length) > max_bytes:
            raise TDXSourceError("TDX_PACKAGE_SIZE_LIMIT_EXCEEDED")
        fd, temp_name = tempfile.mkstemp(prefix="tdx-package-", suffix=".part", dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                while True:
                    chunk = response.read(COPY_CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise TDXSourceError("TDX_PACKAGE_SIZE_LIMIT_EXCEEDED")
                    digest.update(chunk)
                    stream.write(chunk)
                if expected_length and expected_length.isdigit() and total != int(expected_length):
                    raise TDXSourceError("TDX_PACKAGE_CONTENT_LENGTH_MISMATCH")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, destination)
        except Exception:
            Path(temp_name).unlink(missing_ok=True)
            raise
        return final_url, total, {**headers, "sha256": digest.hexdigest()}
    finally:
        response.close()


def _existing_downloader_package(target_date: str, package_url: str, *, max_bytes: int) -> tuple[Path, dict[str, Any]]:
    """Delegate challenge handling to the already accepted R3 downloader.

    A recent receipt can be shared only after a fresh caller publication check;
    byte and date bindings are verified again rather than trusting its pointer.
    """
    root = Path(__file__).resolve().parents[2]
    pointer = root / 'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json'

    def verified() -> tuple[Path, dict[str, Any]]:
        ref = json.loads(pointer.read_bytes())['capture_receipt']
        receipt_path = (root / ref['path']).resolve()
        receipt_path.relative_to(root / 'data/v4/source_evidence/dm01_a01_r3/tdx')
        if sha256_file(receipt_path) != ref['sha256']:
            raise TDXSourceError('TDX_EXISTING_RECEIPT_DIGEST_MISMATCH')
        receipt = json.loads(receipt_path.read_bytes())
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(receipt['observed_at'])).total_seconds()
        if not 0 <= age <= 3600 or receipt['official_publication_date'] != target_date:
            raise TDXSourceError('TDX_EXISTING_RECEIPT_NOT_CURRENT')
        if receipt['status'] != 'PASS_OFFICIAL_ZIP':
            raise TDXSourceError('TDX_EXISTING_DOWNLOADER_NOT_READY')
        successful = next(a for a in receipt['attempts'] if a.get('ZIP_valid'))
        if successful['url'] != package_url or receipt['request_count'] > receipt['request_limit']:
            raise TDXSourceError('TDX_EXISTING_DOWNLOADER_SCOPE_MISMATCH')
        binding = receipt['package']
        package = (root / binding['path']).resolve()
        package.relative_to(receipt_path.parent)
        if (package.stat().st_size != binding['bytes'] or binding['bytes'] > max_bytes
                or sha256_file(package) != binding['sha256']):
            raise TDXSourceError('TDX_EXISTING_PACKAGE_BINDING_MISMATCH')
        return package, {'capture_receipt': ref, 'package': binding,
                         'adapter_contract': 'TDX_EXISTING_R3_DOWNLOADER_ADAPTER_V1',
                         'knowledge_lineage': receipt['knowledge_lineage']}

    try:
        return verified()
    except (OSError, KeyError, ValueError, StopIteration):
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B',
                                 str(root / 'scripts/capture_dm01_a01_r3_tdx_package.py')],
                                cwd=root, capture_output=True, timeout=480)
        if result.returncode:
            raise TDXSourceError('TDX_EXISTING_DOWNLOADER_EXECUTION_FAILED')
        return verified()


def capture_tdx_official_daily_package(
    *,
    target_date: str,
    snapshot_root: Path,
    tdx_root: Path = Path("D:/new_tdx"),
    timeout: int = 30,
    max_page_bytes: int = DEFAULT_MAX_PAGE_BYTES,
    max_info_bytes: int = DEFAULT_MAX_INFO_BYTES,
    max_package_bytes: int = DEFAULT_MAX_PACKAGE_BYTES,
) -> dict[str, Any]:
    """Capture official page evidence and download only when its date is target."""
    try:
        date.fromisoformat(target_date)
    except ValueError as exc:
        raise TDXSourceError("TARGET_DATE_INVALID") from exc
    ensure_outside_tdx(snapshot_root, tdx_root)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    response = _request(PAGE_URL, timeout=timeout)
    try:
        page_final_url = validate_official_url(str(response.geturl()))
        page_headers = {name: _header(response, name) for name in ("ETag", "Last-Modified", "Content-Type")}
        page_html = _read_bounded(response, max_page_bytes)
    finally:
        response.close()
    package_url = discover_download_url(page_html, page_final_url)
    info_url = discover_update_info_url(page_html, package_url)
    parsed_info = urllib.parse.urlparse(info_url)
    query = urllib.parse.parse_qsl(parsed_info.query, keep_blank_values=True)
    query.append(("t", str(int(time.time() // 10))))
    info_url = urllib.parse.urlunparse(parsed_info._replace(query=urllib.parse.urlencode(query)))
    response = _request(info_url, timeout=timeout)
    try:
        info_final_url = validate_official_url(str(response.geturl()))
        info_headers = {name: _header(response, name) for name in ("ETag", "Last-Modified", "Content-Type")}
        info_js = _read_bounded(response, max_info_bytes)
    finally:
        response.close()
    update_date, update_time = parse_update_date(info_js)
    page_sha, info_sha = sha256_bytes(page_html), sha256_bytes(info_js)
    snapshot_key = hashlib.sha256(f"{target_date}\0{page_sha}\0{info_sha}".encode()).hexdigest()
    capture_id = "capture-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ-") + snapshot_key[:16]
    capture_dir = snapshot_root / "tdx" / target_date.replace("-", "") / capture_id
    ensure_outside_tdx(capture_dir, tdx_root)
    capture_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(capture_dir / "page.html", page_html, tdx_root=tdx_root)
    _atomic_write(capture_dir / "update_info.js", info_js, tdx_root=tdx_root)
    receipt: dict[str, Any] = {
        "contract_id": "TDX_OFFICIAL_DAILY_PACKAGE_SOURCE_V1",
        "version": "1.0.0",
        "target_date": target_date,
        "status": "WAIT_TDX_PUBLICATION" if update_date != target_date else "TDX_PAGE_DATE_MATCHED",
        "observed_at": observed_at,
        "page_url": page_final_url,
        "page_http_metadata": page_headers,
        "page_html_path": str((capture_dir / "page.html").resolve()),
        "page_sha256": page_sha,
        "update_info_url": info_final_url,
        "update_info_http_metadata": info_headers,
        "update_info_path": str((capture_dir / "update_info.js").resolve()),
        "update_info_sha256": info_sha,
        "update_date": update_date,
        "update_time": update_time,
        "resolved_download_url": package_url,
        "downloaded_at": None,
        "download": None,
        "zip_validation": None,
        "snapshot_id": None,
        "tdx_root_write_count": 0,
    }
    if update_date == target_date:
        temporary_archive = capture_dir / "download.part"
        download_requested=datetime.now(timezone.utc).isoformat()
        final_url, byte_count, download_headers = _stream_download(
            package_url, temporary_archive, max_bytes=max_package_bytes, timeout=timeout, tdx_root=tdx_root
        )
        download_received=datetime.now(timezone.utc).isoformat()
        transport=dict(contract_id='SOURCE_REQUEST_RESPONSE_CLOCK_V2',requested_at=download_requested,received_at=download_received,
                       capture_method='DIRECT_VERIFIED_OFFICIAL_PACKAGE')
        try:
            validation = _zip_validate(temporary_archive)
        except Exception as exc:
            transport=None  # A challenge response's clock cannot date fallback package bytes.
            # Keep rejected response bytes outside TDX for diagnosis; an HTML
            # edge challenge is not evidence that the provider has no BARs.
            rejected = capture_dir / 'rejected_package_response.bin'
            os.replace(temporary_archive, rejected)
            receipt.update(status='REJECTED_INVALID_PACKAGE_RESPONSE',
                           error_type=type(exc).__name__, error=str(exc),
                           rejected_response=dict(path=str(rejected.resolve()), bytes=byte_count,
                               sha256=sha256_file(rejected), headers=download_headers, final_url=final_url))
            _atomic_write(capture_dir / 'capture_receipt.json', _json_bytes(receipt), tdx_root=tdx_root)
            challenge = rejected.read_bytes() if byte_count <= max_info_bytes else b''
            if not all(re.search(rb'\b' + key + rb':\d+', challenge)
                       for key in (b'WTKkN', b'bOYDu', b'wyeCN')):
                raise
            package, adapter = _existing_downloader_package(target_date, package_url, max_bytes=max_package_bytes)
            _atomic_write(capture_dir / 'rejected_response_receipt.json', _json_bytes(receipt), tdx_root=tdx_root)
            # The original rejected bytes and receipt remain diagnostic evidence.
            # Hard links share immutable source bytes outside the read-only TDX root.
            try:
                os.link(package, temporary_archive)
            except OSError:
                shutil.copyfile(package, temporary_archive)
            byte_count = package.stat().st_size
            download_headers = {'sha256': adapter['package']['sha256']}
            validation = _zip_validate(temporary_archive)
            receipt['existing_downloader'] = adapter
            receipt.pop('error', None)
            receipt.pop('error_type', None)
        package_sha = download_headers.pop("sha256")
        snapshot_id = f"sha256-{package_sha}"
        package_dir = snapshot_root / "tdx" / target_date.replace("-", "") / snapshot_id
        ensure_outside_tdx(package_dir, tdx_root)
        package_dir.mkdir(parents=True, exist_ok=True)
        archive_path = package_dir / "hsjday.zip"
        already_frozen = archive_path.exists()
        if already_frozen:
            if sha256_file(archive_path) != package_sha:
                raise TDXSourceError("TDX_IMMUTABLE_SNAPSHOT_COLLISION")
            temporary_archive.unlink(missing_ok=True)
        else:
            os.replace(temporary_archive, archive_path)
        for name in ("page.html", "update_info.js"):
            candidate = package_dir / name
            source = capture_dir / name
            if not candidate.exists():
                _atomic_write(candidate, source.read_bytes(), tdx_root=tdx_root)
        prior_revisions = [
            path for path in (snapshot_root / "tdx" / target_date.replace("-", "")).glob("sha256-*")
            if path != package_dir and (path / "hsjday.zip").is_file()
        ]
        prior_receipt = package_dir / "capture_receipt.json"
        if already_frozen and prior_receipt.is_file():
            revision_number = int(json.loads(prior_receipt.read_text(encoding="utf-8")).get("source_revision_number", 1))
        else:
            revision_number = len(prior_revisions) + 1
        receipt.update({
            "status": "NOOP_SOURCE_ALREADY_FROZEN" if already_frozen else "TDX_PACKAGE_READY",
            "downloaded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "download": {
                "final_url": final_url,
                "path": str(archive_path.resolve()),
                "bytes": byte_count,
                "sha256": package_sha,
                "http_metadata": download_headers,
            },
            "zip_validation": validation,
            "snapshot_id": snapshot_id,
            "source_revision_number": revision_number,
        })
        if transport is not None:
            receipt['source_transport_v2']=transport
        if not (package_dir / "capture_receipt.json").exists():
            _atomic_write(package_dir / "capture_receipt.json", _json_bytes(receipt), tdx_root=tdx_root)
        _atomic_write(capture_dir / "capture_receipt.json", _json_bytes(receipt), tdx_root=tdx_root)
        receipt["receipt_path"] = str((capture_dir / "capture_receipt.json").resolve())
    else:
        _atomic_write(capture_dir / "capture_receipt.json", _json_bytes(receipt), tdx_root=tdx_root)
        receipt["receipt_path"] = str((capture_dir / "capture_receipt.json").resolve())
    return receipt


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

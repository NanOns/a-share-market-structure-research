import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]
DB = ROOT / "data/database/market_research.duckdb"
PUBLICATION = "m4-8a99c99719061f4f1f166d0b9184506c"
SECURITY = "SZ.300010"


def _browser_executable():
    configured = os.environ.get("M12_BROWSER_EXECUTABLE")
    candidates = [
        configured,
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
        if candidate and shutil.which(candidate):
            return candidate
    return None


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def browser_page():
    playwright = pytest.importorskip("playwright.sync_api")
    executable = _browser_executable()
    if not executable:
        pytest.skip("Chrome/Edge executable is not available for browser behavior tests")
    port = _free_port()
    server_code = (
        "import sys; from pathlib import Path; "
        "sys.path.insert(0, str(Path(sys.argv[1]) / 'src')); "
        "from workbench_service.app import serve; "
        "serve(Path(sys.argv[1]), host='127.0.0.1', port=int(sys.argv[2]), database_path=Path(sys.argv[3]))"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", server_code, str(ROOT), str(port), str(DB)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        import urllib.request

        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/v2", timeout=1).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail("local workbench service did not start")
        browser = playwright.sync_playwright().start()
        instance = browser.chromium.launch(headless=True, executable_path=executable)
        page = instance.new_page(viewport={"width": 1440, "height": 1000})
        page._m12_browser = browser
        page._m12_instance = instance
        page._m12_base = base
        yield page
        instance.close()
        browser.stop()
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _route(base, tab):
    return f"{base}?publication_id={PUBLICATION}&security_id={SECURITY}&tab={tab}&days=20"


def test_browser_deeplink_escape_focus_and_route_cleanup(browser_page):
    page = browser_page
    page.goto(_route(page._m12_base + "/v2", "evidence"), wait_until="networkidle")
    page.get_by_text("证据摘要（5项）", exact=True).wait_for()
    assert page.locator(".modal-card").count() == 1
    assert page.locator(".modal-close").evaluate("node => document.activeElement === node")
    for _ in range(10):
        page.keyboard.press("Tab")
        assert page.locator(".modal-card").evaluate("node => node.contains(document.activeElement)")
    page.keyboard.press("Escape")
    page.locator(".modal-card").wait_for(state="detached")
    assert "security_id" not in page.url
    assert "tab=" not in page.url


def test_browser_evidence_details_are_collapsed_and_history_uses_days(browser_page):
    page = browser_page
    page.goto(_route(page._m12_base + "/v2", "evidence"), wait_until="networkidle")
    page.get_by_text("证据摘要（5项）", exact=True).wait_for()
    details = page.locator("details.evidence-details")
    assert details.count() >= 5
    assert all(not details.nth(index).get_attribute("open") for index in range(details.count()))
    page.goto(_route(page._m12_base + "/v2", "history"), wait_until="networkidle")
    page.get_by_text("历史图表（同一日期锚）", exact=True).wait_for()
    page.get_by_text("结构历史（最近20个交易日）", exact=True).wait_for()
    assert page.locator(".insight-chart-panel").count() == 1

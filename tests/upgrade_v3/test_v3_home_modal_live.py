import shutil
import urllib.request

import pytest


@pytest.mark.skipif(not shutil.which("chrome") and not shutil.which("msedge") and not shutil.which("C:/Program Files/Google/Chrome/Application/chrome.exe"), reason="browser unavailable")
def test_v3_home_modals_show_local_details():
    playwright = pytest.importorskip("playwright.sync_api")
    executable = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    try:
        urllib.request.urlopen("http://127.0.0.1:28765/v3", timeout=1).close()
    except OSError:
        pytest.skip("local V3 service is not running")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, executable_path=executable)
        try:
            page = browser.new_page()
            page.goto("http://127.0.0.1:28765/v3", wait_until="networkidle")
            page.locator("#v3-current-cards [data-v3-sector-id]").first.click()
            page.locator(".v3-member-table [data-detail-stock]").first.wait_for(timeout=10000)
            assert page.locator(".v3-member-table [data-detail-stock]").count() > 0
            page.locator(".modal-close").click()
            page.locator("#v3-current-focus [data-v3-security-id]").first.click()
            page.get_by_text("收盘价", exact=True).wait_for(timeout=10000)
            assert page.locator(".v3-detail-facts").count() == 1
            page.locator(".modal-close").click()
            page.locator("#v3-priority-stocks [data-priority-stock]").first.wait_for(timeout=10000)
            assert page.locator("#v3-priority-stocks [data-priority-stock]").count() == 25
            page.locator("[data-priority-next]").click()
            page.get_by_text("第 2 页", exact=False).first.wait_for(timeout=10000)
            assert page.locator("#v3-priority-stocks [data-priority-stock]").count() == 25
            page.locator("#v3-priority-stocks [data-priority-stock]").first.click()
            page.get_by_text("收盘价", exact=True).wait_for(timeout=10000)
        finally:
            browser.close()

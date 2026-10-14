"""Scoped display contracts; no production writes or scheduler changes."""
import json
import subprocess
from pathlib import Path
from contextlib import contextmanager
import pytest
from workbench_desktop.engine import EngineController

@pytest.mark.parametrize("state", ["RUNNING", "STOPPED", "FAILED"])
def test_startup_snapshot_is_explicitly_historical(tmp_path, monkeypatch, state):
    import workbench_desktop.engine as engine
    import workbench_db.v4_native as native
    monkeypatch.setattr(engine, "verify_resources", lambda: dict(build_release_id="test", source_sha="test", resource_manifest_sha="test", workspace_schema_version=1))
    class DB:
        def execute(self, *_): return self
        def fetchone(self): return (False,)
    @contextmanager
    def connection(*args, **kwargs):
        assert kwargs["read_only"] is True
        yield DB()
    monkeypatch.setattr(native, "connection", connection)
    controller=EngineController(tmp_path)
    controller.state=state
    controller.startup_snapshot=dict(context_token="old-token",context=dict(trade_date="2026-10-12"), captured_at="2026-10-14T00:00:00Z", startup_only=True)
    controller.shutdown_snapshot=dict(context_token="new-token")
    data=controller.status()
    assert data["cached_snapshot"] == data["startup_snapshot"]
    assert data["cached_snapshot_semantics"] == dict(startup_only=True,captured_at="2026-10-14T00:00:00Z",current_context_endpoint="/api/v4/context")
    assert data["shutdown_snapshot"]["context_token"] == "new-token"
    assert data["auto_daily_enabled"] is False

@pytest.mark.parametrize("state,finished,warn", [
    ("RUNNING",None,True),("RUNNING","done",False),
    ("PUBLISHED_FULL","done",False),("FAILED_TERMINAL","done",False),
    ("CANCELLED","done",False),("IDLE",None,False)])
def test_actual_progress_component(state, finished, warn):
    asset=Path(__file__).resolve().parents[1]/"src/workbench_service/static/core-product-r1/desktop_status.js"
    script=r"""
const fs=require('fs'),vm=require('vm');
const p=JSON.parse(process.argv[1]);const nodes=[];
const document={readyState:'complete',hidden:false,getElementById:()=>null,
createElement:()=>{const n={style:{},setAttribute(){},append(){},addEventListener(){}};nodes.push(n);return n;},body:{prepend(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),{document,AbortController,setTimeout,clearTimeout,setInterval(){},fetch:async(url)=>({ok:true,json:async()=>url.endsWith('/progress')?p:{engine_state:'RUNNING'}})});
setImmediate(()=>process.stdout.write(nodes[3].textContent));
"""
    payload=dict(stage_state=state,finished_at=finished,seconds_since_progress=999,elapsed_seconds=42)
    text=subprocess.check_output(["node","-e",script,json.dumps(payload),str(asset)],text=True,encoding="utf-8")
    assert ("近期无进展" in text) is warn
    assert "耗时 42秒" in text
    if finished: assert "完成时间 done" in text


def test_startup_then_publication_keeps_historical_snapshot(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.request import urlopen
    import workbench_desktop.engine as engine
    monkeypatch.setattr(engine, "verify_resources", lambda: {})
    current=dict(context_token="old-token",context=dict(trade_date="2026-10-12"))
    class Handler(BaseHTTPRequestHandler):
        PREFLIGHT_PRODUCT_CONTEXT=True
        def do_GET(self):
            raw=json.dumps(current).encode()
            self.send_response(200);self.end_headers();self.wfile.write(raw)
        def log_message(self,*args): pass
    class Jobs:
        thread=None
        def start(self): pass
        def quiesce(self): pass
        def status(self): return dict(context_token=current["context_token"])
    controller=EngineController(tmp_path,factory=lambda:(ThreadingHTTPServer(("127.0.0.1",0),Handler),Jobs()))
    monkeypatch.setattr(controller,"transition",lambda state,reason=None:setattr(controller,"state",state))
    controller._start()
    try:
        assert controller.startup_snapshot["context_token"] == "old-token"
        assert controller.startup_snapshot["startup_only"] is True
        assert controller.startup_snapshot["captured_at"]
        current.update(context_token="new-token",context=dict(trade_date="2026-10-13"))
        with urlopen(f"http://127.0.0.1:{controller.port}/api/v4/context") as response:
            assert json.load(response)["context_token"] == "new-token"
        assert controller.startup_snapshot["context_token"] == "old-token"
    finally: controller._stop()
    assert controller.shutdown_snapshot["context_token"] == "new-token"
    assert controller.startup_snapshot["context_token"] == "old-token"

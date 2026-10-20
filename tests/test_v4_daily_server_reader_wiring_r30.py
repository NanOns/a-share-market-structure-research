from types import SimpleNamespace


def test_successor_cache_tracks_files_but_never_stats_pg_descriptor_locators(tmp_path):
    from workbench_service.operational_daily_server_v1 import _local_successor_source_paths

    local=tmp_path/'local.json';local.write_text('{}',encoding='utf8')
    candidate={'source':{'path':'local.json','sha256':'a'*64},
        'membership':{'path':'data/v4/membership.json','sha256':'b'*64,
            'pg_descriptor':{'kind':'reference_memberships','fact_key':'c'*64}},
        'escape':{'path':'../outside.json','sha256':'d'*64}}

    assert _local_successor_source_paths(tmp_path,candidate)=={local.resolve()}


def test_daily_status_routes_use_injected_read_only_client(monkeypatch, tmp_path):
    from workbench_service import operational_daily_server_v1 as server
    from workbench_service import current_v4_context

    class Base:
        pass

    class StrictReader:
        def __init__(self, *args, **kwargs):
            pass

    class ReadClient:
        def __init__(self):
            self.calls = []

        def progress(self):
            self.calls.append(("progress",))
            return {"route": "progress"}

        def status(self):
            self.calls.append(("status",))
            return {"route": "status"}

        def settings(self):
            self.calls.append(("settings",))
            return {"route": "settings"}

        def job(self, job_id):
            self.calls.append(("job", job_id))
            return {"route": "job", "job_id": job_id}

        def events(self, job_id, after):
            self.calls.append(("events", job_id, after))
            return [{"event_id": after + 1}]

    class ForbiddenWriterReads:
        def __getattr__(self, name):
            raise AssertionError(f"GET route used writer controller: {name}")

    monkeypatch.setattr(server, "make_v4_handler", lambda *args, **kwargs: Base)
    monkeypatch.setattr(current_v4_context, "CurrentAcceptedV4Reader", StrictReader)
    monkeypatch.setattr(
        "workbench_service.v4_server.pg_candidate_adapter_from_environment",
        lambda **_kwargs: object(),
    )
    reader = ReadClient()
    handler_class = server.make_daily_handler(tmp_path, ForbiddenWriterReads(), status_reader=reader)

    def get(path):
        handler = handler_class.__new__(handler_class)
        handler.path = path
        sent = []
        handler.send = lambda code, payload, *args: sent.append((code, payload))
        handler.do_GET()
        return sent[0]

    prefix = server.PREFIX
    assert get(prefix + "/progress") == (200, {"route": "progress"})
    assert get(prefix + "/status") == (200, {"route": "status"})
    assert get(prefix + "/settings") == (200, {"route": "settings"})
    assert get(prefix + "/jobs/job-1") == (200, {"route": "job", "job_id": "job-1"})
    assert get(prefix + "/jobs/job-1/events?after=4") == (200, {"events": [{"event_id": 5}]})
    assert reader.calls == [
        ("progress",), ("status",), ("settings",), ("job", "job-1"), ("events", "job-1", 4),
    ]


def test_settings_put_uses_writer_mutation_then_reader_readback(monkeypatch, tmp_path):
    import io
    import json
    from workbench_service import operational_daily_server_v1 as server
    from workbench_service import current_v4_context

    class Base:
        pass

    class StrictReader:
        def __init__(self, *args, **kwargs):
            pass

    class Writer:
        def __init__(self):
            self.calls = []

        def set_settings(self, enabled):
            self.calls.append(("set_settings", enabled))

        def settings(self, *args):
            raise AssertionError("HTTP write route must not read through Writer controller")

    class Reader:
        def __init__(self):
            self.calls = []

        def settings(self):
            self.calls.append("settings")
            return {"auto_enabled": False, "revision": 8}

    monkeypatch.setattr(server, "make_v4_handler", lambda *args, **kwargs: Base)
    monkeypatch.setattr(current_v4_context, "CurrentAcceptedV4Reader", StrictReader)
    monkeypatch.setattr(
        "workbench_service.v4_server.pg_candidate_adapter_from_environment",
        lambda **_kwargs: object(),
    )
    writer = Writer()
    reader = Reader()
    handler_class = server.make_daily_handler(tmp_path, writer, status_reader=reader)
    handler = handler_class.__new__(handler_class)
    handler.path = server.PREFIX + "/settings"
    handler.command = "PUT"
    handler.client_address = ("127.0.0.1", 12345)
    handler.server = SimpleNamespace(server_port=28766)
    body = json.dumps({"auto_enabled": False}).encode()
    handler.rfile = io.BytesIO(body)
    handler.headers = {
        "Origin": "http://127.0.0.1:28766",
        "X-V4-Operation": "daily-update",
        "Content-Length": str(len(body)),
    }
    sent = []
    handler.send = lambda code, payload, *args: sent.append((code, payload))

    handler.do_PUT()

    assert writer.calls == [("set_settings", False)]
    assert reader.calls == ["settings"]
    assert sent == [(200, {"auto_enabled": False, "revision": 8})]

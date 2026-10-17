from types import SimpleNamespace


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

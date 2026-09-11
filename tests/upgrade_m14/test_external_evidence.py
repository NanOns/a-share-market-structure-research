from workbench_online.external_evidence import build_external_evidence_view, unavailable_external_evidence_view


def test_external_evidence_is_fail_closed_when_no_source_is_verified():
    view = build_external_evidence_view([], security_id="SH.600000", source_status="UNAVAILABLE")
    assert view["capability_status"] == "UNAVAILABLE"
    assert view["unavailable_reason"] == "NO_VERIFIED_REASON_SOURCE"
    assert view["items"] == []
    assert view["post_hoc_items"] == []
    assert view["batch_id"] is None


def test_external_evidence_as_of_rejects_missing_anchor():
    try:
        unavailable_external_evidence_view(mode="AS_OF")
    except ValueError as exc:
        assert str(exc) == "EXTERNAL_EVIDENCE_AS_OF_REQUIRED"
    else:
        raise AssertionError("AS_OF requires an anchor")


def test_external_evidence_keeps_post_hoc_items_separate():
    item = {
        "evidence_id": "e1",
        "source_id": "licensed-source",
        "security_id": "SH.600000",
        "event_time": "2026-09-11T01:00:00+00:00",
        "published_at": "2026-09-11T02:00:00+00:00",
        "first_seen_at": "2026-09-11T03:00:00+00:00",
        "text_hash": "hash",
        "raw_ref": "raw/e1",
        "text": "reason",
    }
    view = build_external_evidence_view([item], security_id="SH.600000", mode="AS_OF", as_of="2026-09-11T02:30:00+00:00", source_status="ENABLED")
    assert view["items"] == []
    assert [entry["evidence_id"] for entry in view["post_hoc_items"]] == ["e1"]


def test_external_evidence_as_of_keeps_pre_as_of_items():
    item = {
        "evidence_id": "e1",
        "source_id": "licensed-source",
        "security_id": "SH.600000",
        "event_time": "2026-09-11T01:00:00+00:00",
        "published_at": "2026-09-11T02:00:00+00:00",
        "first_seen_at": "2026-09-11T02:05:00+00:00",
        "text_hash": "hash",
        "raw_ref": "raw/e1",
        "text": "reason",
    }
    view = build_external_evidence_view([item], security_id="SH.600000", mode="AS_OF", as_of="2026-09-11T03:00:00+00:00", source_status="ENABLED")
    assert [entry["evidence_id"] for entry in view["items"]] == ["e1"]
    assert view["post_hoc_items"] == []


def test_external_evidence_rejects_missing_time_for_strict_record():
    item = {
        "evidence_id": "e1", "source_id": "s", "security_id": "SH.600000",
        "event_time": None, "published_at": "2026-09-11T02:00:00+00:00",
        "first_seen_at": "2026-09-11T03:00:00+00:00", "text_hash": "h", "raw_ref": "r", "text": "reason",
    }
    try:
        build_external_evidence_view([item], source_status="ENABLED")
    except ValueError as exc:
        assert str(exc) == "EXTERNAL_EVIDENCE_TIME_MISSING"
    else:
        raise AssertionError("missing event time must be rejected")

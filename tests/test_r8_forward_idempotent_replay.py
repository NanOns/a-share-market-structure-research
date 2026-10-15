from workbench_db.forward_r7_store import ForwardR7Store


def test_published_day_reuse_requires_same_day_sources_and_head():
    store = ForwardR7Store.__new__(ForwardR7Store)
    store._daily_facts = lambda: [
        dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R2",
             trade_date="2026-10-14", lane="LATE_OBSERVED_NOT_PIT",
             rows=[{}, {}], stable_sha256="payload",
             source_run=dict(head_token="head", source_hashes={"raw": "raw-hash"})),
        dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R2",
             trade_date="2026-10-14", lane="LIVE_OOS", rows=[],
             source_run=dict(head_token="different-head", source_hashes={"raw": "raw-hash"})),
        dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R1_LEGACY_LANE_H",
             trade_date="2026-10-14", lane="RETROSPECTIVE_RESEARCH", rows=[],
             source_run=dict(head_token="head", source_hashes={"raw": "raw-hash"})),
    ]

    found = store.find_published_day(trade_date="2026-10-14",
        source_hashes={"raw": "raw-hash"}, head_token="head")

    assert list(found) == ["LATE_OBSERVED_NOT_PIT"]
    assert found["LATE_OBSERVED_NOT_PIT"] == dict(status="PUBLISHED_IDEMPOTENT",
        trade_date="2026-10-14", lane="LATE_OBSERVED_NOT_PIT", rows=2,
        payload_sha256="payload", generation=None)


def test_published_day_reuse_rejects_changed_source_or_head():
    store = ForwardR7Store.__new__(ForwardR7Store)
    store._daily_facts = lambda: [dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R2",
        trade_date="2026-10-14", lane="LATE_OBSERVED_NOT_PIT", rows=[],
        source_run=dict(head_token="head", source_hashes={"raw": "raw-hash"}))]

    assert store.find_published_day(trade_date="2026-10-14",
        source_hashes={"raw": "new-hash"}, head_token="head") == {}
    assert store.find_published_day(trade_date="2026-10-14",
        source_hashes={"raw": "raw-hash"}, head_token="new-head") == {}

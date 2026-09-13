from pathlib import Path

from workbench_service.p09_context import CONTRACT_ID, intersect_members, load_mapping, select_mappings
import workbench_service.app as app


def test_mapping_never_uses_name_or_substring_and_requires_evidence():
    topics = [{"source_topic_id": "7", "topic_name": "机器人", "members": [{"source_code": "600001"}]}]
    mapping = {"contract_id": CONTRACT_ID, "entries": [
        {"publication_id": "pub", "sector_id": "机器人", "source_topic_key": "EXT03:7", "relation": "EXACT", "evidence_id": "review-1"},
        {"publication_id": "pub", "sector_id": "7", "source_topic_key": "EXT03:7", "relation": "EXACT"},
    ]}
    assert select_mappings(mapping, publication_id="pub", sector_id="机器人子板块", topics=topics) == []
    assert select_mappings(mapping, publication_id="other", sector_id="机器人", topics=topics) == []
    assert select_mappings(mapping, publication_id="pub", sector_id="7", topics=topics) == []
    selected = select_mappings(mapping, publication_id="pub", sector_id="机器人", topics=topics)
    assert len(selected) == 1
    assert intersect_members(selected, {"SH.600001", "SZ.000001"}, local_complete=True)["count"] == 1
    selected[0]["topic"]["members"].append({"source_code": "600001.SS"})
    assert intersect_members(selected, {"SH.600001"}, local_complete=True)["count"] == 1
    assert intersect_members(selected, {"SH.600001"}, local_complete=False)["count"] is None
    selected[0]["topic"]["members"].append({"source_code": None})
    assert intersect_members(selected, {"INVALID", "SH.600001"}, local_complete=True)["count"] == 1


def test_current_mapping_contract_contains_only_evidence_bound_related_pairs():
    root = Path(__file__).parents[2]
    mapping = load_mapping(root)
    assert mapping["contract_id"] == CONTRACT_ID
    assert len(mapping["entries"]) == 2
    assert {item["relation"] for item in mapping["entries"]} == {"RELATED"}
    assert all(item["overlap_count"] == 3 and item["source_trade_date"] != item["local_trade_date"] for item in mapping["entries"])
    topics = [{"source_topic_id": "18129294", "topic_name": "光通信", "members": []}]
    selected = select_mappings(mapping, publication_id=mapping["entries"][0]["publication_id"], sector_id="THEME:880670", topics=topics, source_date="2026-09-11", local_run_id=mapping["local_run_id"], local_date=mapping["local_trade_date"])
    assert len(selected) == 1
    assert select_mappings(mapping, publication_id=mapping["entries"][0]["publication_id"], sector_id="THEME:880670", topics=topics, source_date="2026-09-12", local_run_id=mapping["local_run_id"], local_date=mapping["local_trade_date"]) == []


def test_online_context_uses_bound_mapping_and_hash_mismatch_fails_closed(monkeypatch):
    mapping = {"contract_id": CONTRACT_ID, "status": "PARTIAL_REVIEWED_RELATED_ONLY", "local_run_id": "run", "local_trade_date": "2026-09-10", "source_ext03_sha256": "h3", "source_ext04_sha256": "h4", "entries": [{"publication_id": "pub", "sector_id": "THEME:7", "source_topic_key": "EXT03:42", "source_topic_name": "主题", "source_trade_date": "2026-09-11", "relation": "RELATED", "evidence_id": "e1"}]}
    monkeypatch.setattr(app, "load_mapping", lambda root: mapping)

    class Research:
        def sector_detail(self, context_id, sector_id):
            return {"status": "READY", "context": {"publication_id": "pub", "run_id": "run", "local_date": "2026-09-10"}, "sector": {"sector_id": sector_id}}

        def sector_members(self, *args, **kwargs):
            return {"items": [{"security_id": "SH.600001"}], "has_more": False}

    class Online:
        hashes = {"EXT03": "h3", "EXT04": "h4"}

        def topics(self, **kwargs):
            return {"status": "AVAILABLE", "source_hashes": self.hashes, "items": [{"source_topic_id": "42", "topic_name": "主题", "unique_member_count": 1, "members": [{"source_code": "600001.SS"}]}], "storage": {"mode": "REQUEST_TIME_ONLY"}}

    online = Online()
    params = {"context_id": "ctx", "trade_date": "2026-09-11"}
    result = app._p09_sector_online_context(Path("."), Research(), online, "THEME:7", params)
    assert result["status"] == "AVAILABLE"
    assert result["event_context"]["intersection"]["count"] == 1
    online.hashes = {"EXT03": "changed", "EXT04": "h4"}
    changed = app._p09_sector_online_context(Path("."), Research(), online, "THEME:7", params)
    assert changed["status"] == "DEGRADED"
    assert changed["event_context"]["reason"] == "SOURCE_HASH_MISMATCH"

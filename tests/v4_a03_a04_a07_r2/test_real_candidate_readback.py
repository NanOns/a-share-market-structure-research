"""Independent checkout readback from real pinned sources; fixtures are never market proof."""
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import zipfile
from workbench_analysis.forward_pit_ledger_r2 import bound, publications, reference
from workbench_analysis.adjusted_price_lineage_r2 import classify_lineage

ROOT=Path(__file__).resolve().parents[2]


def report(name):
    value=json.loads((ROOT/"reports/audits"/name).read_text(encoding="utf8"))
    for key in ("batch_entry","task","contract","accepted_data_head","stage_head"):
        bound(ROOT,value[key])
    assert value["external_acceptance"] is None and value["head_write_permission"] is False
    assert all(v is False for v in value["permissions"].values())
    assert value["engineering_status"]=="CANDIDATE_READY_FOR_EXTERNAL_REAUDIT"
    return value


def test_real_accepted_baseline_immutable_pit_readback():
    value=report("A03_FORWARD_PIT_BUILDER_R2_REAL_OBSERVATION.json")
    publication=json.loads(bound(ROOT,value["publication"]))
    envelope=json.loads(bound(ROOT,value["capture_envelope"]))
    assert publication in publications(ROOT,"data/v4/a03_forward_pit_r2")
    assert publication["target_trade_date"]=="2026-09-30"
    assert publication["first_available_at"]==envelope["received_at"]
    assert publication["first_available_at"][:10]>publication["target_trade_date"]
    assert publication["AS_RECORDED"] is False and publication["knowledge_lineage"]=="RECONSTRUCTED_CORRECTED"
    assert sorted(publication["sources"])==["ADJUSTED_DAILY","IDENTITY_UNIVERSE","ISST","RAW_DAILY","TRADING_STATUS"]
    for source in publication["sources"].values():
        raw=json.loads(bound(ROOT,source["bytes_binding"]))
        assert raw["trade_date"]==publication["target_trade_date"]
        assert raw["contract_id"]==source["schema_id"]
    assert publication["dm01_publication_identity"] is None
    assert value["duplicate_retry"]==["DUPLICATE_CAPTURE"]


def test_real_amount_raw_bytes_and_independent_exact_twenty_arithmetic():
    value=report("A04_AMOUNT_A_FORMAL_AUTHORITY_R2_REAL_PROOF.json")
    samples=json.loads(bound(ROOT,value["real_raw_samples"]))
    archive=samples["official_archive"]
    h=hashlib.sha256()
    with (ROOT/archive["path"]).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    assert h.hexdigest()==archive["sha256"] and (ROOT/archive["path"]).stat().st_size==archive["bytes"]
    session_set=set(samples["exact_sessions"])
    decoded={}
    with zipfile.ZipFile(ROOT/archive["path"]) as z:
        for source in samples["sources"]:
            raw=z.read(source["archive_member"]) if source["member_bytes"] else b""
            assert hashlib.sha256(raw).hexdigest()==source["member_sha256"]
            for record in struct.iter_unpack("<IIIIIfII",raw):
                d=record[0]; day=f"{d//10000:04}-{d//100%100:02}-{d%100:02}"
                if day in session_set:
                    decoded[(source["security_id"],day)]=Fraction(str(record[5]))
            for row in source["sample_rows"]:
                if row["state"]=="SUSPENDED_CONFIRMED":
                    assert source["target_dated_status"]=="SUSPENDED"
                    statuses=json.loads(bound(ROOT,row["evidence"]))["rows"]
                    assert any(s["security_id"]==source["security_id"] and s["status"]=="SUSPENDED" for s in statuses)
                    decoded[(source["security_id"],row["trade_date"])]=Fraction(0)
                else:
                    assert decoded[(source["security_id"],row["trade_date"])]==Fraction(row["amount_cny_native_float32"])
    assert len(value["exact_prior20_sessions"])==20
    for proof in value["sample_groups"]:
        c=proof["candidate"]; dates=c["prior20_sessions"]; members=c["comparable_members"]
        assert dates==value["exact_prior20_sessions"]
        sums={d:sum((decoded[(m,d)] for m in members),Fraction(0)) for d in dates+[c["target_trade_date"]]}
        denominator=sum((sums[d] for d in dates),Fraction(0))/20 if members else None
        numerator=sums[c["target_trade_date"]] if members else None
        assert str(denominator)==proof["independent_rational_denominator"]
        assert str(numerator)==proof["independent_rational_numerator"]
        assert c["formal_amount_a"] is None and c["coverage_threshold"] is None
        assert c["accepted_owner_registered"] is False and c["v4_11_amount_a_branch_enabled"] is False
    assert value["real_new_listing_samples"] and value["real_suspension_samples"]
    assert value["real_missing_amount_cells"]>0
    inventory=json.loads(bound(ROOT,value["consumer_inventory"]))
    assert {r["role"] for r in inventory["files"]}>={"DB_CACHE","UI_API","PRODUCER","CONTRACT"}


def test_real_gbbq_capture_and_historical_fail_closed_readback():
    value=report("A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_REAL_PROOF.json")
    source=value["real_capture"]
    raw=bound(ROOT,source["source_bytes"])
    assert raw and len(raw)>1000000
    assert source["source_revision"]=="sha256:"+hashlib.sha256(raw).hexdigest()
    assert classify_lineage(ROOT,source,knowledge_time=source["received_at"])["lineage"]=="AS_RECORDED"
    historical=classify_lineage(ROOT,source,knowledge_time="2026-09-24T15:00:00+08:00")
    assert historical["lineage"]=="RECONSTRUCTED_CORRECTED"
    assert historical["historical_capability"]=="PERMANENTLY_BLOCKED_PRE_CAPTURE_AS_RECORDED"
    assert value["accepted_head_as_recorded"] is False and value["formal_consumer_enabled"] is False
    assert {s["event_kind"] for s in value["actual_price_event_samples"]}=={"CASH_DIVIDEND","SPLIT_BONUS","RIGHTS_ISSUE"}
    assert value["consumer_inventory"]["V4_12_Structure_Anchor"]["implementation_executed"] is False


def test_final_durable_inventory_byte_archives_and_runtime_handoffs():
    for package in ("A03","A04","A07"):
        handoff=json.loads((ROOT/f"reports/audits/{package}_R2_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json").read_text(encoding="utf8"))
        assert handoff["status"]=="CANDIDATE_READY_FOR_EXTERNAL_REAUDIT"
        for runtime in handoff["runtime_bindings"]:bound(ROOT,runtime)
        bound(ROOT,handoff["contract"])
        bound(ROOT,handoff["candidate_proof"])
    final_a04=report("A04_AMOUNT_A_FORMAL_AUTHORITY_R2_DURABLE_REAL_PROOF_R1.json")
    inventory=json.loads(bound(ROOT,final_a04["consumer_inventory"]))
    for record in inventory["files"]:bound(ROOT,record["binding"])
    assert any(x["durability"]["representation"]=="EXACT_OBSERVED_BYTE_ARCHIVE_NO_HASH_NORMALIZATION" for x in inventory["files"])
    final_a07=report("A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_DURABLE_REAL_PROOF_R1.json")
    for reference in final_a07["raw_source_inventory"]:bound(ROOT,reference)

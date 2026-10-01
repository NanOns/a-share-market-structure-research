"""Independent source oracle plus post-publication readback, no promotion writes."""
from collections import Counter
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from workbench_analysis.forward_pit_ledger_r2 import atomic, bound, canonical, reference
from workbench_analysis.amount_a_source_binding_r3_1 import compute_ledger_candidate, read_verified_observations
from v4.scoped_promotions_r3 import HEADS, publish, read_a02, read_a05, read_a04, read_payload, rollback_pointer
from scripts.verify_a02_a05_formal_amendment_readback_r1 import verify_a02, verify_a05
from scripts.next_round_execution_r3 import verify_protected

OUTPUT = "reports/audits/next_round_r3/scoped_promotions/"


def save(name, value):
    path = ROOT / OUTPUT / name
    atomic(path, canonical(value), immutable=True)
    return reference(ROOT, path)


def verify_a04_sources():
    observations = [reference(ROOT, p) for p in sorted((ROOT / "data/v4/a04_go_forward_r3/observations").glob("*.json"))]
    items = read_verified_observations(ROOT, observations)
    candidate = compute_ledger_candidate(ROOT, observations, target="2026-09-30")
    path = ROOT / "reports/audits/a04_r3/candidates" / (candidate["publication_id"].split(":")[1] + ".json")
    assert path.read_bytes() == canonical(candidate)
    rows = candidate["rows"]
    assert len(rows) == 378 and len(items) == 1
    assert all(r["arithmetic_status"] == "UNKNOWN" and r["amount_a_value"] is None for r in rows)
    assert all(len(r["missing_accepted_membership_sessions"]) == 20 for r in rows)
    assert candidate["formal_consumer_enabled"] is False and candidate["stock_confirmation_dependency"] is False
    return dict(status="PASS", source_admission="EXACT_ACCEPTED_DATA_AND_STAGE_BOUND_MEMBERSHIP",
                source_replay_mismatches=0, sector_rows=378, known_amount_a=0, warmup_UNKNOWN=378,
                accepted_sessions=1, missing_H21=20, formal_consumer_enabled=False,
                observations=observations, candidate=reference(ROOT, path))


def reject(call):
    try:
        call()
    except (ValueError, FileNotFoundError):
        return "REJECTED"
    raise AssertionError("SCOPED_READER_FAIL_CLOSED_REQUIRED")


def post_readback():
    verify_protected()
    proofs = {}
    for stage in ("V4_05", "V4_07", "V4_09"):
        original = read_a02(ROOT, stage, mode="ORIGINAL_ACCEPTED", trade_date="2026-09-28")
        corrected = read_a02(ROOT, stage, mode="RECONSTRUCTED_CORRECTED_AMENDMENT", trade_date="2026-09-28")
        assert len(original["rows"]) == len(corrected["rows"]) == 5222
        assert original["selected_head"] != corrected["selected_head"]
        _, payload = read_payload(ROOT, stage)
        if stage == "V4_09":
            seeds = read_a02(ROOT, "V4_07", mode="RECONSTRUCTED_CORRECTED_AMENDMENT", trade_date="2026-09-28")
            assert all(payload["exact_seed_binding"][k] == seeds["artifact"][k] for k in ("path", "sha256", "bytes"))
        proofs[stage] = dict(status="PASS", old_rows=len(original["rows"]), new_rows=len(corrected["rows"]),
                             recorded_reader_modes=[original["reader_mode"], corrected["reader_mode"]],
                             knowledge_lineage=corrected["knowledge_lineage"], AS_RECORDED=False,
                             invalid_mode=reject(lambda: read_a02(ROOT, stage, mode="AUTO", trade_date="2026-09-28")),
                             future_date=reject(lambda: read_a02(ROOT, stage, mode="RECONSTRUCTED_CORRECTED_AMENDMENT", trade_date="2026-09-30")))
    snapshot = read_a05(ROOT, mode="CURRENT_SNAPSHOT_20260924", trade_date="2026-09-24")
    assert len(snapshot["rows"]) == 541
    assert Counter(r["new"]["confirmed_raw"] for r in snapshot["rows"]) == Counter(FALSE=535, TRUE=2, UNKNOWN=4)
    assert all(r["new"]["warm_raw"] == "UNKNOWN" for r in snapshot["rows"])
    proofs["A05"] = dict(status="PASS", sector_rows=541, states=dict(Counter(r["new"]["confirmed_raw"] for r in snapshot["rows"])),
        invalid_mode=reject(lambda: read_a05(ROOT, mode="AUTO", trade_date="2026-09-24")),
        no_9_30_injection=reject(lambda: read_a05(ROOT, mode="CURRENT_SNAPSHOT_20260924", trade_date="2026-09-30")))
    engineering = read_a04(ROOT, mode="GO_FORWARD_PRODUCER_ENGINEERING_ONLY")
    assert engineering["formal_consumer_enabled"] is False
    proofs["A04"] = dict(status="PASS", formal_consumer_enabled=False,
        formal_consumer_read=reject(lambda: read_a04(ROOT, mode="FORMAL_CONSUMER")),
        H21_auto_activation=False, historical_reconstruction_accepted=False, accumulation="ACCUMULATION_CONTINUES")
    # Actual production pointers are unchanged on a second publication. Revoke
    # a temporary copy only: rollback never removes durable payload or evidence.
    for key, relative in HEADS.items():
        head = ROOT / relative
        before = head.read_bytes()
        pointer, payload = read_payload(ROOT, key)
        publish(ROOT, key, payload)
        assert head.read_bytes() == before
        with tempfile.TemporaryDirectory(prefix="scoped_rollback_") as directory:
            tmp = Path(directory)
            copy_head = tmp / relative
            copy_payload = tmp / pointer["payload"]["path"]
            atomic(copy_payload, bound(ROOT, pointer["payload"]), immutable=True)
            atomic(copy_head, before, immutable=True)
            rollback_pointer(tmp, key, expected_binding=reference(tmp, copy_head))
            assert not copy_head.exists() and copy_payload.read_bytes() == bound(ROOT, pointer["payload"])
            reject(lambda: read_payload(tmp, key))
    verify_protected()
    return dict(contract_id="R3_SCOPED_POST_PROMOTION_INDEPENDENT_READBACK_V1", status="PASS", scopes=proofs,
                idempotent_publication="PASS_ALL_FIVE_POINTERS_EXACT_BYTES",
                rollback="PASS_TEMP_COPY_POINTER_ONLY_DURABLE_ARTIFACTS_PRESERVED",
                old_Data_Stage_heads="PASS_EXACT_STAGE_ENTRY_BYTES", silent_fallback=False,
                V4_11_main_stage_promoted=False, production=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-promotion", action="store_true")
    args = parser.parse_args()
    verify_protected()
    if args.post_promotion:
        result = post_readback()
        save("POST_PROMOTION_INDEPENDENT_READBACK_R1.json", result)
    else:
        result = dict(contract_id="R3_SCOPED_INDEPENDENT_SOURCE_READBACK_V1", status="PASS",
                      A02=verify_a02(), A05=verify_a05(), A04=verify_a04_sources(), production=False)
        save("INDEPENDENT_SOURCE_READBACK_R1.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()

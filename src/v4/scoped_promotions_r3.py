"""R3 explicit research-only amendment/engineering readers and immutable pointers."""
from pathlib import Path
import gzip
import json
from workbench_analysis.forward_pit_ledger_r2 import atomic, bound, canonical, digest, reference
from workbench_analysis.parallel_scoped_acceptance_r1 import PROTECTED_REPRESENTATIONS as PROTECTED_REPRESENTATIONS_BINDING

CONTRACT = "A02_A05_A04_SCOPED_PROMOTIONS_R3_V1"
AUTHORITY = "docs/evidence/next_round_r3/V4_R2_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R2_20261002.md"
AUTHORITY_SHA = "9b630344fa2101786f294fd3234bd275cedd25c73ca380706f56128fbad06d01"
PERMISSIONS = dict(production=False, shadow=False, focus=False, global_mandatory_adoption=False)
HEADS = {
    **{s: f"data/v4/{s}_ACCEPTED_HEAD_AMENDMENT_A02_R1.json" for s in ("V4_05", "V4_07", "V4_09")},
    "A05": "data/v4/V4_08_B2_CURRENT_SNAPSHOT_CAPABILITY_AMENDMENT_R1.json",
    "A04": "data/v4/A04_AMOUNT_A_GO_FORWARD_PRODUCER_ACCEPTED_HEAD_R1.json",
}
AUDITED_CANDIDATES = {
    "V4_05": "1564d6ab5ece7f74ea26974166af92f8121786f1687a999d7336533a6ba40400",
    "V4_07": "7ff4fc474487302b8845270064b1f91152db6c4844aee50623c9e71832a2bcd4",
    "V4_09": "3e4b0d8c6d6156a61596e9f5af0e67e3b3adf136e28bb1d69aaf13f3db506b1d",
    "A05": "c05e409a6436e6d365f196ba6ce9b1aeb02db35d3ea4c0fc77c3be291b74878d",
}
PROTECTED_REPRESENTATIONS = "reports/next_round_r1/BATCH_PROTECTED_REPRESENTATIONS_R1.json"


def verify_protected_metadata(root, ref):
    """Verify only protection metadata against a pre-existing original archive.

    This proof admits the exact CRLF-to-LF Git representation of two historical
    heads. It never supplies business bytes or changes any strict bound reader.
    """
    try:
        bound(root, ref)
        return
    except ValueError:
        records = json.loads(bound(root, PROTECTED_REPRESENTATIONS_BINDING))["representations"]
        matches = [row for row in records if row["original_binding"] == ref]
        if len(matches) != 1:
            raise ValueError("SCOPED_PROTECTED_ORIGINAL_REPRESENTATION_NOT_APPROVED")
        record = matches[0]
        if (record.get("verification") != "EXACT_CRLF_TO_LF_ONLY_WITH_ORIGINAL_BYTES_RETAINED"
                or record["git_representation"]["path"] != ref["path"]):
            raise ValueError("SCOPED_PROTECTED_REPRESENTATION_METADATA_INVALID")
        original = bound(root, record["original_bytes_archive"])
        current = bound(root, record["git_representation"])
        if (digest(original) != ref["sha256"]
                or len(original) != ref.get("bytes", ref.get("byte_count"))
                or original.replace(b"\r\n", b"\n") != current):
            raise ValueError("SCOPED_EXACT_PROTECTED_REPRESENTATION_MISMATCH")


def require_authority(root, ref):
    if ref["path"] != AUTHORITY or ref["sha256"] != AUTHORITY_SHA:
        raise ValueError("R3_EXTERNAL_AUTHORITY_PIN")
    raw = bound(root, ref)
    if b"d119c0526e44a819f85b4917159d3eeb5daadf2a" not in raw:
        raise ValueError("R3_IMPLEMENTATION_AUTHORITY")


def publish(root, key, payload):
    """Idempotent publication; only allowlisted scoped heads can be created."""
    root = Path(root).resolve()
    if key not in HEADS or payload.get("contract_id") != CONTRACT:
        raise ValueError("SCOPED_HEAD_ONLY")
    raw = canonical(payload)
    path = root / "data/v4/scoped_acceptance_r3" / (digest(raw) + ".json")
    atomic(path, raw, immutable=True)
    pointer = dict(contract_id=CONTRACT, scope_key=key, payload=reference(root, path))
    atomic(root / HEADS[key], canonical(pointer), immutable=True)
    return reference(root, root / HEADS[key])


def rollback_pointer(root, key, *, expected_binding):
    """Remove only an explicitly bound scoped pointer; evidence/payload stay intact."""
    if key not in HEADS or expected_binding["path"] != HEADS[key]:
        raise ValueError("ROLLBACK_SCOPED_POINTER_ONLY")
    bound(root, expected_binding)
    (Path(root) / HEADS[key]).unlink()


def read_payload(root, key):
    root = Path(root).resolve()
    pointer = json.loads((root / HEADS[key]).read_bytes())
    if pointer.get("contract_id") != CONTRACT or pointer.get("scope_key") != key:
        raise ValueError("SCOPED_POINTER_CONTRACT")
    ref = pointer["payload"]
    if ref["path"] != "data/v4/scoped_acceptance_r3/" + ref["sha256"] + ".json":
        raise ValueError("CONTENT_ADDRESSED_SCOPED_PAYLOAD_REQUIRED")
    payload = json.loads(bound(root, ref))
    require_authority(root, payload["external_authority"])
    if payload.get("contract_id") != CONTRACT or payload.get("scope_key") != key:
        raise ValueError("SCOPED_PAYLOAD_CONTRACT")
    if payload.get("permissions") != PERMISSIONS:
        raise ValueError("SCOPED_PERMISSION_EXPANSION")
    if key in AUDITED_CANDIDATES and AUDITED_CANDIDATES[key] is not None:
        if payload["accepted_candidate"]["sha256"] != AUDITED_CANDIDATES[key]:
            raise ValueError("R3_AUDITED_CANDIDATE_PIN")
    for ref in payload["protected_heads"]:
        verify_protected_metadata(root, ref)
    proof = json.loads(bound(root, payload["independent_readback"]))
    if proof.get("status") != "PASS":
        raise ValueError("SCOPED_INDEPENDENT_READBACK_REQUIRED")
    return pointer, payload


def rows(root, ref):
    return [json.loads(line) for line in gzip.decompress(bound(root, ref)).decode("utf8").splitlines()]


def read_a02(root, stage, *, mode, trade_date):
    if stage not in ("V4_05", "V4_07", "V4_09"):
        raise ValueError("A02_STAGE_SCOPE")
    if mode not in ("ORIGINAL_ACCEPTED", "RECONSTRUCTED_CORRECTED_AMENDMENT"):
        raise ValueError("A02_EXPLICIT_READER_MODE_REQUIRED")
    root = Path(root).resolve()
    if mode == "ORIGINAL_ACCEPTED":
        head_path = root / f"data/v4/{stage}_ACCEPTED_HEAD.json"
        head = json.loads(head_path.read_bytes())
        key = {"V4_05": "accepted_artifact", "V4_07": "candidate_artifact", "V4_09": "artifact"}[stage]
        source = dict(head[key])
        # V4-07 historical head records actual byte count under its original key.
        if "bytes" not in source and "byte_count" not in source:
            source["bytes"] = source["actual_byte_count"]
        result = rows(root, source)
        if any(r.get("trade_date") != trade_date for r in result):
            raise ValueError("A02_ORIGINAL_TARGET_SCOPE")
        return dict(reader_mode=mode, selected_head=reference(root, head_path), artifact=source, rows=result)
    pointer, payload = read_payload(root, stage)
    if (payload["trade_date"] != trade_date or payload["knowledge_lineage"] != "RECONSTRUCTED_CORRECTED"
            or payload["AS_RECORDED"] is not False or payload["historical_first_availability_proven"] is not False):
        raise ValueError("A02_RECONSTRUCTED_SCOPE")
    replay = json.loads(bound(root, payload["full_old_new_replay"]))
    receipt = json.loads(bound(root, payload["accepted_candidate"]))
    bound(root, payload["accepted_rps_head"])
    bound(root, payload["business_diff"])
    for ref in payload["algorithm_parameter_bindings"]:
        bound(root, ref)
    if (replay["accepted_rps_head"] != payload["accepted_rps_head"]
            or replay["amendments"][stage] != payload["accepted_candidate"]
            or receipt["artifact"] != payload["artifact"]
            or receipt["accepted_rps_head"] != payload["accepted_rps_head"]
            or receipt["full_business_diff"] != payload["business_diff"]
            or receipt["unchanged_algorithms_parameters"] != payload["algorithm_parameter_bindings"]):
        raise ValueError("A02_AUDITED_ARTIFACT_BINDING")
    if stage == "V4_09":
        seed = payload["exact_seed_binding"]
        bound(root, seed)
        other = json.loads(bound(root, replay["amendments"]["V4_07"]))
        actual = replay["new_stock_context"]["source_bindings"]["seed_artifact"]
        if any(seed[k] != other["artifact"][k] or seed[k] != actual[k] for k in ("path", "sha256", "bytes")):
            raise ValueError("V4_09_EXACT_SEED_BINDING")
    return dict(reader_mode=mode, selected_head=reference(root, root / HEADS[stage]),
                knowledge_lineage=payload["knowledge_lineage"], AS_RECORDED=False,
                artifact=payload["artifact"], rows=rows(root, payload["artifact"]))


def read_a05(root, *, mode, trade_date):
    if mode != "CURRENT_SNAPSHOT_20260924" or trade_date != "2026-09-24":
        raise ValueError("A05_EXPLICIT_CURRENT_SNAPSHOT_ONLY")
    _, payload = read_payload(root, "A05")
    if (payload["trade_date"] != trade_date or payload["scope"] != "CURRENT_SNAPSHOT_ONLY"
            or payload["AS_RECORDED"] is not False or payload["historical_PIT_equivalent"] is not False
            or payload["amount_a_warm_branch_enabled"] is not False):
        raise ValueError("A05_SCOPE_EXPANSION")
    candidate = json.loads(bound(root, payload["accepted_candidate"]))
    if (candidate["current_snapshot_replay"] != payload["artifact"]
            or candidate["A05_acceptance_record"] != payload["acceptance_record"]
            or candidate["full_accepted_artifact_diff"] != payload["full_541_sector_diff"]
            or candidate["rotation_context_readback"] != payload["rotation_context_readback"]
            or candidate["unchanged_algorithm_parameters"] != payload["algorithm_parameter_bindings"]
            or candidate["market_universe_count"] != payload["normal_quote_universe"]
            or candidate["zero_member_sector_rows"] != payload["zero_member_sector_rows"]):
        raise ValueError("A05_AUDITED_ARTIFACT_BINDING")
    for key in ("acceptance_record", "full_541_sector_diff", "rotation_context_readback"):
        bound(root, payload[key])
    for ref in payload["algorithm_parameter_bindings"]:
        bound(root, ref)
    return dict(reader_mode=mode, selected_head=reference(root, Path(root) / HEADS["A05"]),
                trade_date=trade_date, rows=rows(root, payload["artifact"]))


def read_a04(root, *, mode):
    if mode != "GO_FORWARD_PRODUCER_ENGINEERING_ONLY":
        raise ValueError("A04_EXPLICIT_ENGINEERING_SCOPE_REQUIRED")
    _, payload = read_payload(root, "A04")
    if (payload["producer_accepted"] is not True or payload["formal_consumer_enabled"] is not False
            or payload["historical_reconstruction_accepted"] is not False or payload["H21_warmup_required"] is not True
            or payload["stock_amr20_dependency"] is not False):
        raise ValueError("A04_ENGINEERING_SCOPE_EXPANSION")
    handoff_ref = payload["audited_engineering_handoff"]
    if (handoff_ref["path"] != "reports/audits/a04_r3/A04_R3_1_EXTERNAL_REAUDIT_HANDOFF_R1.json"
            or handoff_ref["sha256"] != "8e7d36ad4da94d810da04d9351d17629b0a58a9617391d182c717b3fb920fc5d"):
        raise ValueError("A04_AUDITED_ENGINEERING_PIN")
    handoff = json.loads(bound(root, handoff_ref))
    if payload["producer_bindings"] != [handoff["producer_contract"], handoff["source_admission_contract"],
            handoff["namespace_contract"], handoff["scoped_real_proof"], handoff["h21_membership_scope"], *handoff["runtime_bindings"]]:
        raise ValueError("A04_AUDITED_PRODUCER_SUBSTITUTION")
    for ref in payload["producer_bindings"]:
        bound(root, ref)
    return dict(reader_mode=mode, selected_head=reference(root, Path(root) / HEADS["A04"]),
                producer_accepted=True, formal_consumer_enabled=False,
                consumer_acceptance_required=["H21_COMPLETENESS", "SOURCE_CONSISTENCY", "ARITHMETIC_ORACLE", "CONSUMER_SPECIFIC_EXTERNAL_ACCEPTANCE"],
                payload=payload)

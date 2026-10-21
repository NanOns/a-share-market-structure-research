"""Precompute a fixed development candidate's full Priority projection offline."""
from __future__ import annotations

import argparse
from copy import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import time


REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO)]


def precompute(root: Path, candidate_path: Path) -> dict:
    root = root.resolve()
    candidate_path = candidate_path.resolve()
    tmp_root = Path("G:/codex_tmp").resolve()
    if root != tmp_root and tmp_root not in root.parents:
        raise ValueError("R8_PRIORITY_PRECOMPUTE_REQUIRES_G_TMP_CANDIDATE_ROOT")
    if root not in candidate_path.parents:
        raise ValueError("R8_PRIORITY_CANDIDATE_PATH_OUTSIDE_ROOT")
    # Match the existing development preview's secure in-process DSN loading.
    # Never emit values or persist them outside the user's existing config.
    for line in (REPO / "config/.env").read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in ("WORKBENCH_PG_DSN", "V4_NATIVE_PG_DSN", "V4_NATIVE_PG_READER_DSN") and value:
            os.environ.setdefault(key, value)
    if not os.environ.get("V4_NATIVE_PG_DSN") and os.environ.get("WORKBENCH_PG_DSN"):
        os.environ["V4_NATIVE_PG_DSN"] = os.environ["WORKBENCH_PG_DSN"]
    if not os.environ.get("V4_NATIVE_PG_READER_DSN"):
        os.environ["V4_NATIVE_PG_READER_DSN"] = os.environ.get("V4_NATIVE_PG_DSN", "")
    os.environ.pop("R8_REQUIRE_PRIORITY_PRECOMPUTE", None)
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1, validate
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    from workbench_service.research_bff import ResearchBFF
    candidate = json.loads(candidate_path.read_bytes())
    validate(root, candidate)
    api = OperationalSuccessorReaderV1(root, candidate)
    bff = ResearchBFF(root)
    started = time.perf_counter()
    code, response = CoreProductBFFR1(copy(api), bff, chart_history_index_root=REPO).get(
        "/api/v4/radar/priority", {
            "view": "candidate", "context_token": api.token,
            "scope": "stocks", "offset": "0", "limit": "1"})
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    if code != 200 or response.get("status") not in ("READY", "EMPTY_VALID"):
        raise ValueError("R8_PRIORITY_PRECOMPUTE_FAILED:" + str(response.get("reason") or code))
    cache_root = root / "runtime/r8_derived_cache/priority"
    matches = sorted(cache_root.glob("*.json")) if cache_root.exists() else []
    if len(matches) != 1:
        raise ValueError(f"R8_PRIORITY_PRECOMPUTE_SNAPSHOT_COUNT:{len(matches)}")
    raw = matches[0].read_bytes()
    envelope = json.loads(raw)
    payload = envelope.get("payload")
    if not isinstance(payload, dict) or envelope.get("identity", {}).get("token") != api.token:
        raise ValueError("R8_PRIORITY_PRECOMPUTE_SNAPSHOT_IDENTITY_MISMATCH")
    stocks = payload.get("stocks") or {}
    sectors = payload.get("sectors") or {}
    market = response.get("candidate_market_risk") or {}
    return dict(contract_id="R8_CANDIDATE_PRIORITY_OFFLINE_PRECOMPUTE_R1",
        status="PRECOMPUTE_PASS_CANDIDATE_ONLY", T0=api.candidate["accepted_trade_date"],
        token=api.token, candidate_only=True, production_accepted=False,
        formal_head_modified=False, snapshot_path=str(matches[0]),
        snapshot_sha256=hashlib.sha256(raw).hexdigest(), snapshot_bytes=len(raw),
        payload_sha256=envelope.get("payload_sha256"),
        source_binding_identity_sha256=hashlib.sha256(json.dumps(envelope.get("identity"),
            ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest(),
        row_counts={"stocks_total":stocks.get("total"),"stocks_rankable":stocks.get("rankable"),
                    "stocks_excluded":stocks.get("not_rankable"),
                    "sectors_total":sectors.get("total"),"sectors_rankable":sectors.get("rankable"),
                    "sectors_excluded":sectors.get("not_rankable")},
        market_status=market.get("status"),trend_state=market.get("trend_axis_status"),
        d0_seal_state=(payload.get("d0") or {}).get("seal_status"),
        page_measurement_ms=elapsed_ms,
        precompute_stage="OFFLINE_DEVELOPMENT_CANDIDATE_COMPUTE",
        response_payload_sha256=response.get("candidate_payload_sha256"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    result = precompute(args.root, args.candidate)
    target = args.receipt.resolve()
    if target.drive.upper() != "G:" or REPO in target.parents:
        raise ValueError("R8_PRIORITY_PRECOMPUTE_RECEIPT_MUST_BE_G_TMP")
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

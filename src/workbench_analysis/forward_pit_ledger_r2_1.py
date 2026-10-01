"""A03 2.1 payload cross-validation before immutable observation publication.

The R2 ledger/storage remains frozen. This version derives schema and target from
actual pinned JSON artifact bytes, so envelope metadata cannot conceal drift.
"""
from copy import deepcopy
import json
from . import forward_pit_ledger_r2 as frozen

CONTRACT = "A03_FORWARD_PIT_PAYLOAD_GOVERNANCE_R2_1"


def append_observation(root, ledger, envelope, *, failure_after_publication=False):
    checked=deepcopy(envelope)
    for family,source in checked["sources"].items():
        if family not in checked["expected_source_families"]:
            raise ValueError("UNDECLARED_CAPTURE_SOURCE_FAMILY")
        raw=frozen.bound(root,source["bytes_binding"])
        try:
            payload=json.loads(raw)
        except (ValueError,UnicodeDecodeError):
            payload=None
        if not isinstance(payload,dict):
            schema="INVALID_JSON_ARTIFACT_PAYLOAD"
        elif not isinstance(payload.get("contract_id"),str) or not payload["contract_id"]:
            schema="MISSING_PAYLOAD_CONTRACT_ID"
        elif not isinstance(payload.get("rows"),list):
            schema="MISSING_OR_INVALID_PAYLOAD_ROWS"
        elif not isinstance(payload.get("trade_date"),str):
            schema="MISSING_OR_INVALID_PAYLOAD_TARGET_DATE"
        elif any(not isinstance(row,dict) for row in payload["rows"]):
            schema="INVALID_ARTIFACT_ROW_SHAPE"
        else:
            schema=payload["contract_id"]
            # The target detector consumes the actual payload's date.
            source["target_trade_date"]=payload["trade_date"]
            if any(row.get("trade_date") is not None and row["trade_date"]!=payload["trade_date"] for row in payload["rows"]):
                schema="PAYLOAD_ROW_TARGET_DATE_DRIFT"
        if schema!=source.get("schema_id"):
            source["declared_capture_schema_id"]=source.get("schema_id")
            source["schema_id"]=schema
            # Caller expected-schema claims cannot bless malformed bytes or hide
            # a disagreement between capture metadata and actual artifact schema.
            checked["expected_schema_ids"][family]="CAPTURE_METADATA_SCHEMA_MISMATCH:"+str(envelope["sources"][family].get("schema_id"))
    return frozen.append_observation(root,ledger,checked,failure_after_publication=failure_after_publication)


rebuild_latest=frozen.rebuild_latest

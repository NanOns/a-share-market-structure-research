"""Authorize only V4-06 entry after independent V4-05 promotion validation passes."""
from __future__ import annotations

import json

from v4_05_promotion_contract import (
    GLOBAL_HEAD, PROMOTION_PREFLIGHT, ROOT, atomic_json, file_identity, load_json, validate,
)


def authorize() -> dict:
    preflight_path = ROOT / PROMOTION_PREFLIGHT
    if not preflight_path.is_file():
        raise ValueError("independent V4-05 promotion pre-entry validation is missing")
    preflight = load_json(PROMOTION_PREFLIGHT)
    if preflight.get("status") != "PASS" or preflight.get("phase") != "pre-entry" or not all(preflight.get("checks", {}).values()):
        raise ValueError("independent V4-05 promotion validation did not pass")

    current = validate("pre-entry")
    if current["status"] != "PASS":
        raise ValueError("V4-05 promotion evidence changed after validation")
    if (preflight.get("accepted_head") != current.get("accepted_head") or
            preflight.get("global_head") != current.get("global_head")):
        raise ValueError("pre-entry validation is not bound to the current heads")

    global_head = load_json(GLOBAL_HEAD)
    if "v4_06_entry" in global_head:
        raise ValueError("V4-06 entry already has a global authorization state")
    global_head["v4_06_entry"] = "AUTHORIZED_SUPPLEMENTAL_ENRICHMENT"
    global_head["v4_06_status"] = "NOT_STARTED"
    global_head["v4_07_entry"] = "NOT_STARTED"
    atomic_json(GLOBAL_HEAD, global_head)
    return {
        "status": "AUTHORIZED",
        "v4_06_entry": global_head["v4_06_entry"],
        "v4_06_status": global_head["v4_06_status"],
        "v4_07_entry": global_head["v4_07_entry"],
        "promotion_preflight": file_identity(PROMOTION_PREFLIGHT),
        "global_head": file_identity(GLOBAL_HEAD),
    }


if __name__ == "__main__":
    print(json.dumps(authorize(), ensure_ascii=False, sort_keys=True))

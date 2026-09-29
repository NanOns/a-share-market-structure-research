"""Independent read-only validation for V4-05 promotion and V4-06 entry."""
from __future__ import annotations

import argparse
import json
import sys

from v4_05_promotion_contract import (
    PROMOTION_PREFLIGHT, PROMOTION_VALIDATION, ROOT, atomic_json, validate,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("pre-entry", "final"), default="final")
    args = parser.parse_args()
    result = validate(args.phase)
    output = PROMOTION_PREFLIGHT if args.phase == "pre-entry" else PROMOTION_VALIDATION
    atomic_json(output, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

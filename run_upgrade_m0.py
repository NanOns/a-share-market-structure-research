from pathlib import Path
import json
import sys
import argparse


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from upgrade_m0 import run  # noqa: E402
from upgrade_m0_terminal_observer import capture, finalize  # noqa: E402
from common.paths import resolve_tdx_root  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-terminal-baseline", action="store_true")
    parser.add_argument("--finalize-terminal-observation", action="store_true")
    args = parser.parse_args()
    tdx_root = resolve_tdx_root(ROOT)
    if args.capture_terminal_baseline:
        value = capture(ROOT, tdx_root)
        print(json.dumps({"final_status": value["final_status"], "manifest_sha256": value["before"]["manifest_sha256"]}, ensure_ascii=False, indent=2))
        raise SystemExit(0)
    if args.finalize_terminal_observation:
        value = finalize(ROOT, tdx_root)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        raise SystemExit(0 if value["final_status"] == "PASS" else 2)
    receipt = run(ROOT)
    print(json.dumps({"final_status": receipt["final_status"], "receipt_sha256": receipt["receipt_sha256"], "next_stage": receipt["next_stage"]}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if receipt["final_status"] != "BLOCKED" else 2)

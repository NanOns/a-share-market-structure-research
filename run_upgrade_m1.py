from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from upgrade_m1 import run  # noqa: E402

if __name__ == "__main__":
    result = run(ROOT)
    print(json.dumps({"final_status": result["final_status"], "receipt_sha256": result["receipt_sha256"], "next_stage": result["next_stage"]}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["final_status"] == "FULL_PASS" else 2)

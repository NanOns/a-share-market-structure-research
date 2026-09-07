from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from phase0_1_runner import run_phase0_1  # noqa: E402


if __name__ == "__main__":
    receipt = run_phase0_1(PROJECT_ROOT, Path(r"D:\new_tdx"))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    raise SystemExit(0 if receipt["final_status"] != "BLOCKED" else 2)


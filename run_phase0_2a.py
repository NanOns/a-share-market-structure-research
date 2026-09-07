from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from phase0_2a_runner import run_phase0_2a


if __name__ == "__main__":
    receipt = run_phase0_2a(ROOT, Path(r"D:\new_tdx"))
    print(receipt["final_status"])

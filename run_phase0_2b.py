from pathlib import Path
import sys
import argparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from phase0_2b_runner import run

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--network-authorized', action='store_true')
    args = parser.parse_args()
    print(run(ROOT, Path('D:/new_tdx'), args.network_authorized))

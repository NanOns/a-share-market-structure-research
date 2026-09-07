from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from phase3_runner import run
if __name__=='__main__': run(ROOT,Path('D:/new_tdx'))

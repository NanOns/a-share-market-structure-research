"""R4.1 versioned corrected-owner replay entry, shared with DM01."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.corrected_owner_pipeline import run_corrected_owner_pipeline
if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['core','profile','sector','all'],default='all');args=p.parse_args()
    print(json.dumps(run_corrected_owner_pipeline(ROOT,stage=args.stage)))

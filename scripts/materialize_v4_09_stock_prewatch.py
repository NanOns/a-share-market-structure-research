"""Materialize the same-session accepted Stock PREWATCH engineering candidate."""
from pathlib import Path
import sys
import json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.v4.stock_prewatch import materialize
from scripts.build_v4_08_r2_membership_evidence import atomic_json

if __name__=='__main__':
    result=materialize(ROOT, ROOT/'data/v4/artifact_store/v4_09/V4_09_STOCK_PREWATCH_CANDIDATE.jsonl.gz')
    atomic_json(ROOT/'reports/v4_09/V4_09_FULL_MARKET_CANDIDATE.json',result)
    print(json.dumps({k:result[k] for k in ['status','row_count','raw_counts','bucket_counts','artifact']},ensure_ascii=False))

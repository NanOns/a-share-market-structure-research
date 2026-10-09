import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
from workbench_analysis.operational_next_session_v1 import next_session_gate
from workbench_analysis.scoped_successor_r421 import atomic, canonical

if __name__ == '__main__':
    result = next_session_gate(ROOT)
    atomic(ROOT / 'docs/evidence/r43_r2_fp_entry_20261009/R43_R2_NEXT_SESSION_PIPELINE_QA.json', canonical(result))
    print(json.dumps(result, ensure_ascii=True))

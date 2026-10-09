from pathlib import Path
import json
import sys
from workbench_analysis.tdx_member_retro_r43 import capture

if __name__=='__main__':
    s=capture(Path(__file__).resolve().parents[1])
    print(json.dumps({k:s[k] for k in ('membership_snapshot_id','memberships','sector_counts','relation_count','unmapped_count')},ensure_ascii=False))
    if '--run-sectors' in sys.argv:
        from workbench_analysis.tdx_sector_retro_r43 import run
        run(Path(__file__).resolve().parents[1])

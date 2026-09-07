import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'src'))
from production.daily import run_daily
from common.paths import resolve_tdx_root

def main():
 p=argparse.ArgumentParser(description='TDX Market Structure Scanner daily production V1');p.add_argument('--date',required=True);p.add_argument('--dry-run',action='store_true');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
 root=Path(__file__).parent;code,result=run_daily(root,resolve_tdx_root(root),a.date,a.dry_run,a.verify_only);print(json.dumps(result,ensure_ascii=False,indent=2));return code
if __name__=='__main__':raise SystemExit(main())

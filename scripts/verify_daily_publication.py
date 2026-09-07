import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from production.daily import latest_resolution,verify_directory
def main():
 p=argparse.ArgumentParser();p.add_argument('--date',required=True);a=p.parse_args()
 if a.date!='latest':print(json.dumps({'status':'INPUT_NOT_READY','error':'Only latest supported'}));return 2
 r=latest_resolution(ROOT,Path('D:/new_tdx'));v=verify_directory(ROOT,ROOT/'reports'/r['resolved_cutoff_date'],r['resolved_cutoff_date']);print(json.dumps({'status':'PASS',**r,'verification':v},ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())

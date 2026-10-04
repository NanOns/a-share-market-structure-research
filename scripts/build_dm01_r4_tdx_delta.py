"""Exact current V2 package delta input; no generic component builder/promotion."""
from datetime import datetime,timezone
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis import dm01_runtime_r4 as r
from workbench_analysis.dm01_sources_r4 import parent_tdx_package
from workbench_analysis.tdx_snapshot_delta import build_tdx_package_delta

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--target-date',required=True)
    parser.add_argument('--current-snapshot-id',required=True);args=parser.parse_args()
    gate=r.session_gate(args.target_date,datetime.now(timezone.utc).isoformat())
    if gate['status']=='WAIT_MARKET_CLOSE':print(json.dumps(gate));return 0
    parent=parent_tdx_package(ROOT)
    current=ROOT/'data/v4/source_snapshots/tdx'/args.target_date.replace('-','')/args.current_snapshot_id/'hsjday.zip'
    r.require(args.current_snapshot_id=='sha256-'+r.sha(current),'CURRENT_TDX_SNAPSHOT_HASH_MISMATCH')
    delta=build_tdx_package_delta(parent_zip=r.path(ROOT,parent),current_zip=current,target_date=args.target_date,
        parent_snapshot_id='sha256-'+parent['sha256'],current_snapshot_id=args.current_snapshot_id)
    location=current.parent/'delta'/args.target_date.replace('-','')
    binding=r.atomic(ROOT,location/('TDX_PACKAGE_DELTA_'+args.target_date.replace('-','')+'.json'),delta,immutable=True)
    value=dict(contract_id='DM01_R4_TDX_DELTA_BUILD_RECEIPT_V1',status=delta['status'],target_date=args.target_date,
        parent_data_head=gate['parent']['binding'],parent_snapshot_id='sha256-'+parent['sha256'],
        current_snapshot_id=args.current_snapshot_id,delta_path=str(ROOT/binding['path']),delta_sha256=binding['sha256'],tdx_root_write_count=0)
    r.atomic(ROOT,location/'tdx_delta_build_receipt.json',value,immutable=True)
    print(json.dumps(value));return 0 if delta['status']=='READY' else 2

if __name__=='__main__':raise SystemExit(main())

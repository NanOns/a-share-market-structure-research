"""Daily append command for actual local adjustment source observations."""
import argparse
from pathlib import Path
from workbench_analysis.adjusted_price_lineage_r2 import capture_source
from workbench_analysis.forward_pit_ledger_r2 import canonical

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--source-kind",choices=["GBBQ","PROVIDER_FACTOR","MANUAL_RECORD"],required=True)
    p.add_argument("--source-identity",required=True)
    a=p.parse_args()
    print(canonical(capture_source(a.project_root,a.source,source_kind=a.source_kind,source_identity=a.source_identity)).decode("utf8"))

if __name__=="__main__":main()

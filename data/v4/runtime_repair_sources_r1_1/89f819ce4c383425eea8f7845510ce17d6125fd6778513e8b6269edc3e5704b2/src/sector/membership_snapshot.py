"""Build the current TDX sector membership snapshot without writing to TDX."""
from pathlib import Path
import pandas as pd
from tdx.gbbq_reader import file_sha256
from tdx.security_master import read_industry_assignments
from tdx.block_reader import build_industry_memberships,read_industry_names,read_infoharbor_memberships
from sector.roles import sector_role

VERSION="sector-membership-snapshot-v1.0"

def build_snapshot(tdx: Path, cutoff) -> tuple[pd.DataFrame,dict]:
    cache=Path(tdx)/"T0002/hq_cache"; paths=[cache/n for n in ("tdxhy.cfg","tdxzs.cfg","infoharbor_block.dat")]
    industry_names=read_industry_names(paths[1])
    rows=build_industry_memberships(read_industry_assignments(paths[0]),industry_names)
    # TDX stores many level-one industry nodes only in tdxzs.cfg; they do not
    # appear in tdxhy.cfg because stocks are assigned to their leaf nodes.
    # Materialize those audited parent memberships as the union of their
    # children so the workbench can show e.g. 有色金属 -> 铜/铝/黄金.
    parent_rows=[]
    for row in rows:
        code=str(row.get("sector_code") or "")
        parent=code[:5] if len(code)>5 else ""
        if parent and parent in industry_names:
            parent_rows.append({**row,"sector_code":parent,"sector_name":industry_names[parent],"source":"tdxhy.cfg:DERIVED_PARENT"})
    rows.extend(parent_rows)
    extra,meta=read_infoharbor_memberships(paths[2]); rows += [v for v in extra if v["sector_type"] in ("concept","style")]
    frame=pd.DataFrame(rows).drop_duplicates(["sector_type","sector_code","security_id"]).copy()
    frame["sector_type"]=frame.sector_type.map({"industry":"INDUSTRY","concept":"THEME","style":"STYLE"})
    frame["sector_id"]=frame.sector_type+":"+frame.sector_code.astype(str)
    frame["sector_role"]=frame.apply(lambda r:sector_role(r.sector_type.lower().replace("theme","concept"),r.sector_name),axis=1)
    frame["date"]=pd.Timestamp(str(cutoff)).date();frame["membership_asof_date"]=frame["date"]
    frame["pit_membership"]=False;frame["historical_backtest_safe"]=False;frame["snapshot_version"]=VERSION
    cols=["date","membership_asof_date","sector_id","sector_code","sector_name","sector_type","sector_role","security_id","membership_basis","source","pit_membership","historical_backtest_safe","snapshot_version"]
    frame=frame[cols].sort_values(["sector_type","sector_id","security_id"]).reset_index(drop=True)
    return frame,{str(p):file_sha256(p) for p in paths}

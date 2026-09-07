from __future__ import annotations
import argparse,hashlib,json,os,shutil,sys,tempfile
from datetime import timedelta
from pathlib import Path
import pandas as pd
import pyarrow as pa,pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from shadow_v21.pullback import anchored_diagnostics,classify_row,RULESET_ID,CONTRACT_VERSION

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()

def run(requested="latest"):
    if requested!="latest":raise ValueError("V21_SHADOW_LATEST_ONLY")
    pointer=json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text("utf8"));release_info=pointer["latest_release"]
    cutoff=str(release_info.get("cutoff_date") or release_info["date"]);release_id=release_info["run_id"];release=ROOT/f"reports/releases/{cutoff}/{release_id}";d=pd.Timestamp(cutoff).date()
    stocks=pd.read_csv(release/"stocks.csv",encoding="utf-8-sig",usecols=["security_id","strong_pullback"]);stocks["v1_strong_pullback"]=stocks.pop("strong_pullback").astype(str).str.lower().eq("true")
    bars=pq.read_table(ROOT/"data/normalized/adjusted_daily.parquet",columns=["security_id","date","adj_close","raw_amount","has_actual_bar"],filters=[("date",">=",d-timedelta(days=100)),("date","<=",d)]).to_pandas();bars=bars[bars.has_actual_bar.eq(True)&bars.security_id.isin(stocks.security_id)]
    rows=[]
    for sid,g in bars.sort_values("date").groupby("security_id"):
        diagnostic=anchored_diagnostics(g.date,g.adj_close,g.raw_amount);rows.append({"security_id":sid,"date":d,**diagnostic})
    out=stocks.merge(pd.DataFrame(rows),on="security_id",how="left",validate="one_to_one")
    classified=[classify_row(v,r) for v,r in zip(out.v1_strong_pullback,out.to_dict("records"))];out=pd.concat([out,pd.DataFrame(classified)],axis=1)
    old_path=ROOT/f"reports/shadow/v2/{cutoff}/strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet";old=pd.read_parquet(old_path)
    old_cols=["security_id","recent_peak_date_20","pullback_amount_ratio","v2_pullback_class","v2_pullback_structure_hit","v2_pullback_volume_confirmed"]
    out=out.merge(old[old_cols],on="security_id",how="left",validate="one_to_one");out["peak_anchor_changed"]=pd.to_datetime(out.recent_peak_date_20).dt.date!=pd.to_datetime(out.peak_date_v21).dt.date
    out["amount_ratio_changed"]=(pd.to_numeric(out.pullback_amount_ratio,errors="coerce")-pd.to_numeric(out.pullback_amount_ratio_v21,errors="coerce")).abs().gt(1e-12);out["classification_changed"]=out.v2_pullback_class!=out.v21_pullback_class
    out["shadow_ruleset_id"]=RULESET_ID;out["shadow"]=True;out["production_eligible"]=False;out=out.sort_values("security_id").reset_index(drop=True)
    inputs={str(p.relative_to(ROOT)).replace("\\","/"):sha(p) for p in [release/"manifest.json",old_path,ROOT/"reports/phase1/PHASE1_FINAL_RECEIPT.json",ROOT/"src/shadow_v21/pullback.py",ROOT/"docs/STRONG_PULLBACK_V2_1_SHADOW_CONTRACT_V1.md",ROOT/"run_strong_pullback_v21.py"]}
    identity={"version":"v2.1-shadow-identity-v1.0","cutoff":cutoff,"v1_release_id":release_id,"ruleset_id":RULESET_ID,"contract_version":CONTRACT_VERSION,"inputs":inputs};identity["sha256"]=hashlib.sha256(canonical(identity)).hexdigest()
    target=ROOT/f"reports/shadow/v2_1/{cutoff}/strong_pullback/{identity['sha256']}";target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        stage=Path(tempfile.mkdtemp(prefix=".v21_",suffix=".tmp",dir=target.parent))
        try:
            pq.write_table(pa.Table.from_pandas(out,preserve_index=False),stage/"STRONG_PULLBACK_V21_SHADOW.parquet",compression="zstd")
            changed=out[out.classification_changed|out.peak_anchor_changed|out.amount_ratio_changed]
            changed.to_csv(stage/"V2_V21_PULLBACK_DIFF.csv",index=False,encoding="utf-8-sig")
            eligible=out[out.v1_strong_pullback];transitions=pd.crosstab(eligible.v2_pullback_class,eligible.v21_pullback_class).to_dict()
            summary={"cutoff":cutoff,"ruleset_id":RULESET_ID,"rows":len(out),"v1_pullback_rows":int(out.v1_strong_pullback.sum()),"peak_anchor_changed":int(out.peak_anchor_changed.sum()),"amount_ratio_changed":int(out.amount_ratio_changed.sum()),"classification_changed":int(eligible.classification_changed.sum()),"newly_data_insufficient":int((eligible.v21_pullback_class.eq("DATA_INSUFFICIENT")&eligible.v2_pullback_class.ne("DATA_INSUFFICIENT")).sum()),"v2_classes":eligible.v2_pullback_class.value_counts().to_dict(),"v21_classes":eligible.v21_pullback_class.value_counts().to_dict(),"class_transitions":transitions,"production_eligible":False}
            (stage/"V2_1_PULLBACK_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str)+"\n","utf8")
            lines=["# 强势回撤 V2.1 同日比较报告","",f"数据截止日：{cutoff}。V2.1 是影子研究版本，不替换已封存 V2。","",f"原版强势回撤股票 {len(eligible)} 只；峰值日期变化 {summary['peak_anchor_changed']} 只；成交比例变化 {summary['amount_ratio_changed']} 只；分类变化 {summary['classification_changed']} 只；因峰值后没有交易柱而明确转为数据不足 {summary['newly_data_insufficient']} 只。","","## 分类数量","","| 分类 | V2 | V2.1 |","|---|---:|---:|"]
            for name in sorted(set(summary["v2_classes"])|set(summary["v21_classes"])):lines.append(f"| {name} | {summary['v2_classes'].get(name,0)} | {summary['v21_classes'].get(name,0)} |")
            lines += ["","变化原因：V2.1 对峰值日期、回撤深度、持续时间和成交分段使用同一个最近峰值位置；峰值柱只进入上涨段，不再同时进入回撤段。阈值未调整。完整逐股差异见 `V2_V21_PULLBACK_DIFF.csv`。"]
            (stage/"V2_1_PULLBACK_ANALYSIS.md").write_text("\n".join(lines)+"\n","utf8");(stage/"V2_1_IDENTITY.json").write_text(json.dumps(identity,ensure_ascii=False,indent=2,sort_keys=True)+"\n","utf8");os.replace(stage,target)
        finally:shutil.rmtree(stage,ignore_errors=True)
    current={"version":"current-v2.1-pullback-shadow-v1.0","cutoff":cutoff,"path":str(target),"identity":identity};tmp=target.parent/".CURRENT_V2_1.json.tmp";tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+"\n","utf8");os.replace(tmp,ROOT/"reports/shadow/v2_1/CURRENT_V2_1.json")
    return {**json.loads((target/"V2_1_PULLBACK_SUMMARY.json").read_text("utf8")),"path":str(target),"identity":identity["sha256"]}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--date",default="latest");print(json.dumps(run(p.parse_args().date),ensure_ascii=False,indent=2))

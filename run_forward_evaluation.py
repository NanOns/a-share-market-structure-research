from __future__ import annotations
import hashlib,json,os,shutil,sys,tempfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from forward.live import latest_revision,read_observation,sealed_sequence
from forward.evaluation import bind_outcomes,evaluate,VERSION,MIN_OBSERVED_ROWS,MIN_SIGNAL_DATES

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(root=ROOT):
    root=Path(root);dates=sealed_sequence(root);observations=[];inputs={}
    for date in dates:
        revision=latest_revision(root,date);parquet=revision/"FORWARD_OBSERVATION.parquet";identity=revision/"OBSERVATION_IDENTITY.json";observations.extend(read_observation(revision));inputs[str(parquet.relative_to(root)).replace("\\","/")]=sha(parquet);inputs[str(identity.relative_to(root)).replace("\\","/")]=sha(identity)
    outcomes=[]
    for path in sorted((root/"data/forward/observations").rglob("OUTCOME_BATCH.json")):
        value=json.loads(path.read_text("utf8"));outcomes.extend(value.get("rows",[]));inputs[str(path.relative_to(root)).replace("\\","/")]=sha(path)
    obs=pd.DataFrame(observations);out=pd.DataFrame(outcomes);bound=bind_outcomes(obs,out) if outcomes else pd.DataFrame();result=evaluate(bound)
    status="READY" if not result.empty and result.sample_status.eq("SUFFICIENT_FOR_DESCRIPTION").any() else "DATA_INSUFFICIENT"
    identity={"version":"forward-evaluation-identity-v1.0","contract":VERSION,"sealed_dates":dates,"inputs":inputs,"code_sha256":sha(root/"src/forward/evaluation.py"),"runner_sha256":sha(root/"run_forward_evaluation.py"),"contract_sha256":sha(root/"docs/FORWARD_EVALUATION_CONTRACT_V1.md")};identity["sha256"]=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    target=root/f"reports/forward_evaluation/{dates[-1] if dates else 'NO_DATE'}/{identity['sha256']}";target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        stage=Path(tempfile.mkdtemp(prefix=".forward_eval_",suffix=".tmp",dir=target.parent))
        try:
            result.to_csv(stage/"FORWARD_EVALUATION.csv",index=False,encoding="utf-8-sig")
            summary={"status":status,"contract":VERSION,"sealed_trading_dates":dates,"sealed_trading_date_count":len(dates),"outcome_rows":len(outcomes),"evaluation_groups":len(result),"sufficient_groups":int(result.sample_status.eq("SUFFICIENT_FOR_DESCRIPTION").sum()) if not result.empty else 0,"minimum_observed_rows":MIN_OBSERVED_ROWS,"minimum_signal_dates":MIN_SIGNAL_DATES,"probability_claim":False,"thresholds_changed":False,"synthetic_dates_used":False}
            (stage/"FORWARD_EVALUATION_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n","utf8");(stage/"FORWARD_EVALUATION_IDENTITY.json").write_text(json.dumps(identity,ensure_ascii=False,indent=2,sort_keys=True)+"\n","utf8")
            text=["# 真实 Forward 评估报告","",f"当前状态：`{status}`。已封存真实交易日 {len(dates)} 个，到期结果 {len(outcomes)} 条。","",f"每个结构/研究带/周期至少需要 {MIN_OBSERVED_ROWS} 条完整结果并覆盖 {MIN_SIGNAL_DATES} 个信号交易日，才公布描述性收益指标。当前不会使用合成日期补足样本，也不会据此调整阈值。"]
            (stage/"FORWARD_EVALUATION_REPORT.md").write_text("\n".join(text)+"\n","utf8");os.replace(stage,target)
        finally:shutil.rmtree(stage,ignore_errors=True)
    pointer={"version":"current-forward-evaluation-v1.0","status":status,"path":str(target),"identity":identity};pointer_path=root/"reports/forward_evaluation/CURRENT_FORWARD_EVALUATION.json";tmp=pointer_path.with_name("."+pointer_path.name+".tmp");tmp.write_text(json.dumps(pointer,ensure_ascii=False,indent=2)+"\n","utf8");os.replace(tmp,pointer_path)
    return {"status":status,"path":str(target),"identity":identity["sha256"],"sealed_dates":len(dates),"outcomes":len(outcomes),"groups":len(result)}
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,indent=2))

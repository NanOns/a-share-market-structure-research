from __future__ import annotations
import hashlib,json,os,tempfile,shutil
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from .observation import transition

LIVE_CONTRACT_VERSION="r4-live-daily-forward-capture-v1.2-model-preflight"
ORCHESTRATION_ORDER=("RESOLVE_VALID_TDX_CUTOFF","RUN_VERIFY_V1","RUN_FROZEN_V2_STRUCTURES","RUN_FROZEN_V2_PRIORITY","VERIFY_IDENTITIES_CONTRACTS","APPEND_FORWARD_OBSERVATION","COMPUTE_STATE_TRANSITIONS","SETTLE_DUE_OUTCOMES","PUBLISH_DAILY_RECEIPT")
HORIZONS=(1,5,10,20)

def live_event(resolved_cutoff,latest_forward_cutoff,source_identity,latest_source_identity):
    if str(resolved_cutoff)>str(latest_forward_cutoff): return "NEW_DAILY_FORWARD_CAPTURE"
    if str(resolved_cutoff)==str(latest_forward_cutoff) and source_identity==latest_source_identity:return "VERIFIED_NO_NEW_FORWARD_OBSERVATION"
    if str(resolved_cutoff)==str(latest_forward_cutoff):return "SAME_CUTOFF_SOURCE_REVISION"
    raise RuntimeError("HISTORICAL_BACKFILL_BLOCKED")

def states_for_union(prior,current,ever_seen=(),*,same_cutoff_revision=False,model_identity_same=True,data_unavailable=()):
    prior={x["security_id"]:x for x in prior};current={x["security_id"]:x for x in current};seen=set(ever_seen);unavailable=set(data_unavailable);out=[]
    for sid in sorted(set(prior)|set(current)):
        p,c=prior.get(sid),current.get(sid)
        state=transition(p,c,sid in seen,same_cutoff_revision,sid not in unavailable,model_identity_same)
        out.append({"security_id":sid,"candidate_state":state,"prior":p,"current":c})
    return out

def due_horizons(signal_sequence_index,current_sequence_index,settled=()):
    age=current_sequence_index-signal_sequence_index
    return [h for h in HORIZONS if h<=age and h not in set(settled)]

def target_for_horizon(sealed_dates,signal_date,horizon):
    dates=list(sealed_dates)
    if signal_date not in dates:raise RuntimeError("SIGNAL_NOT_IN_FORWARD_SEQUENCE")
    i=dates.index(signal_date)+horizon
    return dates[i] if i<len(dates) else None

def assert_target_in_sequence(target_date,sealed_dates):
    if target_date not in set(sealed_dates):raise RuntimeError("OUTCOME_SOURCE_NOT_SEALED")
    return True

def outcome_identity(row):
    return hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def outcome_replay(existing,proposed):
    key=lambda x:(x.get("security_id"),x["signal_observation_id"],int(x["horizon"]),int(x["target_revision"]))
    if key(existing)!=key(proposed):return "APPEND"
    return "VERIFIED_IDEMPOTENT" if outcome_identity(existing)==outcome_identity(proposed) else "CONFLICT_BLOCKED"

def atomic_json(path,payload):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=path.parent,prefix="."+path.name,suffix=".tmp")
    try:
        with os.fdopen(fd,"w",encoding="utf8") as f:json.dump(payload,f,ensure_ascii=False,indent=2,sort_keys=True);f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    except Exception:
        try:os.unlink(tmp)
        except OSError:pass
        raise

def _complete_revision(root,cutoff,path):
    report=Path(root)/"reports/forward"/str(cutoff)/path.name
    data_complete=(path/"FORWARD_OBSERVATION.parquet").is_file() and (path/"OBSERVATION_IDENTITY.json").is_file()
    live_complete=(report/"DAILY_FORWARD_CAPTURE_RECEIPT.json").is_file() and (report/"manifest.json").is_file()
    legacy_baseline=(report/"R4_00_BASELINE_RECEIPT.json").is_file() and (report/"FORWARD_OBSERVATION_SUMMARY.json").is_file()
    if not data_complete or not (live_complete or legacy_baseline):return False
    try:
        identity=json.loads((path/"OBSERVATION_IDENTITY.json").read_text("utf8"));expected=identity.get("parquet_sha256")
        if expected and expected!=hashlib.sha256((path/"FORWARD_OBSERVATION.parquet").read_bytes()).hexdigest():return False
        if live_complete:
            manifest=json.loads((report/"manifest.json").read_text("utf8"))
            for name,digest in manifest.get("files",{}).items():
                candidate=(path/name) if (path/name).is_file() else (report/name)
                if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest()!=digest:return False
        return True
    except (OSError,ValueError,TypeError):return False

def latest_revision(root,cutoff):
    base=Path(root)/"data/forward/observations"/str(cutoff)
    revisions=sorted((p for p in base.glob("revision_*") if p.is_dir() and _complete_revision(root,cutoff,p)),key=lambda p:int(p.name.split("_")[-1]))
    return revisions[-1] if revisions else None

def next_revision_number(root, cutoff):
    """Allocate after every occupied revision, including invalid evidence.

    Readers ignore incomplete or hash-invalid revisions, but writers must never
    reuse their directory number because those files remain audit evidence.
    """
    root=Path(root);numbers=set()
    for base in (root/"data/forward/observations"/str(cutoff),root/"reports/forward"/str(cutoff)):
        if not base.is_dir():continue
        for path in base.glob("revision_*"):
            if not path.is_dir():continue
            suffix=path.name.removeprefix("revision_")
            if suffix.isdigit():numbers.add(int(suffix))
    return max(numbers,default=0)+1

def sealed_sequence(root):
    base=Path(root)/"data/forward/observations";return sorted(p.name for p in base.iterdir() if p.is_dir() and latest_revision(root,p.name))

def read_observation(path):
    path=Path(path);parquet=path/"FORWARD_OBSERVATION.parquet";identity_path=path/"OBSERVATION_IDENTITY.json"
    if not parquet.is_file() or not identity_path.is_file():raise RuntimeError("INCOMPLETE_FORWARD_OBSERVATION")
    identity=json.loads(identity_path.read_text("utf8"));actual=hashlib.sha256(parquet.read_bytes()).hexdigest()
    if identity.get("parquet_sha256") and identity["parquet_sha256"]!=actual:raise RuntimeError("FORWARD_OBSERVATION_HASH_MISMATCH")
    return pq.read_table(parquet).to_pandas().to_dict("records")

def frame_identity(frame):
    payload=pd.util.hash_pandas_object(frame,index=False).values.tobytes()+"\x1f".join(map(str,frame.columns)).encode()
    return hashlib.sha256(payload).hexdigest()

def make_observation_rows(board,prior,ever_seen,cutoff,revision,observation_id,same_revision=False,prices=None):
    price_map={x["security_id"]:x for x in ([] if prices is None else prices.to_dict("records"))}
    union_ids=set(board.security_id.astype(str))|{x["security_id"] for x in prior}
    unavailable=() if prices is None else union_ids-set(price_map)
    states=states_for_union(prior,board.to_dict("records"),ever_seen,same_cutoff_revision=same_revision,data_unavailable=unavailable);rows=[]
    for item in states:
        source=item["current"] or item["prior"];row=dict(source);row.update(price_map.get(item["security_id"],{}));row.update(observation_date=str(cutoff),source_revision_id=int(revision),candidate_state=item["candidate_state"],comparison_universe=True,active_candidate=item["current"] is not None,observation_id=observation_id,structure_changed=item["candidate_state"]=="STRUCTURE_CHANGED");rows.append(row)
    return pd.DataFrame(rows)

def outcome_stats(rows):
    rows=list(rows);return {"due":len(rows),"observed":sum(x.get("outcome_status")=="OBSERVED" for x in rows),"pending":sum(x.get("outcome_status")=="PENDING" for x in rows),"unavailable":sum(x.get("outcome_status")=="DATA_UNAVAILABLE" for x in rows),"idempotent":0}

def publish_observation(root,cutoff,revision,frame,identity,receipt,fail_before_commit=False,outcome_rows=()):
    root=Path(root);data_target=root/f"data/forward/observations/{cutoff}/revision_{revision}";report_target=root/f"reports/forward/{cutoff}/revision_{revision}"
    expected_frame_identity=frame_identity(frame)
    if data_target.exists() or report_target.exists():
        # A process may stop between the two directory renames. Readers ignore such
        # revisions; a retry removes only that uncommitted pair and rebuilds it.
        if data_target.exists()!=report_target.exists():
            shutil.rmtree(data_target,ignore_errors=True);shutil.rmtree(report_target,ignore_errors=True)
        else:
            old=json.loads((data_target/"OBSERVATION_IDENTITY.json").read_text("utf8")) if (data_target/"OBSERVATION_IDENTITY.json").exists() else {}
            if _complete_revision(root,cutoff,data_target) and old.get("observation_id")==identity["observation_id"] and old.get("frame_identity_sha256")==expected_frame_identity:
                read_observation(data_target);return "VERIFIED_IDEMPOTENT"
            raise RuntimeError("OBSERVATION_CONFLICT_BLOCKED")
    (root/"runtime").mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix="r4_live_",dir=root/"runtime"));ds=stage/"data";rs=stage/"report";ds.mkdir();rs.mkdir()
    try:
        parquet=ds/"FORWARD_OBSERVATION.parquet";pq.write_table(pa.Table.from_pandas(frame,preserve_index=False),parquet,compression="zstd")
        identity={**identity,"frame_identity_sha256":expected_frame_identity,"parquet_sha256":hashlib.sha256(parquet.read_bytes()).hexdigest()};atomic_json(ds/"OBSERVATION_IDENTITY.json",identity)
        atomic_json(ds/"OUTCOME_BATCH.json",{"cutoff":str(cutoff),"revision":int(revision),"rows":[{**row,"outcome_identity":outcome_identity(row)} for row in outcome_rows]})
        counts=frame.candidate_state.value_counts().to_dict();bands=frame.shadow_research_band.value_counts().to_dict() if "shadow_research_band" in frame else {}
        atomic_json(rs/"FORWARD_OBSERVATION_SUMMARY.json",{"cutoff":cutoff,"revision":revision,"rows":len(frame),"state_counts":counts,"research_band_counts":bands});atomic_json(rs/"STATE_TRANSITION_AUDIT.json",{"pass":True,"state_counts":counts});atomic_json(rs/"DUE_OUTCOME_AUDIT.json",receipt["outcomes"]);atomic_json(rs/"DAILY_FORWARD_CAPTURE_RECEIPT.json",receipt)
        atomic_json(rs/"manifest.json",{"files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in list(ds.iterdir())+list(rs.iterdir())}})
        if fail_before_commit:raise RuntimeError("INJECTED_PRECOMMIT_FAILURE")
        data_target.parent.mkdir(parents=True,exist_ok=True);report_target.parent.mkdir(parents=True,exist_ok=True);os.replace(ds,data_target)
        try:os.replace(rs,report_target)
        except Exception:shutil.rmtree(data_target,ignore_errors=True);shutil.rmtree(report_target,ignore_errors=True);raise
        return "PUBLISHED"
    finally:shutil.rmtree(stage,ignore_errors=True)

def append_outcomes(root,rows):
    target=Path(root)/"data/forward/outcomes";target.mkdir(parents=True,exist_ok=True);stats=outcome_stats(rows);stats.update(observed=0,pending=0,unavailable=0)
    for value in rows:
        row=dict(value);row["outcome_identity"]=outcome_identity(row);sid=str(row.get("security_id","SNAPSHOT")).replace(".","_");p=target/f'{row["signal_observation_id"]}_{sid}_T{row["horizon"]}_R{row["target_revision"]}.json'
        if p.exists():
            status=outcome_replay(json.loads(p.read_text("utf8")),row)
            if status=="CONFLICT_BLOCKED":raise RuntimeError(status)
            stats["idempotent"]+=1
        else:atomic_json(p,row);stats["observed"]+=int(row.get("outcome_status")=="OBSERVED");stats["unavailable"]+=int(row.get("outcome_status")=="DATA_UNAVAILABLE")
    return stats

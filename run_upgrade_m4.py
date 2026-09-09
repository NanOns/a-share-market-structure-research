from __future__ import annotations
import json, os, subprocess, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"reports/upgrade_m4"
sys.path.insert(0,str(ROOT/"src"))
from workbench_db import WorkbenchRepository
from workbench_input import verify_source_bundle

def main():
    result=subprocess.run([sys.executable,"-m","pytest","-v","tests/upgrade_m4"],cwd=ROOT,text=True,capture_output=True)
    output=(result.stdout+result.stderr).strip()
    with WorkbenchRepository(ROOT) as repo:
      con=repo.connection
      bundles=con.execute("SELECT source_bundle_id,payload_json FROM source_bundles").fetchall()
      latest_bundle=max(bundles,key=lambda x:(json.loads(x[1]).get('target_trade_date',''),(ROOT/'data/source_bundles'/x[0]/'source_bundle.json').stat().st_mtime_ns))[0]
      latest_head=con.execute("""
        SELECT h.trade_date,h.publication_id
        FROM publication_heads h
        JOIN publications p USING(publication_id)
        WHERE p.status='SUCCESS'
        ORDER BY h.trade_date DESC
        LIMIT 1
      """).fetchone()
      if not latest_head:
          raise RuntimeError("M4_REAL_PUBLICATION_HEAD_MISSING")
      real_trade_date,real_pub=latest_head
      real_counts={name:con.execute(f"SELECT count(*) FROM {name} WHERE publication_id=?",[real_pub]).fetchone()[0] for name in ("stock_daily","sector_daily","candidate_daily","structure_details","queue_memberships","unified_board","queue_rankings")}
      membership_count=con.execute("SELECT count(*) FROM membership_entries e JOIN publication_memberships p USING(membership_snapshot_id) WHERE p.publication_id=?",[real_pub]).fetchone()[0]
      source_path=con.execute("SELECT source_path FROM publications WHERE publication_id=?",[real_pub]).fetchone()[0]
      snapshot=con.execute("SELECT s.membership_snapshot_id,s.logical_sha256,s.row_count FROM publication_memberships p JOIN membership_snapshots s USING(membership_snapshot_id) WHERE p.publication_id=?",[real_pub]).fetchone()
      active_jobs=con.execute("SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING','INTERRUPTED')").fetchone()[0]
    checks={
      "background_job": result.returncode==0 and "test_background_submit_returns_job_and_finishes PASSED" in output,
      "transactional_crash_recovery": result.returncode==0 and "test_crash_before_commit_has_no_half_publication_and_retry_is_clean PASSED" in output and "test_crash_after_commit_recovers_without_duplicate_observation PASSED" in output,
      "same_day_idempotency": result.returncode==0 and "test_same_day_same_identity_is_idempotent PASSED" in output,
      "forward_no_duplicate": result.returncode==0 and "test_crash_after_commit_recovers_without_duplicate_observation PASSED" in output,
      "audited_same_day_revision": result.returncode==0 and "test_same_day_different_model_creates_audited_revision PASSED" in output,
      "identity_guard": result.returncode==0 and "test_invalid_compute_result_fails_before_publication PASSED" in output,
      "bundle_and_forward_binding": result.returncode==0 and "test_missing_bundle_and_dangling_outcome_are_blocked PASSED" in output,
      "restart_recovery": result.returncode==0 and "test_restart_recovers_persisted_request_and_creates_new_attempt PASSED" in output,
      "all_result_groups_transactional": result.returncode==0 and "test_all_workbench_result_groups_commit_together PASSED" in output,
      "workbench_one_click_command": result.returncode==0 and "test_workbench_post_returns_job_and_get_reads_status PASSED" in output,
      "controlled_compute_subprocess": result.returncode==0 and "test_controlled_compute_uses_fixed_project_entry_and_timeout PASSED" in output,
      "real_bundle_end_to_end_publication": all(real_counts.values()) and membership_count>0 and Path(source_path).resolve()==(ROOT/'data/source_bundles'/latest_bundle).resolve() and verify_source_bundle(ROOT/'data/source_bundles'/latest_bundle/'source_bundle.json')['status']=='PASS',
      "membership_snapshot_identity": bool(snapshot and snapshot[0]==snapshot[1] and snapshot[2]==membership_count),
      "no_unrecovered_jobs": active_jobs==0,
    }
    status="FULL_PASS" if all(checks.values()) else "BLOCKED"
    receipt={"phase":"M4","contract_version":"m4-one-click-publication-contract-v1.2","created_at_utc":datetime.now(timezone.utc).isoformat(),"checks":checks,"real_trade_date":str(real_trade_date),"real_publication_id":real_pub,"real_publication_counts":{**real_counts,"membership_entries":membership_count},"active_job_count":active_jobs,"test_output":output,"final_status":status,"next_stage":"M5_OPERATIONS" if status=="FULL_PASS" else None}
    REPORT.mkdir(parents=True,exist_ok=True)
    def atomic(path,text):
      temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');temporary.write_text(text,encoding='utf-8');os.replace(temporary,path)
    atomic(REPORT/"M4_ONE_CLICK_PUBLICATION_RECEIPT.json",json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
    atomic(REPORT/"M4_ONE_CLICK_PUBLICATION.md",f"# M4 一键发布验收\n\n- 状态：`{status}`\n- 测试：`{output}`\n- 下一阶段：`{receipt['next_stage'] or '禁止进入'}`\n")
    print(json.dumps(receipt,ensure_ascii=False,indent=2)); return 0 if status=="FULL_PASS" else 1
if __name__=="__main__": raise SystemExit(main())

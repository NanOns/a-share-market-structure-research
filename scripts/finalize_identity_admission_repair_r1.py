"""Exact-byte closeout before commit; archive remains outside the workspace."""
import sys, os, json, hashlib, zipfile
from pathlib import Path
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.record_next_stage_contract_r1 import text
from scripts.record_identity_admission_repair_contract_r1 import OUT
from workbench_analysis.v4_14_replay_io import ref, publish


def main():
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    junit=Path('G:/codex_tmp/IDENTITY_ADMISSION_FINAL_JUNIT.xml').read_bytes()
    xml=ElementTree.fromstring(junit)
    suites=list(xml.iter('testsuite'))
    totals={key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','errors','failures','skipped')}
    assert totals==dict(tests=123,errors=0,failures=0,skipped=0)
    text(OUT+'/IDENTITY_ADMISSION_FINAL_JUNIT.xml',junit)
    previous=json.loads((ROOT/'docs/evidence/v4_current_snapshot_r4_20261010/CROSS_CUTTING_AUDIT_ITEMS.json').read_bytes())
    publish(ROOT,OUT+'/CROSS_CUTTING_AUDIT_ITEMS.json',dict(
        inherited=previous,inheritance_source=ref(ROOT,'docs/evidence/v4_current_snapshot_r4_20261010/CROSS_CUTTING_AUDIT_ITEMS.json'),
        Amount_A_precise_status=ref(ROOT,'docs/evidence/v4_immediate_r3_20261010/04_P0_AMOUNT/P0_AMOUNT_AUDIT_STATUS.json'),
        stage_gate_cannot_close_comprehensive_items=True,
        new_items=[dict(id='IDENTITY-TRUSTED-SERVICE/R1',scope='Actual dated Identity issuer/revocation/source/CAS authority',status='OPEN_INDEPENDENT_ACCEPTANCE',evidence=ref(ROOT,OUT+'/B_IDENTITY_AUTHORITY_PRODUCER.md'),acceptance='Independent real service deployment and target-day original provenance, explicit publication authorization'),
                   dict(id='STATE-TRUSTED-SERVICE/R1',scope='Actual State/Membership/Model/Event/Benchmark accepted review source',status='OPEN_INDEPENDENT_ACCEPTANCE',evidence=ref(ROOT,OUT+'/STATE_REAL_SOURCE_REQUIREMENTS.json'),acceptance='Accepted independent issuer service; real source binding passed to unchanged Bridge; formal source/date/clock/CAS QA')]))
    contract=json.loads((ROOT/OUT/'STAGE_CONTRACT.json').read_bytes())
    assert all(ref(ROOT,p)==b for p,b in contract['protected_heads_before'].items())
    publish(ROOT,OUT+'/ENGINEERING_ACCEPTANCE.json',dict(
        contract_id='IDENTITY_ADMISSION_REPAIR_ENGINEERING_ACCEPTANCE_R1',validation=totals,
        protected_heads_unchanged=True,TDX_written=False,production_pid=42552,
        production_restart=False,runtime_new_module_loading=False,production_write_authorized=False,
        actual_t0_status='WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER',
        blockers=['REAL_NEW_SESSION_SOURCE_NOT_OCCURRED','ACCEPTED_IDENTITY_AND_STATE_REVIEW_SERVICES_NOT_DEPLOYED','PRODUCTION_MODULE_LOADING_REQUIRES_SEPARATE_SCOPE_AUTHORIZATION_AND_ACCEPTANCE'],
        stage_engineering='PASS',release_readiness=False,
        external_FP13_scope_signoff='PENDING',browser='BLOCKED_BROWSER_ENV',
        next_stage='Independent scope review; actual 10/12 first capture and source/Identity/Member/GBBQ/State/Episode/CAS field QA only within separately authorized scope',
        note='Later-clock candidate retry now preserves the immutable first freeze; synthetic fixture paths and pytest helper return warnings were corrected before this final run.'))
    text(OUT+'/FINAL_VALIDATION_ADDENDUM.md',('''# 最终定点验证补充

最终联合回归 123 passed，0 failures/errors/skipped，见 IDENTITY_ADMISSION_FINAL_JUNIT.xml。新增实际稍后时钟重试检验：同原件重试保留第一次 candidate frozen_at 和所有原始字节。8 个门函数 Oracle 改为 helper，由 pytest wrapper 调用，最终运行无返值警告。

两 Head SHA 不变；生产进程 PID 42552 仍在，未重启，当前生产未加载本轮新模块。真实 T0 唯一状态 WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER。综合审计仍独立开放，源码测试通过不能替代真实审查服务或浏览器外部签收。

Drive 报告已回读：id 1B4DY6I-mf2UXNAHRzXQ5czbxZfvrbE4e，2097 bytes，SHA256 3c711f48b9b59c2418f2b534205978cac1b69b640bf5ae3b799382e619759020，与 REPORT.md 原始字节相同。轻证据包包含此补充和最终 JUnit；Git/ZIP 最终回读另附收据。
''').encode('utf-8'))
    scoped=[ROOT/'.gitattributes']+list((ROOT/OUT).rglob('*'))
    names=['src/workbench_analysis/operational_daily_executor_v1.py','src/workbench_analysis/source_readiness_v2.py','src/workbench_analysis/dated_identity_candidate_v1.py','src/workbench_analysis/trusted_source_review_v1.py','src/workbench_analysis/state_trusted_review_candidate_v1.py','src/sector/episode_genesis_candidate_v2.py','tests/test_next_t0_old_identity_preflight.py','tests/test_dated_identity_candidate_v1.py','tests/test_identity_gate_reason_r2.py','tests/test_state_trusted_review_candidate_v1.py','tests/test_followup_semantics_r2.py','scripts/record_identity_admission_repair_contract_r1.py','scripts/record_identity_admission_repair_evidence_r1.py','scripts/finalize_identity_admission_repair_r1.py']
    scoped+=[ROOT/n for n in names]
    files=sorted({p for p in scoped if p.is_file() and p.suffix not in ('.lock',)},key=str)
    manifest={p.relative_to(ROOT).as_posix():ref(ROOT,p.relative_to(ROOT)) for p in files}
    publish(ROOT,OUT+'/EXACT_BYTE_MANIFEST.json',dict(contract_id='EXACT_BYTES_REPAIR_MANIFEST_R1',files=manifest,self_excluded=True))
    files.append(ROOT/OUT/'EXACT_BYTE_MANIFEST.json')
    archive=Path('G:/codex_tmp/V4_IDENTITY_ADMISSION_REPAIR_R1_20261010.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for p in files:package.write(p,p.relative_to(ROOT).as_posix())
    print(json.dumps(dict(tests=totals,files=len(files),archive=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),bytes=archive.stat().st_size)))


if __name__=='__main__':main()

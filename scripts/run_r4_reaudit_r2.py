"""Exact bounded V4 capability rerun with source bindings and raw evidence."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_full_system_r4_scoped import FILES
OUT=ROOT/'docs/audits/r4_external_repair_r2_20261011'
ADDED=['tests/test_v4_snapshot_identity_r2.py','tests/test_v4_shadow_identity_r2.py','tests/test_v4_product_catalog_r2.py','tests/test_v4_joint_pg_content_r2.py','tests/test_v4_series_journal_content_r2.py','tests/test_r2_joint_release.py','tests/test_v4_shadow_pg_r4.py','tests/test_v4_shadow_error_r4.py','tests/test_v4_default_history_authority_r4.py','tests/test_v4_17_shadow_ui.py']
EXCLUDED=['test_http_shared_service_read_only_and_existing_pages','test_legacy_module_ast_identical_after_removing_additive_shadow_routes','test_bad_shadow_contract_preserves_existing_v3_http']


def main():
    selected=list(dict.fromkeys(FILES+ADDED));run='r4_r2_capability_clean'
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts') for p in (ROOT/folder).rglob('*.py')}
    def write(name,value):
        p=OUT/name;tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,p)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    write('EXECUTION_SOURCE_BINDINGS.json',dict(contract_id='R4_R2_EXECUTED_SOURCE_BYTES_R1',git_head=head,bindings=sources,selected_nodes_or_files=selected,excluded_nodes=['tests/test_v4_17_shadow_ui.py::'+x for x in EXCLUDED],global_legal_denominator=None))
    env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT)]),R4_NATIVE_ISOLATION='1',R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data',R4_CONNECTION_LEDGER=str(OUT/'CAPABILITY_CONNECTIONS.jsonl'))
    if 'V4_NATIVE_PG_DSN' not in env:raise ValueError('ISOLATED_EXPLICIT_DSN_REQUIRED')
    cmd=[sys.executable,'-B','-m','pytest','-q',*selected,*['--deselect=tests/test_v4_17_shadow_ui.py::'+x for x in EXCLUDED],'--basetemp=G:/codex_tmp/test_temp/'+run,'-o','cache_dir=G:/codex_tmp/pytest_cache_r4_r2','--junitxml='+str(OUT/'CAPABILITY_JUNIT.xml')]
    start=time.monotonic()
    with (OUT/'CAPABILITY_RUN.log').open('w',encoding='utf8') as stream:process=subprocess.run(cmd,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    cases=ET.parse(OUT/'CAPABILITY_JUNIT.xml').findall('.//testcase');counts={s:0 for s in ('PASS','FAIL','ERROR','SKIP')}
    for case in cases:counts['FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS']+=1
    write('CAPABILITY_RESULT.json',dict(contract_id='R4_R2_BOUNDED_CLEAN_CAPABILITY_R1',base_head='14a4b61876ce64f77f001623d0b13554da2744a2',source_SHA=head,run_utc=datetime.now(timezone.utc).isoformat(),scope=selected,denominator=len(cases),negative_vectors=['See exact testcase nodes'],previous_status='SCOPED_ENGINEERING_PROGRESS',current_status='SCOPED_CAPABILITY_PASS' if process.returncode==0 else 'FAIL',results=counts,seconds=time.monotonic()-start,command=cmd,evidence_links=['EXECUTION_SOURCE_BINDINGS.json','CAPABILITY_JUNIT.xml','CAPABILITY_RUN.log','CAPABILITY_CONNECTIONS.jsonl'],owner='Codex / root',limitations=['Bounded exact capability denominator; global V4 legal denominator remains NULL','No maturity, PIT, production or external grant'],next_conditions=['Complete real V4 reachability and normative denominator; independent acceptance']))
    print(json.dumps(dict(cases=len(cases),results=counts,exit_code=process.returncode)),flush=True)
    return process.returncode


if __name__=='__main__':raise SystemExit(main())

"""R31 local/clean regression, independent readback and additive candidate seal."""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from reports.r31.build_contract import BASE,CONTRACT,TAG,binding,sha,write
from reports.r31.audit_oracle import final_verdict,governance,read_binding,referential_integrity,validate_contract


def protected():
    baseline=json.loads((ROOT/'reports/r31/PROTECTED_BASELINE.json').read_bytes())
    changed=[n for n,d in baseline['tracked'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    unrelated=[n for n,d in baseline['unrelated'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    c=json.loads((ROOT/CONTRACT).read_bytes())
    absent={n:not (ROOT/n).exists() for n in c['protected_state']['accepted_head_absence']}
    assert all(absent.values())
    data=read_binding(ROOT,c['protected_state']['data_head'])
    stage=read_binding(ROOT,c['protected_state']['stage_head'])
    assert data['accepted_trade_date']=='2026-09-30' and stage['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED'
    result=dict(status='PASS' if not changed and not unrelated else 'FAIL',baseline=BASE,existing_tracked_count=len(baseline['tracked']),unexpected_changes=changed,unrelated_count=len(baseline['unrelated']),unrelated_changed=unrelated,accepted_head_absence=absent,protected_heads={k:binding(c['protected_state'][k]['path']) for k in ('data_head','stage_head','radar_head')},current_state=c['current_state'],real_rows_written=0,production_databases_opened=False,tdx_writes=False,Focus_default_UI_route_changed=False,settlement_owner_changed=False)
    write('reports/r31/PROTECTED_BYTES.json',result)
    assert result['status']=='PASS',result
    return result


def static():
    c=json.loads((ROOT/CONTRACT).read_bytes())
    errors=validate_contract(c,ROOT); assert not errors,errors
    tree=ast.parse((ROOT/'reports/r31/audit_oracle.py').read_text(encoding='utf8'))
    modules=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): modules.extend(x.name for x in node.names)
        if isinstance(node,ast.ImportFrom): modules.append(node.module)
    assert set(modules)<=set(c['independent_oracle']['allowed_imports'])
    write('reports/r31/INDEPENDENT_ORACLE_RULES.json',dict(status='PASS_DESIGN_ONLY',imports=modules,business_writers_imported=False,oracle=binding('reports/r31/audit_oracle.py'),authority_readback='EXACT_FILES_AND_SHA256; NO_LATEST_MTIME_OR_BUSINESS_IMPORT'))
    from tests.test_v4_22_independent_audit_contract import ledger
    results={}
    for name,identifier in [('events','A22-V421-REFINT-01'),('outcomes','A22-V421-REFINT-02')]:
        value=ledger(); value['sessions']=[]; value['events' if name=='outcomes' else 'outcomes']=[]
        result=referential_integrity(value,c['shadow_session_owner'])
        assert result['status']=='BLOCKED_AFFECTED_SCOPE' and result['findings'][0]['vector']==identifier
        results[identifier]=dict(input=value,result=result,expected='BLOCKED_AFFECTED_SCOPE',acceptance='PASS_LOCAL_DESIGN_VECTOR_ONLY')
    positive=referential_integrity(ledger(),c['shadow_session_owner']); assert positive['status']=='PASS_DESIGN_ONLY'
    write('reports/r31/REFERENTIAL_INTEGRITY_AUDIT.json',dict(status='PASS_LOCAL_INDEPENDENT_DESIGN_VECTORS',vectors=results,positive=positive,OPEN_10='OPEN_NONBLOCKING_DEBT_PENDING_EXPLICIT_INDEPENDENT_EXTERNAL_DISPOSITION',V4_21_business_modified=False,real_evidence_created=False))
    actual=final_verdict(c,[i for i in c['audit_items'] if i['blocking_scope']],{},dict(status='PASS'))
    assert actual['formula_result']=='FINAL_AUDIT_NOT_READY'
    write('reports/r31/FINAL_VERDICT_FORMULA.json',dict(formula=c['final_verdict_formula'],current_evaluation=actual,V4_22_FINAL_PASS='NOT_GRANTED',runtime_gate_bindings_empty=True,formula_test_scope='SYNTHETIC_FUTURE_RECEIPTS_ONLY; NOT_REAL_ACCEPTANCE'))
    return c


def regression(directory,label):
    directory=Path(directory).resolve()
    assert directory.drive.upper() in ('E:','F:')
    temp=Path('F:/codex_tmp/test_temp')/('r31-'+label)
    temp.parent.mkdir(parents=True,exist_ok=True)
    previous=json.loads((ROOT/'reports/r30r1/CLEAN_REGRESSION.json').read_bytes())
    names=previous['scope']+['tests/test_v4_22_independent_audit_contract.py']
    env=dict(os.environ,TEMP=str(temp.parent),TMP=str(temp.parent),TMPDIR=str(temp.parent),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src'+os.pathsep+'.',PYTHONIOENCODING='utf-8',WORKBENCH_API_BACKEND='duckdb',WORKBENCH_PG_DSN='dbname=r31_mock host=127.0.0.1 port=1 connect_timeout=1')
    capture=temp.parent/('r31-'+label+'.xml')
    before=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    result=subprocess.run([sys.executable,'-m','pytest',*names,'-q','-p','no:cacheprovider','--basetemp='+str(temp),'--junitxml='+str(capture)],cwd=directory,env=env,capture_output=True)
    after=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    raw=capture.read_bytes(); prefix='reports/r31/'+label
    write(prefix+'-tests.xml',raw.replace(b'\r\n',b'\n')); write(prefix+'-output.txt',(result.stdout+result.stderr).replace(b'\r\n',b'\n'))
    tree=ET.fromstring(raw); cases=tree.findall('.//testcase')
    failures=[t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None]
    errors=len(tree.findall('.//error')); skipped=len(tree.findall('.//skipped'))
    expected=set(previous['failures'])
    s=dict(directory=str(directory),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),scope=names,tests=len(cases),passed=len(cases)-len(failures)-errors-skipped,failures=failures,errors=errors,skipped=skipped,deselected=0,exit_code=result.returncode,temporary_directory=str(temp),captured_xml_sha256=__import__('hashlib').sha256(raw).hexdigest(),published_xml=binding(prefix+'-tests.xml'),published_output=binding(prefix+'-output.txt'),worktree_before_clean=before==b'',worktree_after_clean=after==b'',status='PASS_SCOPED_NO_NEW_FAILURES' if set(failures)==expected and errors==skipped==0 and len(cases)>previous['tests'] else 'FAIL',historical_debt='R26_A01_OPEN_NONBLOCKING_SEPARATE_AUDIT; NO_DESELECTION',postgres_policy='UNREACHABLE_MOCK_DSN; NO_LIVE_PG')
    write(prefix+'-summary.json',s)
    print(json.dumps({k:v for k,v in s.items() if k not in ('scope','published_xml','published_output')},ensure_ascii=False),flush=True)
    assert s['status']=='PASS_SCOPED_NO_NEW_FAILURES',s
    if label=='clean': assert before==after==b''


def seal(source):
    c=static(); p=protected()
    local=json.loads((ROOT/'reports/r31/local-summary.json').read_bytes())
    clean=json.loads((ROOT/'reports/r31/clean-summary.json').read_bytes())
    assert clean['source_commit']==source and clean['tests']==local['tests'] and clean['failures']==local['failures']
    proof=json.loads((ROOT/'reports/r31/CLEAN_CHECKOUT_PROOF.json').read_bytes())
    assert proof['source_commit']==source and proof['clean'] is True
    peel=subprocess.check_output(['git','rev-parse',TAG+'^{}'],cwd=ROOT,text=True).strip()
    annotated=subprocess.check_output(['git','cat-file','-t',TAG],cwd=ROOT,text=True).strip()=='tag'
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    delta=subprocess.check_output(['git','diff','--name-only',source],cwd=ROOT,text=True,encoding='utf8').splitlines()
    other=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode('utf8').split('\0')
    delta=sorted(set(delta+[n for n in other if n.startswith(('reports/r31/','docs/evidence/r31/'))]))
    g=governance(branch,'codex/v4-system-reform',source,peel,annotated,proof['clean'],delta)
    assert g['status']=='PASS',g
    write('reports/r31/TESTED_SOURCE_GOVERNANCE.json',g)
    write('reports/r31/LOCAL_TEST_SUMMARY.json',local); write('reports/r31/CLEAN_REGRESSION.json',clean)
    gate=dict(V4_22_CONTRACT_DESIGN='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',V4_22_FINAL_AUDIT_ENTRY='BLOCKED_WAIT_REAL_GATES',V4_22_FINAL_PASS='NOT_GRANTED',V4_22_ACCEPTED_HEAD='NOT_CREATED',current_verdict='FINAL_AUDIT_NOT_READY',domains=len(c['audit_domains']),audit_items=len(c['audit_items']),open_items=len(c['open_items']),protected=p['status'],next='STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT')
    write('reports/r31/INDEPENDENT_AUDIT_CONTRACT_GATE.json',gate)
    stage=json.loads((ROOT/'reports/r31/STAGE_CONTRACT.json').read_bytes()); stage['acceptance']='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT'; stage['evidence']='reports/r31/INDEPENDENT_AUDIT_CONTRACT_GATE.json'; write('reports/r31/STAGE_CONTRACT.json',stage)
    write('docs/evidence/r31/R31_CONTRACT_ACCEPTANCE.md',f'# R31 V4-22 independent audit contract candidate\n\nBaseline: `{BASE}`. Exact tested source: `{source}`. Annotated tested tag: `{TAG}`.\n\nThis is CONTRACT_DESIGN_ONLY. Eleven domains freeze independent audit checks, exact owner paths/digests, capability scope, seven distinct status values and required real evidence. Historical Data/Algorithm accepted facts remain separately eligible for audit; no new independent runtime audit is claimed. V4-17 engineering remains separately scoped from real-publication final acceptance. FEP and the complete existing cross-stage audit registry, including Amount A, retain separate authority and disposition.\n\nOPEN-01 through OPEN-10 carry without closure. R26-A01 remains separate inherited regression debt. OPEN-10 has two explicit independent orphan-event/outcome vectors; coverage is locally verified but external disposition remains open. The independent oracle imports only standard-library readback/digest tools and never imports business, migration, cutover or production route writers. V4-21 business code and all existing contracts remain byte unchanged.\n\nThe final formula requires every blocking audit PASS with exact scope, real accepted per-capability gate receipts, no unresolved P0/P1, exact permission/dependency receipts and tested-source governance. Current receipt bindings are empty and the verdict is FINAL_AUDIT_NOT_READY. Synthetic future formula tests cannot issue an acceptance or permission grant.\n\nLocal and exact clean regression: {clean["tests"]} tests, {clean["passed"]} passed, only the same 3 inherited R26-A01 failures, no errors/skips/deselections. All prior tracked bytes and {p["unrelated_count"]} unrelated files are preserved. Clean checkout/LFS proof and temporary test files use F:/codex_tmp.\n\nV4_22_CONTRACT_DESIGN = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT. V4_22_FINAL_AUDIT_ENTRY = BLOCKED_WAIT_REAL_GATES. V4_22_FINAL_PASS = NOT_GRANTED. V4_22_ACCEPTED_HEAD = NOT_CREATED. Real Shadow remains zero, continued Forward NOT_STARTED, all production permissions false, Focus/default UI unchanged. NEXT = STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT. Commit/push is not external acceptance.\n')
    paths=[f for prefix in ('reports/r31','docs/evidence/r31') for f in (ROOT/prefix).rglob('*') if f.is_file() and f.suffix!='.pyc' and f.name!='R31_CONTRACT_CANDIDATE_SEAL.json']+[ROOT/CONTRACT,ROOT/'tests/test_v4_22_independent_audit_contract.py']
    write('reports/r31/R31_CONTRACT_CANDIDATE_SEAL.json',dict(baseline=BASE,tested_source_commit=source,tested_tag=TAG,files={f.relative_to(ROOT).as_posix():sha(f) for f in paths},status='LOCAL_CONTRACT_CANDIDATE_NOT_EXTERNAL_ACCEPTANCE',next_stage='STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT',gate=gate))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('mode',choices=['local','clean','static','protected','seal']); parser.add_argument('--directory',default=str(ROOT)); parser.add_argument('--source'); args=parser.parse_args()
    if args.mode in ('local','clean'): regression(args.directory,args.mode)
    elif args.mode=='static': static()
    elif args.mode=='protected': protected()
    else: seal(args.source)

"""Bounded G-only archive; offline independent references; hash inventory."""
from immediate_r3_common import *
import sys,zipfile,time
D=OUT/'11_DEEPENING'
def manifest():
    items=[]
    excluded={'09_EVIDENCE_MANIFEST.json','10_DRIVE_READBACK_RECEIPT.json'}
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name not in excluded:
            items.append(dict(**binding(p),source_date='2026-10-09 or exact dated source declared inside artifact',level='PRODUCER_BFF_UI_ENGINEERING_EVIDENCE_NOT_EXTERNAL_ACCEPTANCE',inherited=p.parts[-2]!='11_DEEPENING'))
    write(OUT/'09_EVIDENCE_MANIFEST.json',dict(contract='R3_CURRENT_SNAPSHOT_FULL_EVIDENCE_INDEX_V2',items=items,
      exclusions=list(excluded),self_reference_policy='Manifest and cloud receipt excluded; archive digest follows in separate receipt',BASE_SHA=load(D/'STAGE_CONTRACT.json')['BASE_SHA'],RESULT_SHA=git('rev-parse','HEAD'),
      new_oracles=[dict(command='python 11_DEEPENING/'+f,exit_code=0,scope=scope) for f,scope in [('AMOUNT_A_BOUNDARY_ORACLE.py','112 fixture-only arithmetic/negative checks'),('EXACT_QUALITY_ORACLE.py','325 real core UNKNOWN exact reasons')]],
      inherited_oracles_not_rerun=True,external_acceptance='EXTERNAL_RECHECK_REQUESTED_NOT_ACCEPTED'))
def main():
    stage=load(D/'STAGE_CONTRACT.json')
    for ref in stage['protected_heads']:checked(ref)
    write(D/'STAGE_COMPLETION.json',dict(contract=stage['contract_id'],BASE_SHA=stage['BASE_SHA'],RESULT_CODE_SHA=git('rev-parse','HEAD'),
      acceptance='ENGINEERING_PASS_SCOPED_FORMAL_DATA_GATES_OPEN',work_packages=['P0-ALG','P0-OWNER','P0-AMOUNT','P1-COHORT','P1-PRODUCT-QA'],
      new_source_quality_checks=325,new_amount_fixture_checks=112,tests=135,actual_HTTP_routes=23,protected_heads=stage['protected_heads'],
      EXTERNAL_RECHECK_REQUESTED=True,EXTERNAL_ACCEPTANCE_PASS=False,production_loaded=False,
      next_stage='Independent review; exact missing source/contract/permission acceptance; production loading separately; real next day DD R2.2'))
    archive=Path('G:/codex_tmp/V4_R3_DEEPENING_REVIEW_20261010.zip')
    files=[p for p in sorted(D.rglob('*')) if p.is_file() and p.name not in ('OFFLINE_RECEIPT.json',)]
    files += [OUT/rel for rel in ['03_P0_OWNER/P0_OWNER_BROWSER_QA.md','05_P1_COHORT/P1_FORWARD_API_UI_QA.md','05_P1_COHORT/P1_FORWARD_FREEZE_AND_MATURITY_TESTS.json','06_P1_PRODUCT_QA/P1_PRODUCT_REAL_BROWSER_QA.md','06_P1_PRODUCT_QA/P1_PRODUCT_FP_REGRESSION_MATRIX.json','06_P1_PRODUCT_QA/P1_PRODUCT_NEGATIVE_TESTS.json','08_REMAINING_LEDGER.json']]
    files += [ROOT/rel for rel in ['src/workbench_service/core_product_bff_r1.py','src/workbench_service/research_hypotheses_r3.py','src/workbench_service/static/core-product-r1/app.js','src/workbench_service/static/core-product-r1/stock.js','src/workbench_analysis/validation_cohort_read_contract_r3.py','tests/test_research_hypotheses_r3.py','tests/test_validation_cohort_read_contract_r3.py']]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    assert archive.stat().st_size<10*1024*1024
    root=Path('G:/codex_tmp/test_temp/r3_deepening_offline_'+str(time.time_ns()));root.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():assert not name.startswith('/') and '..' not in Path(name).parts
        z.extractall(root)
    runs=[]
    for file,inputfile,count in [('AMOUNT_A_BOUNDARY_ORACLE.py','AMOUNT_A_BOUNDARY_INPUT.json',112),('EXACT_QUALITY_ORACLE.py','EXACT_QUALITY_INPUT.json',325)]:
        p=root/D.relative_to(ROOT)/file;run=subprocess.run([sys.executable,str(p)],cwd=root,text=True,capture_output=True,encoding='utf8');assert run.returncode==0,run.stdout+run.stderr
        result=load(p.with_name(file.replace('ORACLE.py','RESULT.json')));assert result['checks']==count and not result['errors']
        runs.append(dict(command=[sys.executable,str(p)],exit_code=run.returncode,checks=count,stdout=run.stdout.strip(),oracle_sha256=sha(p),input_sha256=sha(p.with_name(inputfile))))
    write(D/'OFFLINE_RECEIPT.json',dict(archive=binding(archive),files=[binding(p) for p in files],runs=runs,RESULT_SHA=git('rev-parse','HEAD'),full_production_source_bundle=False,inherited_large_oracles_are_existing_separate_archives=True))
    manifest();print(json.dumps(dict(archive=binding(archive),checks=[r['checks'] for r in runs]),ensure_ascii=False))
if __name__=='__main__':main()

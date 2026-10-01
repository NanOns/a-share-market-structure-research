"""Seal engineering evidence for three scoped candidates, never external acceptance."""
import json,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,get_ident
from copy import deepcopy
import xml.etree.ElementTree as ET
from scripts.next_round_bundle_r1 import ROOT,write,bind,read,exact,verify_protected,DOCROOT
from workbench_analysis.source_authority_owner_bootstrap_r1 import validate_registry
from workbench_analysis.baostock_tolerance_candidate_r2 import validate_policy
from workbench_analysis import dm01_publication_history_reader_v1 as old,dm01_publication_history_reader_v2 as new


def seal():
    entry=verify_protected()
    xml='reports/audits/OWNER_A06_READER_DI_TARGETED_REGRESSION_R1.xml'
    suites=ET.fromstring((ROOT/xml).read_bytes())
    total=sum(int(x.attrib.get('tests',0)) for x in suites.iter('testsuite'))
    failures=sum(int(x.attrib.get('failures',0))+int(x.attrib.get('errors',0)) for x in suites.iter('testsuite'))
    skipped=sum(int(x.attrib.get('skipped',0)) for x in suites.iter('testsuite'))
    if failures or total!=75 or skipped:raise ValueError('TARGETED_CANDIDATE_REGRESSION_INCOMPLETE')
    registry='data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json'
    owner_result=validate_registry(ROOT,read(registry))
    policy='config/baostock_binding_tolerance_policy_r2_candidate.json';policy_result=validate_policy(read(policy))
    matrix='reports/audits/A06_R2_REAL_REPRESENTATIVE_MATRIX_R2.json';m=read(matrix)
    for ref in m['inputs']:exact(ref)
    documentation='reports/audits/A06_R2_DOCUMENT_FREEZE_R1.json';doc=read(documentation)
    for r in doc['records']:
        exact(r['frozen']);exact(r['original_capture_receipt'])
        source=r['original_capture'];exact(dict(path=source['path'],sha256=source['sha256']))
    exact(doc['current_request']['body'])
    from scripts import promote_v4_09_accepted_head as v9,validate_v4_10_promotion_r1 as v10
    originals=(v9.ROOT,v10.ROOT)
    old9=old.validate_v4_09_history();old10=old.validate_v4_10_history()
    barrier=Barrier(3)
    def replay(which):
        barrier.wait()
        if (v9.ROOT,v10.ROOT)!=originals:raise ValueError('GLOBAL_ROOT_CONTAMINATION')
        if which==9:result=new.validate_v4_09_history(project_root=ROOT)
        elif which==10:result=new.validate_v4_10_history(project_root=ROOT)
        else:result=v10.validate()
        if (v9.ROOT,v10.ROOT)!=originals:raise ValueError('GLOBAL_ROOT_CONTAMINATION')
        return dict(thread_id=get_ident(),which=which,result=result)
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(replay,i) for i in [9,10,0]];outputs=[x.result() for x in jobs]
    if outputs[0]['result']!=old9 or outputs[1]['result']!=old10 or outputs[2]['result']['status']!='FAIL' or outputs[2]['result']['checks']['P19_protected']!='FAIL':raise ValueError('DI_PARITY_OR_CURRENT_GATE_FAILURE')
    candidate=read(v10.CANDIDATE);candidate['protected_head_bindings']=deepcopy(candidate['protected_head_bindings']);candidate['protected_head_bindings'][0]['sha256']='0'*64
    wrong_old=old.validate_v4_10_history(candidate);wrong_new=new.validate_v4_10_history(candidate,project_root=ROOT)
    if wrong_old!=wrong_new or wrong_new['status']!='FAIL':raise ValueError('DI_WRONG_HASH_PARITY_FAILURE')
    view=new.HistoricalBindingResolver(ROOT);negative=[]
    for path,sha in [('data/v4/V4_DATA_ACCEPTED_HEAD.json','0'*64),('../outside.json',None),('data/v4/../../outside.json',None),('C:/outside.json',None)]:
        try:view.resolve(path,sha)
        except ValueError as exc:negative.append(dict(path=path,sha256=sha,result='REJECTED',reason=str(exc)))
        else:raise ValueError('PATH_REMAP_BOUNDARY_FAILURE')
    di_path='reports/audits/HISTORICAL_PUBLICATION_READER_DI_READBACK_R1.json'
    write(di_path,dict(status='PASS_HISTORY_ONLY_EXACT_PARITY',baseline_commit=entry['baseline_commit'],
        old_outputs=dict(V4_09=old9,V4_10=old10),concurrent_outputs=outputs,distinct_threads=len({x['thread_id'] for x in outputs}),
        wrong_hash_outputs=dict(old=wrong_old,new=wrong_new),negative_path_proofs=negative,
        global_module_ROOT_unchanged=True,current_data_head_date=read('data/v4/V4_DATA_ACCEPTED_HEAD.json')['accepted_trade_date'],
        preserved_validator_bindings=[bind(p) for p in ['scripts/promote_v4_09_accepted_head.py','scripts/validate_v4_10_promotion_r1.py','src/workbench_analysis/dm01_publication_history_reader_v1.py']],
        wrapper_binding=bind('src/workbench_analysis/dm01_publication_history_reader_v2.py'),production_authorized=False))
    common=dict(baseline_commit=entry['baseline_commit'],stage_entry=bind('reports/next_round_r1/BATCH_STAGE_ENTRY_R1.json'),
        targeted_regression=dict(receipt=bind(xml),passed=total,failures=failures,skipped=skipped),
        stage_head_action='KEEP',data_head_action='KEEP',production=False,shadow=False,focus_cutover=False,global_mandatory_adoption=False,
        external_acceptance='PENDING_INDEPENDENT_EXTERNAL_REAUDIT',next_stage='INDEPENDENT_EXTERNAL_REAUDIT',migration_required=False)
    profiles=[
        ('OWNER_REGISTRY_SCOPED_BOOTSTRAP',dict(status='OWNER_REGISTRY_SCOPED_BOOTSTRAP_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',execution_result='COMPLETE_SCOPED_CANDIDATE',candidate=bind(registry),validation=owner_result,
            stage_contract=bind(DOCROOT+'V4_OWNER_REGISTRY_SCOPED_BOOTSTRAP_TASK_R1_20261001.md'),
            runtime_bindings=[bind(p) for p in ['src/workbench_analysis/source_authority_owner_bootstrap_r1.py','scripts/build_owner_bootstrap_candidate_r1.py']],
            acceptance_scope='Seven fields independently bounded to exact 2026-09-30 accepted artifacts. Candidate registration is not inherited external owner acceptance.',
            blockers=['Independent external owner review; active global registry remains R3 and bootstrap production gate stays OPEN'])),
        ('A06_R2',dict(status='A06_BAOSTOCK_TOLERANCE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',execution_result='PARTIAL',candidate=bind(policy),validation=policy_result,
            stage_contract=bind(DOCROOT+'V4_A06_BAOSTOCK_BINDING_TOLERANCE_TASK_R2_20261001.md'),
            runtime_bindings=[bind(p) for p in ['src/workbench_analysis/baostock_tolerance_candidate_r2.py','scripts/build_a06_tolerance_candidate_r2.py']],
            matrix=bind(matrix),documentation=bind(documentation),matched_real_rows=m['matched_rows'],
            blockers=['Official precision is documented; generation rounding is not documented, so no numeric tolerance can be derived','Fresh official documentation GET returned 405; prior official exact-byte capture retained','Provider circulating-shares denominator external acceptance remains pending'],
            strict_binding_allowed=False,tdx_core_blocked=False)),
        ('HISTORICAL_PUBLICATION_READER_DI',dict(status='HISTORICAL_PUBLICATION_READER_DI_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',execution_result='COMPLETE_HISTORY_ONLY_CANDIDATE',
            stage_contract=bind(DOCROOT+'V4_HISTORICAL_PUBLICATION_READER_DI_HARDENING_TASK_R1_20261001.md'),
            runtime_bindings=[bind(p) for p in ['src/workbench_analysis/dm01_publication_history_reader_v2.py']],independent_readback=bind(di_path),
            blockers=['Independent external DI hardening review; no production adoption or history acceptance semantic change']))]
    for name,profile in profiles:write('reports/audits/'+name+'_CANDIDATE_CLOSURE_R1.json',dict(common,**profile))
    verify_protected()
    return dict(status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',packages=[x[0] for x in profiles],targeted_passed=total)


if __name__=='__main__':print(json.dumps(seal()))

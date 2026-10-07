"""Bind actual execution logs and retain every failure; never infer a green gate."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.full_chain_repair_io import ROOT, write, binding

P='reports/forward_r2_remainder_consolidated_20261007/'
TEMP=Path('E:/codex_tmp')

def run_receipt(name):
    source=TEMP/(name+'.xml')
    if not source.is_file():return None
    cases=[]
    for test in ET.parse(source).getroot().iter('testcase'):
        status=next((s for s in ('failure','error','skipped') if test.find(s) is not None),'passed')
        child=test.find(status)
        cases.append(dict(node=test.attrib['classname']+'::'+test.attrib['name'],status=status,
                          seconds=float(test.attrib.get('time',0)),trace=child.text if child is not None else None))
    files=[]
    for suffix in ('.xml','.log'):
        path=TEMP/(name+suffix)
        if path.is_file():files.append(write(P+'execution/'+path.name,path.read_bytes(),raw=True))
    counts={status:sum(c['status']==status for c in cases) for status in ('passed','failure','error','skipped')}
    return dict(name=name,total=len(cases),counts=counts,cases=cases,artifacts=files,
                acceptance='PASS' if not counts['failure'] and not counts['error'] else 'FAIL')

def build():
    names=['remainder_full_a','remainder_full_b','remainder_full_c','remainder_frozen_b',
           'remainder_pg_tests_c','remainder_pg_tests_fresh','remainder_signal_guard_b',
           'remainder_pg_history_b','remainder_pass_keep_c','remainder_pass_keep_final',
           'remainder_guards_final_b','remainder_final_fixes','remainder_writer_final',
           'remainder_child_final','remainder_api_final','remainder_api_final_b',
           'remainder_frozen_e','remainder_frozen_f','remainder_r24_history',
           'remainder_full_d','remainder_history_recovered_final','remainder_pre16_repr_final',
           'remainder_profile_scope_final','remainder_g_scope_final','remainder_recovered_scope_final',
           'remainder_guards_current_final','remainder_guards_http_final','remainder_history_last_cases','remainder_bounded_g_storage_final','remainder_full_e','remainder_freeze_scope_final','remainder_freeze_scope_final_b','remainder_final_boundary_replays_b','remainder_full_f']
    runs=[r for n in names if (r:=run_receipt(n))]
    write(P+'EXECUTION_RECEIPTS.json',dict(runs=runs))
    pg=[r for r in runs if r['name'] in names[4:8]]
    write(P+'IA06_PG_NEGATIVE_MATRIX.json',dict(runs=pg,
        cluster_manifest=binding(P+'IA06_CLUSTER_BOOTSTRAP.json'),
        populated_upgrade=binding(P+'IA06_POPULATED_UPGRADE_PROOF.json'),
        sql_constraints_relaxed=False,production_cluster_used=False,
        fresh_skip='The one upgrade-owned rollback scenario executes and passes on upgrade, not silently waived'))
    full=[r for r in runs if r['name'].startswith('remainder_full_')]
    write(P+'GLOBAL_PYTEST_RECEIPT.json',dict(runs=full,ignore=[],deselect=[],
        acceptance=full[-1]['acceptance'] if full else 'NOT_RUN',
        latest_is_final_source=False,tdx_zero_write_gate=False))
    write(P+'PASS_KEEP_REGRESSION.json',dict(runs=[r for r in runs if 'pass_keep' in r['name']],
        scope=['IA01','IA02','IA03','IA04','IA09','IA10','FORWARD_WORKER_CAS_RESTART','R25','A08','V4_15'],
        external_acceptance_granted=False))

if __name__=='__main__':build()

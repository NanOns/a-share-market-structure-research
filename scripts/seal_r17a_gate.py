"""Close the two inherited audit items using every original failing test identity."""
from pathlib import Path
import json,sys,xml.etree.ElementTree as ET
from scripts.prepare_r17_governance import ROOT,put,atomic,bind
def seal(output):
    output=Path(output);clean=json.loads((output/'clean_detached.json').read_bytes());reg=json.loads((output/'regression_gate.json').read_bytes())
    assert clean['status']=='PASS' and clean['git_clean_before'] and clean['git_clean_after']
    assert reg['exit_code']==0 and reg['deselected_count']==0 and not reg['failures'] and not reg['errors'] and not reg['skipped']
    cases={(c.attrib['classname'],c.attrib['name']):c for c in ET.parse(output/'regression.xml').iter('testcase')}
    inherited=json.loads((ROOT/'reports/v4_13_runtime_r16r1/separate_cross_stage_audit_items.json').read_bytes());items=[]
    for item in inherited['items']:
        tests=[]
        for evidence in item['evidence']:
            identity=evidence['test'];case=cases[(identity['classname'],identity['name'])]
            assert not any(case.find(k) is not None for k in ['failure','error','skipped'])
            tests.append(dict(classname=identity['classname'],name=identity['name'],acceptance='PASS'))
        items.append(dict(audit_id=item['id'],scope=item['scope'],original_evidence=bind('reports/v4_13_runtime_r16r1/separate_cross_stage_audit_items.json'),acceptance='PASS',test_results=tests,independent_from_promotion=True))
    assert sum(len(i['test_results']) for i in items)==22
    for name in ['clean_detached.json','regression_gate.json','regression.xml','regression.log']:atomic('reports/r17a/clean/'+name,(output/name).read_bytes())
    contract=json.loads((ROOT/'reports/r17a/stage_contract.json').read_bytes())
    for p,ref in contract['protected'].items():assert bind(p)==ref
    put('reports/r17a/separate_audit_item_closure.json',dict(status='PASS',items=items,total_original_failures_retested=22))
    gate=dict(R17A_CROSS_STAGE_GOVERNANCE_REPAIR='PASS',DM01_HISTORICAL_STAGE_BINDING='PASS',HISTORICAL_STAGE_VALIDATOR_MAINTENANCE='PASS',EXPANDED_CURRENT_REGRESSION='PASS',baseline=contract['baseline'],tested_source=clean['source_sha'],clean_detached=bind('reports/r17a/clean/clean_detached.json'),regression=bind('reports/r17a/clean/regression_gate.json'),audit_closure=bind('reports/r17a/separate_audit_item_closure.json'),protected_byte_identical=True,test_totals=clean['test_totals'],NEXT='R17B_V4_13_ACCEPTED_HEAD_PROMOTION')
    put('reports/r17a/completion_gate.json',gate);print(json.dumps(gate))
if __name__=='__main__':seal(sys.argv[1])

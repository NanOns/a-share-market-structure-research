"""Independent JUnit recount and baseline disposition preserving every outcome."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/audits/r4_r3_scope_20261011'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def analyze(path):
    tree = ET.parse(path)
    xml_digest = sha(path)
    rows = []; groups = Counter()
    for case in tree.findall('.//testcase'):
        status = next((s for tag, s in [('failure','FAIL'),('error','ERROR'),('skipped','SKIP')] if case.find(tag) is not None), 'PASS')
        fault = next((case.find(t) for t in ('failure','error','skipped') if case.find(t) is not None), None)
        message = '' if fault is None else fault.get('message','') + '\n' + (fault.text or '')
        category = 'PASS'
        if status != 'PASS':
            if any(s in message for s in ('NON_POSTGRES','SQLITE_FORBIDDEN','DUCKDB_FORBIDDEN')): category = 'NON_PG_BACKEND_ATTEMPT'
            elif any(s in message for s in ('UNATTESTED_PG','WORKBENCH_PG_DSN_REQUIRED','FEP_E1_TEST_DSN','config/.env')): category = 'PG_FIXTURE_ATTESTATION_OR_ENV'
            elif any(s in message for s in ('FileNotFoundError','No such file','ModuleNotFoundError')): category = 'FROZEN_FIXTURE_ABSENT'
            elif 'AssertionError' in message: category = 'BUSINESS_OR_FROZEN_EXPECTATION_MISMATCH'
            else: category = 'REQUIRES_EXACT_CAUSE_REVIEW'
        node = case.get('classname','') + '::' + case.get('name','')
        groups[(case.get('classname',''),status,category)] += 1
        rows.append(dict(nodeid=node,current_result=status,category=category,raw_message=message,
                         original_xml=path.name,original_xml_sha256=xml_digest))
    prefix = path.stem + '_INDEPENDENT'
    with (OUT / (prefix + '_NODES.csv')).open('x',encoding='utf8',newline='') as stream:
        w=csv.DictWriter(stream,list(rows[0]));w.writeheader();w.writerows(rows)
    originals=list(csv.DictReader((ROOT/'docs/audits/r4_external_repair_r2_20261011/TEST_NODE_DISPOSITION_R2.csv').open(encoding='utf-8-sig')))
    current={r['nodeid']:r for r in rows}
    for old in originals:
        row=current.get(old['nodeid']);old['continuation_current_result']=row['current_result'] if row else 'NOT_PRESENT_IN_CURRENT_JUNIT'
        old['continuation_failure_category']=row['category'] if row else 'COLLECTION_OR_NODE_IDENTITY_REVIEW'
        old['continuation_evidence']=path.name
    with (OUT/(prefix+'_4568.csv')).open('x',encoding='utf8',newline='') as stream:
        w=csv.DictWriter(stream,list(originals[0]));w.writeheader();w.writerows(originals)
    result=dict(contract_id='R4_R3_INDEPENDENT_RAW_XML_RECOUNT_R1',xml=str(path.relative_to(ROOT)),xml_sha256=xml_digest,
                counts=dict(Counter(r['current_result'] for r in rows)),raw_testcase_records=len(rows),unique_node_ids=len(current),
                preserved_old_nodes=len(originals),old_outcomes=dict(Counter(r['previous_result'] for r in originals)),
                original_nodes_in_current=sum(r['nodeid'] in current for r in originals),
                groups=[dict(module=m,status=s,category=c,count=n) for (m,s,c),n in sorted(groups.items())],
                status='RAW_RESULT_RECOUNTED_NOT_LEGAL_SCOPE_CERTIFICATION',
                limitations=['Cause grouping is triage; it does not excuse failures or certify old-only exclusions'])
    (OUT/(prefix+'_RESULT.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('counts','raw_testcase_records','unique_node_ids','original_nodes_in_current')}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('xml',type=Path);a=p.parse_args();analyze(a.xml.resolve())

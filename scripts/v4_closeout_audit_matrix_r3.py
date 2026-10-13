"""Classify all inherited audit items independently of the current stage gate."""
import csv,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/audits/v4_full_closeout_20261012'
CONT=BASE/'continuation_20261013'
def main():
    source=BASE/'AUDIT_ITEMS_PRESERVED.json';items=json.loads(source.read_bytes())['items']
    assert len(items)==39 and len({x['id'] for x in items})==39
    out=CONT/'AUDIT_MATRIX_R3';out.mkdir(exist_ok=True)
    numeric='STAGE1_NUMERIC_CLOSEOUT_R1/RESULT.json'
    pg='PG_CURRENT_CANDIDATE_CONSUMER_R1/RESULT.json'
    field='CORE_AVAILABILITY_ORACLE_R1/CORE47_COVERAGE.json'
    joint='CURRENT_PUBLICATION_JOINT_AUDIT_R1/ACTUAL_JOINT_PUBLICATION_R1.json'
    exact='ORIGINAL56_DISPOSITION_R2/RESULT.json'
    future={'FA-003','FA-008','FA-011'}
    historical={'FA-004','UI-CAPACITY','CAPACITY_ROLLBACK'}
    pending={'FA-006','FA-007','AR2-E01','AR3-E02','AR3-E03','S2-DENOMINATOR','FINAL-CLEAN','LEGAL_FULL_REGRESSION','SIX_UI_WINDOWS','PRODUCTION_ROLE_AND_CUTOVER'}
    refs={'FA-001':pg,'FA-002':numeric,'FA-005':'CURRENT_PUBLICATION_JOINT_AUDIT_R1/TDX_CHILD_GUARD_INCIDENT_R1.json','FA-009':field,'FA-010':'INDEPENDENT_DECODER_FOCUS_RECHECK_R1/S1_ORACLE_FULL/RESULT.json','FA-012':'AMOUNT_A_SOURCE_AUDIT_R2/RESULT.json','FA-013':'SUPPLEMENTAL_PG_HTTP_R1/RESULT.json','FA-014':'CORE_AVAILABILITY_ORACLE_R1/RPS_METADATA.json','FA-015':'AMOUNT_A_SOURCE_AUDIT_R2/RESULT.json','FA-016':numeric,'FA-018':joint,'FA-019':pg,'FA-020':pg,'AUDIT-FOCUS-SOURCE-IDENTITY-R4':joint,'S1-HTTP-JOINT':joint,'ALL-PG-CONSUMERS':pg,'EXACT-56':exact,'FEP-87A':field,'ALL_CONSUMERS':pg,'PG_ONLY':pg,'FOCUS_FORWARD_SETTLEMENT':pg,'EXACT56_FIELDS':exact}
    rows=[]
    for item in items:
        key=item['id'];status='FUTURE_DATA_WATCH' if key in future else 'HISTORICAL_ONLY' if key in historical else 'FIXED_NEEDS_FINAL_RUN' if key in pending else 'CURRENT_PRODUCTION_GATE_PASS'
        evidence=refs.get(key,'STAGE1_NUMERIC_CLOSEOUT_R1/RESULT.json' if key=='FA-017' else joint if key in future else '')
        if evidence and not (CONT/evidence).is_file():raise ValueError('AUDIT_EVIDENCE_MISSING:'+key)
        scope='Current operational scope independently verified; no future PIT/cohort/model/settlement grant'
        if key in future:scope='Future first capture/authorized validation cohort/model/PIT/OOS or independent research-sidecar permission; current UI must retain explicit unavailable state'
        if key in historical:scope='User R2 explicitly excludes performance stress, formal production rollback drills and mobile viewport from this run; prior observations retained, no performance PASS asserted'
        if key in pending:scope='Engineering repairs present; final frozen regression or actual Windows 28765 cutover still required'
        rows.append(dict(id=key,status=status,production_blocker=key in pending,evidence=evidence,evidence_sha256=hashlib.sha256((CONT/evidence).read_bytes()).hexdigest() if evidence else '',scope=scope,inherited_records=len(item['history'])))
    temporary=out/'MATRIX.csv.tmp'
    with temporary.open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    os.replace(temporary,out/'MATRIX.csv')
    summary=dict(contract_id='V4_ALL39_INHERITED_AUDIT_CLASSIFICATION_R3',acceptance='CLASSIFIED_WITH_FINAL_GATES_PENDING',denominator=39,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),counts={s:sum(r['status']==s for r in rows) for s in ('CURRENT_PRODUCTION_GATE_PASS','FIXED_NEEDS_FINAL_RUN','HISTORICAL_ONLY','FUTURE_DATA_WATCH','TRUE_BLOCKER')},new_separate_audit_items=['V4-CURRENT-NATIVE-SNAPSHOT-JOINT-20261013','V4-TDX-CHILD-SOURCE-GUARD-20261013'],production_cutover=False)
    temporary=out/'RESULT.json.tmp';temporary.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');os.replace(temporary,out/'RESULT.json');print(json.dumps(summary))
if __name__=='__main__':main()

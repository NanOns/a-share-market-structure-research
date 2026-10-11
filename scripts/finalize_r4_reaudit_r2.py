"""Append-only bounded audit receipt and source/protection readback."""
import csv,hashlib,json,os,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_external_repair_r2_20261011'
OLD=ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'
BASE='14a4b61876ce64f77f001623d0b13554da2744a2'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while part:=stream.read(8*1024*1024):h.update(part)
    return h.hexdigest()


def write(name,value):
    defaults=dict(contract_id='R4_EXTERNAL_REAUDIT_R2_RECEIPT_R1',base_head=BASE,
        source_SHA='4f7e49d22a3f703813c62db0d8132d04eb6f2ae6',run_utc=datetime.now(timezone.utc).isoformat(),
        scope='V4-only isolated PG engineering',denominator=None,negative_vectors=[],
        previous_status='EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE',current_status='SCOPED_ENGINEERING_PROGRESS',
        owner='Codex / root',evidence_links=[],limitations=['No external acceptance or production authorization'],next_conditions=['Independent review'])
    defaults.update(value);path=OUT/name;tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(defaults,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,path)


def main():
    rows=list(csv.DictReader((OLD/'TEST_NODE_DISPOSITION_R4.csv').open(encoding='utf-8-sig')))
    replay={c.get('classname','')+'::'+c.get('name',''):c for c in ET.parse(OUT/'CAPABILITY_JUNIT.xml').findall('.//testcase')}
    fields=list(rows[0])+['r2_current_result','r2_retest','r2_source_binding','r2_scope_disposition']
    matched=0;path=OUT/'TEST_NODE_DISPOSITION_R2.csv';tmp=path.with_suffix('.tmp')
    with tmp.open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fields);writer.writeheader()
        for row in rows:
            case=replay.get(row['nodeid'])
            if case is not None:matched+=1
            row.update(r2_current_result='SCOPED_PASS' if case is not None else 'NOT_RUN',r2_retest='CAPABILITY_JUNIT.xml' if case is not None else '',r2_source_binding='EXECUTION_SOURCE_BINDINGS.json' if case is not None else '',r2_scope_disposition='BOUNDED_CAPABILITY_REPLAY' if case is not None else 'CONTRACT_AND_DYNAMIC_REVIEW_OPEN_NO_EXEMPTION')
            writer.writerow(row)
    os.replace(tmp,path)
    write('BASELINE_RECONCILIATION.json',dict(original_nodes=len(rows),original_statuses={s:sum(r['previous_result']==s for r in rows) for s in ['PASS','FAIL','ERROR','SKIP']},current_capability_nodes=len(replay),matched_baseline_nodes=matched,new_or_separate_nodes=len(replay)-matched,global_legal_denominator=None,limitations=['Do not subtract scoped suite from historical failures','No name-based exclusions or loss of original nodes']))
    shutil.copyfile(OLD/'EFFECTIVE_AUDIT_ITEMS_R4.json',OUT/'INHERITED_EFFECTIVE_AUDIT_ITEMS_R4.json')
    inherited=json.loads((OLD/'EFFECTIVE_AUDIT_ITEMS_R4.json').read_bytes())
    write('R2_DISPOSITION.json',dict(denominator=dict(capability_tests=206,default_charts=450,global_v4=None),negative_vectors=['Four-table/Series/Journal/Shadow corruption','Schema/instance mismatch','Exact rational JSON drift/duplicate keys','CAS contention/health corruption/rollback/recovery','Bad token/period/pagination/future date'],evidence_links=['CAPABILITY_RESULT.json','EXACT_OLD_SNAPSHOT_RESULT.json','DEFAULT_FIVE_DATES_RESULT.json','DEFAULT_FIVE_DATES_ORACLE.json','TEST_NODE_DISPOSITION_R2.csv'],items=[
        dict(id='R4-EXT-R2-01',priority='P1',scope='Snapshot/Series/Journal/Shadow content and infrastructure identity',engineering='SCOPED_CONTENT_IDENTITY_PASS',external_acceptance='PENDING_INDEPENDENT_REVIEW',formal_roles='PENDING_PERMISSION',restore_cross_instance='NEW_DESCRIPTOR_AND_FRESH_ADMISSION_REQUIRED',production='NOT_LOADED'),
        dict(id='R4-R2-CONTENT-VERIFY-PERFORMANCE',priority='P2',scope='Whole-content read verification throughput',engineering='OPEN_INDEPENDENT_AUDIT',evidence='Readers rescan all rows',acceptance='Separate capacity threshold/oracle and full consumer matrix required'),
        dict(id='R4-E02',engineering='FIVE_DATE_FIVE_INDUSTRY_DEFAULT_HTTP_AND_ORACLE_SCOPED_PASS',production_authority='NOT_ADMITTED',period_owner_gaps=240),
        dict(id='R4-E03',engineering='OLD_PUBLICATION_R2_FOUR_TABLE_ZERO_DIFF',identity_grant='NOT_GRANTED',full_real_consumers='OPEN'),
        dict(id='R4-E04',engineering='206_EXACT_CAPABILITY_REPLAY_PASS',global_denominator='OPEN',historical_nodes_preserved=4568),
        dict(id='R4-E05',engineering='BOUNDED_PROTECTION_ONLY',inherited_late_capture_and_hardlink_limits='PRESERVED')],
        inherited_audit_items=inherited,limitations=['DB01 executor, full real Snapshot/Series/Journal consumers, DB06/08/09 dynamic closure, exact-factor 56 consumers and normative semantic denominator remain OPEN','Future T0/PIT/H21/FEP maturity/Windows independent gates preserved'],next_conditions=['Remaining P0 normative capability matrix and dynamic real consumers','Formal Drive readback','Independent external acceptance','Separate production authorization']))
    protected=json.loads((OUT/'PROTECTED_BEFORE.json').read_bytes())['files'];after=[]
    for item in protected:
        p=Path(item['path']);after.append(dict(item,after_sha256=sha(p),unchanged=sha(p)==item['sha256']))
    if not all(r['unchanged'] for r in after):raise ValueError('PROTECTED_SOURCE_CHANGED')
    write('PROTECTED_AFTER.json',dict(denominator=len(after),files=after,current_status='BOUNDED_PROTECTION_PASS',limitations=['Named heads/old snapshot only; original all-history/hardlink limits preserved']))
    current=json.loads((OUT/'CAPABILITY_RESULT.json').read_bytes())
    if current['results']!={'PASS':206,'FAIL':0,'ERROR':0,'SKIP':0}:raise ValueError('CAPABILITY_NOT_GREEN')
    source=json.loads((OUT/'EXECUTION_SOURCE_BINDINGS.json').read_bytes())['bindings']
    changed=[name for name,checksum in source.items() if sha(ROOT/name)!=checksum]
    # Later evidence-only scripts do not retroactively change executed sources.
    if changed:raise ValueError('EXECUTED_SOURCE_CHANGED:'+str(changed))
    write('SOURCE_READBACK.json',dict(denominator=len(source),changed=changed,current_status='EXECUTED_BYTES_UNCHANGED',source_binding='EXECUTION_SOURCE_BINDINGS.json',limitations=['Runner/evidence scripts include explicitly bound uncommitted bytes; Git HEAD alone is not complete execution identity']))
    for name in ['run_r4_reaudit_r2.py','migrate_r4_old_snapshot_exact_r2.py','audit_r4_default_five_dates_r2.py','r4_dated_chart_source_oracle_r2.py']:
        p=ROOT/'scripts'/name;dest=OUT/'executed_source'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
    print(json.dumps(dict(original_nodes=len(rows),current_capability_nodes=len(replay),matched_original_nodes=matched,protected=len(after),source_bindings=len(source))),flush=True)


if __name__=='__main__':main()

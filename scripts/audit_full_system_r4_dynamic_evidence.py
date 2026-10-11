"""Bound dynamic SQL connection stacks and exact baseline-node replay, no admission."""
import csv,json,re,sys
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.audit_full_system_r4_scope import OUT,write,sha

def main():
    ledgers=['R4_SCOPED_01d4c10b_CONNECTIONS.jsonl','R4_SCOPED_683c04b4_CONNECTIONS.jsonl','R4_03_CHART_HTTP_CONNECTIONS.jsonl']
    if (OUT/'R4_03_BROWSER_CONNECTIONS.jsonl').exists():ledgers.append('R4_03_BROWSER_CONNECTIONS.jsonl')
    ledgers.extend(p.name for p in sorted(OUT.glob('R4_WORKER_*_CONNECTIONS.jsonl')))
    edges=Counter();decisions=Counter();operations=Counter();nodes=set();relations=Counter()
    for name in ledgers:
        with (OUT/name).open(encoding='utf8') as stream:
            for line in stream:
                event=json.loads(line);node=event.get('nodeid');nodes.add(node)
                if event.get('event')=='SQL_INTENT':
                    operations[(node,event['operation'],event['read_write'])]+=1
                    for relation in event.get('relations',[]):relations[relation]+=1
                    continue
                decisions[(node,event.get('engine'),event.get('decision'))]+=1
                frames=[]
                for frame in event.get('stack',[]):
                    match=re.search(r'File "([^"]+)", line (\d+), in ([^\n]+)',frame)
                    if not match:continue
                    path=Path(match[1]);parts=path.as_posix()
                    if '/src/' not in parts and '/scripts/' not in parts and '/tests/' not in parts:continue
                    frames.append(dict(path=parts,line=int(match[2]),function=match[3],current_file_sha256=sha(path) if path.is_file() else None))
                for a,b in zip(frames,frames[1:]):edges[(node,json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True))]+=1
    path=OUT/'TEST_NODE_DISPOSITION_R4.csv'
    with path.open(encoding='utf8',newline='') as stream:reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    replay={}
    for name in ('R4_SCOPED_01d4c10b_JUNIT.xml','R4_SCOPED_683c04b4_JUNIT.xml','R4_DB06_PURE_RANK_JUNIT.xml','R4_SOURCE_GUARD_TEST_JUNIT.xml'):
        for case in ET.parse(OUT/name).findall('.//testcase'):
            key=case.attrib.get('classname','')+'::'+case.attrib['name']
            replay[key]=(name,'FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS')
    matched=0
    for row in rows:
        if row['nodeid'] in replay:
            name,status=replay[row['nodeid']];row.update(current_result='SCOPED_'+status,retest=name,current_replay_scope='NAMED_SUBSET_NOT_FULL_LEGAL_DENOMINATOR');matched+=1
        if row['previous_result']=='PASS' and row['current_result'] not in ('SCOPED_PASS',):
            row['business_semantics']='SEMANTIC_REPLAY_REQUIRED_OLD_GUARD'
    temp=path.with_suffix('.tmp')
    with temp.open('w',encoding='utf8',newline='') as stream:writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    temp.replace(path)
    write('R4_DYNAMIC_DB_EVIDENCE_R1.json',dict(contract_id='R4_DYNAMIC_CONNECTION_SQL_STACK_EVIDENCE_R1',current_status='BOUNDED_DYNAMIC_EVIDENCE_ONLY',denominator=dict(original_nodes=len(rows),current_exact_baseline_matches=matched,observed_nodes=len(nodes)),ledgers=[dict(path=n,sha256=sha(OUT/n)) for n in ledgers],connection_decisions=[dict(nodeid=k[0],engine=k[1],decision=k[2],count=v) for k,v in decisions.items()],observed_stack_edges=[dict(nodeid=k[0],caller=json.loads(k[1]),callee=json.loads(k[2]),count=v) for k,v in edges.items()],sql_intents=[dict(nodeid=k[0],operation=k[1],read_write=k[2],count=v) for k,v in operations.items()],relation_tags=dict(relations),legal_denominator=None,limitations=['Connection stacks have bounded depth; not a complete dynamic function/permissions/UI graph','Current file SHA is readback evidence, not retroactive proof of loaded bytes','SQL intent counts include Connection and Cursor instrumentation; not distinct query counts','Old full PASS without current semantic replay remains unaccepted; no baseline exclusion changed'],next_conditions=['Complete actual default entry, desktop and worker capability paths and per-contract legal denominator']))
    print(json.dumps(dict(original_nodes=len(rows),exact_baseline_matches=matched,observed_stack_edges=len(edges))))

if __name__=='__main__':main()

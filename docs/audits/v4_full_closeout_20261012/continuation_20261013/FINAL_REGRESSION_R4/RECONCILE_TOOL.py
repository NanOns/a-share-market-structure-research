import json,hashlib,copy,gzip,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
root=Path('G:/codex work/v4-full-closeout-20261012');folder=root/'docs/audits/v4_full_closeout_20261012/continuation_20261013/FINAL_REGRESSION_R4';out=Path(__file__).parent
freeze=json.loads((folder/'FREEZE.json').read_bytes());execution=json.loads((folder/'EXECUTION.json').read_bytes())
assert not execution['source_drift'] and all(v==0 for v in execution['exit_codes'].values())
combined=ET.Element('testsuites');records=[];skips=[];seen=[]
for name in ('native','historical'):
 prefix=out/('FINAL_COMPLETE_'+name.upper()+'_R4');manifest=json.loads(prefix.with_suffix('.manifest.json').read_bytes());xml=ET.parse(prefix.with_suffix('.xml'));cases=xml.findall('.//testcase');expected=manifest['nodes']
 def identity(n):
  parts=n.split('::');return parts[0][:-3].replace('/','.')+('.'+'.'.join(parts[1:-1]) if len(parts)>2 else '')+'::'+parts[-1]
 mapped={identity(n):n for n in expected};assert len(mapped)==len(expected)
 ids=[c.get('classname')+'::'+c.get('name') for c in cases];assert len(ids)==len(set(ids)) and set(ids)==set(mapped)
 counts=Counter()
 for case,i in zip(cases,ids):
  node=mapped[i];seen.append(node);status=next((s for s in ('failure','error','skipped') if case.find(s) is not None),'passed');counts[status]+=1
  if status=='skipped':skips.append(dict(node=node,profile=name,reason=case.find('skipped').get('message'),detail=case.find('skipped').text))
 for suite in xml.getroot():combined.append(copy.deepcopy(suite))
 records.append(dict(profile=name,nodes=len(expected),counts=dict(counts),xml_path=str(prefix.with_suffix('.xml')),xml_sha256=hashlib.sha256(prefix.with_suffix('.xml').read_bytes()).hexdigest(),source_commit=manifest['source_commit']))
assert len(seen)==7288 and set(seen)==set(freeze['nodes'])
assert all(not r['counts'].get('failure') and not r['counts'].get('error') for r in records)
ET.ElementTree(combined).write(folder/'02_LEGAL_FULL_TESTS.xml',encoding='utf-8',xml_declaration=True)
result=dict(contract_id='V4_COMPLETE_LEGAL_FULL_REGRESSION_RECONCILIATION_R4',acceptance='PASS_COMPLETE_FROZEN_LEGAL_REGRESSION',denominator=7288,records=records,counts={k:sum(r['counts'].get(k,0) for r in records) for k in ('passed','failure','error','skipped')},original_nodes_preserved=True,exclusions=[],source_commit=freeze['source_commit'],source_drift=[],skips=skips,skip_reasons=dict(Counter(s['reason'] for s in skips)),production_cutover=False)
(folder/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for name in ('native','historical'):
 for suffix in ('.log','.manifest.json','.args'):
  path=out/('FINAL_COMPLETE_'+name.upper()+'_R4'+suffix)
  with gzip.open(folder/(path.name+'.gz'),'wb') as f:f.write(path.read_bytes())
print(json.dumps(dict(acceptance=result['acceptance'],counts=result['counts'],skip_reasons=result['skip_reasons']),ensure_ascii=False))

"""Verify delivered audit coverage, links, baseline immutability, and evidence identity."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from write_reports import ROOT,EVIDENCE,AUDITS,STAGES,ISSUES,atomic,HEAD

def main():
    results=[]
    expected={s[0] for s in STAGES}
    for name in ('V4_00_22_FEP_INDEPENDENT_FULL_SCOPE_AUDIT_R1_20261006.md','V4_00_22_FEP_COMPREHENSIVE_CROSS_MODEL_AUDIT_R1_20261006.md'):
        p=AUDITS/name;text=p.read_text(encoding='utf8')
        actual=re.findall(r'^### ((?:V4-[0-9]+[A-HG]?|FEP-E[1-5])) ·',text,re.M)
        targets=re.findall(r'\]\(<([^>]+)>\)',text)
        missing=[];invalid_lines=[]
        for target in targets:
            match=re.search(r':(\d+)$',target)
            path=Path(target[:match.start()] if match else target)
            if not path.exists():missing.append(str(path))
            elif match and int(match[1])>len(path.read_text(encoding='utf8').splitlines()):invalid_lines.append(target)
        results.append(dict(report=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),stage_count=len(actual),stages_complete=set(actual)==expected and len(actual)==len(expected),local_links=len(targets),missing_links=missing,invalid_source_lines=invalid_lines,no_placeholder='__TEST_SECTION__' not in text,all_issues_present=all(i['id'] in text for i in ISSUES)))
    source=json.loads((EVIDENCE/'source_inventory.json').read_bytes())
    changed=[]
    for item in source['files']:
        p=ROOT/item['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:changed.append(item['path'])
    design_paths=['docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md','docs/design/FEP_R2_MODULE_DESIGN_20260930.md','docs/evidence/fep_e1/FEP_R2_MODULE_DESIGN_20260930.md']
    identities=[dict(path=p,bytes=(ROOT/p).stat().st_size,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in design_paths]
    verdict=dict(audited_head=HEAD,publication_head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),reports=results,source_inventory_count=len(source['files']),business_source_inventory_changes=changed,tracked_business_diff=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines(),design_identities=identities,fep_working_design_equals_archived=identities[1]['sha256']==identities[2]['sha256'],issue_count=len(ISSUES),status='PASS' if all(r['stages_complete'] and r['no_placeholder'] and r['all_issues_present'] and not r['missing_links'] and not r['invalid_source_lines'] for r in results) and not changed else 'FAIL',limitations='Deliverable validity only; does not grant project acceptance. Git diff/source immutability does not prove zero ignored-database writes; see IA-09.')
    atomic(EVIDENCE/'deliverable_validation.json',(json.dumps(verdict,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps(verdict,ensure_ascii=False,indent=2))
    if verdict['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()

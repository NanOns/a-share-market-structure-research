"""Read-only exact promotion validator, retained evidence and scope invariants."""
import subprocess,json
from copy import deepcopy
from scripts.v4_12_promotion_r14 import ROOT,BASE,OUT,HEAD,STAGE,DATA,CAP,PERMISSIONS,read,ref,exact,canonical,expected_stage
def check_head(h):
 assert h['contract_id']=='V4_12_ACCEPTED_HEAD_V1' and h['status']=='PASS_SCOPED_ENGINEERING' and h['acceptance_scope']=='SCOPED_ENGINEERING_ACCEPTANCE'
 assert h['capabilities']==CAP and h['knowledge_lineage']=='RECONSTRUCTED_CORRECTED' and h['AS_RECORDED'] is False
 assert all(h[k] is False for k in PERMISSIONS)
 assert set(h['round_bindings'])=={'R8','R9','R10','R11','R12','R13'} and all(h['round_bindings'].values())
 tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()
 expected={p for p in tracked if p.startswith(('config/v4_12_','src/workbench_analysis/v4_12_','reports/v4_12','docs/evidence/next_round_v4_12')) or (p.startswith('scripts/') and 'v4_12' in p)}
 assert {r['path'] for r in h['contracts_runtime_validators_external_evidence']}==expected
 pubs=h['publication_authority'];assert pubs['runtime_contract_id']=='V4_12_R13_RUNTIME_CANDIDATE_MANIFEST' and pubs['scope']=='SCOPED_ENGINEERING_ONLY_NOT_PRODUCTION'
 assert {r['path'] for r in pubs['authorized_manifests']}=={p for p in expected if p.endswith('/runtime_manifest.json') and p.startswith(('reports/v4_12_runtime_r13/synthetic/','reports/v4_12_runtime_r13/real/'))}
 for r in pubs['authorized_manifests']:
  manifest=json.loads(exact(r));assert manifest['contract_id']==pubs['runtime_contract_id'] and manifest['formal_accepted'] is False and manifest['AS_RECORDED'] is False
 prefixes=dict(R8='reports/v4_12_r2/',R9='reports/v4_12_r2_1/',R10='reports/v4_12_runtime_r1/',R11='reports/v4_12_runtime_r11/',R12='reports/v4_12_runtime_r12/',R13='reports/v4_12_runtime_r13/')
 for name,prefix in prefixes.items():assert {r['path'] for r in h['round_bindings'][name]}=={p for p in expected if p.startswith(prefix)}
 for n in ['parent_stage','v4_11_parent','data_head','external_acceptance','promotion_validator','promotion_transaction']:exact(h[n])
 for r in h['contracts_runtime_validators_external_evidence']:exact(r)
 for refs in h['round_bindings'].values():
  for r in refs:exact(r)
 audit=exact(h['external_acceptance']).decode();assert BASE in audit and h['tested_source'] in audit and 'PASS_SCOPED_ENGINEERING' in audit
 assert read(DATA)['accepted_trade_date']=='2026-09-30'
 return True
def validate(post=False):
 h=read(HEAD if post else OUT+'V4_12_ACCEPTED_HEAD_CANDIDATE.json');check_head(h)
 assert h['baseline']==BASE and h['tested_source']=='180606d6fe06f47b3639acf25e1549de1c19429f'
 assert subprocess.run(['git','merge-base','--is-ancestor',h['tested_source'],BASE],cwd=ROOT).returncode==0
 diff=subprocess.check_output(['git','diff',h['tested_source'],BASE,'--name-only'],cwd=ROOT,text=True).splitlines()
 assert set(diff)=={'reports/v4_12_runtime_r13/R13_CLEAN_CHECKOUT_GATE.json','reports/v4_12_runtime_r13/R13_RUNTIME_HANDOFF.json','reports/v4_12_runtime_r13/R13_TEST_RESULTS.xml'}
 parent=read(OUT+'PARENT_STAGE_HEAD.json');assert parent['accepted_stage_range']=='V4_00_TO_V4_11_ACCEPTED'
 if post:
  assert (ROOT/HEAD).read_bytes()==(ROOT/(OUT+'V4_12_ACCEPTED_HEAD_CANDIDATE.json')).read_bytes()
  assert read(STAGE)==expected_stage(h)
 else:assert (ROOT/STAGE).read_bytes()==exact(h['parent_stage'])
 for r in read(OUT+'R14_STAGE_CONTRACT.json')['protected']:exact(r)
 assert not (ROOT/'data/v4/V4_13_ACCEPTED_HEAD.json').exists()
 return dict(status='PASS',scope='SCOPED_ENGINEERING',post=post,head=ref(HEAD) if post else ref(OUT+'V4_12_ACCEPTED_HEAD_CANDIDATE.json'),rounds=['R8','R9','R10','R11','R12','R13'],parent_metadata='EXACT_PRESERVED',data_head='BYTE_IDENTICAL_2026_09_30',ancestry='PASS',permissions='ALL_FALSE')
if __name__=='__main__':print(json.dumps(validate(post=(ROOT/HEAD).exists()),sort_keys=True))

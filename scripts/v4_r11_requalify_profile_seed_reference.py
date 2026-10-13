"""Read-only fixed R1.1 inputs; independent bounded oracle writes G temporary views."""
import json,gzip,copy,ast
from pathlib import Path
from collections import Counter
from dataclasses import asdict
from workbench_analysis.r43_owner_replay import load,checked,ref,gzrows
from workbench_analysis.operational_component_source_conservation_v2 import ast_conservation
from workbench_analysis.tdx_official_daily_source import sha256_file
from scripts.v4_04_machine_executor_r4 import execute_rule
from v4.profile_core import extension_risk,severe_extension
from v4.profile_status import component_status
from v4.state_identity import digest
from v4.base_seed import _normalize_facts,_known,_unknown,evaluate_facts
root=Path('G:/codex work/v4-production-20261012');dev=Path('G:/codex work/v4-full-closeout-20261012');old=root/'data/v4/dynamic_daily_owners/2026-10-13/35e5a7c80925e59b640bcc694df1184e8bb850634b10085473cd26f6b9b89b57';actual=root/'data/v4/dynamic_daily_owners/2026-10-13/fff118fef56ef5a4993b92496d352e8b977f5be17b9b6e66380e512d91bf5778'
def owner(g):return next(x['owner'] for x in load(g/'owner_v3/PROFILE_STRUCTURE_REPLAY.json')['owners'] if x['owner']['trade_date']=='2026-10-13')
o=owner(old);a=owner(actual);policy=load(root/'config/operational_daily_exact_release_policy_v2.json');binding=next(x for x in policy['accepted_algorithm_bindings'] if x.get('module_path')=='src/v4/profile_core.py');correct=checked(root,binding);assert sha256_file(dev/'src/v4/profile_core.py')==binding['sha256'];ast_conservation((root/'src/v4/profile_core.py').read_text('utf8'),correct.read_text('utf8'))
contract=load(root/'config/v4_04_algorithm_contracts_v3.json');parameters={x['parameter_id']:x['value'] for x in load(root/'config/v4_04_parameter_set_v1.json')['parameters']};patches={};errors=[];scan=0
with gzip.open(checked(root,o['profiles']),'rt',encoding='utf8') as stream:
 for line in stream:
  row=json.loads(line);scan+=1;cell=row['states']['core_extension_risk'];e=cell['evidence'];risk=extension_risk(e);oracle=execute_rule(contract['rules'],'EXTENSION_RISK_V1',e,parameters)
  if risk.value!=oracle:errors.append(dict(id=row['security_id'],kind='INDEPENDENT_AST_ORACLE',actual=risk.value,expected=oracle))
  if risk.value==cell['value']:continue
  replacement=copy.deepcopy(row)
  for field,state in [('core_extension_risk',risk),('severe_extension',severe_extension(risk))]:
   c=replacement['states'][field];c.update(asdict(state));c['input_digest']=digest(state.evidence);c.pop('output_digest');c['output_digest']=digest(c)
  states=[c for k,c in replacement['states'].items() if k!='relative_sector_state'];unknown=sum(c.get('unknown_reason') is not None for c in states);replacement['profile_component_status']=component_status(len(states)-unknown,len(states));replacement['profile_quality']='COMPLETE' if unknown==0 else 'PARTIAL_UNKNOWN';replacement.pop('output_digest');replacement['output_digest']=digest(replacement)
  patches[row['security_id']]=dict(original_risk=cell['value'],evidence=e,independent_oracle=oracle,replacement=replacement)
# No producer actual values were used in constructing any replacement.
actual_profiles={}
with gzip.open(checked(root,a['profiles']),'rt',encoding='utf8') as stream:
 for line in stream:
  row=json.loads(line)
  if row['security_id'] in patches:actual_profiles[row['security_id']]=row
for sid,p in patches.items():
 for key in ('core_extension_risk','severe_extension'):
  for field in ('value','unknown_reason','evidence'):
   if actual_profiles[sid]['states'][key][field]!=p['replacement']['states'][key][field]:errors.append(dict(id=sid,kind='PROFILE',field=key+'.'+field))
 for key in ('profile_component_status','profile_quality'):
  if actual_profiles[sid][key]!=p['replacement'][key]:errors.append(dict(id=sid,kind='PROFILE',field=key))
factors={x['security_id']:x for x in gzrows(checked(root,o['core'])) if x['security_id'] in patches};prior={x['security_id']:x for x in gzrows(checked(root,o['prior_core'])) if x['security_id'] in patches};hist={}
with gzip.open(checked(root,o['history']),'rt',encoding='utf8') as stream:
 for line in stream:
  x=json.loads(line)
  if x['security_id'] in patches:hist[x['security_id']]={b['trade_date']:b for b in x['bars']}
seedparams=load(root/'config/v4_07_parameter_set_v1.json');newseeds=[]
for sid,p in patches.items():
 row=p['replacement'];f=factors[sid];context=dict(trade_date='2026-10-13',expected_board_counts=dict(Counter(x['board_scope'] for x in gzrows(checked(root,o['core'])))),profile_row_publication_id=row['publication_id']);facts=_normalize_facts(dict(row,historical_as_recorded_claim=False),f,context);pc=prior[sid]['fields']['ma20'];pb=hist[sid].get('2026-10-12');facts['ma20_t_minus_1']=_known(pc['value']) if pc.get('quality_state')=='OBSERVED' else _unknown('EXACT_PRIOR_CORE_MA20_UNKNOWN');facts['close_t_minus_1']=_known(pb['qfq_ohlc'][3]) if pb and pb['qfq_ohlc'] else _unknown('EXACT_PRIOR_ADJUSTED_CLOSE_UNKNOWN');seed=evaluate_facts(facts,seedparams);newseeds.append(dict(security_id=sid,trade_date='2026-10-13',**seed,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,stock_only=True))
so=next(x for x in load(actual/'sector_v3/SECTOR_REPLAY.json')['owners'] if x['trade_date']=='2026-10-13');actualseeds={x['security_id']:x for x in gzrows(checked(root,so['seed']))}
for row in newseeds:
 if row!=actualseeds[row['security_id']]:errors.append(dict(id=row['security_id'],kind='SEED',fields=[k for k in row if row[k]!=actualseeds[row['security_id']].get(k)]))
out=Path('G:/codex_tmp/r11_qualified_profile_seed_reference');out.mkdir(exist_ok=True)
(out/'PROFILE_AFFECTED6.json').write_text(json.dumps(dict(rows=[p['replacement'] for p in patches.values()]),ensure_ascii=False),encoding='utf8');(out/'SEED_AFFECTED6.json').write_text(json.dumps(dict(rows=newseeds),ensure_ascii=False),encoding='utf8')
report=dict(contract_id='V4_R11_REFERENCE_ALGORITHM_REQUALIFICATION',acceptance='PASS_AFFECTED_REFERENCE_REQUALIFICATION' if not errors else 'FAIL',scan_rows=scan,changed_rows=len(patches),old_reference_invalid_assumption='Old 35e5 reference executed outdated extension_risk; algorithm version equality premise false',old_reference_profile=o['profiles'],old_kernel=dict(path=str(root/'src/v4/profile_core.py'),sha256=sha256_file(root/'src/v4/profile_core.py')),accepted_kernel=binding,AST_all_other_functions_conserved=True,parameters=ref(root,root/'config/v4_04_parameter_set_v1.json'),independent_oracle_contract=ref(root,root/'config/v4_04_algorithm_contracts_v3.json'),errors=errors,corrections=[dict(security_id=sid,old_risk=p['original_risk'],new_risk=p['replacement']['states']['core_extension_risk']['value'],evidence=p['evidence'],oracle=p['independent_oracle']) for sid,p in patches.items()],actual_used_only_after_reference_construction=True,old_FAIL_retained=True,production_head_mutated=False)
(out/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(dict(acceptance=report['acceptance'],scan=scan,changed=len(patches),errors=errors,out=str(out))))

from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import os
from typing import Any, Mapping, Sequence

ROOT=Path(__file__).resolve().parents[1]
SOURCE_ROOT=Path(os.environ.get('V4_07_ACCEPTED_INPUTS_ROOT', str(ROOT))).resolve()
TASK='V4_06_R2_CONTRACT_REPAIR_AND_V4_07_BASE_SEED_STAGE_TASK_20260929'
MODEL='BASE_SEED_V1'
PARAMS='V4_07_BASE_SEED_PARAMETER_SET_V1'
TARGET='2026-09-28'
PUBLICATION='PUB-3c03e227-c60a-4d8c-86ae-2861507c257b'
ROW_PUBLICATION='V4_05_R4_T0_CURRENT_COORDINATE'
CORE_LOGICAL='d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74'
CORE_SHA='9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0'
FACTORS_SHA='17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48'
BOARDS={'SH_MAIN':1702,'SZ_MAIN':1494,'CHINEXT':1408,'STAR':618}

def canon(x:Any)->bytes: return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(x:Any)->str: return hashlib.sha256(canon(x)).hexdigest()
def file_sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def readj(p:Path)->Any: return json.loads(p.read_text(encoding='utf-8'))
def path_checked(rel:str)->Path:
 p=(SOURCE_ROOT/rel).resolve()
 if not p.is_relative_to(SOURCE_ROOT) or not p.is_file(): raise ValueError('missing/unsafe accepted source: '+rel)
 return p
def verify(binding:Mapping[str,Any],label:str)->tuple[Path,str]:
 p=path_checked(binding['path']); got=file_sha(p)
 if got!=str(binding['sha256']).lower(): raise ValueError(f'{label} hash mismatch')
 if 'byte_count' in binding and p.stat().st_size!=int(binding['byte_count']): raise ValueError(f'{label} byte count mismatch')
 return p,got
def read_gzip(path:Path)->list[dict[str,Any]]:
 with gzip.open(path,'rt',encoding='utf-8') as f: return [json.loads(line) for line in f if line.strip()]
def num(x:Any)->float|None:
 if isinstance(x,bool) or not isinstance(x,(int,float)): return None
 x=float(x)
 return x if math.isfinite(x) else None
def unk(reason:str)->dict[str,Any]: return {'value':None,'reason':reason or 'UPSTREAM_UNKNOWN'}
def known(value:Any)->dict[str,Any]: return {'value':value,'reason':None}
def tri(f:Mapping[str,Any])->str: return 'TRUE' if f.get('value') is True else 'FALSE' if f.get('value') is False else 'UNKNOWN'
def tnot(v:str)->str: return {'TRUE':'FALSE','FALSE':'TRUE','UNKNOWN':'UNKNOWN'}[v]
def tand(xs:Sequence[str])->str: return 'FALSE' if 'FALSE' in xs else 'UNKNOWN' if 'UNKNOWN' in xs else 'TRUE'
def tor(xs:Sequence[str])->str: return 'TRUE' if 'TRUE' in xs else 'UNKNOWN' if 'UNKNOWN' in xs else 'FALSE'
def unknown_reason(item:Any,fallback:str)->str:
 if not isinstance(item,Mapping): return fallback
 return str(item.get('unknown_reason') or item.get('reason') or fallback)
def fact_from_value(item:Any,qkey:str,vkey:str,field:str,kind:str)->dict[str,Any]:
 if not isinstance(item,Mapping): return unk('MISSING_ACCEPTED_CORE_FIELD:'+field)
 if item.get(qkey)!='OBSERVED': return unk(unknown_reason(item,'UPSTREAM_UNKNOWN:'+field))
 val=item.get(vkey)
 if kind=='bool' and isinstance(val,bool): return known(val)
 if kind=='number' and num(val) is not None: return known(num(val))
 if kind=='enum' and isinstance(val,str) and val and val!='UNKNOWN': return known(val)
 return unk('INVALID_ACCEPTED_VALUE:'+field)
def fact_from_state(item:Any,field:str,kind:str)->dict[str,Any]:
 if not isinstance(item,Mapping): return unk('MISSING_ACCEPTED_CORE_FIELD:'+field)
 val=item.get('value')
 if val is None or val=='UNKNOWN' or item.get('unknown_reason') is not None: return unk(unknown_reason(item,'UPSTREAM_UNKNOWN:'+field))
 if kind=='bool' and isinstance(val,bool): return known(val)
 if kind=='number' and num(val) is not None: return known(num(val))
 if kind=='enum' and isinstance(val,str) and val: return known(val)
 return unk('INVALID_ACCEPTED_VALUE:'+field)
def core_facts(c:Mapping[str,Any],factor:Mapping[str,Any])->dict[str,dict[str,Any]]:
 facts={'research_universe':known(True)}
 status=c.get('trading_status')
 facts['actual_bar']=known(True) if status=='ACTUAL_TRADED' else known(False) if status=='SUSPENDED' else unk('UPSTREAM_TRADING_STATUS:'+str(status or 'MISSING'))
 sid=c.get('security_id'); sym=c.get('symbol'); board=c.get('board')
 ident=(isinstance(sid,str) and re.fullmatch(r'SEC-[0-9A-F]{32}',sid) is not None and isinstance(sym,str) and re.fullmatch(r'(?:SH|SZ)\.[0-9]{6}',sym) is not None and board in BOARDS and ((board in ('SH_MAIN','STAR') and sym.startswith('SH.')) or (board in ('SZ_MAIN','CHINEXT') and sym.startswith('SZ.'))) and c.get('trade_date')==TARGET and c.get('publication_id')==ROW_PUBLICATION and c.get('historical_as_recorded_claim') is False)
 facts['price_identity_READY']=known(True) if ident else unk('ACCEPTED_CORE_IDENTITY_BINDING_INVALID')
 derived=c.get('derived_fields',{}); quality=c.get('primitive_quality',{}); states=c.get('states',{})
 facts['minimum_liquidity']=fact_from_value(derived.get('minimum_liquidity'),'quality','value','minimum_liquidity','bool')
 meta=quality.get('core_price_damage'); evidence=states.get('trend_state',{}).get('evidence',{})
 damage=evidence.get('core_price_damage') if isinstance(evidence,Mapping) else None
 facts['core_price_damage']=known(damage) if isinstance(meta,Mapping) and meta.get('quality_state')=='OBSERVED' and isinstance(damage,bool) else unk(unknown_reason(meta,'UPSTREAM_UNKNOWN:core_price_damage'))
 facts['severe_extension']=fact_from_state(states.get('severe_extension'),'severe_extension','bool')
 facts['bias20_atr']=fact_from_value(derived.get('bias20_atr'),'quality','value','bias20_atr','number')
 facts['compression_state']=fact_from_state(states.get('compression_state'),'compression_state','enum')
 fdelta=factor.get('fields',{}).get('rps5_delta3'); cdelta=quality.get('rps5_delta3')
 if not isinstance(fdelta,Mapping) or not isinstance(cdelta,Mapping): facts['delta3']=unk('MISSING_ACCEPTED_CORE_FIELD:rps5_delta3')
 else:
  keys=('contract_id','input_digest','output_digest','parameter_set_id','quality_state','unknown_reason','window_identity','actual_count','calendar_span','suspended_count','window_start_trade_date','window_end_trade_date')
  facts['delta3']=unk('ACCEPTED_FACTOR_PROFILE_BINDING_MISMATCH:rps5_delta3') if any(fdelta.get(k)!=cdelta.get(k) for k in keys) else fact_from_value(fdelta,'quality_state','value','rps5_delta3','number')
 facts['ma_structure_state']=fact_from_state(states.get('ma_structure_state'),'ma_structure_state','enum')
 ev=evidence if isinstance(evidence,Mapping) else {}
 for output,source in (('close_t','close'),('ma20_t','ma20')):
  facts[output]=known(num(ev.get(source))) if num(ev.get(source)) is not None else unk('MISSING_ACCEPTED_CORE_FIELD:'+output)
 facts['close_t_minus_1']=unk('ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE')
 facts['ma20_t_minus_1']=unk('ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE')
 facts['core_participation_result']=fact_from_state(states.get('core_participation_result'),'core_participation_result','enum')
 return facts
def independent_eval(f:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
 safety=tand((tri(f['research_universe']),tri(f['actual_bar']),tri(f['price_identity_READY']),tri(f['minimum_liquidity']),tnot(tri(f['core_price_damage'])),tnot(tri(f['severe_extension']))))
 bias='UNKNOWN' if num(f['bias20_atr'].get('value')) is None else 'TRUE' if num(f['bias20_atr']['value'])<3 else 'FALSE'
 compval=f['compression_state'].get('value'); comp='UNKNOWN' if compval is None else 'TRUE' if compval in {'COMPRESSING','COMPRESSING_STRONG'} else 'FALSE'
 delta=num(f['delta3'].get('value')); d3='UNKNOWN' if delta is None else 'TRUE' if delta>=3 else 'FALSE'; d10='UNKNOWN' if delta is None else 'TRUE' if delta>=10 else 'FALSE'
 ma=f['ma_structure_state'].get('value'); bull='UNKNOWN' if ma is None else 'TRUE' if ma=='BULL_TRANSITION' else 'FALSE'
 pclose=num(f['close_t_minus_1'].get('value')); pma=num(f['ma20_t_minus_1'].get('value')); cclose=num(f['close_t'].get('value')); cma=num(f['ma20_t'].get('value'))
 before='UNKNOWN' if pclose is None or pma is None else 'TRUE' if pclose<=pma else 'FALSE'; now='UNKNOWN' if cclose is None or cma is None else 'TRUE' if cclose>cma else 'FALSE'
 transition=tor((bull,tand((before,now))))
 s1=tand((bias,comp,d3)); s2=tand((bias,d10,transition)); paths=tor((s1,s2)); base=tand((safety,paths))
 domains={'research_universe':tri(f['research_universe']),'actual_bar':tri(f['actual_bar']),'price_identity_READY':tri(f['price_identity_READY']),'minimum_liquidity':tri(f['minimum_liquidity']),'core_price_damage':tri(f['core_price_damage']),'severe_extension':tri(f['severe_extension']),'safety':safety,'position_ok':bias,'structure_improving':comp,'relative_change_improving':d3,'relative_change_strong':d10,'trend_transition_early':transition,'S1':s1,'S2':s2,'seed_paths':paths,'base_seed_state':base}
 p=f['core_participation_result'].get('value'); annotation={'HIGH_PARTICIPATION_EFFECTIVE_ADVANCE':'SUPPORTED','HIGH_PARTICIPATION_REVERSAL':'CONFLICTING','HIGH_PARTICIPATION_LOW_EFFICIENCY':'CONFLICTING','LOW_PARTICIPATION_ADVANCE':'NEUTRAL','LOW_PARTICIPATION_DECLINE':'NEUTRAL','NORMAL_PARTICIPATION':'NEUTRAL'}.get(p,'UNKNOWN')
 relevant={'research_universe','actual_bar','price_identity_READY','minimum_liquidity','core_price_damage','severe_extension','bias20_atr','compression_state','delta3','ma_structure_state','core_participation_result'}
 if transition=='UNKNOWN': relevant.update(('close_t_minus_1','ma20_t_minus_1','close_t','ma20_t'))
 waiting=[{'field_id':k,'reason':str(f[k].get('reason') or 'UPSTREAM_UNKNOWN')} for k in sorted(relevant) if f[k].get('value') is None]
 invalid=[]
 if base!='TRUE':
  for k in ('research_universe','actual_bar','price_identity_READY','minimum_liquidity'):
   if domains[k]=='FALSE': invalid.append({'predicate':k,'state':'FALSE'})
  for k in ('core_price_damage','severe_extension'):
   if domains[k]=='TRUE': invalid.append({'predicate':'NOT_'+k,'state':'FALSE'})
  if safety!='FALSE':
   for k,v in (('S1',s1),('S2',s2)):
    if v=='FALSE': invalid.append({'predicate':k,'state':'FALSE'})
 invalid.sort(key=lambda q:q['predicate'])
 codes=sorted({f"UNKNOWN_INPUT:{x['field_id']}:{x['reason']}" for x in waiting})
 return {'base_seed_state':base,'matched_seed_paths':[p for p,v in (('S1',s1),('S2',s2)) if v=='TRUE'],'domain_states':domains,'waiting_for':waiting,'invalid_if':invalid,'quality':'COMPLETE' if not waiting else 'PARTIAL_UNKNOWN','quality_codes':codes,'seed_participation_annotation':annotation}
def input_digest(c:Mapping[str,Any],f:Mapping[str,Mapping[str,Any]],sb:Mapping[str,Any])->str:
 payload={'source_bindings':{k:sb[k] for k in ('publication_id','profile_row_publication_id','trade_date','core_logical_digest','core_profile_artifact_sha256','full_scope_factors_logical_digest','full_scope_factors_artifact_sha256')},'identity':{'trade_date':c.get('trade_date'),'security_id':c.get('security_id'),'symbol':c.get('symbol'),'board':c.get('board')},'accepted_facts':f}
 return digest(payload)
def row_fact_digest(r:Mapping[str,Any])->str: return digest({k:v for k,v in r.items() if k not in {'fact_digest','created_at'}})
def logical_digest(rows:Sequence[Mapping[str,Any]],sb:Mapping[str,Any])->str:
 rr=[{k:v for k,v in r.items() if k!='created_at'} for r in rows]; rr.sort(key=lambda r:(r['trade_date'],r['security_id']))
 b={k:sb[k] for k in ('publication_id','trade_date','core_logical_digest','core_profile_artifact_sha256','full_scope_factors_logical_digest','full_scope_factors_artifact_sha256')}
 return digest({'contract_id':MODEL,'parameter_set_id':PARAMS,'accepted_source_bindings':b,'rows':rr})
def main()->int:
 stage=readj(path_checked('data/v4/V4_STAGE_ACCEPTED_HEAD.json')); head=readj(path_checked('data/v4/V4_05_ACCEPTED_HEAD.json'))
 assert stage['accepted_stage_range']=='V4_00_TO_V4_05_ACCEPTED' and stage['v4_05_external_acceptance']=='EXTERNALLY_ACCEPTED'
 assert head['external_acceptance_decision']=='V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2' and head['target_trade_date']==TARGET and head['target_identity_count']==5222
 exact_path,exact_sha=verify(head['evidence_bindings']['exact_candidate_ledger_binding'],'V4-05 exact ledger')
 exact=readj(exact_path); assert exact['status']=='PASS' and exact['all_exact_bindings_match'] is True and exact['old_r4_binding_count']==0
 formal=exact['actual_postgresql']['publication_head']['publication_id']; assert formal==PUBLICATION
 core_path,core_sha=verify(head['accepted_artifact'],'accepted core profile'); factor_path,factor_sha=verify(head['accepted_artifacts']['full_scope_factors'],'accepted full factors')
 assert core_sha==CORE_SHA and factor_sha==FACTORS_SHA and head['accepted_artifact']['logical_digest']==CORE_LOGICAL
 core_receipt_path,core_receipt_sha=verify(head['evidence_bindings']['r4_1_core_profile_receipt'],'core receipt')
 factors_receipt_path,factors_receipt_sha=verify(head['evidence_bindings']['r4_1_full_scope_factors_receipt'],'factor receipt')
 cr=readj(core_receipt_path); fr=readj(factors_receipt_path)
 assert cr['logical_digest']==CORE_LOGICAL and cr['row_count']==5222 and cr['artifact_sha256']==core_sha
 assert fr['logical_digest']==head['accepted_artifacts']['full_scope_factors']['logical_digest'] and fr['artifact_sha256']==factor_sha
 contract=readj(ROOT/'config/v4_07_base_seed_contract_v1.json'); params=readj(ROOT/'config/v4_07_parameter_set_v1.json'); freeze=readj(ROOT/'reports/v4_07/V4_07_CONTRACT_FREEZE_RECEIPT.json')
 for rel,h in freeze['config_sha256'].items(): assert file_sha(ROOT/rel)==h, rel
 assert freeze['status']=='PASS_CONTRACT_FREEZE_CANDIDATE' and contract['status']=='FROZEN_CANDIDATE'
 sb={'publication_id':formal,'profile_row_publication_id':ROW_PUBLICATION,'trade_date':TARGET,'core_logical_digest':CORE_LOGICAL,'core_profile_artifact_sha256':core_sha,'core_profile_receipt_sha256':core_receipt_sha,'full_scope_factors_logical_digest':head['accepted_artifacts']['full_scope_factors']['logical_digest'],'full_scope_factors_artifact_sha256':factor_sha,'full_scope_factors_receipt_sha256':factors_receipt_sha,'exact_ledger_binding_sha256':exact_sha,'model_contract_id':MODEL,'parameter_set_id':PARAMS}
 core=read_gzip(core_path); factors=read_gzip(factor_path)
 assert len(core)==5222 and len(factors)==5222
 byid={}
 boards=Counter(); sources=Counter()
 for row in core:
  sid=row['security_id']; assert sid not in byid; byid[sid]=row; boards[row['board']]+=1
 assert dict(boards)==BOARDS
 f_by={}
 for row in factors:
  sid=row['security_id']; assert sid not in f_by; f_by[sid]=row
 assert set(byid)==set(f_by)
 candidate_path=ROOT/'reports/v4_07/staging/V4_07_BASE_SEED_CANDIDATE_R1.jsonl.gz'
 candidate=read_gzip(candidate_path); assert len(candidate)==5222
 candidate_by={r['security_id']:r for r in candidate}; assert len(candidate_by)==5222 and set(candidate_by)==set(byid)
 mismatch=[]; expected=[]; expected_state=Counter(); state_by_board=Counter(); unknowns=Counter(); annotations=Counter()
 forbidden=('turnover','baostock','supplemental_extension_note','binding_quality','prewatch','radar','focus','anchor','forward')
 for sid in sorted(byid):
  c=byid[sid]; fac=f_by[sid]; actual=candidate_by[sid]
  assert c['trade_date']==TARGET and c['publication_id']==ROW_PUBLICATION
  assert fac['trade_date']==TARGET and fac['board_scope']==c['board'] and fac['coordinate_basis']==c['coordinate_basis']
  facts=core_facts(c,fac); calc=independent_eval(facts)
  row={'publication_id':formal,'source_publication_id':c['publication_id'],'trade_date':TARGET,'security_id':sid,
       'base_seed_state':calc['base_seed_state'],'matched_seed_paths':calc['matched_seed_paths'],'domain_states':calc['domain_states'],
       'waiting_for':calc['waiting_for'],'invalid_if':calc['invalid_if'],'quality':calc['quality'],'quality_codes':calc['quality_codes'],
       'seed_participation_annotation':calc['seed_participation_annotation'],'model_contract_id':MODEL,'parameter_set_id':PARAMS,
       'source_core_logical_digest':CORE_LOGICAL,'input_digest':input_digest(c,facts,sb),'created_at':actual.get('created_at')}
  row['fact_digest']=row_fact_digest(row)
  comparable=set(row)|{'fact_digest'}
  diffs={k:(actual.get(k),row.get(k)) for k in comparable if actual.get(k)!=row.get(k)}
  if diffs: mismatch.append({'security_id':sid,'fields':diffs})
  if any(any(term in key.lower() for term in forbidden) for key in actual): mismatch.append({'security_id':sid,'fields':{'forbidden_output_key':True}})
  expected.append(row); expected_state[row['base_seed_state']]+=1; state_by_board[(c['board'],row['base_seed_state'])]+=1; annotations[row['seed_participation_annotation']]+=1
  if row['base_seed_state']=='UNKNOWN':
   for w in row['waiting_for']: unknowns[(c['board'],w['field_id'],w['reason'])]+=1
 if mismatch: raise AssertionError(json.dumps(mismatch[:3],ensure_ascii=False))
 expected.sort(key=lambda r:(r['trade_date'],r['security_id']))
 logical=logical_digest(expected,sb)
 receipt=readj(ROOT/'reports/v4_07/V4_07_FULL_MARKET_CANDIDATE_RECEIPT.json')
 assert receipt['source_bindings']==sb and receipt['logical_artifact_digest']==logical
 assert all(r['created_at'] and r['created_at'].endswith('Z') for r in candidate)
 counts=Counter(r['base_seed_state'] for r in candidate)
 assert sum(counts.values())==5222 and receipt['row_count']==5222
 samples=[]
 for board in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR'):
  b=[r for r in candidate if byid[r['security_id']]['board']==board]
  samples.extend({'board':board,'security_id':r['security_id'],'base_seed_state':r['base_seed_state'],'matched_seed_paths':r['matched_seed_paths']} for r in (b[0],b[-1]))
 evidence={'contract_id':'V4_07_INDEPENDENT_POSTCHECK_V1','stage_contract':TASK,'status':'PASS_INDEPENDENT_SOURCE_RECOMPUTE','oracle':'accepted V4-05 Core profile + accepted V4-05 Full Scope Factors + frozen BASE_SEED_V1 contract/parameters; candidate output used only for equality comparison','accepted_inputs_root':str(SOURCE_ROOT),
  'independent_implementation':'scripts/verify_v4_07_base_seed.py (no import of src.v4.base_seed)','checked_rows':len(expected),'mismatch_count':0,'target_trade_date':TARGET,'publication_id':formal,'accepted_core_logical_digest':CORE_LOGICAL,
  'candidate_logical_digest':logical,'expected_state_counts':dict(sorted(expected_state.items())),'state_counts_by_board':{b:dict(sorted({s:n for (br,s),n in state_by_board.items() if br==b}.items())) for b in sorted(BOARDS)},
  'participation_annotation_counts':dict(sorted(annotations.items())),'samples':samples,'accepted_delta3_unknown_count':5222,'accepted_t_minus_1_core_fields':'ABSENT; reclaim branch remains UNKNOWN where required','source_bindings':sb,'candidate_artifact_sha256':file_sha(candidate_path),'created_at_excluded_from_comparison':True,'next_stage':'V4_07_SUPPLEMENTAL_ISOLATION_AND_DETERMINISM'}
 out=ROOT/'reports/v4_07/V4_07_INDEPENDENT_POSTCHECK.json'; out.parent.mkdir(parents=True,exist_ok=True)
 data=(json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode(); fd,tmp=tempfile.mkstemp(prefix=out.name+'.',suffix='.tmp',dir=out.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(tmp,out)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 print(json.dumps({'status':evidence['status'],'checked_rows':len(expected),'mismatch_count':0,'logical_digest':logical,'state_counts':dict(expected_state),'unknown_reason_count':len(unknowns)},sort_keys=True))
 return 0
if __name__=='__main__': raise SystemExit(main())

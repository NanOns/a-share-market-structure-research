import os,json,re,hashlib,csv,io,collections
from pathlib import Path
R=Path('G:/codex work/大A交易');B=Path('G:/codex_tmp/full_system_audit_r2_58faf74e')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(name,raw):
 p=B/name;t=p.with_suffix('.tmp');t.write_bytes(raw);os.replace(t,p)
def js(name,x):atomic(name,json.dumps(x,ensure_ascii=False,indent=2).encode('utf8'))
def csvout(name,rows):
 s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows);atomic(name,s.getvalue().encode('utf8'))
main=R/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md';lines=main.read_text(encoding='utf8').splitlines()
start=next(i for i,l in enumerate(lines) if l.startswith('# 87A.'));end=next(i for i in range(start+1,len(lines)) if lines[i].startswith('# 88.'))
expansions={'pos60/250':['pos60','pos250'],'RPS5/20':['rps5','rps20'],'rel_market_1/3/5':['rel_market_1','rel_market_3','rel_market_5'],'turnover_pct20/60':['turnover_pct20','turnover_pct60'],'sector_rs5/20':['sector_rs5','sector_rs20'],'top1/top3_concentration':['top1_concentration','top3_concentration'],'impulse_retention_1/3':['impulse_retention_1','impulse_retention_3'],'effective_from/to':['effective_from','effective_to'],'delta1/3':['rps5_delta1','rps5_delta3','rps20_delta3'],'entered/exited':['entered_count','exited_count'],'market_regime_axes':['trend_axis','breadth_axis','participation_axis','stress_level']}
unresolved={'delta1/3','entered/exited','market_regime_axes','controls','Focus timeline/path/outcome','profile component statuses','context token','diagnostic counters'}
sources=[]
for base in ('src','scripts','config','migrations','artifacts/fep_r2_20260930'):
 for p in (R/base).rglob('*'):
  if p.is_file() and p.suffix in ('.py','.js','.json','.sql'):
   try:sources.append((p.relative_to(R).as_posix(),p.read_text(encoding='utf8').splitlines()))
   except UnicodeError:pass
families=[];fields=[]
for i in range(start,end):
 l=lines[i]
 if not l.startswith('| ') or l.startswith('| 字段') or l.startswith('|---'):continue
 cols=[x.strip() for x in l.strip('|').split('|')]
 if len(cols) not in (4,5):continue
 fid='87A-'+str(len(families)+1).zfill(2);contract=cols[2] if len(cols)==5 else cols[1];stage=cols[3] if len(cols)==5 else cols[2];quality=cols[-1]
 names=[x.strip() for x in cols[0].split(';')];out=[];gaps=[]
 for name in names:
  if name in expansions:out.extend(expansions[name])
  elif name in unresolved or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_ ]*',name):gaps.append(name)
  else:out.append(name)
 families.append(dict(family_id=fid,source_line=i+1,family=cols[0],contract=contract,stage=stage,quality=quality,explicit_fields=out,unresolved=gaps,line_sha256=hashlib.sha256(l.encode()).hexdigest(),expansion_status='PARTIAL_UNRESOLVED_FAMILY' if gaps else 'EXPLICIT_NAME_EXPANSION_ONLY'))
 for name in out:
  anchors=[];pat=re.compile(r'(?<![A-Za-z0-9_])'+re.escape(name)+r'(?![A-Za-z0-9_])',re.I)
  for path,ls in sources:
   for n,src in enumerate(ls,1):
    if pat.search(src):anchors.append(path+':'+str(n))
    if len(anchors)>=25:break
   if len(anchors)>=25:break
  fields.append(dict(field_requirement_id=fid+':'+name,field=name,family_id=fid,authority_line=i+1,algorithm_contract=contract,stage=stage,quality_policy=quality,anchors=';'.join(anchors),anchor_status='LOCATION_ONLY_NOT_SEMANTIC_PASS' if anchors else 'NO_EXACT_NAME_ANCHOR',producer_semantics='NOT_YET_INDIVIDUALLY_VERIFIED',consumer_ui_permission='NOT_YET_INDIVIDUALLY_VERIFIED',acceptance='OPEN'))
js('b1_field_family_expansion.json',dict(contract='87A_EXPLICIT_FAMILY_EXPANSION_R2',authority=dict(path=main.relative_to(R).as_posix(),sha256=sha(main)),families=families,distinct_explicit_names=len({r['field'] for r in fields}),requirement_rows=len(fields),family_count=len(families),unresolved_count=sum(len(r['unresolved']) for r in families),not_full_field_denominator=True,not_all_versions=True))
csvout('b1_explicit_fields.csv',fields)
atoms=[]
for row in fields:
 for dimension in ['data_type','unit','producer','required_optional','time','output_digest','display_label','algorithm_contract_version','parameter_instance']:
  atoms.append(dict(requirement_id=row['field_requirement_id']+':'+dimension,field_requirement_id=row['field_requirement_id'],field=row['field'],dimension=dimension,authority_line=row['authority_line'],authority_requirement='87A opening paragraph: per-field schema and unique algorithm contract plus parameter instance',acceptance='NOT_YET_SEMANTICALLY_VERIFIED'))
csvout('b1_87a_scoped_atomic_requirements.csv',atoms)
js('b1_expansion_interpretation.json',dict(explicit_rules=expansions,additional_authority_anchors={'delta1/3':[2729,2730,2731,2764],'entered/exited':[2075,2076,3559],'market_regime_axes':[3727,3728,3729]},atomic_scope='Only explicit expanded 87A schema dimensions; excludes unresolved family internals, normative requirements outside 87A and full FEP',scoped_atomic_count=len(atoms),not_global_denominator=True))

core=R/'config/v4_03_algorithm_contracts_v1.json';data=json.loads(core.read_bytes());core_rows=[]
for c in data['contracts']:
 for out in c.get('outputs',[]):
  core_rows.append(dict(contract_id=c.get('contract_id'),field=out['field_id'],output=out,inputs=c.get('inputs'),ast=c.get('ast'),parameters=c.get('parameter_bindings',c.get('parameters')),contract_source_sha256=sha(core),machine_contract_registration='PRESENT',independent_semantic_verification='B2_FULL_NATIVE_RET_RPS_ONLY' if out['field_id'] in ('ret1','ret3','ret5','ret20','rps5','rps20') else 'NOT_EXTENDED_IN_R2',semantic_pass_not_inferred_from_registration=True))
js('b1_core_machine_contract_fields.json',dict(contract_count=data['contract_count'],output_count=len(core_rows),rows=core_rows))
# DDL is an additional implemented-field namespace, not a substitute for normative requirements.
ddl=R/'src/workbench_db/migrations/v4_postgres/028_fep_schema_v1.sql';text=ddl.read_text(encoding='utf8');ddlrows=[]
for match in re.finditer(r'CREATE TABLE\s+(fep\.\w+)\s*\((.*?)\n\);',text,re.S):
 table,body=match.groups()
 clean=re.sub(r'--[^\n]*','',body);depth=0;quoted=False;parts=[];mark=0
 for j,ch in enumerate(clean):
  if ch=="'":quoted=not quoted
  if quoted:continue
  if ch=='(':depth+=1
  elif ch==')':depth-=1
  elif ch==',' and depth==0:parts.append(clean[mark:j]);mark=j+1
 parts.append(clean[mark:])
 for declaration in parts:
  m=re.match(r'\s*(\w+)\s+(.+)',declaration,re.S)
  if not m or m[1].upper() in ('PRIMARY','FOREIGN','UNIQUE','CHECK','CONSTRAINT'):continue
  ddlrows.append(dict(table=table,column=m[1],declaration=' '.join(m[2].split()),source_table_line=text[:match.start()].count('\n')+1,source_sha256=sha(ddl),semantic_status='DDL_REGISTRATION_ONLY_NOT_PRODUCER_VALIDATOR_UI_PASS'))
js('b1_fep_ddl_columns.json',dict(table_count=len({r['table'] for r in ddlrows}),column_count=len(ddlrows),rows=ddlrows,scope='028 initial schema; successor migrations and normative FEP requirements remain separate'))
js('b1_acceptance.json',dict(stage_contract='B1_87A_EXPLICIT_FIELDS_AND_CORE_FEP_REGISTRATION_R2',status='PARTIAL_AUDIT_COMPLETION_GAP',family_count=len(families),explicit_requirement_rows=len(fields),unresolved_families=[dict(family_id=r['family_id'],tokens=r['unresolved']) for r in families if r['unresolved']],full_atomic_requirement_denominator=None,full_versioned_field_denominator=None,coverage_percentage=None,next_stage='MANUAL_NORMATIVE_CLAUSE_ATOMIZATION_AND_PER_FIELD_PRODUCER_CONSUMER_QUALITY_PERMISSION_REVIEW',clv_erratum=dict(authority_formula='(C-L)/(H-L)',range='0..1',flat_bar='UNKNOWN',prior_numeric_oracle_formula_was_correct=True,prior_prose_and_formula_registry_wrong=True)))
print(json.dumps(dict(families=len(families),fields=len(fields),core_outputs=len(core_rows),ddl_columns=len(ddlrows))))

from pathlib import Path
import sys,re,json,hashlib,os
B=Path(__file__).parent;sys.path.insert(0,str(B/'parser_deps'))
import pglast
from pglast.ast import CreateStmt,ColumnDef,Constraint
from pglast.enums import ConstrType
sql=(B/'FEP_R2_SCHEMA_DESIGN_20260930.sql').read_text(encoding='utf8')
main=(B/'FINAL_REV4_FEP_R2_DRAFT.md').read_text(encoding='utf8')
ast=pglast.parse_sql(sql);tables={};fks=[]
for raw in ast:
 st=raw.stmt
 if not isinstance(st,CreateStmt) or st.relation.schemaname!='fep':continue
 name=st.relation.relname;cols=set();keys=set()
 for c in st.tableElts:
  if isinstance(c,ColumnDef):
   cols.add(c.colname)
   for con in c.constraints or ():
    if con.contype in (ConstrType.CONSTR_PRIMARY,ConstrType.CONSTR_UNIQUE):keys.add((c.colname,))
    if con.contype==ConstrType.CONSTR_FOREIGN:fks.append((name,(c.colname,),con.pktable,tuple(x.sval for x in con.pk_attrs or ())))
  elif isinstance(c,Constraint):
   if c.contype in (ConstrType.CONSTR_PRIMARY,ConstrType.CONSTR_UNIQUE):keys.add(tuple(x.sval for x in c.keys))
   if c.contype==ConstrType.CONSTR_FOREIGN:fks.append((name,tuple(x.sval for x in c.fk_attrs),c.pktable,tuple(x.sval for x in c.pk_attrs or ())))
 tables[name]=(cols,keys)
for owner,local,target,remote in fks:
 assert set(local)<=tables[owner][0],(owner,local)
 if target.schemaname=='fep':
  assert target.relname in tables
  cols,keys=tables[target.relname]
  assert set(remote)<=cols,(owner,target.relname,remote)
  assert remote in keys,(owner,target.relname,remote,'non-unique target')
heads=re.findall(r'^#{1,6}\s+(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)(?=[.\s])',main,re.M)
assert len(heads)==len(set(heads));assert not set(re.findall(r'§\s*(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)',main))-set(heads)
assert len(re.findall(r'^```',main,re.M))%2==0 and main.count('**文档结束**')==1
ledger=sql.split('CREATE TABLE fep.dataset_eligibility_ledger')[1].split('CREATE TABLE fep.dataset_fold_cutoffs')[0]
assert 'selected_label_revision' not in ledger
assert 'CHECK(system_available_at>=label_due_at)' not in sql
guards=set(re.findall(r'CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep\.(\w+)',sql))
assert guards==set(tables)-{'deployment_heads'}
assert 'controlled_head BEFORE INSERT OR UPDATE OR DELETE' in sql
assert '当前生效版本为REV3-FEP' not in main
# Minimal independent relational/time/permission scenarios, not DB execution.
revs=[{'rev':1,'available':10,'mature':5},{'rev':2,'available':20,'mature':5}]
chosen=lambda c:max((x['rev'] for x in revs if x['available']<=c and x['mature']<=c),default=None)
assert chosen(15)==1 and chosen(25)==2
source_at,mature_at,revision_at=2,5,2
eligible=lambda c:all(x<=c for x in (source_at,mature_at,revision_at))
assert not eligible(3) and eligible(5)
g=('S','MARKET_EXCESS',5,'CORE_SCHEMA','SET_A','MODEL_DISPLAY')
assert g!=('S','INVALIDATION',20,'CORE_SCHEMA','SET_A','MODEL_DISPLAY')
head={'version':7,'activation':'A'}
def cas(expected,prior,activation):
 if head['version']!=expected or head['activation']!=prior:return 'CONFLICT'
 head.update(version=expected+1,activation=activation);return 'COMMITTED'
assert cas(7,'A','B')=='COMMITTED' and cas(7,'A','C')=='CONFLICT' and head['version']==8
assert ('STOCK_A','episode_1')!=('STOCK_B','episode_1')
result={'status':'R2_DOCUMENT_SQL_AST_AND_HAND_SCENARIOS_PASS','sql_parser':'pglast '+pglast.__version__,
 'sql_statements':len(ast),'ddl_tables':len(tables),'foreign_keys_checked':len(fks),'immutable_fact_tables':len(guards),
 'phase_revision_scenario':'early=r1,late=r2 PASS','three_times_scenario':'T2 fact,T5 mature: T3 reject,T5 eligible PASS',
 'permission_scenario':'T5 grant does not imply T20 grant PASS','cas_scenario':'one v7 request commits,v8 rejects stale v7 PASS',
 'priority_scope':'ENTRY is annotation only; daily PRIORITY_USE requires DAILY scope (document check)',
 'plpgsql_execution':'NOT_RUN; parser cannot resolve fep schema rowtypes','database_constraints_and_concurrency':'NOT_RUN',
 'external_acceptance':'EXTERNAL_REAUDIT_PENDING','source':'design/reference only'}
p=B/'R2_QA.json';t=p.with_name('.'+p.name+'.tmp')
with t.open('wb') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2).encode('utf8'));f.flush();os.fsync(f.fileno())
os.replace(t,p);print(json.dumps(result,ensure_ascii=False))

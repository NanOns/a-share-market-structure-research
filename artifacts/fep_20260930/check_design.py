from pathlib import Path
import math,re,json,os
B=Path(__file__).parent
doc=(B/'FINAL_REV3_FEP_DRAFT.md').read_text(encoding='utf8')
module=(B/'FEP_R1_DRAFT.md').read_text(encoding='utf8')
sql=Path('docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql').read_text(encoding='utf8')
heads=re.findall(r'^#{1,6}\s+(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)(?=[.\s])',doc,re.M)
refs=re.findall(r'§\s*(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)',doc)
assert not(set(refs)-set(heads));assert len(heads)==len(set(heads))
fence=False
for line in doc.splitlines():
 if line.startswith('```'):
  if fence:assert line.strip()=='```'
  fence=not fence
assert not fence
assert all(f'V4-15E{i}' in doc for i in range(1,6))
assert '明天上涨概率多少？' not in doc
assert doc.count('**文档结束**')==1
tables=set(re.findall(r'CREATE TABLE fep\.(\w+)',sql))
referenced=set(re.findall(r'REFERENCES fep\.(\w+)',sql))
assert not referenced-tables
slot=sql.split('CREATE TABLE fep.prediction_slots (')[1].split('CREATE TABLE fep.slot_model_bindings')[0]
assert 'model_set_id' not in slot
assert 'CREATE TABLE fep.dataset_eligibility_ledger' in sql
assert 'REFERENCES fep.slot_model_bindings' in sql
checks=[]
def eq(name,value,expected):
 assert math.isclose(value,expected,abs_tol=1e-12),(name,value,expected)
 checks.append({'case':name,'actual':value,'expected':expected,'status':'PASS'})
# Independent hand-computable vectors, NOT production algorithm executions.
ys=[.1]; ds=['d1']; n={d:ds.count(d) for d in set(ds)}
w=[1/(len(n)*n[d]) for d in ds]
eq('single_matched_bucket_weight',sum(w),1)
eq('single_matched_bucket_mean',sum(a*b for a,b in zip(w,ys)),.1)
eq('single_matched_bucket_positive_rate',sum(a*(y>0) for a,y in zip(w,ys)),1)
ys=[.1,.3,-.2]; ds=['d1','d1','d2'];n={d:ds.count(d) for d in set(ds)};w=[1/(len(n)*n[d]) for d in ds]
eq('date_weighted_mean',sum(a*b for a,b in zip(w,ys)),0)
eq('date_weighted_positive_rate',sum(a*(y>0) for a,y in zip(w,ys)),.5)
path=[100,120,110]; atr=2
eq('price_drawdown_atr',min(p-max(path[:i+1]) for i,p in enumerate(path))/atr,-5)
eq('ratio_drawdown_over_atr_ratio_is_different',min(p/max(path[:i+1])-1 for i,p in enumerate(path))/(atr/path[0]),-25/6)
events=[(2,'CONFIRMED'),(4,'INVALIDATED')]
assert min(events)[1]=='CONFIRMED' and {x[1] for x in events}=={'CONFIRMED','INVALIDATED'}
checks.append({'case':'first_exit_vs_any_event','status':'PASS','first':'CONFIRMED','any_confirm':1,'any_invalidate':1})
revisions=[('r1','2026-09-01'),('r2','2026-10-01')]
assert [r for r,d in revisions if d<='2026-09-30']==['r1']
checks.append({'case':'late_label_revision_cutoff','status':'PASS'})
result={'status':'DOCUMENT_QA_AND_HAND_VECTORS_PASS','numbered_headings':len(heads),'ddl_tables':len(tables),'ddl_reference_names':'PASS','sql_runtime':'NOT_EXECUTED','implementation_tests':'NOT_RUN','cases':checks}
p=B/'qa.json';t=p.with_name('.'+p.name+'.tmp')
with t.open('wb') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2).encode('utf8'));f.flush();os.fsync(f.fileno())
os.replace(t,p)
print(json.dumps(result,ensure_ascii=False))

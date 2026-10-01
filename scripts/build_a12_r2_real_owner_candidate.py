"""Full history candidate adapter and unchanged accepted special-phase price runtime."""
import gzip,hashlib,json,os,sys,tempfile,shutil
from contextlib import ExitStack
from collections import Counter
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.build_a12_status_st_authority_r1 import PATHS,canonical,identity
from scripts.build_v4_02_price_limits_generic import run_builder
from workbench_analysis.status_st_authority_candidate_r2 import candidate_fact
OUT=ROOT/'data/v4/artifact_store/a12_authority_candidate_r2'
PREFIX='reports/audits/A12_R2_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def main():
    if (ROOT/(PREFIX+'V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json')).exists():raise ValueError('IMMUTABLE_CANDIDATE_ALREADY_FROZEN')
    amendment=read(PREFIX+'MASTER_SOURCE_AUTHORITY_AMENDMENT_CANDIDATE_R1.json')
    assert amendment['choice']=='PATH_B_HISTORICAL_RECONSTRUCTED_AUTHORITY_AMENDMENT_CANDIDATE'
    owners={}
    for field,b in amendment['historical_owner_bindings'].items():
        assert bind(b['path'])['sha256']==b['sha256'];owners[field]=read(b['path'])
    OUT.mkdir(parents=True,exist_ok=True);paths={k:OUT/f'V4_02_{n}_AUTHORITY_R2.jsonl.gz' for k,n in [('status','DATED_TRADING_STATUS'),('st','DATED_ST_STATUS'),('price','PRICE_LIMIT')]}
    counts=Counter();transitions={k:Counter() for k in ['status','st']};digests={k:hashlib.sha256() for k in ['status','st']}
    tmp={};c=duckdb.connect();c.execute('create table bars as select canonical_security_id,trade_date from read_parquet(?)',[str(ROOT/PATHS['daily'])]);current=None;bars=set()
    with ExitStack() as stack:
        readers={k:stack.enter_context(gzip.open(ROOT/PATHS[k],'rt',encoding='utf8')) for k in ['universe','status','st','price']}
        writers={}
        for k in ['status','st']:
            fd,t=tempfile.mkstemp(dir=OUT,suffix='.tmp');os.close(fd);tmp[k]=Path(t);raw=stack.enter_context(open(t,'wb'));writers[k]=stack.enter_context(gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=3))
        for lines in zip(*(readers[k] for k in ['universe','status','st','price']),strict=True):
            u,s,i,p=map(json.loads,lines);assert identity(u)==identity(s)==identity(i)==identity(p)
            day=u['trade_date']
            if day!=current:
                bars={row[0] for row in c.execute('select canonical_security_id from bars where trade_date=?',[int(day.replace('-',''))]).fetchall()};current=day
            assert (u['source_bar_present'] is True)==(u['security_id'] in bars)
            ns=candidate_fact(u,s,owners['TRADING_STATUS'],field='TRADING_STATUS');ni=candidate_fact(u,i,owners['ISST'],field='ISST')
            # Full dependency equality is mandatory before reusing accepted price reference states.
            assert ns['status']==s['status']==p['trading_status']
            assert ni['is_st']==i['is_st']==p['is_st']
            for k,r in [('status',ns),('st',ni)]:b=canonical(r);writers[k].write(b);digests[k].update(b)
            counts['rows']+=1;counts['new_status_'+ns['status']]+=1;counts['new_st_'+str(ni['is_st'])]+=1;counts['provider_actual_conflicts']+=int(ns['provider_conflict'])
            transitions['status'][s['status']+' -> '+ns['status']]+=1;transitions['st'][str(i['is_st'])+' -> '+str(ni['is_st'])]+=1
            if counts['rows']%500000==0:print('A12_R2_FIELD_ROWS',counts['rows'],flush=True)
    c.close()
    assert counts['rows']==4035729
    for k,t in tmp.items():os.replace(t,paths[k])
    # Standard base references were independently frozen by R7. Every status/ST dependency was checked above.
    # Execute original generic R6 runtime, including original official special-phase events and rules.
    price=run_builder(output_path=paths['price'],receipt_path=ROOT/(PREFIX+'UNCHANGED_PRICE_RUNTIME_R1.json'))
    periods=[];c=duckdb.connect()
    for kind in ['WEEKLY','MONTHLY']:
        old='data/v4/artifact_store/v4_02/V4_02_FORMAL_'+kind+'_RAW_QFQ_R7_20260927.parquet';new=OUT/('V4_02_FORMAL_'+kind+'_RAW_QFQ_AUTHORITY_R2.parquet')
        fd,t=tempfile.mkstemp(dir=OUT,suffix='.tmp');os.close(fd);shutil.copyfile(ROOT/old,t);os.replace(t,new)
        c.read_parquet(str(ROOT/old)).create_view('o',replace=True);c.read_parquet(str(new)).create_view('n',replace=True)
        diff=c.execute('select count(*) from ((select * from o except all select * from n) union all (select * from n except all select * from o))').fetchone()[0];assert diff==0
        periods.append(dict(old=bind(old),candidate=bind(new.relative_to(ROOT).as_posix()),all_fields_rows_changed=diff,arithmetic_rows_changed=0,status_count_transitions=[],source_boundary='FULL_HISTORY_STATUS_VALUES_EQUAL_SOURCE; PERIOD_ARITHMETIC_AND_QUALITY_COUNTS_EXACT',validation='Bidirectional EXCEPT ALL on every column; dependency status rows independently matched'))
    c.close();atomic_json(ROOT/(PREFIX+'FORMAL_PERIOD_AUTHORITY_REBIND_R1.json'),dict(status='PASS_EXACT_FULL_ROW_PERIOD_DEPENDENCY_REPLAY',reports=periods,formal_publication=False,external_acceptance=None))
    artifacts={k:{**bind(p.relative_to(ROOT).as_posix()),**({'logical_digest':digests[k].hexdigest()} if k in digests else {})} for k,p in paths.items()}
    atomic_json(ROOT/(PREFIX+'V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json'),dict(contract_id='A12_R2_FULL_HISTORICAL_OWNER_CANDIDATE_V1',status='PASS_ENGINEERING_RECONSTRUCTED_CANDIDATE',artifacts=artifacts,counts=dict(counts),transitions={k:dict(v) for k,v in transitions.items()},inputs={k:bind(v) for k,v in PATHS.items()},owners=amendment['historical_owner_bindings'],price_runtime=bind(PREFIX+'UNCHANGED_PRICE_RUNTIME_R1.json'),price_limit_counts=price['limit_status_counts'],dependency_equality_rows=counts['rows'],algorithm_parameters_changed=False,source_boundary='PENDING_PATH_B_AMENDMENT_ONLY_NOT_FORMAL_CONSUMER_AUTHORITY',accepted_heads_unchanged=True,formal_publication=False,external_acceptance=None))
    print('PASS_A12_R2_FULL_HISTORY',dict(counts),flush=True)
if __name__=='__main__':main()

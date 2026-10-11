"""Independent Fraction arithmetic against native persisted settlement facts."""
import collections,hashlib,json,os,sys
from fractions import Fraction as F
from pathlib import Path
import psycopg
from psycopg import sql
ROOT=Path('G:/codex work/r4-pg-only-20261011')
OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
label=sys.argv[1];destination=OUT/(label+'_INDEPENDENT_NUMERIC_R1.json')
if destination.exists():raise ValueError('RETAIN_EXISTING_NUMERIC_EVIDENCE')
start=(OUT/(label+'_SOURCE_BINDINGS.json')).stat().st_mtime
end=(OUT/(label+'.xml')).stat().st_mtime
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def fail(ok,reason):
    if not ok:raise ValueError(reason)
def q(x):return F(str(x))
checks=0;statuses=collections.Counter();mismatches=[];receipts=[]
def equal(value,wanted,where):
    global checks
    checks+=1
    ok=value is None if wanted is None else isinstance(value,(int,float)) and abs(q(value)-wanted)<=F(1,10**12)
    if not ok:mismatches.append(dict(where=where,actual=value,expected=str(wanted)))
def exact(binding):
    p=(ROOT/binding['path']).resolve();fail(p.is_relative_to(ROOT),'NUMERIC_SOURCE_PATH_ESCAPE')
    b=p.read_bytes();fail(sha(b)==binding['sha256'] and len(b)==binding['bytes'],'NUMERIC_SOURCE_BYTES_MISMATCH');return json.loads(b)
def row_at(rows,sid,day,basis,cutoff):
    row=dict(rows.get(sid,{}).get(day,{}));available=row.get('available_at',day)
    if day>cutoff or available is None or available>cutoff:row={}
    row.setdefault('trade_date',day);row.setdefault('evaluation_basis_date',basis);return row
def path_values(reference,rows,basis):
    wanted={k:None for k in ('R_N','MFE_N','MAE_N','PATH_MDD_CLOSE_N')}
    if not rows:return 'PENDING',wanted
    ep=rows[-1]
    if ep.get('verified_identity') is not True:return 'IDENTITY_UNKNOWN',wanted
    if ep.get('verified_adjustment') is not True or ep.get('evaluation_basis_date')!=basis or ep.get('T0_basis_verified') is not True:return 'ADJUSTMENT_UNKNOWN',wanted
    t=ep.get('transform_coefficients',dict(alpha=1,beta=0));t0=ep.get('T0_transform_coefficients',t)
    p0=q(t0['alpha'])*q(reference)+q(t0['beta'])
    if p0<=0:return 'ADJUSTMENT_UNKNOWN',wanted
    if ep.get('status')=='DELISTED':
        if ep.get('terminal_verified') is True and ep.get('terminal_evidence') and ep.get('terminal_value') is not None:wanted['R_N']=q(ep['terminal_value'])/p0-1
        return 'DELISTED_BEFORE_HORIZON',wanted
    if ep.get('status')=='CONFIRMED_SUSPENSION':return 'SUSPENDED_AT_HORIZON',wanted
    if ep.get('close') is None:return 'MATURED_DATA_MISSING',wanted
    def price(r,key):
        tr=r.get('transform_coefficients',dict(alpha=1,beta=0));return q(tr['alpha'])*q(r[key])+q(tr['beta'])
    wanted['R_N']=price(ep,'close')/p0-1
    valid=[r for r in rows if r.get('status')!='CONFIRMED_SUSPENSION']
    if any(r.get(k) is None for r in valid for k in ('high','low','close')) or any(r.get('verified_identity') is not True or r.get('verified_adjustment') is not True or r.get('evaluation_basis_date')!=basis for r in valid):return 'OBSERVED',wanted
    wanted['MFE_N']=max([p0]+[price(r,'high') for r in valid])/p0-1
    wanted['MAE_N']=min([p0]+[price(r,'low') for r in valid])/p0-1
    closes=[p0]+[price(r,'close') for r in valid]
    wanted['PATH_MDD_CLOSE_N']=min([F(0)]+[close/max(closes[:i+1])-1 for i,close in enumerate(closes)])
    return 'OBSERVED',wanted
dsn='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres'
with psycopg.connect(dsn,autocommit=True) as pg:
    fail(pg.execute('SHOW data_directory').fetchone()[0].replace('\\','/').casefold()=='g:/codex_tmp/full_system_r4_fbd23a6b/pg_data','EXACT_ISOLATED_CLUSTER_REQUIRED')
    for family in ('r24','r24r1'):
        for descriptor in sorted((ROOT/'reports'/family/'activation_simulation').glob('*/successor.pg.json')):
            if not start<=descriptor.stat().st_mtime<=end:continue
            identity=json.loads(descriptor.read_bytes());schema=identity['schema'];fail(schema.startswith('v4_shadow_live_') and schema.replace('_','').isalnum(),'EXACT_NATIVE_SCHEMA_REQUIRED')
            with pg.transaction():
                pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
                facts=pg.execute('SELECT kind,id,payload,digest FROM facts ORDER BY ordinal').fetchall()
                for kind,key,raw,digest in facts:fail(sha(raw.encode())==digest,'PERSISTED_FACT_RAW_SHA_MISMATCH')
                artifacts={key:json.loads(raw)['value'] for kind,key,raw,digest in facts if kind=='artifact'}
                outcomes=[json.loads(raw) for kind,key,raw,digest in facts if kind=='outcome']
                count_before=checks
                for o in outcomes:
                    statuses[o['outcome_status']]+=1
                    frozen_binding=o['frozen_t0'];fail(frozen_binding['path'].startswith('pg-shadow:'),'NATIVE_ARTIFACT_REQUIRED')
                    frozen=artifacts[frozen_binding['path'][10:]];fail(sha(canonical(frozen))==frozen_binding['sha256'] and len(canonical(frozen))==frozen_binding['bytes'],'FROZEN_ARTIFACT_BYTES_MISMATCH')
                    raw_source=exact(o['evaluation_source'])['rows'];basis=o['due_date'];cutoff=o['report_cutoff']
                    path=[row_at(raw_source,frozen['signal_id'],r['trade_date'],basis,cutoff) for r in o['price_path']]
                    fail(path==o['price_path'],'PERSISTED_PATH_DIFFERS_FROM_RAW_SOURCE')
                    status,wanted=path_values(frozen['comparison_reference'],path,basis)
                    if status!=o['outcome_status']:mismatches.append(dict(where=o['outcome_revision_id']+'/status',actual=o['outcome_status'],expected=status))
                    for k,v in wanted.items():equal(o[k],v,o['outcome_revision_id']+'/'+k)
                receipts.append(dict(descriptor=descriptor.relative_to(ROOT).as_posix(),descriptor_sha256=sha(descriptor.read_bytes()),facts=len(facts),outcomes=len(outcomes),checks=checks-count_before,raw_facts_sha256=sha(canonical(facts))))
record=dict(contract='R4_R3_NATIVE_SHADOW_INDEPENDENT_FRACTION_ORACLE_V1',matrix=label,oracle_source_sha256=sha(Path(__file__).read_bytes()),ledgers=receipts,outcome_status_counts=dict(statuses),numeric_checks=checks,mismatches=mismatches,acceptance='SCOPED_PRICE_PATH_ORACLE_PASS' if checks and not mismatches else 'FAIL',limitations=['Scope is persisted subject price paths and their exact raw endpoints; benchmark/control semantics require separate comparison.','Simulation-only outcomes do not grant real maturity or deployment.'],production_changed=False,full_system_acceptance='OPEN')
destination.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in record.items() if k!='ledgers'}));sys.exit(0 if checks and not mismatches else 1)

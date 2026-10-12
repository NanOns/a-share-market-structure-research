"""Read-only Fraction oracle for every existing isolated native Shadow descriptor.

Simulation and corruption fixtures remain identified; this grants no maturity.
"""
from pathlib import Path
import json, hashlib, os, sys
from fractions import Fraction as F
from collections import Counter
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/pg_semantics/SHADOW_ALL_DESCRIPTOR_ORACLE_R2.json')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def q(value):return F(str(value))
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def oracle(reference,rows,basis,worker):
    wanted={k:None for k in ('R_N','MFE_N','MAE_N','PATH_MDD_CLOSE_N')}
    if not rows:return 'PENDING',wanted
    end=rows[-1]
    def coeff(c):return isinstance(c,dict) and set(c)=={'alpha','beta'} and all(type(c[k]) in (int,float) for k in c) and q(c['alpha'])>0
    if worker:
        identity=end.get('adjustment_identity')
        if not isinstance(identity,str) or not identity or not coeff(end.get('T0_transform_coefficients',end.get('transform_coefficients'))):return 'ADJUSTMENT_UNKNOWN',wanted
        for row in rows:
            if row.get('status')=='CONFIRMED_SUSPENSION' and row is not end:continue
            if row.get('verified_adjustment') is not True or row.get('evaluation_basis_date')!=basis or row.get('adjustment_identity')!=identity or not coeff(row.get('transform_coefficients')):return 'ADJUSTMENT_UNKNOWN',wanted
    if end.get('verified_identity') is not True:return 'IDENTITY_UNKNOWN',wanted
    if end.get('verified_adjustment') is not True or end.get('evaluation_basis_date')!=basis or end.get('T0_basis_verified') is not True:return 'ADJUSTMENT_UNKNOWN',wanted
    t0=end.get('T0_transform_coefficients',end.get('transform_coefficients',dict(alpha=1,beta=0)))
    p0=q(t0['alpha'])*q(reference)+q(t0['beta'])
    if p0<=0:return 'ADJUSTMENT_UNKNOWN',wanted
    if end.get('status')=='DELISTED':
        if end.get('terminal_verified') is True and end.get('terminal_evidence') and end.get('terminal_value') is not None:wanted['R_N']=q(end['terminal_value'])/p0-1
        return 'DELISTED_BEFORE_HORIZON',wanted
    if end.get('status')=='CONFIRMED_SUSPENSION':return 'SUSPENDED_AT_HORIZON',wanted
    if end.get('close') is None:return 'MATURED_DATA_MISSING',wanted
    def price(row,key):
        c=row.get('transform_coefficients',dict(alpha=1,beta=0));return q(c['alpha'])*q(row[key])+q(c['beta'])
    wanted['R_N']=price(end,'close')/p0-1
    actual=[r for r in rows if r.get('status')!='CONFIRMED_SUSPENSION']
    if any(r.get(k) is None for r in actual for k in ('high','low','close')) or any(r.get('verified_identity') is not True or r.get('verified_adjustment') is not True or r.get('evaluation_basis_date')!=basis for r in actual):return 'OBSERVED',wanted
    wanted['MFE_N']=max([p0]+[price(r,'high') for r in actual])/p0-1
    wanted['MAE_N']=min([p0]+[price(r,'low') for r in actual])/p0-1
    closes=[p0]+[price(r,'close') for r in actual]
    wanted['PATH_MDD_CLOSE_N']=min([F(0)]+[v/max(closes[:i+1])-1 for i,v in enumerate(closes)])
    return 'OBSERVED',wanted

def main():
    if OUT.exists():raise ValueError('PRESERVE_EXISTING_ORACLE')
    descriptors=sorted(p for family in ('r24','r24r1') for p in (ROOT/'reports'/family/'activation_simulation').glob('*/successor.pg.json'))
    records=[];statuses=Counter();checks=0;errors=[]
    with psycopg.connect('host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres',autocommit=True) as pg:
        ident=pg.execute("SELECT current_database(),current_setting('data_directory'),system_identifier::text FROM pg_control_system()").fetchone()
        assert ident==('postgres','G:/codex_tmp/full_system_r4_fbd23a6b/pg_data','7695278778933357404')
        for path in descriptors:
            record=dict(path=path.relative_to(ROOT).as_posix(),descriptor_sha256=sha(path.read_bytes()))
            try:
                descriptor=json.loads(path.read_bytes());schema=descriptor['schema']
                assert descriptor.get('contract_id')=='R4_R3_NATIVE_SHADOW_LIVE_STORAGE_V1' and schema.startswith('v4_shadow_live_') and schema.replace('_','').isalnum()
                with pg.transaction():
                    pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                    pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(schema)))
                    facts=pg.execute('SELECT kind,id,payload,digest FROM facts ORDER BY ordinal').fetchall()
                    for kind,key,raw,d in facts:assert sha(raw.encode())==d,'PERSISTED_FACT_DIGEST_MISMATCH'
                    artifacts={key:json.loads(raw)['value'] for kind,key,raw,d in facts if kind=='artifact'}
                    outcomes=[json.loads(raw) for kind,key,raw,d in facts if kind=='outcome']
                    worker={r[0] for r in pg.execute('SELECT accepted_outcome_revision FROM settlement_queue_v2 WHERE accepted_outcome_revision IS NOT NULL')}
                    record.update(facts=len(facts),outcomes=len(outcomes),checks=0,mismatches=[])
                    for outcome in outcomes:
                        frozen_ref=outcome['frozen_t0'];assert frozen_ref['path'].startswith('pg-shadow:')
                        frozen=artifacts[frozen_ref['path'][10:]]
                        assert sha(canonical(frozen))==frozen_ref['sha256']
                        binding=outcome['evaluation_source'];source_path=(ROOT/binding['path']).resolve()
                        assert source_path.is_relative_to(ROOT) and sha(source_path.read_bytes())==binding['sha256']
                        source=json.loads(source_path.read_bytes())['rows'];basis=outcome['due_date'];cutoff=outcome['report_cutoff'];rows=[]
                        for value in outcome['price_path']:
                            day=value['trade_date'];row=dict(source.get(frozen['signal_id'],{}).get(day,{}));available=row.get('available_at',day)
                            if day>cutoff or available is None or available>cutoff:row={}
                            row.setdefault('trade_date',day);row.setdefault('evaluation_basis_date',basis);rows.append(row)
                        assert rows==outcome['price_path'],'PERSISTED_PATH_DIFFERS_FROM_SOURCE'
                        status,wanted=oracle(frozen['comparison_reference'],rows,basis,outcome['outcome_revision_id'] in worker)
                        statuses[outcome['outcome_status']]+=1
                        if status!=outcome['outcome_status']:record['mismatches'].append(dict(revision=outcome['outcome_revision_id'],field='status',expected=status,actual=outcome['outcome_status']))
                        for field,expected in wanted.items():
                            actual=outcome[field];checks+=1;record['checks']+=1
                            if not (actual is None if expected is None else type(actual) in (int,float) and abs(q(actual)-expected)<=F(1,10**12)):
                                record['mismatches'].append(dict(revision=outcome['outcome_revision_id'],field=field,expected=str(expected),actual=actual))
                    record['status']='NUMERIC_FAIL' if record['mismatches'] else 'SCOPED_NUMERIC_PASS' if record['checks'] else 'EMPTY_OUTCOME_SET_NO_NUMERIC_SAMPLE'
            except (Exception,AssertionError) as error:
                record.update(status='DESCRIPTOR_OR_SOURCE_REJECTED',exception=type(error).__name__,reason=str(error))
            records.append(record)
    result=dict(contract_id='V4_NATIVE_SHADOW_ALL_DESCRIPTOR_FRACTION_ORACLE_R1',database_identity=ident,descriptor_denominator=len(descriptors),numeric_checks=checks,status_counts=dict(statuses),records=records,
        full_acceptance='OPEN_NEGATIVE_FIXTURE_CLASSIFICATION_AND_BENCHMARK_ORACLE_REQUIRED',production_changed=False,evidence_scope='All existing isolated simulation descriptors; not real enrollment/maturity',oracle_source_sha256=sha(Path(__file__).read_bytes()))
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(descriptors=len(records),checks=checks,disposition=dict(Counter(r['status'] for r in records)))))

if __name__=='__main__':main()

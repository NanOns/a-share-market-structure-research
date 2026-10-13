"""Reconcile all 47 declared current Core fields without repeating arithmetic."""
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

ROOT=Path('G:/codex work/v4-production-20261012')
BASE=Path(__file__).resolve().parents[1]/'docs/audits/v4_full_closeout_20261012/continuation_20261013'
OUT=BASE/'CORE_AVAILABILITY_ORACLE_R1'


def load(path):return json.loads(path.read_bytes())


def main():
    target=OUT/'CORE47_COVERAGE.json'
    if target.exists():raise ValueError('PRESERVE_CORE47_COVERAGE')
    cpath=ROOT/'data/v4/sealed_numeric_preparations_v1/412bb713abc87cd16cf2cb0bff5653971dcd97909609b6a7c574c616f18ca858/CANDIDATE.json'
    candidate=load(cpath);day=candidate['accepted_trade_date'];owner_ref=candidate['owners'][day]['core']
    availability=load(OUT/'RESULT.json');metadata=load(OUT/'WINDOW_METADATA.json');rps=load(OUT/'RPS_METADATA.json')
    known=load(BASE/'UNCOVERED_NUMERIC_R1/CORE_UNCOVERED_NUMERIC_ORACLE_R6_R1.json')
    relative=load(BASE/'RELATIVE_FULL_CURRENT_R1/RELATIVE_MARKET_NUMERIC_ORACLE_R6_R1.json')
    for report,expected in ((availability,'PASS_CORE_AVAILABILITY_SCOPE'),(metadata,'PASS_CORE_WINDOW_METADATA_SCOPE'),(rps,'PASS_RPS_METADATA_SCOPE'),(known,'PASS_KNOWN_SCOPE'),(relative,'PASS_DATED_RELATIVE_SCOPE')):
        if report['acceptance']!=expected or report.get('error_count',0):raise ValueError('CORE_COVERAGE_REQUIRED_RECEIPT_FAILED')
    if known['core']['sha256']!=owner_ref['sha256']:raise ValueError('CORE_NUMERIC_OWNER_BINDING_CHANGED')
    for report in (availability,metadata,rps,relative):
        if report['candidate']['sha256']!=hashlib.sha256(cpath.read_bytes()).hexdigest():raise ValueError('CORE_COVERAGE_CURRENT_CANDIDATE_MISMATCH')
    qa=load(ROOT/candidate['day_receipt']['path']);replay=load(ROOT/qa['numeric_core_oracle']['path'])
    primitive=next(row for row in replay['oracle'] if row['trade_date']==day)
    if primitive['result']!='PASS' or primitive['errors']:raise ValueError('CORE_MA_ATR_ORIGINAL_ACCEPTANCE_FAILED')
    contracts_path=ROOT/'config/v4_03_algorithm_contracts_v1.json';contracts=load(contracts_path)['contracts']
    declared={out['field_id']:(contract,out) for contract in contracts for out in contract['outputs']}
    if len(declared)!=47:raise ValueError('CORE47_NORMATIVE_DENOMINATOR')
    errors=[];typed_checks=0;row_count=0;actual_fields=None
    with gzip.open(ROOT/owner_ref['path'],'rt',encoding='utf-8') as stream:
        for row in map(json.loads,stream):
            row_count+=1;actual_fields=set(row['fields'])
            if actual_fields!=set(declared):raise ValueError('CORE47_ACTIVE_FIELD_SET_CHANGED')
            for name,cell in row['fields'].items():
                expected_type=declared[name][1]['type'];value=cell['value'];typed_checks+=1
                valid=value is None or (isinstance(value,bool) if expected_type in ('bool','boolean') else type(value) in (int,float) and math.isfinite(value))
                if not valid:errors.append(dict(security_id=row['security_id'],field=name,declared_type=expected_type,actual_type=type(value).__name__))
    ready={row['field']:row['count'] for row in availability['reason_counts'] if row['reason']=='OBSERVED'}
    matrix=[]
    for name,(contract,output) in sorted(declared.items()):
        if name.startswith('rel_market_'):
            scope='RELATIVE_MARKET_NUMERIC_ORACLE_R6_R1';numeric=relative['checks'][name]
        elif name.startswith('rps'):
            scope='CORE_UNCOVERED_NUMERIC_ORACLE_R6_R1 + RPS_METADATA';numeric=known['checks'][name]
        elif name in ('ma20','atr20'):
            scope='Bound current CORE_REPLAY original acceptance + new availability/window metadata';numeric=primitive['checks'][name]
            if numeric!=ready.get(name,0):raise ValueError('CORE_MA_ATR_KNOWN_DENOMINATOR_DRIFT')
        else:
            scope='CORE_UNCOVERED_NUMERIC_ORACLE_R6_R1 + availability/window metadata';numeric=known['checks'][name]
            if numeric!=ready.get(name,0):raise ValueError('CORE_KNOWN_FIELD_DENOMINATOR_DRIFT:'+name)
        matrix.append(dict(field=name,contract_id=contract['contract_id'],contract_version=contract['contract_version'],declared_type=output['type'],numeric_checks=numeric,coverage=scope,status='PASS_CURRENT_FIELD_SCOPE'))
    result=dict(contract_id='V4_CURRENT_CORE_ALL47_EXPLICIT_CONTRACT_COVERAGE_R1',acceptance='PASS_CURRENT_CORE47_SCOPE' if not errors else 'FAIL',T0=day,candidate=dict(path=cpath.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(cpath.read_bytes()).hexdigest(),bytes=cpath.stat().st_size),core=owner_ref,normative_contract=dict(path=str(contracts_path),sha256=hashlib.sha256(contracts_path.read_bytes()).hexdigest()),field_count=47,rows=row_count,typed_checks=typed_checks,type_error_count=len(errors),type_errors=errors,matrix=matrix,
        reused_numeric_comparison_boundary='Original bound MA20/ATR20 acceptance retained with its original 1e-9 verifier comparison; exact rational OHLC and the other known factor checks retain their independent comparison contracts. No stronger exact-all-factor claim is made.',
        known_numerical_arithmetic_reexecuted=False,publication_ready=False,scope='Current Core47 typed formula/UNKNOWN/window/source metadata coverage reconciliation. Global numerical, PG consumers and real publication are separate gates.')
    temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2),encoding='utf-8');os.replace(temporary,target)
    print(json.dumps(dict(acceptance=result['acceptance'],fields=47,rows=row_count,type_checks=typed_checks,errors=len(errors))))
    return bool(errors)


if __name__=='__main__':raise SystemExit(main())

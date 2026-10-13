"""Previously uncovered RPS quality, denominator and exact dated endpoint facts."""
import gzip
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('G:/codex work/v4-production-20261012')
BASE = Path(__file__).resolve().parents[1] / 'docs/audits/v4_full_closeout_20261012/continuation_20261013'


def load(path): return json.loads(path.read_bytes())


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return {row['security_id']: row for row in map(json.loads, stream)}


def main():
    target = BASE / 'CORE_AVAILABILITY_ORACLE_R1/RPS_METADATA.json'
    if target.exists(): raise ValueError('PRESERVE_RPS_METADATA_ORACLE')
    cpath = ROOT / 'data/v4/sealed_numeric_preparations_v1/412bb713abc87cd16cf2cb0bff5653971dcd97909609b6a7c574c616f18ca858/CANDIDATE.json'
    candidate = load(cpath)
    day = candidate['accepted_trade_date']
    dates = load(ROOT/'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json')['session_dates']
    position = dates.index(day)
    current = rows(ROOT/candidate['owners'][day]['core']['path'])
    prior = {lag: rows(ROOT/candidate['owners'][dates[position-lag]]['core']['path']) for lag in (1,3)}
    count, errors = 0, []
    def check(sid, name, actual, expected):
        nonlocal count
        count += 1
        if actual != expected: errors.append(dict(security_id=sid,field=name,actual=actual,expected=expected))
    for n in (5,20):
        denominator = sum(row['fields']['ret'+str(n)]['value'] is not None for row in current.values())
        for sid, row in current.items():
            ready = denominator >= 2 and row['fields']['ret'+str(n)]['value'] is not None
            cell = row['fields']['rps'+str(n)]
            for key, expected in dict(quality_state='OBSERVED' if ready else 'UNKNOWN',unknown_reason=None if ready else 'RETURN_OR_UNIVERSE_UNKNOWN',contract_id='RPS_MIDRANK_V1',denominator=denominator).items():
                check(sid,'rps'+str(n)+'.'+key,cell[key],expected)
            for lag in ((1,3) if n == 5 else (3,)):
                old = prior[lag].get(sid,{}).get('fields',{}).get('rps'+str(n),{}).get('value')
                delta_ready = ready and old is not None
                delta = row['fields']['rps'+str(n)+'_delta'+str(lag)]
                for key, expected in dict(quality_state='OBSERVED' if delta_ready else 'UNKNOWN',unknown_reason=None if delta_ready else 'EXACT_DATED_RPS_ENDPOINT_UNKNOWN',prior_endpoint=dates[position-lag],contract_id='RPS_MIDRANK_V1').items():
                    check(sid,'rps'+str(n)+'_delta'+str(lag)+'.'+key,delta[key],expected)
    result = dict(contract_id='V4_CURRENT_RPS_METADATA_INDEPENDENT_ORACLE_R1',acceptance='PASS_RPS_METADATA_SCOPE' if not errors else 'FAIL',T0=day,candidate=dict(path=cpath.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(cpath.read_bytes()).hexdigest(),bytes=cpath.stat().st_size),checks=count,error_count=len(errors),first_errors=errors[:100],rows=len(current),prior_dates=[dates[position-lag] for lag in (1,3)],known_rank_and_delta_arithmetic_reexecuted=False,publication_ready=False,
        scope='Five current RPS fields: quality, UNKNOWN reason, denominators, exact prior endpoints and versioned contracts. Existing numeric rank/delta PASS is conserved.')
    temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2),encoding='utf-8');os.replace(temporary,target)
    print(json.dumps(dict(acceptance=result['acceptance'],checks=count,errors=len(errors))))
    return bool(errors)


if __name__=='__main__':raise SystemExit(main())

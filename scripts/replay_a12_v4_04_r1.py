"""True full-market V4-04 replay with unchanged build_row and candidate authority inputs."""
from collections import Counter
import gzip,hashlib,json,os,sys,tempfile
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts import run_v4_04_full_market_candidate_r4 as b
from src.v4.accepted_input import resolve,AcceptedInput
from src.v4.market_regime_ui import project
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    sources=resolve(ROOT)
    status=json.loads((ROOT/'reports/audits/A12_V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json').read_text(encoding='utf8'))['artifacts']['status']
    period=json.loads((ROOT/'reports/audits/A12_FORMAL_PERIOD_AUTHORITY_REBIND_R1.json').read_text(encoding='utf8'))['reports']
    replacements={'trading_status':status,**{k:r['candidate'] for k,r in zip(['weekly','monthly'],period,strict=True)},
        'factors':bind('reports/audits/a12_v4_03_r1/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz'),
        'market_regime':bind('reports/audits/a12_v4_03_r1/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz')}
    for k,ref in replacements.items():
        assert bind(ref['path'])['sha256']==ref['sha256'];sources[k]=AcceptedInput(ROOT/ref['path'],ref['sha256'],'A12_CANDIDATE_'+k.upper())
    accepted=json.loads((ROOT/'data/v4/V4_04_ACCEPTED_HEAD.json').read_text(encoding='utf8'))
    contracts={p:bind(p)['sha256'] for p in b.CONTRACT_FILES};assert all(contracts[p]==accepted['contract_bindings'][p]['sha256'] for p in contracts)
    conn=duckdb.connect();daily=b._daily(conn,sources['daily'].path)
    weekly=b._periods(conn,sources['weekly'].path,int(b.P['WEEKLY_MA_WINDOW'])+1);monthly=b._periods(conn,sources['monthly'].path,int(b.P['MONTHLY_MA_WINDOW'])+1)
    universe=b._cutoff_universe(sources['universe'].path);starts={sid:(rows[-int(b.P['POS250_WINDOW'])] if len(rows)>=b.P['POS250_WINDOW'] else rows[0])['trade_date'] for sid,rows in daily.items() if rows}
    statuses=b._statuses(sources['trading_status'].path,starts)
    calendars={market:json.loads(sources[name].path.read_text(encoding='utf8'))['session_dates'] for market,name in [('SH','calendar'),('SZ','calendar_szse')]}
    regimes=project([json.loads(l) for l in gzip.open(sources['market_regime'].path,'rt',encoding='utf8')]);conn.close()
    source_digest=b.digest({k:v.sha256 for k,v in sorted(sources.items())});contract_digest=b.digest(contracts)
    out=ROOT/'reports/audits/a12_candidate_r1/V4_04_FULL_MARKET_CORE_PROFILE_AUTHORITY_R1.jsonl.gz';out.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=out.name+'.',suffix='.tmp',dir=out.parent);os.close(fd)
    counts=Counter();logical=hashlib.sha256()
    with open(temp,'wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=6) as writer,gzip.open(sources['factors'].path,'rt',encoding='utf8') as factors:
        for line in factors:
            f=json.loads(line);sid=f['security_id'];assert sid in universe
            row=b.build_row(f,daily.get(sid,[]),weekly.get(sid,[]),monthly.get(sid,[]),statuses.get(sid,[]),universe[sid],source_digest,contract_digest,calendars['SH' if f['board_scope'] in ('SH_MAIN','STAR') else 'SZ'],regimes[b.CUTOFF])
            data=(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();writer.write(data);logical.update(data)
            counts['rows']+=1;counts[row['profile_quality']]+=1
    os.replace(temp,out)
    assert counts['rows']==5222
    atomic_json(ROOT/'reports/audits/A12_V4_04_TRUE_REPLAY_R1.json',dict(status='PASS_TRUE_FULL_SCOPE_UNCHANGED_ALGORITHM_REPLAY',algorithm=bind('scripts/run_v4_04_full_market_candidate_r4.py'),artifact=bind(out.relative_to(ROOT).as_posix()),logical_digest=logical.hexdigest(),counts=dict(counts),sources={k:dict(path=v.path.relative_to(ROOT).as_posix(),sha256=v.sha256) for k,v in sources.items()},contract_bindings=contracts,source_digest=source_digest,contract_digest=contract_digest,formal_publication=False,external_acceptance=None))
    print(json.dumps(dict(status='PASS_TRUE_V4_04_REPLAY',counts=dict(counts))))

if __name__=='__main__':main()

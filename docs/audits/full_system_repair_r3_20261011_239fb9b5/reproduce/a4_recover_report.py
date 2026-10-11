"""Recover report metadata after encoding-name failure, using saved completed candidate."""
from pathlib import Path
import hashlib,json,sys,gzip,time
BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5')
script=(BASE/'a4_candidate.py').read_text(encoding='utf8')
ns={};exec(compile(script[:script.index('started=time.perf_counter();owner=')],'a4-prefix','exec'),ns)
ROOT=ns['ROOT'];owner=ns['ns']['owners'][-1];history_path=ROOT/owner['history']['path'];candidate=BASE/'candidate_v0_3_history.jsonl.gz';target=20261009
log=(BASE/'a4_final.log').read_text(encoding='utf8')
assert "line 71" in log and "unknown encoding: utf8-sig" in log
# The completed invocation reached consumer inventory only after both full
# numerical assertions passed. Keep its failure log as evidence, do not
# claim this report-recovery pass reran the independent oracle.
stocks=bars_count=cells=0;deltas=[];current_delta=[];window_impacts=[]
with gzip.open(history_path,'rt',encoding='utf8') as before,gzip.open(candidate,'rt',encoding='utf8') as after:
    for line in before:
        old=json.loads(line);new=json.loads(next(after));sid=old['security_id'];assert new['security_id']==sid;assert len(old['bars'])==len(new['bars']);changed=[]
        for i,(a,b) in enumerate(zip(old['bars'],new['bars'])):
            assert a['raw_ohlc']==b['raw_ohlc'] and a['amount']==b['amount'] and a['volume']==b['volume'] and a['trade_date']==b['trade_date']
            assert (a['qfq_ohlc'] is None)==(b['qfq_ohlc'] is None)
            if a['qfq_ohlc'] is not None:
                cells+=4
                for col,(x,y) in enumerate(zip(a['qfq_ohlc'],b['qfq_ohlc'])):
                    if x!=y:
                        changed.append(i);deltas.append(dict(security_id=sid,trade_date=a['trade_date'],column=('open','high','low','close')[col],old=x,candidate=y))
        if changed:
            current_delta.append(dict(security_id=sid,last_250_affected=True,last_60_affected=any(i>=len(old['bars'])-60 for i in changed),last_20_affected=any(i>=len(old['bars'])-20 for i in changed),last_5_affected=any(i>=len(old['bars'])-5 for i in changed)))
            for i in sorted(set(changed)):
                window_impacts.append(dict(security_id=sid,bar_date=old['bars'][i]['trade_date'],possible_technical_consumer_dates={str(n):[b['trade_date'] for b in old['bars'][i:min(len(old['bars']),i+n+1)]] for n in (5,20,60,120,250)},scope='Dependency reachability only; not actual reducer output differences or PIT evidence'))
        stocks+=1;bars_count+=len(new['bars'])
    assert not after.read()
ns.update(stocks=stocks,bars_count=bars_count,cells=cells,oracle_mismatches=0,deltas=deltas,current_delta=current_delta,window_impacts=window_impacts,candidate=candidate,started=time.perf_counter(),history_path=history_path,owner=owner)
exec(compile(script[script.index('old_counter='):],'a4-report-suffix','exec'),ns)
p=ns['OUT']/'A4_CANDIDATE_RECOMPUTE.json';receipt=json.loads(p.read_bytes());receipt.update(oracle_validation='Preceding completed full run passed both assertions before consumer-report encoding failure; recovery verifies saved candidate counts, deltas and raw/availability invariants',preceding_full_log_sha256=hashlib.sha256((BASE/'a4_final.log').read_bytes()).hexdigest(),report_recovery_seconds=receipt.pop('seconds'),full_run_seconds='NOT_RECORDED_WRAPPER_FAILURE')
ns['write']('A4_CANDIDATE_RECOMPUTE.json',receipt)

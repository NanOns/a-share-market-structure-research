"""Independent complete-row oracle from accepted local bars; no producer imports."""
import gzip, hashlib, json, sys
from collections import Counter
from itertools import zip_longest
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def rows(ref):
    assert bind(ref['path'])['sha256']==ref['sha256']
    with gzip.open(ROOT/ref['path'],'rt',encoding='utf8') as stream:
        for line in stream: yield json.loads(line)

def main():
    receipt=json.loads((ROOT/'reports/audits/A12_V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json').read_text(encoding='utf8'))
    contract=json.loads((ROOT/'config/v4_02_status_st_authority_r1.json').read_text(encoding='utf8'))
    assert contract['accepted_dated_evidence']==[], 'This oracle requires the frozen empty accepted dated pool'
    db=duckdb.connect(); source=ROOT/receipt['inputs']['daily']['path']
    assert bind(receipt['inputs']['daily']['path'])['sha256']==receipt['inputs']['daily']['sha256']
    dates={sid:set(ds) for sid,ds in db.execute('select canonical_security_id,list(trade_date) from read_parquet(?) group by canonical_security_id',[str(source)]).fetchall()};db.close()
    counts=Counter();transitions=Counter();digest=hashlib.sha256();samples={}
    iterators=[rows(receipt['inputs']['universe']),rows(receipt['inputs']['status']),rows(receipt['artifacts']['status']),rows(receipt['artifacts']['st']),rows(receipt['artifacts']['price'])]
    for group in zip_longest(*iterators):
        assert all(r is not None for r in group),'Unequal full-universe row counts'
        member,old,status,st,price=group
        keys=[(r['security_id'],str(r['trade_date']).replace('-','')) for r in group]
        assert len(set(keys))==1,keys
        sid,date=keys[0];expected='ACTUAL_TRADED' if int(date) in dates.get(sid,set()) else 'UNKNOWN'
        assert status['status']==expected and st['is_st'] is None
        assert price['limit_status']=='UNKNOWN' and price.get('risk_status') in [None,'UNKNOWN']
        for row in [status,st]:
            assert row['lineage']=='RECONSTRUCTED_CORRECTED' and row['first_availability_at_target_proven'] is False
        assert status['provider_role']=='SUPPLEMENTAL_CROSSCHECK' and st['provider_role']=='SUPPLEMENTAL_CROSSCHECK'
        assert price['knowledge_lineage']=='RECONSTRUCTED_CORRECTED'
        counts['rows']+=1;counts[expected]+=1;transition=old['status']+' -> '+expected;transitions[transition]+=1
        samples.setdefault(transition,dict(security_id=sid,trade_date=date,local_bar_present=expected=='ACTUAL_TRADED'))
        digest.update(json.dumps(dict(security_id=sid,trade_date=date,trading_status=expected,is_st=None,limit_status='UNKNOWN'),sort_keys=True,separators=(',',':')).encode()+b'\n')
    assert counts['rows']==4035729 and counts['UNKNOWN']==9118
    atomic_json(ROOT/'reports/audits/A12_INDEPENDENT_FULL_ROW_ORACLE_R1.json',dict(status='PASS_FULL_UNIVERSE_INDEPENDENT_LOCAL_BAR_ORACLE',counts=dict(counts),transitions=dict(transitions),samples=samples,oracle_business_digest=digest.hexdigest(),oracle='Direct SQL accepted canonical local-bar date membership; empty frozen dated authority pool; no status/ST/price producer helper imported',inputs=receipt['inputs'],outputs=receipt['artifacts'],external_acceptance=None,formal_publication=False))
    print(json.dumps(dict(status='PASS_INDEPENDENT_FULL_ROWS',counts=dict(counts))))

if __name__=='__main__':main()

"""Actual pending-candidate BFF reads; no production Head or service mutation."""
import argparse,json,os,hashlib,gzip
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_service.core_product_bff_r1 import CoreProductBFFR1
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from scripts.r4_r3_consumer_trace import ConsumerTrace

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

class NoLegacyFacts:
    def __getattr__(self,name):raise RuntimeError('LEGACY_FACT_ACCESS_FORBIDDEN:'+name)

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--resume-six',action='store_true');a=p.parse_args()
    if not a.label.isalnum():raise ValueError('VERSIONED_BFF_READBACK_REQUIRED')
    previous_folder=OUT/('SEALED_BFF_'+a.label)
    folder=OUT/('SEALED_BFF_'+a.label+('_FIELD_CONTINUATION' if a.resume_six else ''));folder.mkdir(exist_ok=False)
    preparation=json.loads((OUT/('SEALED_PRODUCT_CATALOG_'+a.label+'.json')).read_bytes())
    candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());day=candidate['accepted_trade_date']
    heads={n:(ROOT/'data/v4'/n).read_bytes() for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    api=OperationalSuccessorReaderV1(ROOT,candidate);bff=CoreProductBFFR1(api,NoLegacyFacts());records=[];errors=[];checks=0
    trace=ConsumerTrace(folder/'EXACT56_TRACE.json','Sealed new-day six BFF entries and affected history charts; real formal SELECT-only PG')
    trace.start()
    try:
        stocks=None
        for route in ('home','stocks','sectors','focus','market','diagnostics'):
            if a.resume_six:
                original_trace=json.loads((previous_folder/'EXACT56_TRACE.json').read_bytes())
                source_root=Path(__file__).resolve().parents[1]
                if any(not row['source_unchanged_during_run'] or hashlib.sha256((source_root/row['path']).read_bytes()).hexdigest()!=row['source_sha256'] for row in original_trace['rows']):
                    raise ValueError('REUSED_SIX_ENTRY_SOURCE_CHANGED')
                data=json.loads(gzip.decompress((previous_folder/(route+'.json.gz')).read_bytes()));code=200
            else:code,data=bff.get('/api/v4/'+route,dict(trade_date=day,context_token=api.token,limit='30'))
            raw=json.dumps(data,ensure_ascii=False,sort_keys=True).encode();(folder/(route+'.json.gz')).write_bytes(gzip.compress(raw,mtime=0))
            valid=code==200 and data.get('context_token')==api.token and data.get('context',{}).get('trade_date')==day
            checks+=1
            if not valid:errors.append(dict(route=route,code=code,status=data.get('status')))
            records.append(dict(route=route,code=code,status=data.get('status'),T0=data.get('context',{}).get('trade_date'),context_token=data.get('context_token'),total=data.get('total'),sha256=hashlib.sha256(raw).hexdigest(),reused_from_completed_entry=a.resume_six))
            if route=='stocks':stocks=data
            print(json.dumps(records[-1]),flush=True)
        diagnosis=json.loads((OUT/'formal_capture_diagnosis_20261013.json').read_bytes())
        freeze=json.loads(checked(ROOT,diagnosis['execution']['source_freeze']).read_bytes());binding=freeze['tdx'];path=Path(binding['path']).resolve()
        if not path.is_relative_to(Path('G:/codex_tmp').resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=binding['sha256']:raise ValueError('ACTUAL_NATIVE_SOURCE_REQUIRED')
        native={row['source_security_key'].upper():row for row in json.loads(path.read_bytes())['target_bars']}
        day_receipt=json.loads(checked(ROOT,candidate['day_receipt']).read_bytes())
        replay=json.loads(checked(ROOT,day_receipt['numeric_core_oracle']).read_bytes())
        owner=next(row for row in replay['owners'] if row['trade_date']==day)
        identities={row['security_id']:row['source_security_key'].upper() for row in json.loads(checked(ROOT,owner['sources']['identity']).read_bytes())['rows']}
        raw_rows=api.read('raw',day,api.token)['rows'];native_checks=0
        for row in raw_rows:
            source=native[identities[row['security_id']]]
            for field in ('open','high','low','close','amount','volume'):
                checks+=1;native_checks+=1
                if row[field]!=source[field]:errors.append(dict(scope='ACTUAL_NATIVE_TO_READER',security=row['security_id'],field=field,actual=row[field],expected=source[field]))
        correction=json.loads((OUT/('HISTORY_PROJECTION_CONSERVATION_'+a.label+'.json')).read_bytes())
        for row in correction['dates']:
            for difference in row['first_differences']:
                code,data=bff.chart(row['T0'],difference['security_id'],dict(period='D',price_basis='QFQ',limit='200',offset='0'))
                match=[bar for bar in data.get('items',[]) if bar['trade_date']==difference['day']]
                # Query the earlier slice when the corrected bar predates the last 200.
                if not match:
                    code,data=bff.chart(row['T0'],difference['security_id'],dict(period='D',price_basis='QFQ',limit='200',offset='200'))
                    match=[bar for bar in data.get('items',[]) if bar['trade_date']==difference['day']]
                checks+=1
                if code!=200 or len(match)!=1 or [match[0][name] for name in ('open','high','low','close')]!=difference['current']:
                    errors.append(dict(scope='CORRECTED_DATED_CHART',T0=row['T0'],difference=difference,code=code,match=match))
        result=dict(contract_id='V4_SEALED_CANDIDATE_BFF_FORMAL_PG_READBACK_R1',acceptance='PASS_BFF_SCOPED' if not errors else 'FAIL',
            candidate=preparation['candidate'],T0=day,context_token=api.token,records=records,checks=checks,native_checks=native_checks,errors=errors,
            scope='Six actual BFF entries, new-date native six-field conservation and directly affected dated QFQ charts; HTTP/desktop/snapshot/56 classification remain separate',
            publication=False,legacy_facts_access_allowed=False,existing_pass_suites_repeated=False)
    finally:trace.close()
    if any((ROOT/'data/v4'/name).read_bytes()!=before for name,before in heads.items()):raise ValueError('HEAD_MOVED_DURING_BFF_READBACK')
    atomic_json(folder,folder/'RESULT.json',result);print(json.dumps(dict(acceptance=result['acceptance'],checks=checks,errors=len(errors))),flush=True)
    return int(bool(errors))

if __name__=='__main__':raise SystemExit(main())

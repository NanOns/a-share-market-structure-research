"""Independent frozen-evidence verifier; does not import producer admission logic."""
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def binding(path):return {'path':path,'sha256':digest(path)}
def verified(item):return digest(item.get('path',item.get('frozen_path')))==item['sha256']

def main():
    target='2026-09-30'
    candidate=read('reports/v4_08/V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json')
    identity=read(candidate['identity_revision']['path'])
    parent=read(identity['parent_identity']['path'])
    capture=read('reports/v4_08/V4_08_R3_OFFICIAL_LIFECYCLE_SOURCE_CAPTURE.json')
    by_id={x['id']:x for x in capture['sources']}
    catalogue=read('reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json')
    rows=[]
    for page in catalogue['pages']:
        assert verified(page)
        doc=read(page['path'])[0];m=doc['metadata']
        assert m['pageno']==page['page_no'] and m['subname'].strip()==target
        assert m['recordcount']==catalogue['official_record_count']
        rows.extend(doc['data'])
    active={'SZ.'+x['agdm'] for x in rows}
    assert len(active)==len(rows)==catalogue['official_record_count']
    assert rows==catalogue['records']
    for entry in identity['target_sse_catalogues']:
        assert verified(entry)
        doc=read(entry['path'])
        assert doc['isPagination']=='false' and len(doc['result'])<doc['pageHelp']['pageSize']
        active.update('SH.'+x['A_STOCK_CODE'] for x in doc['result'])
    manifest=read('reports/v4_08/audit_inputs/V4_08_R3_LIFECYCLE_CAPTURE_MANIFEST.json')
    scope=manifest['scope_binding']
    assert manifest['runtime_authorized'] is False and manifest['scope']=='R3_IDENTITY_AUDIT_ONLY'
    frozen_path=manifest['source_contract_path']
    assert frozen_path.startswith('reports/v4_08/audit_inputs/')
    frozen_contract=(ROOT/frozen_path).read_bytes()
    assert hashlib.sha256(frozen_contract).hexdigest()==manifest['source_contract_sha256']
    assert json.loads(frozen_contract)==manifest['source_contract']
    assert digest(scope['classification_path'])==scope['classification_sha256']
    r2=read(scope['classification_path'])
    keys={x['source_security_key'] for x in r2['classification_detail'] if x['classification']=='AMBIGUOUS_IDENTITY' and x.get('formal_board_candidate') in ['SH_MAIN','SZ_MAIN','CHINEXT','STAR']}
    assert len(keys)==scope['expected_key_count']
    dispositions={x['source_security_key']:x for x in identity['dispositions']}
    assert set(dispositions)==keys
    for key,item in dispositions.items():
        assert all(verified(x) for x in item['evidence'])
        expected='FORMAL_IN_SCOPE_A_STOCK' if key in active else 'NOT_LISTED_AT_TARGET'
        assert item['classification']==expected
        if key.startswith('SZ.'):
            doc=read(by_id['SZ_'+key[3:]+'_exchange_query']['path'])[0]
            assert doc['metadata']['recordcount']==len(doc['data'])
            assert bool(doc['data'])==(key in active)
        if expected=='FORMAL_IN_SCOPE_A_STOCK':
            anchor=f"SZ\0{key}\0{item['listing_date']}".encode('ascii')
            assert item['security_id']=='SEC-'+hashlib.sha256(anchor).hexdigest()[:32].upper()
            assert item['listing_date']<=target
            assert by_id['SZ_'+key[3:]+'_listing']['status']=='PASS_CAPTURE'
    assert identity['records'][:len(parent['records'])]==parent['records']
    additions=identity['records'][len(parent['records']):]
    assert {x['source_security_key'] for x in additions}=={k for k in keys if k in active}
    assert not identity['unresolved_remainder']
    assert all(x['acceptance']=='CANDIDATE_PENDING_EXTERNAL_PROMOTION' for x in additions)
    id_checks={'prior_records_exactly_preserved':True,'all_11_terminal_dispositions':True,'official_complete_catalogues_recomputed':True,'canonical_ids_independently_recomputed':True,'no_active_lifecycle_ambiguity':True,'candidate_not_self_promoted':True}
    extension=read(candidate['calendar_extension']['path'])
    assert all(verified(x) for x in extension['sources'])
    for exchange in ['SSE','SZSE']:
        old=next(x for x in extension['sources'] if '/calendar_'+exchange.lower()+'_' in x['path'])
        dates=read(old['path'])['session_dates'];assert dates[-1]=='2026-09-24'
        new=[x for x in extension['sessions'] if x['market']==exchange]
        assert [x['trade_date'] for x in new]==['2026-09-28','2026-09-29',target]
        assert [x['session_no'] for x in new]==list(range(len(dates)+1,len(dates)+4))
        assert all(x['extension_parent_digest']==old['sha256'] for x in new)
        notice=next(x for x in extension['sources'] if x['path'].endswith(exchange.lower()+'_2026_mid_autumn_national_day.html'))
        text=BeautifulSoup((ROOT/notice['path']).read_bytes(),'html.parser').get_text()
        assert all(x in text for x in ['9月25日','9月27日','9月28日'])
    cal_checks={'both_exchanges_identical_dates':True,'official_holiday_reopening_verified':True,'session_numbers_recomputed_from_parent':True,'target_is_valid_session':True,'parent_digests_unchanged':True}
    source=read(candidate['source_capture']['path']);assert all(verified(x) for x in source['files'])
    assert datetime.fromisoformat(source['complete_observed_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()==target
    assert source['complete_observed_at']<=source['system_available_at']<=candidate['target_publication_cutoff_candidate']
    assert source['complete_observed_at']==max(x['observed_at'] for x in source['files'])
    assert not source['daily_capture_reused_from_previous_day'] and not source['filesystem_mtime_used_as_availability']
    raw=[json.loads(line) for line in gzip.decompress((ROOT/candidate['raw_diagnostic_artifact']['path']).read_bytes()).decode().splitlines()]
    identities={x['source_security_key']:x for x in identity['records']}
    noncore={x['source_security_key']:x['classification'] for x in read('reports/v4_08/V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION.json')['classification_detail']}
    counts=Counter();excluded=Counter()
    for row in raw:
        key=row['source_security_key'];record=identities.get(key);reason=None
        if row['sector_type'] not in ['INDUSTRY','THEME']:reason='NON_FORMAL_SECTOR_TYPE'
        elif key in dispositions and dispositions[key]['classification']=='NOT_LISTED_AT_TARGET':reason='NOT_LISTED_AT_TARGET'
        elif not record:reason=noncore.get(key,'UNMAPPED_IDENTITY')
        else:
            board=record['board']
            if board=='MAIN':board={'SH':'SH_MAIN','SZ':'SZ_MAIN'}.get(record['exchange'])
            if record['security_type']!='A_STOCK':reason='NON_EQUITY'
            elif board not in ['SH_MAIN','SZ_MAIN','CHINEXT','STAR']:reason='OPTIONAL_BOARD_OUTSIDE_REQUIRED_SCOPE'
            elif not record.get('list_date'):reason='UNVERIFIED_LISTING_DATE'
            elif record['list_date']>target:reason='NOT_LISTED_AT_TARGET'
            elif record.get('delist_date') and record['delist_date']<=target:reason='DELISTED_AT_TARGET'
            elif record.get('system_available_at') and record['system_available_at']>candidate['target_publication_cutoff_candidate']:reason='IDENTITY_UNAVAILABLE_AT_CUTOFF'
            elif key not in active:reason='NOT_IN_TARGET_ACTIVE_EXCHANGE_CATALOGUE'
        assert reason==row['active_universe_exclusion_reason']
        assert row['prospective_candidate_eligible_after_input_promotion']==(reason is None)
        if reason:excluded[reason]+=1
        else:
            assert row['security_id']==record['security_id']
            counts[row['sector_type']]+=1
    assert dict(counts)==candidate['prospective_candidate_member_rows_by_type']
    assert dict(excluded)==candidate['active_universe_exclusions_by_reason']
    assert len(raw)==candidate['raw_source_fact_count']
    assert not candidate['snapshot_created'] and not candidate['pit_observed'] and not candidate['historical_backtest_safe']
    assert not (ROOT/'data/v4/V4_08_ACCEPTED_HEAD.json').exists()
    pit_checks={'source_hashes_and_daily_timestamps_recomputed':True,'every_diagnostic_row_independently_adjudicated':True,'member_counts_and_exclusions_recomputed':True,'no_formal_snapshot_or_accepted_head':True,'no_self_promotion':True}
    verifier={'path':'scripts/postcheck_v4_08_r3_admission.py','sha256':digest('scripts/postcheck_v4_08_r3_admission.py'),'producer_admission_functions_imported':False,'active_catalogue_keys':len(active)}
    for path,checks in [('reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json',id_checks),('reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_POSTCHECK_R1.json',cal_checks),('reports/v4_08/V4_08_R3_FORWARD_PIT_INDEPENDENT_POSTCHECK.json',pit_checks)]:
        doc=read(path);doc.update(independent_checks=checks,independent_verifier=verifier)
        if 'identity_postcheck' in doc:doc['identity_postcheck']=binding('reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json');doc['calendar_postcheck']=binding('reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_POSTCHECK_R1.json')
        atomic_json(ROOT/path,doc)
    for head,postcheck in [('data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json','reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json'),('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json','reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_POSTCHECK_R1.json')]:
        doc=read(head);doc['postcheck']=binding(postcheck);atomic_json(ROOT/head,doc)
    for filename in ['V4_08_R3_FORMAL_UNIVERSE_IDENTITY_GATE.json','V4_08_R3_FORWARD_PIT_IDENTITY_GATE.json','V4_08_R3_CALENDAR_EXTENSION_BINDING.json','V4_08_R3_FORWARD_PIT_CALENDAR_BINDING.json']:
        path='reports/v4_08/'+filename;doc=read(path)
        field='identity_head' if 'identity_head' in doc else 'calendar_head';doc[field]=binding(doc[field]['path']);atomic_json(ROOT/path,doc)
    print(json.dumps({'status':'PASS_INDEPENDENT_ENGINEERING_POSTCHECK','active_keys':len(active),'prospective':dict(counts),'excluded':dict(excluded),'formal_snapshot_created':False}))

if __name__=='__main__':main()

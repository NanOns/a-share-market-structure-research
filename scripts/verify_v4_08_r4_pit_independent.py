"""Independent PIT membership recomputation from frozen inputs, not producer decisions."""
from __future__ import annotations
from collections import Counter
from datetime import date,datetime,timezone
import gzip
import hashlib
import json
import gzip
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json

TARGET='2026-09-30'
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def data(path):return (ROOT/path).read_bytes()
def digest_bytes(value):return hashlib.sha256(value).hexdigest()
def digest(path):return digest_bytes(data(path))
def bind(path):return {'path':path,'sha256':digest(path),'byte_count':len(data(path))}
def canon(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def parse_rows(path):
    with gzip.open(ROOT/path,'rt',encoding='utf-8') as stream:return [json.loads(line) for line in stream]
def available(record,cutoff):
    at=record.get('system_available_at') or record.get('observed_at')
    return not at or datetime.fromisoformat(at.replace('Z','+00:00'))<=datetime.fromisoformat(cutoff.replace('Z','+00:00'))
def classify_identity(record,target,cutoff,active):
    if not record:return 'UNMAPPED_IDENTITY'
    if record.get('security_type')!='A_STOCK':return 'NON_EQUITY'
    board=record.get('board')
    if board=='MAIN':board={'SH':'SH_MAIN','SZ':'SZ_MAIN'}.get(record.get('exchange'))
    if board not in {'SH_MAIN','SZ_MAIN','CHINEXT','STAR'}:return 'OPTIONAL_BOARD_OUTSIDE_REQUIRED_SCOPE'
    listed=record.get('list_date')
    if not listed:return 'UNVERIFIED_LISTING_DATE'
    if date.fromisoformat(listed)>date.fromisoformat(target):return 'NOT_LISTED_AT_TARGET'
    delisted=record.get('delist_date')
    if delisted and date.fromisoformat(delisted)<=date.fromisoformat(target):return 'DELISTED_AT_TARGET'
    if not available(record,cutoff):return 'IDENTITY_UNAVAILABLE_AT_CUTOFF'
    if record.get('acceptance')!='ACCEPTED':return 'IDENTITY_NOT_ACCEPTED'
    if record.get('source_security_key') not in active:return 'NOT_IN_TARGET_ACTIVE_EXCHANGE_CATALOGUE'
    return None

def own_snapshot_id(snapshot,revision,rows):
    stable=[]
    for row in rows:
        stable.append({key:row.get(key) for key in ('sector_id','sector_code','sector_name','sector_type','security_id','source_security_key','source_sector_type','membership_basis','membership_quality','pit_observed','historical_backtest_safe','identity_status','child_sector_ids','source_snapshot_id','parent_snapshot_id','parent_source_revision_id') if key in row})
    stable.sort(key=lambda x:(str(x.get('sector_type','')),str(x.get('sector_id','')),str(x.get('security_id','')),str(x.get('source_security_key',''))))
    payload={'target_trade_date':snapshot['target_trade_date'],'cutoff':datetime.fromisoformat(snapshot['cutoff'].replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z'),'sector_type_registry_digest':snapshot['sector_type_registry_digest'],'source_revision_ids':[revision['source_revision_id']],'source_digest':snapshot['source_digest'],'source_file_digests':dict(sorted(snapshot['source_file_digests'].items())),'membership_rows':stable,'membership_basis':snapshot['membership_basis'],'membership_quality':snapshot['membership_quality'],'parent_snapshot_id':None}
    return digest_bytes(canon(payload))

def verify():
    candidate=read('reports/v4_08/V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json')
    source_capture=read(candidate['source_capture']['path'])
    source_report=read('reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json')
    policy=read('config/v4_08_tdx_source_availability_policy_v2.json')
    identity_head=read('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json')
    identity=read(identity_head['identity_revision']['path'])
    calendar_head=read('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json')
    calendar=read(calendar_head['accepted_extension']['path'])
    catalogue=read('reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json')
    active={'SZ.'+x['agdm'] for x in catalogue['records']}
    for binding in identity['target_sse_catalogues']:
        active.update('SH.'+x['A_STOCK_CODE'] for x in read(binding['path'])['result'])
    raw= parse_rows(candidate['raw_diagnostic_artifact']['path'])
    facts=parse_rows('data/v4/artifact_store/v4_08/V4_08_PIT_MEMBERSHIP_FACTS_20260930_R1.jsonl.gz')
    revision=read('data/v4/artifact_store/v4_08/V4_08_PIT_SOURCE_REVISION_20260930_R1.json')
    snapshot=read('data/v4/artifact_store/v4_08/V4_08_PIT_SNAPSHOT_20260930_R1.json')
    registry=read('config/v4_08_sector_type_registry_v1.json')
    r2=read('reports/v4_08/V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION.json')
    noncore={x['source_security_key']:x['classification'] for x in r2['classification_detail']}
    identities={x['source_security_key']:dict(x) for x in identity['records']}
    parent_count=len(read(identity['parent_identity']['path'])['records'])
    for i,row in enumerate(identity['records']):
        if i<parent_count:identities[row['source_security_key']]['acceptance']='ACCEPTED'
    dispositions={x['source_security_key']:x['classification'] for x in identity['dispositions']}
    type_map=registry['source_mapping'];expected=[];exclusions=Counter()
    for source in raw:
        row=dict(source);row['sector_type']=type_map.get(str(source.get('source_sector_type','')).lower(),'UNKNOWN')
        key=row['source_security_key'];reason=None
        if row['source_fact_kind']=='DERIVED_PARENT':reason='DERIVED_PARENT_LINEAGE'
        elif row['sector_type'] not in {'INDUSTRY','THEME'}:reason='NON_FORMAL_SECTOR_TYPE'
        elif dispositions.get(key)=='NOT_LISTED_AT_TARGET':reason='NOT_LISTED_AT_TARGET'
        elif key not in identities:reason=noncore.get(key,'UNMAPPED_IDENTITY')
        else:reason=classify_identity(identities[key],TARGET,candidate['target_publication_cutoff_candidate'],active)
        if reason:exclusions[reason]+=1;continue
        identity_record=identities[key]
        expected.append({'sector_id':source['sector_id'],'sector_code':source['sector_code'],'sector_name':source['sector_name'],'sector_type':row['sector_type'],'source_sector_type':source['source_sector_type'],'source_security_key':key,'security_id':identity_record['security_id'],'identity_status':'MAPPED','target_trade_date':TARGET,'membership_asof_date':TARGET,'cutoff':candidate['target_publication_cutoff_candidate'],'membership_basis':'PIT_OBSERVED','membership_quality':'PIT_OBSERVED_ACCEPTED','pit_observed':True,'historical_backtest_safe':True,'source_revision_id':revision['source_revision_id'],'snapshot_id':snapshot['snapshot_id'],'source_digest':revision['source_digest'],'source_file_digests':revision['source_file_digests'],'source_revision_membership_basis':'PIT_OBSERVED','source_revision_quality':'PIT_OBSERVED_ACCEPTED','snapshot_membership_basis':'PIT_OBSERVED','snapshot_membership_quality':'PIT_OBSERVED_ACCEPTED','source_revision_chain_valid':True,'source_fact_kind':source['source_fact_kind'],'source_file':source['source_file'],'source_line_number':source['source_line_number'],'observed_at':source_capture['complete_observed_at'],'provider_available_at':source_capture['complete_observed_at'],'system_available_at':source_capture['system_available_at'],'ingested_at':source_capture['system_available_at'],'supersedes_revision_id':None,'snapshot_lineage_role':'FORWARD_PIT_CANDIDATE','active_universe_exclusion_reason':None})
    expected.sort(key=lambda x:(x['sector_type'],x['sector_id'],x['security_id'],x['source_security_key']))
    observed=[{k:v for k,v in row.items() if k!='membership_fact_id'} for row in facts]
    # Facts retain all source provenance fields; compare both canonical identity sets and each materialized logical record.
    expected_by_key={(x['sector_id'],x['security_id'],x['source_security_key']):x for x in expected}
    observed_by_key={(x['sector_id'],x['security_id'],x['source_security_key']):x for x in observed}
    set_match=set(expected_by_key)==set(observed_by_key)
    logical_mismatches=[]
    for key in expected_by_key.keys()&observed_by_key.keys():
        a,b=expected_by_key[key],observed_by_key[key]
        for field,value in a.items():
            if b.get(field)!=value:logical_mismatches.append({'key':list(key),'field':field,'expected':value,'actual':b.get(field)})
    temporal_day=datetime.fromisoformat(source_report['complete_observed_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    temporal_ok=(policy['provider_available_at_basis']==revision['provider_available_at_basis'] and policy['membership_asof_basis']==revision['membership_asof_basis'] and temporal_day==TARGET and source_report['complete_observed_at']<=source_report['system_available_at']<=revision['temporal_evidence']['cutoff'] and revision['membership_asof_date']==TARGET and not source_report['daily_capture_reused_from_previous_day'] and not source_report['filesystem_mtime_used_as_availability'])
    # Independently rebuild source revision and snapshot identities without producer helpers.
    temporal_digest=digest_bytes(canon(revision['temporal_evidence']))
    own_revision='sha256:'+digest_bytes(canon({'source_bytes_digest':revision['source_bytes_digest'],'temporal_evidence_digest':temporal_digest}))
    own_sid=own_snapshot_id(snapshot,revision,facts)
    sector_types=dict(sorted(Counter(x['sector_type'] for x in facts).items()))
    counts_match=sector_types==read('reports/v4_08/V4_08_R4_PIT_FACT_COUNTS.json')['formal_rows_by_type'] and dict(sorted(exclusions.items()))==read('reports/v4_08/V4_08_R4_PIT_EXCLUSION_INVENTORY.json')['exclusions_by_reason']
    checks={'P0_gate_and_both_external_promotions_accepted':read('reports/v4_08/V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json')['status']=='PASS' and identity_head['status']=='ACCEPTED' and calendar_head['status']=='ACCEPTED','independent_row_membership_set_matches':set_match,'all_logical_fact_fields_match':not logical_mismatches,'member_sector_and_exclusion_counts_recomputed':counts_match,'source_revision_id_recomputed':revision['source_revision_id']==own_revision,'snapshot_id_recomputed':snapshot['snapshot_id']==own_sid,'all_snapshot_facts_are_target_day_accepted_raw_only':all(x['target_trade_date']==TARGET and x['membership_asof_date']==TARGET and x['membership_basis']=='PIT_OBSERVED' and x['membership_quality']=='PIT_OBSERVED_ACCEPTED' and x['pit_observed'] and x['historical_backtest_safe'] and x['source_fact_kind']!='DERIVED_PARENT' and x['sector_type'] in {'INDUSTRY','THEME'} for x in facts),'source_time_policy_and_no_backfill':temporal_ok,'snapshot_fact_and_revision_bindings_consistent':all(x['snapshot_id']==snapshot['snapshot_id'] and x['source_revision_id']==revision['source_revision_id'] and x['source_digest']==revision['source_digest'] and x['source_file_digests']==revision['source_file_digests'] for x in facts),'no_final_v4_08_accepted_head':not (ROOT/'data/v4/V4_08_ACCEPTED_HEAD.json').exists()}
    report={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'logical_mismatch_count':len(logical_mismatches),'logical_mismatch_sample':logical_mismatches[:10],'independent_verifier':'scripts/verify_v4_08_r4_pit_independent.py','producer_admission_and_snapshot_functions_imported':False,'raw_source_rows':len(raw),'independently_admitted_rows':len(expected),'artifact_rows':len(facts),'independently_recomputed_exclusions':dict(sorted(exclusions.items())),'formal_fact_set_digest':digest_bytes(canon(expected)),'candidate_fact_artifact':bind('data/v4/artifact_store/v4_08/V4_08_PIT_MEMBERSHIP_FACTS_20260930_R1.jsonl.gz'),'identity_head':bind('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json'),'calendar_head':bind('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json')}
    atomic_json(ROOT/'reports/v4_08/V4_08_R4_PIT_INDEPENDENT_POSTCHECK.json',report)
    print(json.dumps({'status':report['status'],'checks':checks,'rows':len(facts),'expected':len(expected),'logical_mismatches':len(logical_mismatches)}))
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(verify())

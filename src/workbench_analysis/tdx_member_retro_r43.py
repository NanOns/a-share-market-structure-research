"""Actual read-only latest TDX capture, independently versioned retro scope."""
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import json
import re
import tempfile
from sector.membership_snapshot import build_snapshot
from .corrected_owner_replay import load, ref, gzrows, gzwrite, OUT
from .r43_owner_replay import source_ingress as checked
from .market_source_acquisition import write
from .tdx_official_daily_source import _atomic_write
from common.paths import resolve_tdx_root

MODE='TDX_LATEST_MEMBER_RETRO_V1'
EVIDENCE='data/v4/tdx_member_retro/r4_3_four_session_closeout_20261009'
REPAIR_EVIDENCE='data/v4/tdx_member_retro/r4_3_r1_targeted_repair_20261009'
ROW_NORMALIZATION_CONTRACT='TDX_MEMBER_ROW_NORMALIZATION_V2'


def row_classification(row):
    """Pure source-derived classification; preserve the existing capture semantics."""
    parent='DERIVED_PARENT' in row['source']
    return dict(industry_level='PARENT_DERIVED' if parent else 'LEAF' if row['sector_type']=='INDUSTRY' else 'CONCEPT',
                primary_industry_rank_eligible=not parent)


def normalize_member_row(row, mapping):
    """Deterministic parser-row to complete member-row normalization, with no I/O."""
    code=row['security_id'];ident=mapping.get(code)
    return dict(sector_id=row['sector_id'],sector_type=row['sector_type'],sector_code=row['sector_code'],
        sector_name=row['sector_name'],source_security_key=code,source=row['source'],**row_classification(row),
        security_id=ident['security_id'] if ident else None,identity_status='MAPPED' if ident else 'UNMAPPED_QUARANTINED',
        list_date=ident.get('list_date') if ident else None,delist_date=ident.get('delist_date') if ident else None)


def normalize_member_rows(records, mapping):
    rows=[normalize_member_row(r,mapping) for r in records if r['sector_type'] in ('INDUSTRY','THEME')]
    rows.sort(key=lambda r:(r['sector_type'],r['sector_id'],r['source_security_key']))
    if len({(r['sector_id'],r['source_security_key']) for r in rows})!=len(rows):raise ValueError('DUPLICATE_NORMALIZED_MEMBER')
    return rows


def normalized_frozen_rows(rows):
    """Add an explicit view for legacy ten-column S; never remove original columns."""
    result=[]
    for row in rows:
        derived=row_classification(row)
        if any(key in row and row[key]!=value for key,value in derived.items()):raise ValueError('SOURCE_CLASSIFICATION_CONFLICT')
        result.append(dict(row,**derived))
    return sorted(result,key=lambda r:(r['sector_type'],r['sector_id'],r['source_security_key']))


def _identity_records(payload):
    """Normalize only the exact identity rows covered by an accepted PG view."""
    if payload.get('contract_id')=='ACCEPTED_IDENTITY_NORMALIZED_VIEW_R3':
        rows=payload.get('records')
        if not isinstance(rows,list):raise ValueError('ACCEPTED_IDENTITY_RECORDS_REQUIRED')
    else:
        rows=payload.get('rows')
        if not isinstance(rows,list):raise ValueError('IDENTITY_ROWS_REQUIRED')
        rows=[row for row in rows if row.get('identity_status')=='IDENTITY_BOUND']
    keys=[str(row.get('source_security_key','')).upper() for row in rows]
    if any(not key or not row.get('security_id') for key,row in zip(keys,rows)):
        raise ValueError('IDENTITY_SOURCE_KEY_AND_SECURITY_ID_REQUIRED')
    if len(keys)!=len(set(keys)):raise ValueError('IDENTITY_SOURCE_KEY_NOT_UNIQUE')
    return rows


def parse_frozen_rows(root,snapshot):
    root=Path(root).resolve();from workbench_db.v4_historical_source_ingress_pg_r1 import materialize_bound
    from common.paths import resolve_ingest_temp_root
    temp_root=resolve_ingest_temp_root(root);temp_root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v4_tdx_member_parse_',dir=temp_root) as temporary:
        frozen=Path(temporary);cache=frozen/'T0002'/'hq_cache';cache.mkdir(parents=True)
        for source in snapshot['sources']:
            original=materialize_bound(root,source)
            target=cache/Path(source['path']).name
            target.write_bytes(original.read_bytes())
        frame,_=build_snapshot(frozen,snapshot['membership_observed_at'])
    identity_raw=materialize_bound(root,snapshot['identity_source']).read_bytes()
    identity_payload=json.loads(identity_raw)
    mapping={r['source_security_key'].upper():r for r in _identity_records(identity_payload)}
    return normalize_member_rows(frame.to_dict('records'),mapping)


def _latest_membership_candidate(root):
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    store=ForwardFactStore(Path(root),'data/v4/historical_source_ingress_pg_r1')
    rows=[]
    for binding in store.refs('tdx_membership_candidate'):
        record=store.read(binding)
        if (record.get('contract_id')=='V4_TDX_MEMBER_SNAPSHOT_CANDIDATE_PG_R1'
                and record.get('accepted_head') is False
                and isinstance(record.get('membership_observed_at'),str)):
            rows.append((record['membership_observed_at'],binding,record))
    if not rows:raise ValueError('TDX_MEMBER_PG_CANDIDATE_NOT_FOUND')
    _,binding,record=max(rows,key=lambda item:(item[0],str(item[1].get('pg_descriptor',{}).get('fact_key',''))))
    snapshot={k:record[k] for k in ('snapshot_id','trade_date','taxonomy','membership_mode',
        'membership_observed_at','knowledge_lineage','member_digest','source_bindings','identity_source',
        'AS_RECORDED','PIT_ELIGIBLE','accepted_head') if k in record}
    snapshot.update(membership_snapshot_id=record['snapshot_id'],member_set_asof=record['membership_observed_at'],
        sources=record['source_bindings'],memberships=None,production_eligible_scope='DATED_OPERATIONAL_RESEARCH_REPROJECTION_ONLY',
        survivorship_bias_risk=True,HISTORICAL_FIRST_AVAILABLE_PROVEN=False)
    snapshot['pg_candidate']=binding
    return snapshot,record


def digest(rows):
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _membership_candidate(root,snapshot,rows=None):
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore,canonical,digest as pg_digest
    store=ForwardFactStore(Path(root),'data/v4/historical_source_ingress_pg_r1')
    key=pg_digest(canonical({'membership_snapshot_id':snapshot['membership_snapshot_id'],
                             'membership_observed_at':snapshot['membership_observed_at']}))
    bindings=store.refs('tdx_membership_candidate')
    binding=next((b for b in bindings if b.get('pg_descriptor',{}).get('fact_key')==key),None)
    if binding:
        record=store.read(binding)
        if (record.get('contract_id')!='V4_TDX_MEMBER_SNAPSHOT_CANDIDATE_PG_R1'
                or record.get('snapshot_id')!=snapshot['membership_snapshot_id']
                or digest(record.get('rows',[]))!=snapshot['member_digest']
                or record.get('accepted_head') is not False):raise ValueError('TDX_MEMBER_PG_CANDIDATE_IDENTITY_MISMATCH')
        return dict(binding=binding,record=record)
    if rows is None:rows=gzrows(checked(root,snapshot['memberships']))
    if digest(rows)!=snapshot['member_digest']:raise ValueError('TDX_MEMBER_PG_INGRESS_DIGEST_MISMATCH')
    record={'contract_id':'V4_TDX_MEMBER_SNAPSHOT_CANDIDATE_PG_R1','contract_version':'1.0.0',
        'candidate_status':'DIAGNOSTIC_ONLY','snapshot_id':snapshot['membership_snapshot_id'],
        'membership_observed_at':snapshot['membership_observed_at'],'trade_date':snapshot.get('trade_date'),
        'taxonomy':snapshot['taxonomy'],'membership_mode':snapshot['membership_mode'],
        'knowledge_lineage':snapshot['knowledge_lineage'],'member_digest':snapshot['member_digest'],
        'row_count':len(rows),'source_bindings':snapshot['sources'],'identity_source':snapshot['identity_source'],
        'rows':rows,'AS_RECORDED':False,'PIT_ELIGIBLE':False,'accepted_head':False}
    binding=store.append('tdx_membership_candidate',key,record,migration_timeout_seconds=120)
    readback=store.read(binding)
    if readback!=record or digest(readback['rows'])!=snapshot['member_digest']:
        raise ValueError('TDX_MEMBER_PG_CANDIDATE_READBACK_MISMATCH')
    return dict(binding=binding,record=readback)


def validate_snapshot(snapshot, root, *, strict_pit=False):
    if strict_pit:raise ValueError('LATEST_MEMBERSHIP_NOT_STRICT_PIT')
    if snapshot['membership_mode']!=MODE or snapshot['taxonomy']!='TDX_INDUSTRY_CONCEPT':
        raise ValueError('WRONG_TAXONOMY_OR_MODE')
    if any(snapshot[k] is not False for k in ('AS_RECORDED','PIT_ELIGIBLE','HISTORICAL_FIRST_AVAILABLE_PROVEN')):
        raise ValueError('RETRO_FLAGS_MUST_REMAIN_FALSE')
    if snapshot['knowledge_lineage']!='RECONSTRUCTED_LATEST_MEMBERSHIP' or not snapshot['survivorship_bias_risk']:
        raise ValueError('RETRO_LINEAGE_REQUIRED')
    observed=datetime.fromisoformat(snapshot['membership_observed_at'])
    if observed.utcoffset()!=timedelta(hours=8) or snapshot['member_set_asof']!=snapshot['membership_observed_at']:
        raise ValueError('ACTUAL_SHANGHAI_OBSERVED_TIME_REQUIRED')
    expected_snapshot_id='TDX_MEMBER_SNAPSHOT_S_'+observed.strftime('%Y%m%d')+'_'+snapshot['member_digest']
    if snapshot['membership_snapshot_id']!=expected_snapshot_id:
        raise ValueError('SNAPSHOT_ID_DIGEST_MISMATCH')
    if len(snapshot['sources'])!=3:raise ValueError('COMPLETE_TDX_SOURCE_REQUIRED')
    from workbench_db.v4_historical_source_ingress_pg_r1 import materialize_bound
    for source in snapshot['sources']:materialize_bound(root,source)
    identity={r['source_security_key'].upper():r['security_id'] for r in _identity_records(load(materialize_bound(root,snapshot['identity_source'])))}
    candidate=_membership_candidate(root,snapshot)
    rows=candidate['record']['rows']
    if digest(rows)!=snapshot['member_digest']:raise ValueError('MEMBER_SET_DIGEST_MISMATCH')
    names={};keys=set()
    for r in rows:
        if r['sector_type'] not in ('INDUSTRY','THEME') or not r['sector_id'].startswith(r['sector_type']+':'):
            raise ValueError('TDX_NAMESPACE_REQUIRED')
        if not re.fullmatch(r'(SH|SZ|BJ)\.\d{6}',r['source_security_key']):raise ValueError('UNKNOWN_SOURCE_SECURITY_SYNTAX')
        if r['security_id']!=identity.get(r['source_security_key']):raise ValueError('CANONICAL_IDENTITY_MISMATCH')
        key=(r['sector_id'],r['source_security_key'])
        if key in keys:raise ValueError('DUPLICATE_MEMBER')
        keys.add(key);name=(r['sector_type'],r['sector_name'])
        if r['sector_id'] in names and names[r['sector_id']]!=name:raise ValueError('SECTOR_ID_NAME_TYPE_COLLISION')
        names[r['sector_id']]=name
    return rows


def metadata(snapshot, day):
    return {k:snapshot[k] for k in ('membership_mode','taxonomy','membership_snapshot_id',
        'membership_observed_at','member_set_asof','knowledge_lineage','AS_RECORDED','PIT_ELIGIBLE',
        'HISTORICAL_FIRST_AVAILABLE_PROVEN','production_eligible_scope','survivorship_bias_risk')} | {'trade_date':day}


def reparse_verification(root, output=None, snapshot=None):
    root=Path(root).resolve();out=root/REPAIR_EVIDENCE
    if snapshot is None:s,_=_latest_membership_candidate(root)
    else:
        pg_snapshot,record=_latest_membership_candidate(root)
        if snapshot.get('membership_snapshot_id')!=pg_snapshot.get('membership_snapshot_id'):
            raise ValueError('TDX_MEMBER_SNAPSHOT_PG_SELECTOR_MISMATCH')
        s=pg_snapshot
    original=validate_snapshot(s,root);rows=parse_frozen_rows(root,s)
    normalized_original=normalized_frozen_rows(original)
    if rows!=normalized_original:raise ValueError('FULL_NORMALIZED_MEMBER_ROW_MISMATCH')
    # Legacy S's complete ten-column digest is retained, explicitly separate
    # from the additive twelve-column view. No column is silently discarded.
    schema=set().union(*(r.keys() for r in original))
    legacy_projection=[{key:row[key] for key in schema} for row in rows]
    if legacy_projection!=original or digest(legacy_projection)!=s['member_digest']:raise ValueError('FROZEN_S_COMPLETE_SCHEMA_DIGEST_MISMATCH')
    code=root/'src/workbench_analysis/tdx_member_retro_r43.py';sha=hashlib.sha256(code.read_bytes()).hexdigest()
    frozen_code=out/'capture_builder_versions'/sha/'tdx_member_retro_r43.py'
    _atomic_write(frozen_code,code.read_bytes(),tdx_root=resolve_tdx_root(root))
    receipt=dict(contract_id=ROW_NORMALIZATION_CONTRACT,original_capture=ref(root,root/EVIDENCE/'01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json'),
        verification_observed_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),snapshot_pg_candidate=s['pg_candidate'],
        frozen_sources=s['sources'],executed_parser=ref(root,root/'src/sector/membership_snapshot.py'),executed_block_reader=ref(root,root/'src/tdx/block_reader.py'),
        executed_verifier=ref(root,code),frozen_executed_verifier=ref(root,frozen_code),member_digest=digest(original),normalized_row_digest=digest(rows),relation_count=len(rows),
        original_field_names=sorted(schema),normalized_field_names=sorted(set().union(*(r.keys() for r in rows))),
        legacy_schema='TEN_COLUMN_FROZEN_IDENTITY' if len(schema)==10 else 'COMPLETE_CLASSIFIED_MEMBER_SCHEMA',
        normalized_view_is_not_new_snapshot_identity=True,all_original_fields_preserved=True,
        member_key_unique=len({(r['sector_id'],r['source_security_key']) for r in rows})==len(rows),
        sector_coverage=dict(Counter(level for level,sector in {(r['industry_level'],r['sector_id']) for r in rows})),
        mismatched_records=0,exact_names_identity_members_equal=True,acceptance='FROZEN_SOURCE_REPARSE_V2_PASS',original_capture_code_hash_preserved=True)
    write(output or out/'SOURCE_CAPTURE_REPARSE_VERIFICATION_V2.json',receipt)
    return receipt


def capture(root):
    root=Path(root).resolve();out=root/EVIDENCE;pointer=out/'MEMBER_SNAPSHOT_S.json'
    now=datetime.now(timezone(timedelta(hours=8))).isoformat();tdx=resolve_tdx_root(root)
    sources=[]
    for name in ('tdxhy.cfg','tdxzs.cfg','infoharbor_block.dat'):
        source=tdx/'T0002/hq_cache'/name;raw=source.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        target=out/'latest_member_raw'/sha/name;_atomic_write(target,raw,tdx_root=tdx)
        sources.append(dict(address=str(source),observed_at=now,**ref(root,target)))
    # Parse only exact PG-ingressed bytes in a disposable G: temp tree.
    from workbench_db.v4_historical_source_ingress_pg_r1 import materialize_bound
    from common.paths import resolve_ingest_temp_root
    temp_root=resolve_ingest_temp_root(root);temp_root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v4_tdx_member_capture_',dir=temp_root) as temporary:
        frozen=Path(temporary);cache=frozen/'T0002'/'hq_cache';cache.mkdir(parents=True)
        for source in sources:
            original=checked(root,source)
            (cache/Path(source['path']).name).write_bytes(original.read_bytes())
        frame,_=build_snapshot(frozen,now)
    from .v4_current_stage_authority import CurrentStageAuthority
    current_authority=CurrentStageAuthority(root)
    identity_source=current_authority.identity_ref
    identity_payload=json.loads(materialize_bound(root,identity_source).read_bytes())
    identity=_identity_records(identity_payload)
    mapping={r['source_security_key'].upper():r for r in identity}
    rows=normalize_member_rows(frame.to_dict('records'),mapping)
    quarantine=[row for row in rows if row['identity_status']=='UNMAPPED_QUARANTINED']
    sha=digest(rows);snapshot=dict(membership_mode=MODE,taxonomy='TDX_INDUSTRY_CONCEPT',
        membership_snapshot_id='TDX_MEMBER_SNAPSHOT_S_'+datetime.fromisoformat(now).strftime('%Y%m%d')+'_'+sha,
        membership_observed_at=now,member_set_asof=now,knowledge_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP',
        AS_RECORDED=False,PIT_ELIGIBLE=False,HISTORICAL_FIRST_AVAILABLE_PROVEN=False,
        production_eligible_scope='DATED_OPERATIONAL_RESEARCH_REPROJECTION_ONLY',survivorship_bias_risk=True,
        member_digest=sha,memberships=gzwrite(root,out/'latest_member_S.jsonl.gz',rows),
        sources=sources,identity_source=identity_source,
        sector_counts=dict(Counter(t for t,s in {(r['sector_type'],r['sector_id']) for r in rows})),
        relation_count=len(rows),mapped_count=len(rows)-len(quarantine),unmapped_count=len(quarantine))
    accepted_membership=json.loads(materialize_bound(root,current_authority.membership_ref).read_bytes())
    oldbinding=accepted_membership['facts']
    # The accepted artifact is a historical source ingress: admit its exact
    # Head-bound bytes once, then downstream reads use the resulting PG binding.
    old_ingress=checked(root,oldbinding)
    old=gzrows(old_ingress);oldkeys={(r['sector_id'],r['source_security_key']) for r in old};newkeys={(r['sector_id'],r['source_security_key']) for r in rows}
    diffs=[dict(kind='SNAPSHOT_S',**snapshot)]
    diffs.extend(dict(kind='ADDED',sector_id=s,source_security_key=c) for s,c in sorted(newkeys-oldkeys))
    diffs.extend(dict(kind='REMOVED',sector_id=s,source_security_key=c) for s,c in sorted(oldkeys-newkeys))
    oldnames={r['sector_id']:r['sector_name'] for r in old};newnames={r['sector_id']:r['sector_name'] for r in rows}
    diffs.extend(dict(kind='NAME_CHANGE',sector_id=s,old_name=oldnames[s],new_name=newnames[s]) for s in sorted(oldnames.keys()&newnames.keys()) if oldnames[s]!=newnames[s])
    diff=gzwrite(root,out/'02_TDX_MEMBER_SNAPSHOT_S_AND_0930_PIT_DIFF.jsonl.gz',diffs)
    snapshot['pg_candidate']=_membership_candidate(root,snapshot,rows)['binding']
    # The workspace JSON is a compatibility mirror; selection and verification
    # below read the candidate fact from PG, never this pointer.
    write(pointer,snapshot)
    inventory=[]
    write(out/'01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json',dict(snapshot=ref(root,pointer),sources=sources,
        parser=ref(root,root/'src/sector/membership_snapshot.py'),block_reader=ref(root,root/'src/tdx/block_reader.py'),
        code=ref(root,root/'src/workbench_analysis/tdx_member_retro_r43.py'),block_dat_inventory=inventory,
        block_dat_inventory_status='NOT_SCANNED_UNUSED_BY_PARSER',
        accepted_0930=oldbinding,old_members=len(old),old_sectors=len({r['sector_id'] for r in old}),
        added=len(newkeys-oldkeys),removed=len(oldkeys-newkeys),same_membership=newkeys==oldkeys,
        quarantine=gzwrite(root,out/'latest_member_unmapped.jsonl.gz',quarantine),diff=diff,
        acceptance='TDX_LATEST_SNAPSHOT_SOURCE_PASS',next_stage='FOUR_DAY_RETRO_SECTOR',
        historical_effective_date='NOT_CLAIMED; mtime never used',download='NOT_REQUIRED: complete local industry/concept source parsed'))
    return snapshot

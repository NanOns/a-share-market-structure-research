"""Actual read-only latest TDX capture, independently versioned retro scope."""
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import json
import re
from sector.membership_snapshot import build_snapshot
from .corrected_owner_replay import load, ref, checked, gzrows, gzwrite, OUT
from .market_source_acquisition import write
from .tdx_official_daily_source import _atomic_write

MODE='TDX_LATEST_MEMBER_RETRO_V1'
EVIDENCE='docs/evidence/r4_3_four_session_closeout_20261009'


def digest(rows):
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


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
    if snapshot['membership_snapshot_id']!='TDX_MEMBER_SNAPSHOT_S_20261009_'+snapshot['member_digest']:
        raise ValueError('SNAPSHOT_ID_DIGEST_MISMATCH')
    if len(snapshot['sources'])!=3:raise ValueError('COMPLETE_TDX_SOURCE_REQUIRED')
    for source in snapshot['sources']:checked(root,source)
    identity={r['source_security_key'].upper():r['security_id'] for r in load(checked(root,snapshot['identity_source']))['rows'] if r.get('identity_status')=='IDENTITY_BOUND'}
    rows=gzrows(checked(root,snapshot['memberships']))
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


def reparse_verification(root):
    root=Path(root).resolve();out=root/EVIDENCE;s=load(out/'MEMBER_SNAPSHOT_S.json')
    original=validate_snapshot(s,root);frozen=out/'latest_member_parse'
    frame,_=build_snapshot(frozen,s['membership_observed_at'])
    identity={r['source_security_key'].upper():r for r in load(checked(root,s['identity_source']))['rows'] if r.get('identity_status')=='IDENTITY_BOUND'}
    rows=[]
    for row in frame.to_dict('records'):
        if row['sector_type'] not in ('INDUSTRY','THEME'):continue
        code=row['security_id'];ident=identity.get(code)
        rows.append(dict(sector_id=row['sector_id'],sector_type=row['sector_type'],sector_code=row['sector_code'],
            sector_name=row['sector_name'],source_security_key=code,source=row['source'],
            security_id=ident['security_id'] if ident else None,identity_status='MAPPED' if ident else 'UNMAPPED_QUARANTINED',
            list_date=ident.get('list_date') if ident else None,delist_date=ident.get('delist_date') if ident else None))
    rows.sort(key=lambda r:(r['sector_type'],r['sector_id'],r['source_security_key']))
    assert rows==original and digest(rows)==s['member_digest']
    code=root/'src/workbench_analysis/tdx_member_retro_r43.py';sha=hashlib.sha256(code.read_bytes()).hexdigest()
    frozen_code=out/'capture_builder_versions'/sha/'tdx_member_retro_r43.py'
    _atomic_write(frozen_code,code.read_bytes(),tdx_root=Path('D:/new_tdx'))
    write(out/'SOURCE_CAPTURE_REPARSE_VERIFICATION.json',dict(original_capture=ref(root,out/'01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json'),
        verification_observed_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),snapshot=ref(root,out/'MEMBER_SNAPSHOT_S.json'),
        frozen_sources=s['sources'],executed_parser=ref(root,root/'src/sector/membership_snapshot.py'),executed_block_reader=ref(root,root/'src/tdx/block_reader.py'),
        executed_verifier=ref(root,code),frozen_executed_verifier=ref(root,frozen_code),member_digest=digest(rows),relation_count=len(rows),
        exact_names_identity_members_equal=True,acceptance='FROZEN_SOURCE_REPARSE_PASS',original_capture_code_hash_preserved=True))


def capture(root):
    root=Path(root).resolve();out=root/EVIDENCE;pointer=out/'MEMBER_SNAPSHOT_S.json'
    if pointer.exists():
        snapshot=load(pointer);validate_snapshot(snapshot,root);return snapshot
    now=datetime.now(timezone(timedelta(hours=8))).isoformat();tdx=Path('D:/new_tdx')
    sources=[]
    for name in ('tdxhy.cfg','tdxzs.cfg','infoharbor_block.dat'):
        source=tdx/'T0002/hq_cache'/name;raw=source.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        target=out/'latest_member_raw'/sha/name;_atomic_write(target,raw,tdx_root=tdx)
        sources.append(dict(address=str(source),observed_at=now,**ref(root,target)))
    # Parse only frozen bytes, preventing mixed source versions during capture.
    frozen=out/'latest_member_parse';cache=frozen/'T0002/hq_cache'
    for source in sources:
        target=cache/Path(source['address']).name
        _atomic_write(target,checked(root,source).read_bytes(),tdx_root=tdx)
    frame,_=build_snapshot(frozen,now)
    identity=load(checked(root,load(root/OUT/'SOURCE_BINDINGS.json')['sources']['identity']))['rows']
    mapping={r['source_security_key'].upper():r for r in identity if r.get('identity_status')=='IDENTITY_BOUND'}
    rows=[];quarantine=[]
    for r in frame.to_dict('records'):
        if r['sector_type'] not in ('INDUSTRY','THEME'):continue
        code=r['security_id'];ident=mapping.get(code)
        base=dict(sector_id=r['sector_id'],sector_type=r['sector_type'],sector_code=r['sector_code'],
            sector_name=r['sector_name'],source_security_key=code,source=r['source'],
            industry_level='PARENT_DERIVED' if 'DERIVED_PARENT' in r['source'] else 'LEAF' if r['sector_type']=='INDUSTRY' else 'CONCEPT',
            primary_industry_rank_eligible='DERIVED_PARENT' not in r['source'],
            security_id=ident['security_id'] if ident else None,
            identity_status='MAPPED' if ident else 'UNMAPPED_QUARANTINED',
            list_date=ident.get('list_date') if ident else None,delist_date=ident.get('delist_date') if ident else None)
        rows.append(base)
        if not ident:quarantine.append(base)
    rows.sort(key=lambda r:(r['sector_type'],r['sector_id'],r['source_security_key']))
    sha=digest(rows);snapshot=dict(membership_mode=MODE,taxonomy='TDX_INDUSTRY_CONCEPT',
        membership_snapshot_id='TDX_MEMBER_SNAPSHOT_S_20261009_'+sha,
        membership_observed_at=now,member_set_asof=now,knowledge_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP',
        AS_RECORDED=False,PIT_ELIGIBLE=False,HISTORICAL_FIRST_AVAILABLE_PROVEN=False,
        production_eligible_scope='DATED_OPERATIONAL_RESEARCH_REPROJECTION_ONLY',survivorship_bias_risk=True,
        member_digest=sha,memberships=gzwrite(root,out/'latest_member_S.jsonl.gz',rows),
        sources=sources,identity_source=load(root/OUT/'SOURCE_BINDINGS.json')['sources']['identity'],
        sector_counts=dict(Counter(t for t,s in {(r['sector_type'],r['sector_id']) for r in rows})),
        relation_count=len(rows),mapped_count=len(rows)-len(quarantine),unmapped_count=len(quarantine))
    oldbinding=load(root/'config/v4_sector_operational_authority_v1.json')['sources']['membership']
    old=gzrows(checked(root,oldbinding));oldkeys={(r['sector_id'],r['source_security_key']) for r in old};newkeys={(r['sector_id'],r['source_security_key']) for r in rows}
    diffs=[dict(kind='SNAPSHOT_S',**snapshot)]
    diffs.extend(dict(kind='ADDED',sector_id=s,source_security_key=c) for s,c in sorted(newkeys-oldkeys))
    diffs.extend(dict(kind='REMOVED',sector_id=s,source_security_key=c) for s,c in sorted(oldkeys-newkeys))
    oldnames={r['sector_id']:r['sector_name'] for r in old};newnames={r['sector_id']:r['sector_name'] for r in rows}
    diffs.extend(dict(kind='NAME_CHANGE',sector_id=s,old_name=oldnames[s],new_name=newnames[s]) for s in sorted(oldnames.keys()&newnames.keys()) if oldnames[s]!=newnames[s])
    diff=gzwrite(root,out/'02_TDX_MEMBER_SNAPSHOT_S_AND_0930_PIT_DIFF.jsonl.gz',diffs)
    write(pointer,snapshot)
    inventory=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),parser_role='NOT_REQUIRED: full industry/concept relations recovered from supported cfg/infoharbor') for p in tdx.rglob('block_*.dat')]
    write(out/'01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json',dict(snapshot=ref(root,pointer),sources=sources,
        parser=ref(root,root/'src/sector/membership_snapshot.py'),block_reader=ref(root,root/'src/tdx/block_reader.py'),
        code=ref(root,root/'src/workbench_analysis/tdx_member_retro_r43.py'),block_dat_inventory=inventory,
        accepted_0930=oldbinding,old_members=len(old),old_sectors=len({r['sector_id'] for r in old}),
        added=len(newkeys-oldkeys),removed=len(oldkeys-newkeys),same_membership=newkeys==oldkeys,
        quarantine=gzwrite(root,out/'latest_member_unmapped.jsonl.gz',quarantine),diff=diff,
        acceptance='TDX_LATEST_SNAPSHOT_SOURCE_PASS',next_stage='FOUR_DAY_RETRO_SECTOR',
        historical_effective_date='NOT_CLAIMED; mtime never used',download='NOT_REQUIRED: complete local industry/concept source parsed'))
    return snapshot

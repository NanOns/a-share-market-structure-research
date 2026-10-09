"""Typed official package delta: integrity applies to all, stocks to exact identities.

V1 is deliberately unchanged. Unknown identities and foreign consumers retain
bytes and diagnostics in the manifest, and cannot become canonical stock rows.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import struct
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from .tdx_snapshot_delta import TDXDeltaError, _entry_index, _security_key

CONTRACT = 'TDX_A_STOCK_PACKAGE_DELTA_V2'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def decode(raw):
    if not raw or len(raw) % 32:
        raise TDXDeltaError('TDX_DAY_FILE_LENGTH_INVALID')
    result=[]; previous=0
    for offset, r in enumerate(struct.iter_unpack('<IIIIIfII', raw)):
        day,o,h,l,c,amount,volume,reserved=r
        try:
            date(day//10000,(day//100)%100,day%100)
        except (ValueError, OverflowError) as error:
            raise TDXDeltaError(f'TDX_DAY_FILE_DATE_INVALID:record={offset}:date={day}') from error
        if day<=previous:
            raise TDXDeltaError(f'TDX_DAY_FILE_DATE_ORDER_INVALID:record={offset}:date={day}')
        if not math.isfinite(amount) or amount<0 or h<max(o,l,c) or l>min(o,h,c):
            raise TDXDeltaError(f'TDX_DAY_FILE_OHLC_INVALID:record={offset}:date={day}')
        result.append((raw[offset*32:(offset+1)*32], dict(trade_date=day,open=o/100,high=h/100,low=l/100,close=c/100,amount=amount,volume=volume)))
        previous=day
    return result


def classify(key, identity):
    if identity:
        if identity.get('security_type')!='A_STOCK' or not identity.get('security_id','').startswith('SEC-'):
            raise TDXDeltaError('CANONICAL_IDENTITY_TYPE_INVALID:'+key)
        return 'A_STOCK_CANONICAL', 'A_STOCK_RESEARCH', 'ACCEPTED_CANONICAL_IDENTITY'
    market,code=key.split('.')
    if (market=='SH' and code.startswith('900')) or (market=='SZ' and code.startswith('200')):
        return 'B_STOCK', 'NON_A_STOCK_ENTRY_QUARANTINED', 'TDX_SECURITY_MASTER_B_SHARE_RANGE'
    if (market=='SH' and code.startswith('000')) or (market=='SZ' and code.startswith('399')) or (market=='BJ' and code.startswith('899')):
        return 'INDEX', 'INDEX_SEPARATE_CONSUMER_REQUIRED', 'TDX_SECURITY_MASTER_INDEX_RANGE'
    if market=='SZ' and code.startswith('131'):
        return 'REPO_RANGE_INFERRED', 'NON_A_STOCK_ENTRY_QUARANTINED', 'SZSE_REPO_CODE_RANGE; INFERENCE_NOT_LIFECYCLE_AUTHORITY'
    if market=='SH' and code.startswith(('88','99')):
        return 'TDX_CUSTOM_INSTRUMENT_UNVERIFIED', 'UNSUPPORTED_INSTRUMENT', 'VENDOR_NAMESPACE_ONLY; NO_ACCEPTED_STOCK_IDENTITY'
    if (market=='SH' and re.fullmatch('(600|601|603|605|688|689)[0-9]{3}',code)) or (market=='SZ' and re.fullmatch('(000|001|002|003|300|301)[0-9]{3}',code)) or market=='BJ':
        return 'UNBOUND_STOCK_CANDIDATE', 'CANONICAL_IDENTITY_UNPROVEN', 'CODE_FAMILY_IS_NOT_IDENTITY_AUTHORITY'
    if market=='SH' and code.startswith(('110','111','113','118')):
        return 'BOND_RANGE_INFERRED', 'NON_A_STOCK_ENTRY_QUARANTINED', 'TDX_SECURITY_MASTER_BOND_RANGE'
    return 'UNVERIFIED_OTHER', 'UNSUPPORTED_INSTRUMENT', 'NO_ACCEPTED_INSTRUMENT_AUTHORITY'


def validate_identity(identity, target):
    start=identity.get('normalized_effective_from') or identity.get('symbol_effective_from') or identity.get('list_date')
    end=identity.get('normalized_effective_to') or identity.get('symbol_effective_to') or identity.get('delist_date')
    return bool(start and start<=target and (not end or target<=end))


def build_typed_delta(*, parent_zip, current_zip, target_dates, identities, identity_binding,
                      policy_binding, parent_sha256, current_sha256, dated_members):
    dates=sorted(set(target_dates)); nums={int(d.replace('-','')):d for d in dates}
    for d in dates: date.fromisoformat(d)
    if file_sha(parent_zip)!=parent_sha256 or file_sha(current_zip)!=current_sha256:
        raise TDXDeltaError('TDX_PACKAGE_SHA_MISMATCH')
    if parent_sha256==current_sha256:
        raise TDXDeltaError('TDX_SNAPSHOT_PARENT_IDENTITY_INVALID')
    manifest=[]; target_rows={d:[] for d in dates}; revisions=[]; failures=[]
    with zipfile.ZipFile(parent_zip) as old, zipfile.ZipFile(current_zip) as new:
        oi,ni=_entry_index(old),_entry_index(new)
        for archive in (old,new):
            if any((i.external_attr>>16)&0o170000==0o120000 for i in archive.infolist()):
                raise TDXDeltaError('TDX_ZIP_SYMLINK')
            if archive.testzip() is not None:
                raise TDXDeltaError('TDX_ZIP_CRC_FAILURE')
        for name in sorted(set(oi)|set(ni)):
            op,np=oi.get(name),ni.get(name)
            before=old.read(op) if op else b''; after=new.read(np) if np else b''
            kind='REMOVED' if not np else 'NEW' if not op else 'UNCHANGED' if before==after else 'CHANGED'
            row=dict(path=name,current_sha=hashlib.sha256(after).hexdigest() if np else None,
                parent_sha=hashlib.sha256(before).hexdigest() if op else None,current_bytes=len(after),parent_bytes=len(before),change=kind)
            if not name.endswith('.day'):
                manifest.append(dict(row,inferred_type='NON_DAILY',consumer_scope='NON_DAILY_ENTRY_RETAINED'));continue
            try:
                key=_security_key(name)
            except TDXDeltaError as error:
                # Some vendor non-equity symbols are alphanumeric. They cannot
                # match a canonical identity; retain their bytes and exact error.
                manifest.append(dict(row,inferred_type='UNPARSED_VENDOR_INSTRUMENT',
                    verified_instrument_class='NOT_POSITIVELY_VERIFIED',consumer_scope='UNSUPPORTED_INSTRUMENT',
                    validation_error=[str(error)],action='QUARANTINED_UNPARSED_ENTRY'))
                continue
            identity=identities.get(key)
            instrument,consumer,evidence=classify(key,identity)
            row.update(source_security_key=key,market=key.split('.')[0],inferred_type=instrument,
                       verified_instrument_class='A_STOCK' if identity else 'NOT_POSITIVELY_VERIFIED',
                       consumer_scope=consumer,authoritative_classification_evidence=evidence,
                       validation_error=[],revision_errors=[],current_target_bar={},action=consumer)
            nr=pr=[]
            for label,raw in (('parent',before),('current',after)):
                if not raw: continue
                if label=='current' and before==after and pr:
                    nr=pr;continue
                try:
                    rs=decode(raw)
                    if label=='parent':pr=rs
                    else:nr=rs
                except TDXDeltaError as error:
                    row['validation_error'].append(label+':'+str(error))
            # Record target presence even when another record is invalid.
            if after and len(after)%32==0:
                present={r[0] for r in struct.iter_unpack('<IIIIIfII',after)}
                row['current_target_bar']={d:int(d.replace('-','')) in present for d in dates}
            if not np: row['revision_errors'].append('SOURCE_REVISION_ANOMALY_REMOVED_ENTRY')
            if pr and nr:
                if len(nr)<len(pr):row['revision_errors'].append('SOURCE_REVISION_ANOMALY_TRUNCATION')
                common=min(len(nr),len(pr))
                if any(pr[i][1]['trade_date']!=nr[i][1]['trade_date'] for i in range(common)):
                    row['revision_errors'].append('SOURCE_REVISION_ANOMALY_REWRITE')
                changes=[i for i in range(common) if pr[i][0]!=nr[i][0]]
                if changes:
                    revisions.append(dict(source_security_key=key,consumer_scope=consumer,
                        affected_trade_dates=[pr[i][1]['trade_date'] for i in changes],
                        old_rows_sha256=hashlib.sha256(b''.join(pr[i][0] for i in changes)).hexdigest(),
                        new_rows_sha256=hashlib.sha256(b''.join(nr[i][0] for i in changes)).hexdigest(),classification='HISTORICAL_CORRECTION'))
            if identity:
                if row['validation_error'] or row['revision_errors']:
                    failures.append(row)
                else:
                    for _,bar in nr:
                        if bar['trade_date'] not in nums:continue
                        day=nums[bar['trade_date']]
                        if not validate_identity(identity,day) or key not in dated_members.get(day,set()):
                            row['action']='DATE_IDENTITY_NOT_ADMITTED';continue
                        if min(bar[k] for k in ('open','high','low','close'))<=0:
                            failures.append(dict(row,target_date=day,target_error='NONPOSITIVE_TARGET_OHLC'));continue
                        if bar['volume']==0:
                            row.setdefault('capability_restrictions',[]).append('ZERO_VOLUME_REQUIRES_STATUS_OWNER')
                            continue
                        target_rows[day].append(dict(bar,security_id=identity['security_id'],source_security_key=key))
            manifest.append(row)
    for day in dates:target_rows[day].sort(key=lambda x:x['security_id'])
    result=dict(contract_id=CONTRACT,version='2.0.0',status='BLOCKED_TARGET_A_STOCK' if failures else 'READY',
        source_scope_policy=policy_binding,identity_binding=identity_binding,
        parent_package_sha256=parent_sha256,current_package_sha256=current_sha256,
        package_integrity='PASS_SHA_CRC_PATHS_DUPLICATES_SYMLINKS',target_dates=dates,
        targets={d:dict(status='BLOCKED_TARGET_A_STOCK' if failures else 'READY',target_bar_count=len(rs),
                        target_bar_digest=digest(rs),target_bars=rs) for d,rs in target_rows.items()},
        entry_manifest=manifest,entry_counts=dict(Counter(r['change'] for r in manifest)),
        consumer_counts=dict(Counter(r['consumer_scope'] for r in manifest)),target_failures=failures,
        revision_events=revisions,AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',
        production_permission=False,price_limit_capability='REQUIRES_SEPARATE_DATED_OWNER')
    result['delta_sha256']=digest(result)
    return result

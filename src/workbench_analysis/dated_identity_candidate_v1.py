"""Same-day identity source candidate. Facts and hashes never grant authority."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from .v4_14_replay_io import exact, publish, digest, ref
from .validation_cohort_read_contract_r3 import instant

CONTRACT='DATED_IDENTITY_AUTHORITY_SOURCE_CANDIDATE_V1'
SHANGHAI=timezone(timedelta(hours=8))


def build(root, *, sources, parent_head, candidate_directory, cutoff,
          clock=lambda:datetime.now(timezone.utc)):
    directory=Path(candidate_directory)
    if directory.is_absolute() or '..' in directory.parts or directory.parts[:2]!=('docs','evidence'):
        raise ValueError('ISOLATED_IDENTITY_CANDIDATE_DIRECTORY_REQUIRED')
    required={'roster','tdx','gbbq','identity_events','membership'}
    if set(sources)!=required:raise ValueError('EXACT_IDENTITY_SOURCE_SET_REQUIRED')
    now=clock(); target=instant(cutoff).astimezone(SHANGHAI).date().isoformat()
    if now.tzinfo is None or instant(cutoff)>now or target!=now.astimezone(SHANGHAI).date().isoformat():
        raise ValueError('REAL_CURRENT_IDENTITY_CLOCK_REQUIRED_NO_BACKFILL')
    docs={name:json.loads(exact(root,binding)) for name,binding in sources.items()}
    parent=json.loads(exact(root,parent_head))
    if parent.get('accepted_trade_date','9999')>=target:raise ValueError('PREVIOUS_ACCEPTED_HEAD_REQUIRED')
    synthetic=all(d.get('evidence_class')=='SYNTHETIC_ISOLATED_TEST_ONLY' for d in docs.values())
    gaps=[]
    for name,doc in docs.items():
        if doc.get('T0')!=target or not doc.get('revision'):
            raise ValueError('DATED_IDENTITY_SOURCE_REVISION_REQUIRED:'+name)
        if doc.get('evidence_class') not in ('OBSERVED_SOURCE_CANDIDATE','SYNTHETIC_ISOLATED_TEST_ONLY'):
            gaps.append(name+':AS_RECORDED_SOURCE_NOT_PROVEN')
        for field in ('requested_at','received_at','first_available'):
            if not doc.get(field):gaps.append(name+':'+field+'_MISSING')
        if all(doc.get(k) for k in ('requested_at','received_at','first_available')):
            if not (instant(doc['requested_at'])<=instant(doc['received_at'])<=instant(cutoff)
                    and instant(doc['first_available'])<=instant(doc['received_at'])):
                raise ValueError('IDENTITY_SOURCE_CLOCK_MISMATCH:'+name)
    if docs['membership'].get('membership_basis')!='AS_RECORDED':gaps.append('membership:NOT_AS_RECORDED')
    if docs['roster'].get('membership')!=sources['membership']:
        raise ValueError('SOURCE_CAPTURE_MEMBER_REVISION_MISMATCH')
    gbbq=docs['gbbq'].get('raw_binding')
    if not gbbq:gaps.append('gbbq:RAW_SOURCE_MISSING')
    else:exact(root,gbbq)
    roster=docs['roster']['rows']; native=docs['tdx']['rows']
    rmap={r['source_security_key']:r for r in roster}
    tmap={r['source_security_key']:r for r in native}
    if len(rmap)!=len(roster) or len(tmap)!=len(native):raise ValueError('DUPLICATE_IDENTITY_SOURCE_ROWS')
    active={key for key,row in rmap.items() if row.get('tradestatus')=='1'}
    reconciled=bool(rmap) and active==set(tmap)
    for key,row in rmap.items():
        if row.get('trade_date')!=target or row.get('tradestatus') not in ('0','1'):
            reconciled=False
        if row.get('tradestatus')=='1':
            bar=tmap.get(key)
            if not bar or bar.get('trade_date')!=target or any(row.get(f)!=bar.get(f) for f in ('open','high','low','close','volume')):
                reconciled=False
    if not reconciled:gaps.append('native:TDX_BAOSTOCK_DATE_OR_VALUE_OR_COVERAGE_MISMATCH')
    records=docs['identity_events'].get('records',[])
    temporal={}
    for row in records:
        key=row['source_security_key']
        if key in temporal:raise ValueError('AMBIGUOUS_DATED_IDENTITY_RECORD')
        temporal[key]=row
    if parent.get('evidence_class')=='SYNTHETIC_ISOLATED_TEST_ONLY':
        previous=set(parent.get('identity_codes',[]))
    else:
        life=json.loads(exact(root,parent['owners'][parent['accepted_trade_date']]['lifecycle']))
        prior_identity=json.loads(exact(root,life['identity']))
        previous={r['source_security_key'] for r in prior_identity['rows']}
    rows=[]
    for key in sorted(previous|set(rmap)|set(temporal)):
        fact=temporal.get(key,{})
        known=(bool(fact.get('security_id')) and bool(fact.get('list_date')) and
               fact.get('effective_from','9999')<=target and
               fact.get('event_basis') in ('OFFICIAL_DATED_IDENTITY','PRIOR_ACCEPTED_IDENTITY') and
               bool(fact.get('source_binding')))
        if known:
            original=json.loads(exact(root,fact['source_binding']))
            bound_fact={k:v for k,v in fact.items() if k!='source_binding'}
            if bound_fact not in original.get('records',[]):
                known=False;gaps.append(key+':IDENTITY_FACT_SOURCE_MISMATCH')
        removed=key in previous and key not in rmap
        delisted=known and bool(fact.get('delist_date')) and fact['delist_date']<=target
        change=fact.get('code_change') or {}
        alias_closed=(known and change.get('from')==key and bool(change.get('to')) and
            change.get('effective_date','9999')<=target and fact.get('event_basis')=='OFFICIAL_DATED_IDENTITY')
        if not known:gaps.append(key+':TEMPORAL_IDENTITY_UNKNOWN')
        if removed and not (delisted or alias_closed):gaps.append(key+':ABSENCE_NOT_DELISTING_EVIDENCE')
        if known and key in rmap and (fact['list_date']>target or delisted or alias_closed):
            gaps.append(key+':ROSTER_CONTRADICTS_DATED_LIFECYCLE')
        rows.append(dict(source_security_key=key,security_id=fact.get('security_id') if known else None,
            identity_status='CANDIDATE_KNOWN' if known else 'UNKNOWN',
            list_date=fact.get('list_date') if known else None,delist_date=fact.get('delist_date') if known else None,
            code_change=fact.get('code_change') if known else None,
            name=fact.get('name') if known else None,temporal_source=fact.get('source_binding') if known else None,
            provider_present=key in rmap,suspended=rmap.get(key,{}).get('tradestatus')=='0',
            removed_from_roster=removed,delisting_proven=delisted,code_boundary_proven=alias_closed,
            # A rename relationship must be an original temporal fact, never name inference.
            rename_status='SOURCE_FACT_CANDIDATE' if known and fact.get('code_change') else 'NOT_PROVEN'))
    document=dict(contract_id=CONTRACT,T0=target,revision=docs['roster']['revision'],
        parent_head=parent_head,sources=sources,member_revision=docs['membership']['revision'],rows=rows,
        observed_codes=sorted(rmap),previous_codes=sorted(previous),added_codes=sorted(set(rmap)-previous),
        removed_codes=sorted(previous-set(rmap)),provider_fact='NATIVE_PROVIDERS_RECONCILED' if reconciled else 'NATIVE_RECONCILIATION_FAILED',
        source_gaps=sorted(set(gaps)),status='SOURCE_GAPS' if gaps else 'IDENTITY_AUTHORITY_CANDIDATE_COMPLETE',
        first_available=(max(instant(d['first_available']) for d in docs.values()).isoformat()
            if all(d.get('first_available') for d in docs.values()) else None),
        frozen_at=now.isoformat(),evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY' if synthetic else 'OBSERVED_SOURCE_CANDIDATE',
        identity_authority_admitted=False,production_write_authorized=False,
        next_gate='AUTHENTICATED_INDEPENDENT_SOURCE_REVIEW_AND_ATOMIC_HEAD_CAS')
    path=(directory/digest([CONTRACT,parent_head,sources])/'candidate.json').as_posix()
    existing=Path(root)/path
    if existing.exists():
        previous_document=json.loads(existing.read_bytes())
        # Retry preserves the first immutable candidate freeze; a later call
        # cannot rewrite it or alter any source-derived fact.
        if ({k:v for k,v in previous_document.items() if k!='frozen_at'} !=
                {k:v for k,v in document.items() if k!='frozen_at'}):
            raise ValueError('IDENTITY_CANDIDATE_CHANGED_BYTE_OVERWRITE_FORBIDDEN')
        return ref(root,path)
    return publish(root,path,document)


def admission_candidate(root, *, candidate_binding, review_binding=None):
    """Ordinary caller documents cannot install dated identity into main DD."""
    candidate=json.loads(exact(root,candidate_binding))
    if candidate.get('contract_id')!=CONTRACT:raise ValueError('DATED_IDENTITY_CANDIDATE_REQUIRED')
    if review_binding:exact(root,review_binding)
    return dict(contract_id='DATED_IDENTITY_INDEPENDENT_ADMISSION_BOUNDARY_V1',
        candidate=candidate_binding,review=review_binding,status='NOT_ADMITTED',
        reason='TRUSTED_DATED_IDENTITY_REVIEW_SERVICE_NOT_DEPLOYED',
        review_status='UNTRUSTED_REVIEW_CANDIDATE',identity_authority_admitted=False,
        production_write_authorized=False,main_dd_scope_changed=False)

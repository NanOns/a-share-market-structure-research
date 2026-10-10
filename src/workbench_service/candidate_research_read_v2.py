"""Optional, head-bound candidate display. No formal fields or counts change."""
import json
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.r43_operational_publication import digest

CONTRACT='OPERATIONAL_CANDIDATE_DISPLAY_READ_V2'


def accepted_candidate_head(root, current, token, binding, day):
    """Resolve only a hash-linked predecessor of the authenticated active reader.

    An archive's existence is not acceptance. Its bytes must also be linked by
    the current accepted release, whose token and fixed pointer still agree.
    """
    pointer=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    if digest(current)!=token or not pointer.is_file() or json.loads(pointer.read_bytes())!=current:
        raise ValueError('OLD_TOKEN')
    cutoff=current.get('accepted_trade_date')
    if not cutoff or day>cutoff:raise ValueError('FUTURE_DATE')
    candidate=current;seen=set()
    for _ in range(4096):
        identity=digest(candidate)
        if identity in seen:raise ValueError('UNACCEPTED_HEAD')
        seen.add(identity)
        if identity==binding['sha256']:
            if json.loads(checked(root,binding).read_bytes())!=candidate:
                raise ValueError('MUTATED_ARCHIVE')
            if day not in candidate.get('published_sessions',candidate.get('dates',[])) or day not in candidate.get('owners',{}):
                raise ValueError('WRONG_SESSION')
            return candidate
        predecessor=candidate.get('predecessor')
        if not predecessor:break
        # CAS preserves each predecessor at this fixed content-addressed path.
        archive=root/'data/v4/predecessors'/(predecessor['sha256']+'.json')
        try:
            raw=checked(root,predecessor).read_bytes()
            archived=checked(root,dict(path=archive.relative_to(root).as_posix(),sha256=predecessor['sha256'])).read_bytes()
            if raw!=archived:raise ValueError('MUTATED_ARCHIVE')
            candidate=json.loads(archived)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            raise ValueError('MUTATED_ARCHIVE') from exc
    raise ValueError('UNACCEPTED_HEAD')


def read_candidates(root, *, head, token, day, sector_id=None):
    root=Path(root)
    result=dict(contract_id=CONTRACT,candidate_status='NOT_CAPTURED',production=False,
        formal_consumer_enabled=False,observed_count=None,matured_count=None,
        cohort_enrollment_enabled=False,trade_date=day)
    try:
        pointer=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
        if digest(head)!=token or not pointer.is_file() or json.loads(pointer.read_bytes())!=head:
            raise ValueError('OLD_TOKEN')
        if not head.get('accepted_trade_date') or day>head['accepted_trade_date']:
            raise ValueError('FUTURE_DATE')
        index_path=root/'data/v4/producer_candidate_index_v2.json'
        if not index_path.exists():return dict(result,reason='CANDIDATE_INDEX_NOT_CREATED')
        index=json.loads(index_path.read_bytes());entry=index.get('sessions',{}).get(day)
        if not entry:return dict(result,reason='HISTORICAL_CANDIDATE_SOURCE_NOT_CAPTURED')
        if index.get('contract_id')!='PRODUCER_CANDIDATE_INDEX_V2' or entry.get('production') is not False:
            raise ValueError('CANDIDATE_INDEX_SCOPE_REQUIRED')
        head=accepted_candidate_head(root,head,token,entry['head'],day)
        if sector_id is not None:
            binding=entry['sector'];document=json.loads(checked(root,binding).read_bytes())
            if document['T0']!=day or document['production'] is not False:raise ValueError('RESEARCH_SCOPE_REQUIRED')
            if set(document['sources'])!={'lifecycle','core','sector','prewatch'}:
                raise ValueError('COMPLETE_CANDIDATE_SOURCE_BINDINGS_REQUIRED')
            for name,source in document['sources'].items():
                if source!=head['owners'][day][name]:raise ValueError('CANDIDATE_OWNER_MISMATCH')
                checked(root,source)
            if document['membership']!=head['membership_snapshot']:raise ValueError('CANDIDATE_MEMBERSHIP_MISMATCH')
            checked(root,document['membership'])
            for dep in document['dependencies']+[document['model']]:checked(root,dep)
            rows=[r for r in document['rows'] if r['sector_id']==sector_id]
            if len(rows)>1:raise ValueError('DUPLICATE_SECTOR_CANDIDATE')
            for row in rows:
                if row['T0']!=day or row['production'] is not False or row['formal_consumer_enabled'] is not False:
                    raise ValueError('RESEARCH_ROW_SCOPE_REQUIRED')
                for cell in row['inputs'].values():
                    if cell.get('source'):
                        receipt=json.loads(checked(root,cell['source']).read_bytes())
                        if receipt['T0']!=day or receipt['sector_id']!=sector_id:raise ValueError('RANK_SOURCE_SCOPE_REQUIRED')
                        for source in receipt['sources']:checked(root,source)
            return dict(result,candidate_status='AVAILABLE' if rows else 'NOT_CAPTURED',item=rows[0] if rows else None,
                source=binding,evidence_class=document['evidence_class'],
                reason='VERSIONED_IDENTIFIER_CORRECTION_FOR_RESEARCH; A05_FORMAL_ADMISSION_PENDING')
        bindings={k:entry.get(k) for k in ('source_capture','full_state','strict_source')}
        docs={k:json.loads(checked(root,b).read_bytes()) for k,b in bindings.items() if b}
        state=docs.get('full_state',{});strict=docs.get('strict_source',{})
        if state and (state.get('T0')!=day or state.get('production') is not False or state.get('source')!=head['owners'][day]['prewatch']):
            raise ValueError('STATE_CANDIDATE_SCOPE_REQUIRED')
        if state:
            if state['membership']!=head['membership_snapshot']:raise ValueError('STATE_MEMBERSHIP_MISMATCH')
            for key in ('source','membership','model','config','implementation'):checked(root,state[key])
        if strict:
            if (strict['T0']!=day or strict['production'] is not False or strict['candidate_head']!=entry['head']
                    or strict['source_capture']!=bindings['source_capture']):raise ValueError('STRICT_CANDIDATE_SCOPE_REQUIRED')
            for key in ('frozen_scanner_inputs','calendar','model','config','implementation','state_implementation'):checked(root,strict[key])
            for name,source in strict['input_bindings'].items():
                if source!=head['owners'][day][name]:raise ValueError('STRICT_INPUT_BINDING_MISMATCH')
                checked(root,source)
        capture=docs.get('source_capture')
        if capture:
            if capture['T0']!=day or capture['production'] is not False:raise ValueError('CAPTURE_SCOPE_REQUIRED')
            for source in capture['sources']:checked(root,source['original_bytes'])
        next_session=entry.get('next_session')
        return dict(result,candidate_status='RESEARCH_CANDIDATE_FROZEN' if state else 'NOT_CAPTURED',
            universe_count=state.get('universe_count'),research_signal_count=state.get('signal_count'),
            research_eligible_count=state.get('research_eligible_count'),
            strict_source_status=strict.get('review_readiness','NOT_CAPTURED'),source_gaps=strict.get('source_gaps',[]),
            formal_admission='NOT_GRANTED',next_real_session=next_session,sources=bindings,
            evidence_class=state.get('evidence_class'),reason='Research candidate totals are not formal Cohort observations')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        # Optional capability failures stay local; existing product domains read.
        return dict(result,candidate_status='UNAVAILABLE',reason=str(exc))

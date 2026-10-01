"""Inventory every frozen notice name and capture-manifest reference, without raw edits."""
import copy,hashlib,json,re,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.official_event_semantics_v1 import parse_document_semantics,CONTRACT,EVENT_TYPES
P='reports/audits/A13_'
TASK='V4_A13_OFFICIAL_NOTICE_EVENT_SEMANTICS_RETROSPECTIVE_TASK_R1_20261001.md'
TERMS=re.compile(r'suspension|resumption|listing|issuance|delist|risk[_-]?warning|risk[_-]?transition|st[_-]removal|code[_-]?change|notice|停牌|复牌|上市|发行|退市|风险警示|代码变更',re.I)
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def write(p,v):atomic_json(ROOT/p,v)
def main():
    taskpath='docs/evidence/source_authority/'+TASK
    atomic_bytes(ROOT/taskpath,(Path('D:/Users/lps/Desktop/阶段任务')/TASK).read_bytes())
    sourcefiles=sorted(p for p in (ROOT/'data/v4/source_evidence').rglob('*') if p.is_file() and '/a13/' not in p.as_posix())
    protected=copy.deepcopy(read('reports/audits/A10_A12_R3_STAGE_ENTRY_R1.json')['protected_bindings'])
    existing={b['path'] for b in protected}
    for p in sourcefiles:
        path=p.relative_to(ROOT).as_posix()
        if path not in existing:protected.append(bind(path));existing.add(path)
    for path in ['data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R2.json','data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json','config/source_authority_governance_r3.json','reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R6.json']:
        protected.append(bind(path))
    write(P+'STAGE_ENTRY_R1.json',dict(contract_id='WP-A13-OFFICIAL-NOTICE-EVENT-SEMANTICS',
        task=bind(taskpath),document_baseline_commit='a43d663a0cc62d48f65a1160fae9c50874d86548',
        stage_contract='FULL_NOTICE_INVENTORY_DOCUMENT_SEMANTICS_AND_ADMISSION_COUNTERFACTUAL',
        protected_bindings=protected,phase0_status='FULL_PASS',
        phase0_evidence=bind('reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json'),
        next_stage='Independent A13 external reaudit; business accepted heads default KEEP'))
    capture_refs={};manifests=[];parse_errors=[];manifest_objects=0
    def walk(v,manifest):
        nonlocal manifest_objects
        if isinstance(v,dict):
            paths=[v.get(k) for k in ('path','source_capture_path','frozen_path','extracted_text_path') if isinstance(v.get(k),str)]
            for path in paths:
                if path.startswith('data/v4/source_evidence/') and (ROOT/path).is_file():
                    manifest_objects+=1
                    capture_refs.setdefault(path,[]).append(dict(manifest=manifest,
                        old_capture_id=v.get('id',v.get('capture_id',v.get('event_id'))),
                        security_key=v.get('key',v.get('source_security_key',v.get('security_key'))),
                        published_date=v.get('published_date',v.get('source_published_date')),
                        event_effective_date=v.get('phase_effective_from',v.get('effective_date')),
                        observed_at=v.get('observed_at'),url=v.get('url',v.get('source_ref')),
                        extracted_text_path=v.get('extracted_text_path'),
                        claimed_event_type=v.get('event_type'),claimed_status=v.get('status',v.get('quality'))))
            for key,x in v.items():
                if key not in ('rows','records','classifications','allowed_named_security_hits','file_classifications'):walk(x,manifest)
        elif isinstance(v,list):
            for x in v:walk(x,manifest)
    manifest_paths=list((ROOT/'reports').rglob('*.json'))+[p for p in sourcefiles if p.suffix=='.json']
    for p in sorted(manifest_paths):
        if not re.search(r'capture|manifest|source|lifecycle|semantics',p.name,re.I) or p.name.startswith('A13_') or 'NO_SYMBOL' in p.name:continue
        path=p.relative_to(ROOT).as_posix()
        try:value=read(path)
        except (ValueError,UnicodeError) as exc:parse_errors.append(dict(path=path,error=type(exc).__name__));continue
        manifests.append(bind(path));walk(value,path)
    phases={}
    for line in (ROOT/'data/v4/bootstrap/special_price_phase_events_r4.jsonl').read_text(encoding='utf8').splitlines():
        v=json.loads(line);phases.setdefault(v['source_capture_path'],[]).append(v)
    code_events={}
    for line in (ROOT/'data/v4/source_evidence/official_code_change_event_index/official_security_code_change_events_v1.jsonl').read_text(encoding='utf8').splitlines():
        v=json.loads(line);code_events.setdefault(v['source_capture_path'],[]).append(v)
    # Include named objects referenced by capture IDs even if their file name is neutral.
    relevant=[p for p in sourcefiles if TERMS.search(p.relative_to(ROOT).as_posix())
              or any(TERMS.search(str(r.get('old_capture_id',''))) for r in capture_refs.get(p.relative_to(ROOT).as_posix(),[]))]
    notice_manifest_paths={ref['manifest'] for p in relevant for ref in capture_refs.get(p.relative_to(ROOT).as_posix(),[])}
    manifest_archives={}
    for path in sorted(notice_manifest_paths):
        original=bind(path)
        archived='data/v4/source_evidence/a13/manifest_archives/'+original['sha256']+'.json'
        atomic_bytes(ROOT/archived,(ROOT/path).read_bytes())
        manifest_archives[path]=bind(archived)
    for refs in capture_refs.values():
        for ref in refs:
            if ref['manifest'] in manifest_archives:ref['manifest_artifact']=manifest_archives[ref['manifest']]
    entries=[]
    identity=read(read('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json')['identity_revision']['path'])
    lifecycle_paths={b['path'] for row in identity['dispositions'] for b in row.get('dated_lifecycle_evidence',[])}
    listing_paths={b['path'] for row in identity.get('new_lifecycle_events',[]) for b in row.get('source_evidence',[])}
    adjudications=read('data/v4/source_evidence/a13/REVIEWED_EVENT_DATE_ADJUDICATION_R1.json')['cases']
    for p in relevant:
        path=p.relative_to(ROOT).as_posix();refs=capture_refs.get(path,[])
        textpath=None;text='';extraction='NO_TEXT_AVAILABLE'
        if p.suffix.lower() in ('.txt','.md','.html','.json','.jsonl'):
            try:text=p.read_text(encoding='utf8');textpath=path;extraction='FROZEN_TEXT_OR_DOCUMENT'
            except UnicodeError:pass
        if p.suffix.lower()=='.html':
            sibling=p.with_suffix('.txt')
            if sibling.is_file():textpath=sibling.relative_to(ROOT).as_posix();text=sibling.read_text(encoding='utf8');extraction='FROZEN_CAPTURE_EXTRACTED_TEXT'
            else:text=re.sub('<[^>]+>',' ',text)
        if p.suffix.lower()=='.pdf':
            options=[ROOT/r['extracted_text_path'] for r in refs if r.get('extracted_text_path')]
            options += [p.with_suffix('.txt'),ROOT/'reports/audits/a12_r2/source_text'/p.with_suffix('.txt').name]
            selected=next((x for x in options if x.is_file()),None)
            if selected:textpath=selected.relative_to(ROOT).as_posix();text=selected.read_text(encoding='utf8');extraction='FROZEN_CAPTURE_OR_A12_PDF_TEXT'
        semantics=parse_document_semantics(text) if text.strip() else dict(actual_event_type='UNKNOWN_EVENT_SEMANTICS',semantic_evidence=None)
        event=semantics['actual_event_type'];phase=phases.get(path,[])
        # Structured accepted phase evidence is separately bound and corroborated by document text.
        key=next((r['security_key'] for r in refs if r.get('security_key')),None)
        effective=next((r['event_effective_date'] for r in refs if r.get('event_effective_date')),None)
        if phase:
            key=phase[0]['source_security_key'];effective=phase[0]['phase_effective_from']
        published=next((r['published_date'] for r in refs if r.get('published_date')),None)
        code_event=code_events.get(path,[])
        if code_event:
            key=code_event[0]['new_source_security_key'];effective=code_event[0]['effective_date'];published=code_event[0]['published_at']
        if key is None:
            match=re.search(r'(SH|SZ|BJ)[_.](\d{6})',p.name,re.I)
            key=(match.group(1).upper()+'.'+match.group(2)) if match else None
        if key is None:
            match=re.search(r'证券代码[:：]?(\d{6})',re.sub(r'\s+','',text)[:800])
            if match:
                anchors={r['source_security_key'] for r in identity['records'] if r['source_security_key'].endswith('.'+match.group(1))}
                if len(anchors)==1:key=next(iter(anchors))
        date_adjudication=next((c for c in adjudications if c['security_key']==key and c['actual_event_type']==event),None)
        if date_adjudication:
            assert date_adjudication['semantic_phrase'] in re.sub(r'\s+','',text)
            effective=date_adjudication['event_effective_date']
        capture_ids=sorted({r['old_capture_id'] for r in refs if isinstance(r.get('old_capture_id'),str)})
        original_text_path=textpath
        original_text_sha=bind(textpath)['sha256'] if textpath else None
        if textpath and textpath.startswith('reports/'):
            archived='data/v4/source_evidence/a13/text_archives/'+original_text_sha+'.txt'
            atomic_bytes(ROOT/archived,(ROOT/textpath).read_bytes())
            textpath=archived
        usages={stage:'NOT_CONSUMED' for stage in ['V4_01_IDENTITY_LIFECYCLE','V4_02_TRADING_STATUS','V4_02_ST','V4_02_SPECIAL_PHASE','V4_08_IDENTITY_ADMISSION','V4_08_PIT_MEMBERSHIP','A12_SAMPLE_MATRIX','DM01']}
        if path in lifecycle_paths:
            usages.update(V4_01_IDENTITY_LIFECYCLE='SUPPORTING_EVIDENCE',V4_08_IDENTITY_ADMISSION='SUPPORTING_EVIDENCE',V4_08_PIT_MEMBERSHIP='SUPPORTING_EVIDENCE')
        elif path in listing_paths:
            usages.update(V4_01_IDENTITY_LIFECYCLE='BUSINESS_DECISION',V4_08_IDENTITY_ADMISSION='BUSINESS_DECISION',V4_08_PIT_MEMBERSHIP='BUSINESS_DECISION')
        if phase:usages['V4_02_SPECIAL_PHASE']='BUSINESS_DECISION'
        if code_event:usages.update(V4_01_IDENTITY_LIFECYCLE='BUSINESS_DECISION',V4_02_TRADING_STATUS='BUSINESS_DECISION',V4_02_ST='BUSINESS_DECISION')
        if '/a12_r2/' in path or phase or 'code_change' in path or 'suspension' in path:usages['A12_SAMPLE_MATRIX']='DIAGNOSTIC_ONLY'
        if '/v4_08_r3/' in path and path not in lifecycle_paths | listing_paths:
            usages['V4_08_IDENTITY_ADMISSION']='DIAGNOSTIC_ONLY'
        if '/official_code_change_event_index/' in path:
            usages['V4_01_IDENTITY_LIFECYCLE']='SUPPORTING_EVIDENCE';usages['A12_SAMPLE_MATRIX']='DIAGNOSTIC_ONLY'
        entries.append(dict(old_capture_id=capture_ids or [p.stem],raw_artifact=bind(path),
            filename_semantic=TERMS.findall(p.name),capture_id_semantic={x:TERMS.findall(x) for x in capture_ids},
            actual_event_type=event,security_key=key,event_effective_date=effective,source_published_date=published,
            temporal_limit='NULL_DATE_IS_UNPROVEN_NEVER_INFER_FROM_FILE_NAME',semantic_evidence=semantics['semantic_evidence'],
            semantic_text_binding=bind(textpath) if textpath else None,extraction=extraction,
            original_semantic_text_path=original_text_path,original_semantic_text_observed_sha256=original_text_sha,
            dated_trading_statements=semantics.get('dated_trading_statements',[]),
            event_date_adjudication=date_adjudication,
            identity_evidence=bind('data/v4/bootstrap/special_price_phase_events_r4.jsonl') if phase else None,
            existing_dated_phase_events=phase,consumer_semantics=usages,capture_manifest_refs=refs,
            existing_dated_code_change_events=code_event,
            consumer_permissions=dict(TRADING_STATUS_TRUTH=False,ST_TRUTH=False,LIFECYCLE_TRUTH=False,
                SUPPORTING_EVIDENCE=event!='UNKNOWN_EVENT_SEMANTICS',DIAGNOSTIC_ONLY=True),
            semantic_authority_status='CANDIDATE_PENDING_EXTERNAL_ACCEPTANCE',
            source_primary_status='DOCUMENT_BODY_NOT_ISSUER_OR_EXCHANGE_AUTHORITY_BY_HOST_OR_FILENAME_ALONE',
            semantic_mismatch=bool('suspension' in p.name.lower() and event not in ('LISTED_STOCK_TRADING_SUSPENSION','UNKNOWN_EVENT_SEMANTICS'))))
    sidecar='data/v4/source_evidence/a13/OFFICIAL_NOTICE_EVENT_SEMANTICS_AMENDMENT_R1.json'
    write(sidecar,dict(contract_id=CONTRACT,external_acceptance=None,formal_consumer_authorization=False,
        status='CANDIDATE_PENDING_EXTERNAL_REAUDIT',raw_bytes_renamed_or_overwritten=False,entries=entries))
    write('config/official_event_semantics_v1.json',dict(contract_id=CONTRACT,version='1.0.0',
        event_types=sorted(EVENT_TYPES),runtime=bind('src/workbench_analysis/official_event_semantics_v1.py'),
        candidate_sidecar=bind(sidecar),filename_or_capture_id_grants_trading_authority=False,
        unknown_event_may_enter_trading_status=False,formal_event_truth_requires='EXACT_ACCEPTED_SIDECAR_RAW_TEXT_IDENTITY_AND_EFFECTIVE_DATE',
        existing_business_inputs_preserved=True))
    write(P+'FULL_NOTICE_AND_CAPTURE_MANIFEST_INVENTORY_R1.json',dict(status='PASS_FULL_INVENTORY',
        source_root_file_count=len(sourcefiles),named_or_capture_id_object_count=len(entries),
        examined_manifest_candidate_file_count=len(manifests),capture_manifest_count=len(manifest_archives),capture_reference_object_count=manifest_objects,parse_errors=parse_errors,
        scanned_capture_manifests=[dict(original_path=p,artifact=b) for p,b in manifest_archives.items()],
        examined_manifest_census=[dict(source_path=b['path'],source_sha256=b['sha256'],scope='NOTICE_REFERENCES_ARCHIVED' if b['path'] in notice_manifest_paths else 'NON_NOTICE_MANIFEST_NAME_CENSUS_ONLY') for b in manifests],
        source_inventory=[bind(p.relative_to(ROOT).as_posix()) for p in sourcefiles],
        sidecar=bind(sidecar),event_counts=dict(Counter(e['actual_event_type'] for e in entries)),
        mismatches=[e['raw_artifact'] for e in entries if e['semantic_mismatch']],network_calls=0,
        unknown_objects_fail_closed=True))
    spec=read('data/v4/source_evidence/a12_r2/REAL_VALIDATION_CASE_SPEC_R1.json')
    write('data/v4/source_evidence/a13/COUNTERFACTUAL_CASE_SPEC_R1.json',dict(contract_id='A13_COUNTERFACTUAL_CASE_SPEC_V1',
        known_case_keys=sorted(spec['ipo_misbinding_examples']),case_spec_parent=bind('data/v4/source_evidence/a12_r2/REAL_VALIDATION_CASE_SPEC_R1.json'),
        authority='AUDIT_INPUT_ONLY_NOT_RUNTIME_SPECIAL_CASE'))
    write(P+'CONSUMER_INVENTORY_R1.json',dict(status='PASS',entries=[dict(raw_artifact=e['raw_artifact'],actual_event_type=e['actual_event_type'],consumers=e['consumer_semantics']) for e in entries],
        policy=bind('config/official_event_semantics_v1.json'),trading_notice_consumer='require_trading_event',
        existing_status_authority='Dated structured facts and local TDX precedence; no suspension filename inference',
        dm01_authority='Dated provider field instances; notices not consumed',
        v4_08_decision='Active catalogue/exchange query and dated accepted identity; lifecycle attachments do not infer termination',
        accepted_identity_source=bind(read('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json')['identity_revision']['path']),
        consumed_lifecycle_attachment_paths=sorted(lifecycle_paths),consumed_listing_paths=sorted(listing_paths)))
    print(json.dumps(dict(objects=len(entries),manifests=len(manifests),events=dict(Counter(e['actual_event_type'] for e in entries)))))
if __name__=='__main__':main()

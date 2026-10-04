"""Versioned runtime envelope around unchanged R3_3 business function code.

The nine function bodies are reused with a private globals dictionary containing
only replacement admission and publication hooks. The historical module is never
patched. Independent numerical postchecks remain the accepted R3_3 oracle.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, time, date, timedelta
from pathlib import Path
from types import FunctionType
from zoneinfo import ZoneInfo
import hashlib
import json
import os

from . import dm01_incremental_component_builders_r3_3 as kernels
from .dm01_independent_postcheck_r3_3 import check_component, check_cross_components
from .daily_data_head import CAPABILITIES
from .daily_source_freeze import ensure_outside_tdx, source_freeze_complete_v2

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = 'config/dm01_go_forward_runtime_contract_r4r1.json'
POLICY = 'config/dm01_v2_promotion_policy_r4r1.json'
CALENDAR = 'data/v4/DM01_R4_CALENDAR_HEAD_V1.json'
HEAD = 'data/v4/V4_DATA_ACCEPTED_HEAD.json'
ACCEPTANCE = 'data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json'
PERMISSIONS = dict(production=False, shadow=False, focus=False)
digest = kernels.digest
sha = kernels.sha

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def path(root, binding):
    root = Path(root).resolve()
    p = Path(binding['path'])
    p = p.resolve() if p.is_absolute() else (root / p).resolve()
    require(p.is_relative_to(root), 'INPUT_OUTSIDE_PROJECT')
    require(p.is_file() and sha(p) == binding['sha256'], 'INPUT_DIGEST_MISMATCH')
    if 'bytes' in binding:
        require(p.stat().st_size == binding['bytes'], 'INPUT_SIZE_MISMATCH')
    return p

def read(root, binding):
    return json.loads(path(root, binding).read_bytes())

def ref(root, p):
    p = Path(p).resolve()
    return dict(path=p.relative_to(Path(root).resolve()).as_posix(), sha256=sha(p), bytes=p.stat().st_size)

def atomic(root, p, value, *, immutable=False):
    root = Path(root).resolve(); p = Path(p).resolve()
    require(p.is_relative_to(root), 'OUTPUT_OUTSIDE_PROJECT')
    contract = json.loads((ROOT / CONTRACT).read_bytes())
    for tdx in contract['read_only_tdx_roots']:
        ensure_outside_tdx(p, Path(tdx))
    raw = value if isinstance(value, bytes) else kernels.canonical(value) + b'\n'
    if immutable and p.exists():
        require(p.read_bytes() == raw, 'IMMUTABLE_CANDIDATE_COLLISION')
        return ref(root, p)
    p.parent.mkdir(parents=True, exist_ok=True)
    staging = p.with_name(p.name + '.r4-staging')
    with staging.open('wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(staging, p)
    return ref(root, p)

def accepted_envelope(root):
    """One externally accepted envelope; no caller-supplied acceptance booleans."""
    p = Path(root) / ACCEPTANCE
    require(p.is_file(), 'BLOCKED_PENDING_DM01_R4_EXTERNAL_ACCEPTANCE')
    a = json.loads(p.read_bytes())
    require(a.get('status') == 'EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME', 'R4_ENVELOPE_NOT_ACCEPTED')
    for name, key in ((CONTRACT, 'runtime_contract'), (POLICY, 'promotion_policy'), (CALENDAR, 'calendar_head')):
        require(a[key] == ref(root, Path(root) / name), 'R4_ACCEPTED_ENVELOPE_DIGEST_MISMATCH')
    document = path(root, a['independent_external_authority']).read_text(encoding='utf8')
    require(a.get('external_verdict') == 'PASS_DM01_R4R1_GO_FORWARD_RUNTIME' and
            'PASS_DM01_R4R1_GO_FORWARD_RUNTIME' in document and
            a['runtime_contract']['sha256'] in document and
            a['promotion_policy']['sha256'] in document and
            a['calendar_head']['sha256'] in document, 'R4_EXTERNAL_DISPOSITION_MISSING')
    require(a.get('permissions') == PERMISSIONS, 'R4_ENVELOPE_PERMISSION_ESCALATION')
    return a

def calendar(root=ROOT):
    head = json.loads((Path(root) / CALENDAR).read_bytes())
    require(head.get('contract_id') == 'DM01_R4_CALENDAR_HEAD_V1' and head.get('status') in ('ACCEPTED', 'LOCAL_READY_FOR_EXTERNAL_AUDIT'), 'CALENDAR_HEAD_NOT_ACCEPTED_OR_AUDIT_CANDIDATE')
    cal = read(root, head['calendar'])
    require(cal['agreement'] is True and cal['exchanges'] == ['SSE', 'SZSE'], 'CALENDAR_EXCHANGE_DISAGREEMENT')
    require(cal['session_dates'] == sorted(set(cal['session_dates'])), 'CALENDAR_SESSION_ORDER')
    require({s['exchange'] for s in cal['sources']} == {'SSE','SZSE'} and len(cal['sources'])==2, 'CALENDAR_OFFICIAL_SOURCE_MISSING')
    days=[]; day=date.fromisoformat(cal['coverage_start']); end=date.fromisoformat(cal['coverage_end'])
    while day<=end:
        days.append(day.isoformat()); day+=timedelta(days=1)
    closures={c['trade_date'] for c in cal['closures']}
    require(set(days)==set(cal['session_dates'])|closures and not set(cal['session_dates'])&closures,
            'CALENDAR_COVERAGE_PARTITION_INCOMPLETE')
    require(all(date.fromisoformat(d).weekday()<5 for d in cal['session_dates']), 'CALENDAR_WEEKEND_SESSION')
    for source in cal['sources']:
        path(root, source['source'])
    return dict(cal, head_binding=ref(root, Path(root) / CALENDAR), binding=head['calendar'], publication_id=head['calendar']['sha256'], payload_digest=digest(cal), status='ACCEPTED_CALENDAR_BYTES_LOCAL_AUDIT_CANDIDATE')

def current_parent(root=ROOT):
    root = Path(root); binding = ref(root, root / HEAD); head = read(root, binding)
    schema = json.loads((ROOT / 'config/v4_data_accepted_head_v2.json').read_bytes())
    require(head.get('contract_id') == 'V4_DATA_ACCEPTED_HEAD_V2', 'V1_PARENT_HISTORY_ONLY')
    require(set(schema['required_fields']) <= set(head), 'V2_PARENT_SCHEMA_INCOMPLETE')
    require(head['external_acceptance'] in ('EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN', 'ACCEPTED_UNDER_DM01_R4_MACHINE_POLICY'), 'V2_PARENT_NOT_ACCEPTED')
    require(head['permissions'] == PERMISSIONS, 'PARENT_PERMISSION_ESCALATION')
    for key in ('accepted_chain', 'external_acceptance_record', 'final_candidate', 'source_authority_governance', 'source_authority_registry'):
        read(root, head[key])
    if head['external_acceptance'] == 'EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN':
        from .dm01_accepted_chain_v1 import validate_head_v2
        validate_head_v2(root, head)
    else:
        accepted_envelope(root)
        record = read(root, head['external_acceptance_record'])
        chain = read(root, head['accepted_chain']); candidate = read(root, head['final_candidate'])
        require(record.get('status') == 'ACCEPTED_UNDER_DM01_R4_MACHINE_POLICY' and
                record['candidate'] == head['final_candidate'] == chain['candidate'] and
                chain['acceptance'] == head['external_acceptance_record'] and
                record['permissions'] == candidate['permissions'] == PERMISSIONS and
                record['policy'] == ref(root, root/POLICY) and record['envelope'] == ref(root, root/ACCEPTANCE) and
                candidate['target_trade_date'] == head['accepted_trade_date'] and
                candidate.get('real_forward_evidence') is True and head['AS_RECORDED'] is False,
                'V2_PARENT_ACCEPTANCE_RECORD_MISMATCH')
        archive = read(root, chain['parent_head'])
        require(chain['parent'] == archive['accepted_chain'] and
                record['parent'] == chain['parent_head'] == head['parent_archive'] and
                chain['parent_head']['sha256'] == head['parent_head_sha256'] == candidate['parent_data_head_digest'],
                'V2_PARENT_CHAIN_LINKAGE_MISMATCH')
        from .dm01_lineage_r4r1 import validate_head_lineage
        validate_head_lineage(head,archive)
    require(set(head['component_artifacts']) == set(head['component_permissions']) == set(CAPABILITIES), 'V2_PARENT_NINE_COMPONENTS_REQUIRED')
    components = head['component_artifacts']
    for cap in CAPABILITIES:
        permission = head['component_permissions'][cap]; artifact = read(root, components[cap]); receipt = read(root, permission['receipt'])
        require(permission['status'] in ('FULL_PASS', 'DEGRADED_PASS') and permission['cutoff'] == head['accepted_trade_date'], 'PARENT_COMPONENT_NOT_ACCEPTED')
        require(permission['artifact'] == components[cap] and receipt['artifact_sha256'] == components[cap]['sha256'] and receipt['logical_digest'] == digest(artifact['rows']), 'PARENT_COMPONENT_DIGEST_MISMATCH')
    return dict(kind='CURRENT_ACCEPTED_V2', binding=binding, head=head, components=components)

def session_gate(target, observed_at, root=ROOT):
    cal = calendar(root); parent = current_parent(root)
    require(target <= cal['coverage_end'], 'BLOCKED_CALENDAR_COVERAGE')
    require(parent['head']['accepted_trade_date'] in cal['session_dates'], 'PARENT_CALENDAR_SESSION_MISSING')
    try:
        next_session = kernels.resolve_target_session(parent['head']['accepted_trade_date'], cal, observed_at, target)
    except ValueError as error:
        if str(error) == 'WAIT_MARKET_CLOSE':
            return dict(status='WAIT_MARKET_CLOSE', target_trade_date=target, parent=parent['binding'], calendar=cal['binding'], source_requests=0, candidate_created=False, data_head_moved=False)
        raise
    accepted_envelope(root)
    return dict(status='SOURCE_CAPTURE_ALLOWED', target_trade_date=next_session, parent=parent, calendar=cal)

def validate_registry(builders, root=ROOT):
    c = json.loads((ROOT / CONTRACT).read_bytes())
    require(set(builders) == set(CAPABILITIES), 'ONE_OR_MORE_BUILDERS_MISSING')
    for cap in CAPABILITIES:
        require(builders[cap] is BUILDERS[cap], 'BUILDER_CALLABLE_MISMATCH:' + cap)
        require(builders[cap].__name__ == kernels.BUILDERS[cap].__name__ and builders[cap].__module__ == __name__, 'BUILDER_EXPORT_MISMATCH:' + cap)
    for binding in c['runtime_bindings']:
        path(ROOT, binding)
    return c

def validate_lineage(freeze, root, *, simulation=False):
    require(freeze['manifest_sha256'] == digest({k:v for k,v in freeze.items() if k != 'manifest_sha256'}), 'SOURCE_MANIFEST_DIGEST_MISMATCH')
    require(source_freeze_complete_v2(freeze), 'SOURCE_FREEZE_INCOMPLETE')
    target = freeze['trade_date']; now = datetime.fromisoformat(freeze['observed_at'].replace('Z', '+00:00'))
    require(now.tzinfo is not None, 'OBSERVATION_TIMEZONE_REQUIRED')
    require(now.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat() == target, 'RECONSTRUCTED_SOURCE_CANNOT_MINT_PIT')
    require(freeze.get('knowledge_lineage') == 'PIT_OBSERVED' and freeze.get('AS_RECORDED') is True, 'RECONSTRUCTED_SOURCE_CANNOT_MINT_PIT')
    require(not simulation or Path(root).resolve() != ROOT.resolve(), 'REAL_ROOT_SIMULATION_FORBIDDEN')
    require(bool(freeze.get('availability_evidence')), 'PIT_AVAILABILITY_EVIDENCE_MISSING')
    for family, evidence in freeze['availability_evidence'].items():
        native = read(root, evidence['binding'])
        require(evidence['target_trade_date'] == evidence['provider_date'] == target, 'TARGET_SOURCE_DATE_MISMATCH:' + family)
        for key in ('system_available_at', 'captured_at', 'received_at'):
            stamp = datetime.fromisoformat(evidence[key].replace('Z', '+00:00'))
            require(stamp.tzinfo is not None and stamp <= now and stamp.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat() == target, 'SOURCE_FUTURE_OR_RECONSTRUCTED_TIMESTAMP:' + family)
        stamps={k:datetime.fromisoformat(evidence[k].replace('Z','+00:00')) for k in ('system_available_at','received_at','captured_at')}
        require(stamps['system_available_at'] <= stamps['received_at'] and stamps['captured_at'] <= stamps['received_at'], 'SOURCE_TIMESTAMP_ORDER')
        if evidence.get('source_provider_available_at'):
            require(datetime.fromisoformat(evidence['source_provider_available_at'].replace('Z','+00:00')) <= now, 'FUTURE_PROVIDER_TIMESTAMP')
        require(native.get('target_date', native.get('trade_date')) == target and native.get('provider_date', native.get('update_date', target)) == target, 'NATIVE_SOURCE_TARGET_MISMATCH')
        require(native.get('fixture_scope') is None or simulation, 'REAL_SOURCE_FIXTURE_FORBIDDEN')
        if not simulation:
            captured = native.get('captured_at') or native.get('observed_at')
            received = native.get('received_at') or native.get('downloaded_at') or native.get('system_available_at')
            require(received is not None, 'NATIVE_RECEIPT_COMPLETION_TIME_MISSING')
            require(evidence['captured_at'] == captured and evidence['received_at'] == received and evidence['system_available_at'] == (native.get('system_available_at') or received), 'AVAILABILITY_NOT_EXACT_NATIVE_READBACK')
            require(evidence.get('source_provider_available_at') == native.get('source_provider_available_at'), 'PROVIDER_AVAILABILITY_NOT_EXACT_NATIVE_READBACK')
    require({'TDX_FULL_PACKAGE','BAOSTOCK_DAILY_UPDATE'} <= set(freeze['availability_evidence']), 'REQUIRED_SOURCE_AVAILABILITY_MISSING')
    for value in freeze['source_families'].values(): path(root, value)
    for value in freeze['inputs'].values(): path(root, value)
    if not simulation:
        accepted_envelope(root)
        for value in freeze['source_authority_bindings']: read(root, value)
        require(len(freeze['source_authority_bindings']) >= 2, 'SOURCE_ACCEPTED_AUTHORITY_MISSING')
        from .source_authority_producers_r4 import require_accepted_producer
        c = json.loads((ROOT/CONTRACT).read_bytes())
        rules = read(root,c['producer_governance'])['field_rules']
        for field in ('TRADING_STATUS','ISST'):
            proof = require_accepted_producer(root,next(r for r in rules if r['field_id']==field),consumer_contract_id='DM01_FINAL_ALL_NINE')
            require(proof['entry']['producer_contract'] in freeze['source_authority_bindings'], 'EXACT_ACCEPTED_PRODUCER_MISSING')
    return True

def _context(root, cap, target, parent, freeze, cal, identity, staging):
    c = validate_registry(BUILDERS, root)
    require(parent['binding']['sha256'] == freeze['parent_data_head_digest'], 'V2_PARENT_DIGEST_MISMATCH')
    require(read(root, parent['binding']) == parent['head'], 'V2_PARENT_RAW_READBACK_MISMATCH')
    validate_lineage(freeze, root, simulation=bool(freeze.get('engineering_simulation')))
    require(target == kernels.resolve_target_session(parent['head']['accepted_trade_date'], cal, freeze['observed_at'], target), 'INTERMEDIATE_SESSION_REQUIRED')
    require(read(root, identity['binding'])['records'] == identity['records'], 'IDENTITY_PUBLICATION_MISMATCH')
    if not freeze.get('engineering_simulation'):
        require(parent['binding'] == current_parent(root)['binding'], 'BLOCKED_DATA_HEAD_PARENT_MOVED')
        require(cal['binding'] == calendar(root)['binding'] and read(root,cal['binding'])['session_dates']==cal['session_dates'], 'CALENDAR_PUBLICATION_MISMATCH')
        idpayload=read(root,identity['binding'])
        require(idpayload['accepted_head']==c['accepted_identity_head'], 'IDENTITY_ACCEPTED_HEAD_MISMATCH')
    require(identity['publication_id'] == freeze['identity_publication_id'] and cal['publication_id'] == freeze['calendar_publication_id'], 'SOURCE_PUBLICATION_MISMATCH')
    for binding in parent['components'].values(): path(root, binding)
    return dict(root=Path(root), cap=cap, target=target, parent=parent, freeze=freeze, calendar=cal, identity=identity, staging=Path(staging), contract=c)

def _finish(c, rows, extra=None):
    from .dm01_lineage_r4r1 import observation, annotate_rows, first_availability
    kernels._unique(rows, c['cap'].startswith('PERIOD_'))
    rows = sorted(rows, key=lambda r:(kernels._key(r), r.get('period_type',''), r.get('period_key','')))
    simulated = bool(c['freeze'].get('engineering_simulation'))
    observed=observation(c['freeze'],c['root']);comp=annotate_rows(c,rows,observed)
    payload = dict(contract_id='DM01_'+c['cap']+'_ARTIFACT_R4R1', trade_date=c['target'], rows=rows, lineage_composition=comp, **(extra or {}))
    artifact = atomic(c['root'], c['staging']/c['cap']/'artifact.json', payload, immutable=True)
    unknown = Counter(str(r['unknown_reason']) for r in rows if r.get('unknown_reason'))
    receipt = dict(component_id=c['cap'], contract_id='DM01_'+c['cap']+'_INCREMENT_R4', version='4.0.0', status='DEGRADED_PASS' if unknown else 'FULL_PASS', target_trade_date=c['target'], trade_date=c['target'], parent_data_head_digest=c['parent']['binding']['sha256'], source_revision=c['freeze']['manifest_sha256'], calendar_publication_id=c['calendar']['publication_id'], identity_publication_id=c['identity']['publication_id'], runtime_bindings=c['contract']['capabilities'][c['cap']]['runtime_bindings'], accepted_owner_stage=c['contract']['capabilities'][c['cap']]['owner_stage'], accepted_algorithm_contract=c['contract']['capabilities'][c['cap']]['accepted_algorithm_contract'], artifact_path=str((c['root']/artifact['path']).resolve()), artifact_sha256=artifact['sha256'], artifact_bytes=artifact['bytes'], logical_digest=digest(rows), row_count=len(rows), quality_counts=dict(Counter(str(r.get('quality') or r.get('status') or 'READY') for r in rows)), unknown_reason_counts=dict(unknown), candidate_only=True, knowledge_lineage='CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION' if simulated else 'MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT', AS_RECORDED=False, first_available_at_target_proven=False)
    receipt.update(contract_id='DM01_'+c['cap']+'_INCREMENT_R4R1',version='4.1.0',lineage_composition=comp,
        target_identity_unknown_count=sum(r.get('security_id') is None for r in rows),
        knowledge_lineage='CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION' if simulated else
            ('MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT' if comp['contains_inherited_parent_state'] else 'PIT_OBSERVED'),
        AS_RECORDED=bool(not simulated and not comp['contains_inherited_parent_state']),first_available_at_target_proven=False,
        target_session_observation_proven=observed['target_session_observation_proven'],
        target_session_observed_at=observed['target_session_observed_at'],target_session_received_at=observed['target_session_received_at'],
        first_availability_by_source=first_availability(c['freeze'],c['root']))
    post = check_component(receipt,payload,c['freeze'],c['parent'],c['calendar'],c['identity'])
    require(post['status']=='PASS', 'COMPONENT_POSTCHECK_FAIL:'+c['cap'])
    receipt['postcheck_digest']=digest(post)
    receipt.update(input_publication_ids=sorted({c['parent']['binding']['sha256'],c['freeze']['manifest_sha256'],
        c['calendar']['publication_id'],c['identity']['publication_id'],*[b['sha256'] for b in c['freeze']['inputs'].values()]}),
        parent_component_bindings=c['parent']['components'],temporal_scope='TARGET_SESSION_NEW_ROWS_ONLY',
        market_acceptance_claim=False)
    atomic(c['root'],c['staging']/c['cap']/'postcheck.json',post,immutable=True)
    atomic(c['root'],c['staging']/c['cap']/'receipt.json',receipt,immutable=True)
    return receipt

def run_kernel(cap, *args, project_root=ROOT):
    scope = dict(vars(kernels))
    # Helpers such as _build_period must share the private hooks as well.
    for name, original in vars(kernels).items():
        if isinstance(original, FunctionType) and original.__module__ == kernels.__name__:
            scope[name] = FunctionType(original.__code__, scope, original.__name__, original.__defaults__, original.__closure__)
            scope[name].__kwdefaults__ = original.__kwdefaults__
    scope.update(_context=lambda *a:_context(project_root,*a), _finish=_finish)
    original = kernels.BUILDERS[cap]
    function = scope[original.__name__]
    return function(*args)

def build_identity_universe(*a, **kw): return run_kernel('IDENTITY_UNIVERSE',*a,**kw)
def build_raw_daily(*a, **kw): return run_kernel('RAW_DAILY',*a,**kw)
def build_trading_status(*a, **kw): return run_kernel('TRADING_STATUS',*a,**kw)
def build_isst(*a, **kw): return run_kernel('ISST',*a,**kw)
def build_adjusted_daily(*a, **kw): return run_kernel('ADJUSTED_DAILY',*a,**kw)
def build_period_raw(*a, **kw): return run_kernel('PERIOD_RAW',*a,**kw)
def build_period_adjusted(*a, **kw): return run_kernel('PERIOD_ADJUSTED',*a,**kw)
def build_price_limit(*a, **kw): return run_kernel('PRICE_LIMIT',*a,**kw)
def build_special_phase(*a, **kw): return run_kernel('SPECIAL_PHASE',*a,**kw)
BUILDERS = {cap:globals()[kernels.BUILDERS[cap].__name__] for cap in CAPABILITIES}

def build_candidate(*, parent, freeze, cal, identity, root=ROOT, builders=None):
    root=Path(root); builders=BUILDERS if builders is None else builders
    require(parent['head'].get('contract_id')=='V4_DATA_ACCEPTED_HEAD_V2', 'V1_PARENT_HISTORY_ONLY')
    validate_registry(builders,root); validate_lineage(freeze,root,simulation=bool(freeze.get('engineering_simulation')))
    require(freeze['parent_data_head_digest']==parent['binding']['sha256'], 'V2_PARENT_DIGEST_MISMATCH')
    protected={p:sha(root/p) for p in json.loads((ROOT/CONTRACT).read_bytes())['protected_runtime_paths']}
    target=kernels.resolve_target_session(parent['head']['accepted_trade_date'],cal,freeze['observed_at'],freeze['trade_date'])
    run_id=digest(dict(target=target,parent=parent['binding']['sha256'],source=freeze['manifest_sha256'],contract=sha(ROOT/CONTRACT)))
    staging=root/'data/v4/dm01_r4/candidates'/run_id; marker=staging/'PROMOTION_CANDIDATE.json'
    if marker.exists():
        old=json.loads(marker.read_bytes()); post=check_cross_components(old['components'],freeze,parent,cal,identity)
        require(post['status']=='PASS' and digest(post)==old['postcheck_digest'], 'CANDIDATE_RECHECK_FAILED')
        require(all(sha(root/p)==d for p,d in old['protected_heads'].items()), 'PROTECTED_STATE_MOVED')
        return dict(status='NOOP_IDENTICAL_CANDIDATE',candidate=ref(root,marker),candidate_id=run_id)
    manifest=atomic(root,staging/'parent_components.json',dict(parent_data_head_digest=parent['binding']['sha256'],components=parent['components']),immutable=True)
    parent=dict(parent,component_manifest_binding=dict(manifest,path=str(root/manifest['path'])))
    receipts={}
    for cap in kernels.BUILD_ORDER:
        receipts[cap]=builders[cap](target,parent,freeze,cal,identity,staging,project_root=root)
    post=check_cross_components(receipts,freeze,parent,cal,identity)
    require(set(receipts)==set(CAPABILITIES) and post['status']=='PASS', 'CROSS_COMPONENT_POSTCHECK_FAILED')
    require(all(sha(root/p)==d for p,d in protected.items()), 'PROTECTED_STATE_MOVED')
    postref=atomic(root,staging/'cross_postcheck.json',post,immutable=True)
    freeze_ref=atomic(root,staging/'source_manifest.json',freeze,immutable=True)
    parent_ref=atomic(root,staging/'parent_context.json',parent,immutable=True)
    from .dm01_lineage_r4r1 import forward_admission, composition
    observed=forward_admission(parent,freeze,cal,receipts,post,root)
    observation_ref=atomic(root,staging/'target_session_observation.json',observed,immutable=True)
    marker_value=dict(contract_id='DM01_ATOMIC_GO_FORWARD_CANDIDATE_R4',candidate_id=run_id,target_trade_date=target,parent_data_head_digest=parent['binding']['sha256'],parent_context=parent_ref,components=receipts,source_manifest=freeze_ref,source_manifest_digest=freeze['manifest_sha256'],calendar=cal['binding'],identity=identity['binding'],cross_postcheck=postref,postcheck_digest=digest(post),protected_heads=protected,permissions=PERMISSIONS,knowledge_lineage='CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION' if freeze.get('engineering_simulation') else 'MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT',real_forward_evidence=observed['real_forward_evidence'],external_acceptance='PENDING',data_head_moved=False)
    marker_value.update(knowledge_lineage='CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION' if freeze.get('engineering_simulation') else 'MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT',
        engineering_simulation=bool(freeze.get('engineering_simulation')),real_forward_evidence=observed['real_forward_evidence'],
        target_session_observation_proven=observed['target_session_observation_proven'],target_session_observation_receipt=observation_ref,
        lineage_composition=composition(parent,'ALL_NINE',observed),AS_RECORDED=False,first_available_at_target_proven=False)
    result=atomic(root,marker,marker_value,immutable=True)
    return dict(status='ALL_NINE_CANDIDATE_READY',candidate=result,candidate_id=run_id)

def promote(candidate_binding, *, expected_parent_sha, root=ROOT):
    """CAS V2 pointer under the externally accepted once-only machine policy."""
    root=Path(root).resolve(); accepted_envelope(root)
    policy=json.loads((root/POLICY).read_bytes()); require(policy['output_contract_id']=='V4_DATA_ACCEPTED_HEAD_V2', 'STALE_V1_PROMOTER_FORBIDDEN')
    candidate=read(root,candidate_binding); target=candidate['target_trade_date']
    protected_scope=json.loads((ROOT/CONTRACT).read_bytes())['protected_runtime_paths']
    require(set(candidate['protected_heads'])==set(protected_scope), 'PROTECTED_STATE_SCOPE_INCOMPLETE')
    require(candidate['contract_id']=='DM01_ATOMIC_GO_FORWARD_CANDIDATE_R4', 'WRONG_CANDIDATE_CONTRACT')
    expected_id=digest(dict(target=target,parent=candidate['parent_data_head_digest'],source=candidate['source_manifest_digest'],contract=sha(ROOT/CONTRACT)))
    require(expected_id==candidate['candidate_id'], 'CANDIDATE_ID_MISMATCH')
    head=json.loads((root/HEAD).read_bytes())
    if head.get('final_candidate')==candidate_binding:
        current_parent(root)
        return dict(status='NOOP_IDENTICAL_PROMOTION',data_head=ref(root,root/HEAD))
    require(sha(root/HEAD)==expected_parent_sha==candidate['parent_data_head_digest'], 'BLOCKED_DATA_HEAD_PARENT_MOVED')
    parent=current_parent(root); cal=calendar(root); freeze=read(root,candidate['source_manifest']); identity_payload=read(root,candidate['identity'])
    identity=dict(binding=candidate['identity'],publication_id=candidate['identity']['sha256'],records=identity_payload['records'])
    require(candidate['knowledge_lineage'] in ('PIT_OBSERVED','MIXED_ACCEPTED_PARENT_PLUS_TARGET_SESSION_PIT') and candidate['permissions']==PERMISSIONS, 'SIMULATED_OR_ESCALATED_PROMOTION_FORBIDDEN')
    require(candidate.get('real_forward_evidence') is True,'REAL_FORWARD_EVIDENCE_REQUIRED')
    validate_lineage(freeze,root)
    from .dm01_lineage_r4r1 import require_real_forward, head_lineage, validate_head_lineage
    require_real_forward(candidate,freeze,parent,cal,root)
    require(freeze['manifest_sha256']==candidate['source_manifest_digest'] and candidate['calendar']==cal['binding'] and freeze['calendar_publication_id']==cal['publication_id'] and freeze['identity_publication_id']==candidate['identity']['sha256'], 'CANDIDATE_SOURCE_IDENTITY_MISMATCH')
    require(target==kernels.resolve_target_session(head['accepted_trade_date'],cal,freeze['observed_at'],target), 'PROMOTION_SKIPPED_SESSION')
    require(set(candidate['components'])==set(CAPABILITIES), 'PARTIAL_PROMOTION_FORBIDDEN')
    for cap,r in candidate['components'].items():
        require(r['status'] in policy['allowed_component_statuses'], 'COMPONENT_STATUS_NOT_ACCEPTED')
        artifact=Path(r['artifact_path']).resolve()
        require(artifact.is_relative_to(root), 'COMPONENT_OUTSIDE_PROJECT')
        require(sha(artifact)==r['artifact_sha256'], 'COMPONENT_DIGEST_MISMATCH')
        require(read(root,ref(root,artifact.parent/'receipt.json'))==r, 'COMPONENT_RECEIPT_READBACK_MISMATCH')
    post=check_cross_components(candidate['components'],freeze,parent,cal,identity)
    require(post['status']=='PASS' and digest(post)==candidate['postcheck_digest'] and read(root,candidate['cross_postcheck'])==post, 'PROMOTION_INDEPENDENT_POSTCHECK_FAILED')
    require(all(sha(root/p)==d for p,d in candidate['protected_heads'].items()), 'PROTECTED_STATE_MOVED')
    location=root/'data/v4/dm01_r4/accepted'/candidate['candidate_id']
    archive=atomic(root,location/'parent_head.json',(root/HEAD).read_bytes(),immutable=True)
    record=atomic(root,location/'session_acceptance.json',dict(contract_id='DM01_R4_MACHINE_SESSION_ACCEPTANCE_V1',status='ACCEPTED_UNDER_DM01_R4_MACHINE_POLICY',candidate=candidate_binding,policy=ref(root,root/POLICY),envelope=ref(root,root/ACCEPTANCE),parent=archive,permissions=PERMISSIONS,independent_postcheck_digest=digest(post)),immutable=True)
    chain=atomic(root,location/'accepted_chain.json',dict(contract_id='DM01_R4_ACCEPTED_CHAIN_V1',parent=head['accepted_chain'],parent_head=archive,candidate=candidate_binding,acceptance=record),immutable=True)
    next_head=deepcopy(head)
    artifacts={cap:ref(root,Path(r['artifact_path'])) for cap,r in candidate['components'].items()}
    permissions={cap:dict(status=r['status'],cutoff=target,artifact=artifacts[cap],receipt=ref(root,Path(r['artifact_path']).parent/'receipt.json'),logical_digest=r['logical_digest'],row_count=r['row_count'],accepted_algorithm_contract=r['accepted_algorithm_contract'],accepted_owner_stage=r['accepted_owner_stage']) for cap,r in candidate['components'].items()}
    for cap,permission in permissions.items():
        if head['component_permissions'][cap]['status']=='DEGRADED_PASS':
            permission['status']='DEGRADED_PASS'
    next_head.update(accepted_trade_date=target,source_revision=freeze['manifest_sha256'],canonical_data_revision=candidate['candidate_id'],manifest_path=chain['path'],manifest_sha256=chain['sha256'],parent_head_sha256=expected_parent_sha,component_permissions=permissions,component_artifacts=artifacts,accepted_chain=chain,final_candidate=candidate_binding,external_acceptance_record=record,calendar=candidate['calendar'],identity=candidate['identity'],parent_archive=archive,external_acceptance='ACCEPTED_UNDER_DM01_R4_MACHINE_POLICY',permissions=PERMISSIONS,promoted_at_utc=freeze['observed_at'])
    next_head.update(head_lineage(head,candidate,candidate['target_session_observation_receipt']))
    validate_head_lineage(next_head,head)
    lock=root/'data/v4/DM01_R4_PROMOTION.lock'
    try:
        descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError as error:
        raise ValueError('BLOCKED_DATA_HEAD_PROMOTION_LOCKED') from error
    try:
        os.close(descriptor)
        require(sha(root/HEAD)==expected_parent_sha, 'BLOCKED_DATA_HEAD_PARENT_MOVED')
        require(all(sha(root/p)==d for p,d in candidate['protected_heads'].items()), 'PROTECTED_STATE_MOVED')
        result=atomic(root,root/HEAD,next_head)
    finally:
        lock.unlink()
    return dict(status='PROMOTED_V2',data_head=result,session_acceptance=record,r25_grant=False,real_shadow_observations_increment=0)

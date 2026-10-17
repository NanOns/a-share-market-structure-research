"""Explicit sealed-candidate publication resume; no numerical producer replay."""
from pathlib import Path
from .r43_owner_replay import checked,load,ref
from .tdx_official_daily_source import sha256_file,sha256_bytes,_json_bytes
from .operational_daily_storage_v1 import atomic_json

CONTRACT='SEALED_CANDIDATE_RESUME_R1'
POINTER='config/v4_sealed_candidate_resume_r1.json'

def selected(root,day,mode):
    root=Path(root);path=root/POINTER
    if not path.is_file():return None
    pointer=load(path)
    if pointer.get('target_session')!=day or mode=='PROBE':return None
    if pointer.get('allowed_modes')!=['CATCH_UP']:raise ValueError('SEALED_RESUME_JOB_MODE_CONTRACT_REQUIRED')
    if mode!='CATCH_UP':return None
    document=load(checked(root,pointer['manifest']))
    if document.get('contract_id')!=CONTRACT or document.get('target_session')!=day or document.get('allowed_modes')!=['CATCH_UP']:raise ValueError('SEALED_RESUME_SCOPE_MISMATCH')
    return document,pointer['manifest']

def verify(root,manifest):
    root=Path(root);candidate=load(checked(root,manifest['candidate']))
    day=manifest['target_session'];head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    current=load(head)
    if current['accepted_trade_date']>=day:return None
    if candidate['accepted_trade_date']!=day or candidate['predecessor']!=manifest['predecessor'] or sha256_file(head)!=manifest['predecessor']['sha256']:raise ValueError('SEALED_RESUME_PARENT_CHANGED')
    generation=load(checked(root,manifest['generation']))
    if candidate['exact_daily_generation_scope']!=manifest['generation'] or generation['parent_head']!=manifest['predecessor']['sha256']:raise ValueError('SEALED_RESUME_GENERATION_CHANGED')
    freeze=load(checked(root,manifest['source_freeze']))
    if freeze['target_session']!=day or generation['source_freeze']!=manifest['source_freeze']['sha256']:raise ValueError('SEALED_RESUME_FREEZE_CHANGED')
    gate=load(checked(root,manifest['source_readiness']))
    gate_parent=gate['dependency_bindings']['parent_head']
    expected_parent=checked(root,manifest['predecessor'])
    actual_parent=checked(root,gate_parent)
    if (not gate.get('source_ready') or gate['source_freeze']!=manifest['source_freeze'] or
            gate_parent['sha256']!=manifest['predecessor']['sha256'] or actual_parent.read_bytes()!=expected_parent.read_bytes() or
            load(actual_parent)['accepted_trade_date']!=current['accepted_trade_date']):raise ValueError('SEALED_RESUME_SOURCE_NOT_READY')
    checked(root,freeze['native_baostock']);native=Path(freeze['tdx']['path'])
    if not native.is_absolute():native=root/native
    if sha256_file(native)!=freeze['tdx']['sha256']:raise ValueError('SEALED_RESUME_NATIVE_CHANGED')
    if sha256_file(Path(gate['dependency_bindings']['gbbq']['path']))!=gate['dependency_bindings']['gbbq']['sha256']:raise ValueError('SEALED_RESUME_GBBQ_CHANGED')
    if candidate['release_policy']!=manifest['runtime_policy'] or generation['adjustment_contract']['policy']!=manifest['generation_policy']:raise ValueError('SEALED_RESUME_POLICY_LINEAGE_CHANGED')
    attestation=load(checked(root,manifest['gate_attestation']))
    if (attestation.get('contract_id')!='SEALED_RESUME_GATE_ATTESTATION_R1' or attestation.get('acceptance')!='PASS' or
            attestation.get('candidate')!=manifest['candidate'] or attestation.get('generation')!=manifest['generation'] or
            attestation.get('source_freeze')!=manifest['source_freeze'] or attestation.get('predecessor')!=manifest['predecessor'] or
            attestation.get('gates')!=manifest['gates'] or attestation.get('target_session')!=day):raise ValueError('SEALED_RESUME_GATE_CANDIDATE_MISMATCH')
    for key in ('G1','G2','G3','G4_PREPUBLICATION'):
        evidence=load(checked(root,manifest['gates'][key]))
        if not str(evidence.get('acceptance',evidence.get('status',''))).startswith('PASS') or evidence.get('errors'):raise ValueError('SEALED_RESUME_GATE_NOT_PASSED:'+key)
    from .operational_successor_v1 import validate
    from .operational_successor_release_v1 import verify_policy
    validate(root,candidate);verify_policy(root,candidate)
    checked(root,manifest['period_verifier'])
    return candidate

def resume(root,day,mode,*,cancelled=lambda:False,readback_url=None,progress=lambda *args:None):
    choice=selected(root,day,mode)
    if choice is None:return None
    manifest,binding=choice;root=Path(root)
    progress(day,'REVALIDATE',dict(mode='SEALED_RESUME',numerical_recomputed=False))
    candidate=verify(root,manifest)
    if candidate is None:return dict(status='PUBLISHED',reason='NOOP_ALREADY_CURRENT',published=True,recovered_after_cas=True)
    if cancelled():return dict(status='CANCELLED',reason='CANCELLED_BEFORE_PG')
    folder=checked(root,manifest['generation']).parent
    from scripts import audit_dynamic_daily_period_numbers_v1 as period
    from .operational_owner_adapter_v1 import private_scope
    if sha256_file(Path(period.__file__))!=manifest['period_verifier']['sha256']:raise ValueError('SEALED_RESUME_LOADED_VERIFIER_CHANGED')
    output=root/'runtime/sealed_resume_r1'/binding['sha256']
    def write_audit(r,path,value):
        if Path(path).name!='PERIOD_NUMERIC_ORACLE.json':raise ValueError('SEALED_RESUME_UNEXPECTED_VERIFIER_WRITE')
        target=output/(sha256_bytes(_json_bytes(value))+'.json')
        if not target.exists():atomic_json(root,target,value)
    qa=private_scope(period,dict(__file__=str(checked(root,manifest['period_verifier'])),atomic_json=write_audit))['audit'](root,folder)
    if qa['acceptance']!='PASS' or qa['errors']:raise ValueError('FULL_PERIOD_NUMERIC_ORACLE_FAILED')
    if cancelled():return dict(status='CANCELLED',reason='CANCELLED_BEFORE_PG')
    progress(day,'PG_PREPARE',dict(numerical_recomputed=False))
    from .operational_product_pack_v3 import prepare
    core=load(folder/'owner_v3/CORE_REPLAY.json');owner=next(r for r in core['owners'] if r['trade_date']==day)
    prepare(root,candidate,owner)
    # Metadata producers must leave the fully admitted candidate token unchanged.
    if candidate!=load(checked(root,manifest['candidate'])):raise ValueError('SEALED_RESUME_CANDIDATE_MUTATED')
    progress(day,'READ_INDEX',dict(processed=0,total=2,unit='versions'))
    from workbench_db.v4_read_index_r1 import prepare_bff as prepare_read_index_r1
    from workbench_db.v4_read_index_r2 import prepare_bff as prepare_read_index_r2
    prepare_read_index_r1(root,candidate)
    progress(day,'READ_INDEX',dict(processed=1,total=2,unit='versions'))
    prepare_read_index_r2(root,candidate)
    from .operational_daily_storage_v1 import atomic_json
    from .r43_owner_replay import ref
    candidate_path=output/'candidate_pg_read_index.json'
    atomic_json(root,candidate_path,candidate)
    manifest['candidate']=ref(root,candidate_path)
    progress(day,'READ_INDEX',dict(processed=2,total=2,unit='versions'))
    if cancelled():return dict(status='CANCELLED',reason='CANCELLED_BEFORE_CAS')
    if not readback_url:return dict(status='QA_BLOCKED',reason='LIVE_SERVICE_READBACK_ENDPOINT_REQUIRED',candidate=manifest['candidate'])
    from .operational_successor_release_v1 import promote
    from .operational_daily_http_readback_v1 import readback
    progress(day,'PUBLISHING',dict(candidate=manifest['candidate'],numerical_recomputed=False))
    if cancelled():return dict(status='CANCELLED',reason='CANCELLED_AT_PUBLICATION_BOUNDARY')
    publication=promote(root,candidate,manifest['predecessor']['sha256'],lambda c:readback(readback_url,c))
    return dict(publication,status='PUBLISHED',published=True,source_ready=True,derived_ready=True,candidate=manifest['candidate'],sealed_resume=binding,numerical_recomputed=False)

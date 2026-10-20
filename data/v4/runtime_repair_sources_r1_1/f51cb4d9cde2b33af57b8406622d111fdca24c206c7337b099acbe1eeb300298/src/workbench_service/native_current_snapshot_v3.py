"""Immutable current product snapshot over already sealed native PG content."""
import json
import hashlib
from pathlib import Path

from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import checked, ref
from workbench_analysis.operational_successor_v1 import digest as business_token

CONTRACT='V4_CURRENT_NATIVE_PRODUCT_SNAPSHOT_V3'
JOINT_CONTRACT='V4_CURRENT_NATIVE_PRODUCT_JOINT_V3'
AUTHORITY='config/v4_current_native_joint_authority_v3.json'
CONTENT_KEYS=('native_pg_owner_authority','native_product_read_authority',
              'native_membership_reference','native_profile_semantic_corrections',
              'native_profile_dependent_corrections')


def load(path):return json.loads(Path(path).read_bytes())


def validate_document(document,candidate):
    """Pure invariants, independent of filesystem/PG setup."""
    if document.get('contract_id')!=CONTRACT:raise ValueError('CURRENT_SNAPSHOT_CONTRACT_REQUIRED')
    token=business_token(candidate);day=candidate['accepted_trade_date']
    if document.get('business_token')!=token:raise ValueError('CURRENT_SNAPSHOT_TOKEN_MISMATCH')
    if document.get('T0')!=day:raise ValueError('CURRENT_SNAPSHOT_DATE_MISMATCH')
    if document.get('published_sessions')!=candidate['published_sessions']:raise ValueError('CURRENT_SNAPSHOT_SESSION_DENOMINATOR_MISMATCH')
    if document.get('owners')!=candidate['owners']:raise ValueError('CURRENT_SNAPSHOT_OWNER_BINDING_MISMATCH')
    if document.get('native_content')!={key:candidate[key] for key in CONTENT_KEYS if key in candidate}:
        raise ValueError('CURRENT_SNAPSHOT_NATIVE_CONTENT_MISMATCH')
    for key in ('PIT_ELIGIBLE','AS_RECORDED','historical_PIT_permission','trading','probability_claims'):
        if document.get(key) is not False:raise ValueError('CURRENT_SNAPSHOT_SCOPE_ESCALATION:'+key)
    return document


def validate(root,binding,candidate):
    root=Path(root);document=load(checked(root,binding));validate_document(document,candidate)
    original=load(checked(root,document['candidate']))
    if original!=candidate:raise ValueError('CURRENT_SNAPSHOT_IMMUTABLE_CANDIDATE_MISMATCH')
    if document.get('producer'):checked(root,document['producer'])
    for item in document['native_content'].values():checked(root,item)
    from workbench_db.v4_operational_owner_authority_v2 import load as load_owner
    from .native_product_catalog_v3 import load as load_catalog
    load_owner(root,candidate);load_catalog(root,candidate)
    return document


def prepare(root,candidate):
    """Prepare only; every count comes from the actual corrected PG reader."""
    root=Path(root).resolve();token=business_token(candidate);day=candidate['accepted_trade_date']
    source_path=Path(__file__).resolve();source_bytes=source_path.read_bytes();source_sha=hashlib.sha256(source_bytes).hexdigest()
    source_archive=root/'data/v4/current_native_snapshot_sources_v3'/source_sha/'native_current_snapshot_v3.py'
    if source_archive.exists() and source_archive.read_bytes()!=source_bytes:raise ValueError('CURRENT_SNAPSHOT_SOURCE_IMMUTABLE_CONFLICT')
    if not source_archive.exists():
        from .v4_daily_refresh import atomic_bytes
        atomic_bytes(source_archive,source_bytes)
    folder=root/'data/v4/current_native_snapshots_v3'/token/source_sha
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from .core_product_bff_r1 import CoreProductBFFR1
    class NoLegacy:
        def __getattr__(self,name):raise ValueError('CURRENT_SNAPSHOT_LEGACY_READ_FORBIDDEN:'+name)
    reader=OperationalSuccessorReaderV1(root,candidate);api=CoreProductBFFR1(reader,NoLegacy())
    counts={domain:len(api.source(source,day)) for domain,source in (('stocks','core'),('profiles','profile'),('sectors','sector'),('actual_quotes','raw'))}
    counts['focus_episodes']=len(api.source('forward',day)['episodes'])
    candidate_path=folder/'CANDIDATE.json'
    if candidate_path.exists() and load(candidate_path)!=candidate:raise ValueError('CURRENT_SNAPSHOT_CANDIDATE_IMMUTABLE_CONFLICT')
    atomic_json(root,candidate_path,candidate)
    document=dict(contract_id=CONTRACT,business_token=token,T0=day,candidate=ref(root,candidate_path),published_sessions=candidate['published_sessions'],owners=candidate['owners'],native_content={key:candidate[key] for key in CONTENT_KEYS if key in candidate},counts=counts,
        PIT_ELIGIBLE=False,AS_RECORDED=False,historical_PIT_permission=False,trading=False,probability_claims=False,
        snapshot_kind='IMMUTABLE_NATIVE_CONTENT_INDEX_NO_DUPLICATE_PAYLOAD',producer=ref(root,source_archive),historical_data_head_role='SEPARATE_HISTORICAL_BASELINE_NOT_CURRENT_QUOTE_AUTHORITY',numerical_producers_reexecuted=False)
    path=folder/'SNAPSHOT.json'
    if path.exists() and load(path)!=document:raise ValueError('CURRENT_SNAPSHOT_IMMUTABLE_CONFLICT')
    atomic_json(root,path,document);binding=ref(root,path);validate(root,binding,candidate)
    return binding


def validate_joint_document(joint,snapshot,candidate):
    validate_document(snapshot,candidate)
    if joint.get('contract_id')!=JOINT_CONTRACT:raise ValueError('CURRENT_JOINT_CONTRACT_REQUIRED')
    if (joint.get('business_token'),joint.get('T0'))!=(snapshot['business_token'],snapshot['T0']):
        raise ValueError('CURRENT_JOINT_BUSINESS_CONTEXT_MISMATCH')
    if joint.get('operational_candidate')!=snapshot['candidate']:raise ValueError('CURRENT_JOINT_HEAD_SNAPSHOT_MISMATCH')
    if not joint.get('ui_assets'):raise ValueError('CURRENT_JOINT_UI_BINDINGS_REQUIRED')
    for key in ('PIT_ELIGIBLE','AS_RECORDED','trading','probability_claims'):
        if joint.get(key) is not False:raise ValueError('CURRENT_JOINT_SCOPE_ESCALATION:'+key)
    return joint


def validate_joint(root,joint,candidate,*,verify_loaded=True):
    root=Path(root);snapshot=validate(root,joint['snapshot'],candidate)
    validate_joint_document(joint,snapshot,candidate)
    for asset in joint['ui_assets'].values():checked(root,asset)
    from workbench_analysis.operational_successor_release_v1 import verify_policy
    verify_policy(root,candidate,verify_loaded=verify_loaded)
    policy=load(checked(root,candidate['release_policy']))
    if joint['admission_evidence']!=policy['admission_evidence']:raise ValueError('CURRENT_JOINT_ADMISSION_SOURCE_MISMATCH')
    checked(root,joint['admission_evidence'])
    return joint


def prepare_joint(root,candidate):
    """Prepare an admitted current Joint; never change its active pointer."""
    root=Path(root)
    from workbench_analysis.operational_successor_release_v1 import verify_policy
    verify_policy(root,candidate)
    policy=load(checked(root,candidate['release_policy']))
    snapshot_binding=prepare(root,candidate);snapshot=load(checked(root,snapshot_binding))
    historical=load(root/'config/v4_joint_release_authority_v1.json')
    joint=dict(contract_id=JOINT_CONTRACT,business_token=snapshot['business_token'],T0=snapshot['T0'],snapshot=snapshot_binding,operational_candidate=snapshot['candidate'],ui_assets=historical['ui_assets'],admission_evidence=policy['admission_evidence'],full_product_release=False,
        PIT_ELIGIBLE=False,AS_RECORDED=False,trading=False,probability_claims=False,historical_joint_is_current=False,
        scope='CURRENT_NATIVE_DATED_OPERATIONAL_RESEARCH; HISTORICAL_DATA_AND_PIT_AUTHORITIES_SEPARATE')
    validate_joint(root,joint,candidate)
    path=(root/snapshot_binding['path']).with_name('JOINT.json')
    if path.exists() and load(path)!=joint:raise ValueError('CURRENT_JOINT_IMMUTABLE_CONFLICT')
    atomic_json(root,path,joint)
    return ref(root,path)


def current(root,candidate,*,required=True):
    root=Path(root);path=root/AUTHORITY
    if not path.exists():
        if required:raise ValueError('CURRENT_JOINT_REQUIRED_NO_HISTORICAL_FALLBACK')
        return None
    return validate_joint(root,load(path),candidate,verify_loaded=False)

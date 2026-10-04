"""R29 additive contract authoring only, atomic E-drive repository artifacts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BASE='7f637644546a59b4cd28650def63be942f81b32a'


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    assert path.startswith(('reports/r29/','docs/evidence/r29/','config/v4_20_'))
    target=ROOT/path; target.parent.mkdir(parents=True,exist_ok=True)
    data=value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+'\n'
    staging=target.with_name(target.name+'.r29-staging')
    with staging.open('wb') as stream:
        stream.write(data.replace('\r\n','\n').encode('utf8')); stream.flush(); os.fsync(stream.fileno())
    os.replace(staging,target)


def build():
    from reports.r29.design_resolver import CAPS,DEPS,MODULES
    upgrade='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
    documents=[]
    for name in ('V4_NEXT_ROUND_EXECUTION_MASTER_R29_20261004.md','V4_20_R29_DEFAULT_UI_CUTOVER_CONTRACT_DESIGN_TASK_20261004.md','V4_R28_V4_19_FOCUS_SOURCE_CUTOVER_CONTRACT_DESIGN_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'):
        source=Path('D:/Users/lps/Desktop/阶段任务')/name
        documents.append(dict(source=str(source),original_sha256=sha(source),copy='docs/evidence/r29/'+name)); write(documents[-1]['copy'],source.read_text(encoding='utf8'))
    write('reports/r29/STAGE_CONTRACT.json',dict(stage='V4-20',mode='CONTRACT_DESIGN_ONLY',baseline=BASE,upgrade=dict(path=upgrade,sha256=sha(ROOT/upgrade),sections=['52A','78/V4-20','81.4','83']),documents=documents,allowed=['config/v4_20_*','reports/r29/*','docs/evidence/r29/*','tests/test_v4_20_default_ui_contract.py'],forbidden=['actual router/default page changes','Focus source mutation','permission grants','accepted heads','TDX writes'],acceptance='PENDING_LOCAL_DESIGN_VALIDATION',next='STOP_WAIT_R29_INDEPENDENT_EXTERNAL_AUDIT'))
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True,encoding='utf8').splitlines()
    unrelated=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode('utf8').split('\0')
    write('reports/r29/PROTECTED_BASELINE.json',dict(baseline=BASE,tracked={n:sha(ROOT/n) for n in names if (ROOT/n).is_file()},unrelated={n:sha(ROOT/n) for n in unrelated if n and not n.startswith(('reports/r29/','docs/evidence/r29/','config/v4_20_','tests/test_v4_20_'))}))
    native_legacy=['run_id','publication_id','local_date','mode','snapshot_id','algorithm_version']
    native_shadow=json.loads((ROOT/'config/v4_17_shadow_ui_contract_v1.json').read_text(encoding='utf8'))['identity_fields']
    fields=['module','trade_date','source_mode','namespace','publication_id','publication_revision','capability_scope','model_contract_id','parameter_digest','state_lineage_id','permission_receipt_digests','route_heads','native_context_digest']
    labels={'today_overview':'Today Overview','sector_research':'Sector Research','stock_research':'Stock Research','focus_tracking':'Focus Tracking','market_events':'Market / Events','data_diagnostics':'Data / Diagnostics','stock_sector_dependent':'Stock Research / Sector-dependent','rotation':'Sector Research / Rotation','sector_risk_change':'Sector Research / Risk Change'}
    registry={m:dict(product_module=labels[m],required_capabilities=r,optional_capabilities=o,fallback_source='EXACT_LEGACY_PRODUCTION',default_source='LEGACY_PRODUCTION_CURRENT; FUTURE_EXACT_PRODUCTION_V4_ONLY_IF_ALL_REQUIRED_PERMISSIONS_ACTIVE',shadow_only_subcomponents=['explicit_shadow_'+c for c in o],write_permissions='SHADOW_READ_ONLY; LEGACY_EXISTING_ENDPOINT_AUTHORITY; V4_FOCUS_REQUIRES_EXACT_CAPABILITY_PERMISSION_ACTIVE_V4_19_ROUTE_AND_ENDPOINT_AGREEMENT',context_identity_fields=fields,resolution_granularity='PER_COMPONENT_OR_FOCUS_ITEM; EMPTY_REQUIRED_LIST_NEVER_GRANTS_V4_BY_VACUOUS_TRUTH' if not r else 'MODULE_AND_SEPARATE_OPTIONAL_COMPONENTS') for m,(r,o) in MODULES.items()}
    registry['today_overview']['component_mapping']={'stock_core':'stock_research','sector_stage':'sector_research','rotation':'rotation','sector_risk':'sector_risk_change'}
    registry['focus_tracking']['component_mapping']='PER_ITEM_EXACT_SOURCE_CAPABILITY; PRESERVE_LEGACY_USER_WORK_AND_PIN_AUTHORITY'
    registry['market_events']['component_mapping']='PER_EVENT_NATIVE_PUBLICATION_AND_CAPABILITY; NO_MARKET_PAGE_GLOBAL_GRANT'
    c=dict(contract_id='V4_20_DEFAULT_UI_CUTOVER_CONTRACT_V1',version='1.0.0',stage='V4-20',mode='CONTRACT_DESIGN_ONLY',baseline=BASE,status='LOCAL_DESIGN_PENDING_EXTERNAL_AUDIT',module_registry=registry,dependency_graph=DEPS,
        permission_binding=dict(contract='config/v4_19_focus_source_cutover_contract_v1.json',sha256=sha(ROOT/'config/v4_19_focus_source_cutover_contract_v1.json'),receipt='EXACT_EXTERNALLY_ACCEPTED_ACTIVE_V4_19_PRODUCTION_PERMISSION_RECEIPT_PER_CAPABILITY; MATCH_MODEL_PARAMETER_LINEAGE_PUBLICATION_SCOPE_AND_RECEIPT_HEAD',missing_unknown_stale='LEGACY_PRODUCTION_AND_NO_PERMISSION; NEVER_V4',dependency='ALL_TRANSITIVE_REQUIRED_CAPABILITIES_ACTIVE; OPTIONAL_OUTPUTS_CANNOT_BECOME_HARD_DEPENDENCIES',shared_source='DOES_NOT_GRANT_PRODUCTION_PERMISSION'),
        source_resolution=dict(default='ALL_REQUIRED_ACTIVE_ACCEPTED_PERMISSIONS -> EXACT_ACCEPTED_V4_PRODUCTION_PUBLICATION; OTHERWISE_EXACT_LEGACY_PRODUCTION_ROUTE',empty_required='COMPOSITE_OR_DIAGNOSTIC_CONTAINER_REMAINS_LEGACY; RESOLVE_CHILDREN_OR_ITEMS_INDEPENDENTLY',v4_binding_conflict='UNKNOWN_AFFECTED_MODULE_NO_DISPLAY_NO_WRITE; NEVER_GUESS_ANOTHER_PUBLICATION',missing_legacy='UNKNOWN_NO_DISPLAY_NO_WRITE',explicit_shadow='SHADOW_V4_EXACT_READ_ONLY_ENGINEERING_CONTEXT; NEVER_PRODUCTION_FALLBACK',forbidden=['latest publication','mtime','page-local source choice','browser session as authority','global V4 flag'],inputs=['module contract','accepted capability permission heads','exact accepted route heads','exact publication bindings'],implemented_in_router=False),
        context_composition=dict(native_legacy_fields=native_legacy,native_shadow_fields=native_shadow,component_fields=fields,page_fields=['module_context_manifest','route_head_versions','permission_receipt_heads','manifest_digest'],token='DESIGN: SHA256_UTF8_SORTED_COMPACT_TYPED_JSON_NO_NAN_OF_EXACT_SUBCONTEXT_MANIFEST; FUTURE_TOKEN_PREFIX_UICTX_V1',mixed='PRESERVE_NATIVE_MODULE_NAMESPACES_AND_MODE_LABELS; SHARED_PAGE_TOKEN_NEVER_IMPLIED_PERMISSION',consistency='PAGE_SNAPSHOT_PINS_ALL_READ_HEADS; ROUTE_CHANGE_MARKS_LIVE_SESSION_STALE_REQUIRES_EXPLICIT_NEW_PAGE_CONTEXT; HISTORICAL_CONTEXT_READ_ONLY'),
        labels=['PRODUCTION_V4_PROVISIONAL','LEGACY_PRODUCTION','SHADOW','NO_PERMISSION','UNKNOWN'],aggregate_v4_production_label=False,
        deep_links=dict(required=['module','trade_date','source_mode','publication_id','publication_revision','capability_scope','permission_receipt_digests','context_digest'],resolve='EXACT_ACCEPTED_ARCHIVED_CONTEXT_BY_TOKEN_AND_DIGEST; NOT_NEW_DEFAULT',after_cutover_or_rollback='REPRODUCE_OLD_NATIVE_CONTEXT_READ_ONLY; WRITE_REQUIRES_FRESH_CURRENT_ENDPOINT_AUTHORITY',unavailable='EXACT_CONTEXT_UNAVAILABLE_WITH_REASON; NO_LATEST_FALLBACK',tampering='DIGEST_OR_IDENTITY_MISMATCH_REJECTED'),
        cache_session=dict(cache_namespace_fields=['contract_version','module','source_mode','native_context_digest','publication_id','publication_revision','route_head/version','permission_receipt_head','capability_scope'],route_change='INVALIDATE_AFFECTED_MODULE_AND_TRANSITIVE_CONSUMER_LIVE_CACHE_SESSION_BINDINGS; PRESERVE_ARCHIVED_HISTORICAL_CONTEXT',permission_change='REVOCATION_SUPERSESSION_MODEL_OR_DEPENDENCY_CHANGE_INVALIDATES_AFFECTED_LIVE_BINDINGS',session='TOKEN_PINS_EXACT_HEADS; STALE_TOKEN_CANNOT_WRITE_OR_MERGE_WITH_NEW_PAGE; EXPLICIT_REFRESH_CREATES_NEW_TOKEN',no_silent_merge=True),
        focus_write=dict(v4_required_all=['exact capability accepted active production permission','exact active accepted V4_19 Focus source route','endpoint authority source/model/parameter/lineage/context/permission/route-head agreement'],check_time='RECHECK_AT_WRITE_CAS_NOT_JUST_PAGE_RENDER',shadow='READ_ONLY_REJECT_ALL_ALGORITHM_FOCUS_WRITES',legacy='RETAIN_EXISTING_LEGACY_WRITE_AUTHORITY_UNTIL_EXACT_CAPABILITY_ROUTE_CUTOVER; ENDPOINT_CHECKS_EXACT_CURRENT_LEGACY_ROUTE',user_pins='PRODUCT_STATE_OWNERSHIP_PRESERVED; NEVER_ALGORITHM_EVIDENCE_OR_PERMISSION; SEPARATE_AUTHORIZED_PRODUCT_ENDPOINT',implemented=False),
        rollback=dict(primary='FOLLOW_ACCEPTED_V4_19_CAPABILITY_ROUTE_ROLLBACK',scope='AFFECTED_CAPABILITY_PLUS_TRANSITIVE_CONSUMERS',sector_stage_affected=['SECTOR_STAGE','ROTATION','SECTOR_RISK_CHANGE','STOCK_SECTOR_DEPENDENT'],independent_stock_core='REMAINS_ON_ITS_VALID_SOURCE',steps=['fence affected module writes','restore exact previous accepted UI source via routing authority','invalidate affected V4 live cache/session bindings','append scoped UI rollback receipt linked to V4_19 rollback'],preserve=['historical deep-link native contexts','user pins/manual work','accepted V4 history','pending settlement ownership'],missing_previous_route='BLOCKED_AFFECTED_SCOPE_NO_GUESS',implemented=False),
        current_state=dict(production_permission={cap:False for cap in CAPS},Focus_source_cutover=False,R25='WAIT_ACCEPTED_DAILY_INPUT',V4_17G='NOT_GRANTED',MIGRATION_REPLAY_PASS='NOT_GRANTED',V4_19_CONTRACT_DESIGN='EXTERNALLY_ACCEPTED',V4_19_IMPLEMENTATION_ENTRY='BLOCKED_WAIT_REAL_GATES',default_modules={m:'LEGACY_PRODUCTION' for m in MODULES},explicit_shadow_page='EXISTING_ENGINEERING_READ_ONLY_NOT_DEFAULT',DEFAULT_UI_CUTOVER=False,V4_20_ACCEPTED_HEAD='NOT_CREATED'),
        implementation_entry=dict(status='BLOCKED_WAIT_PRODUCTION_PERMISSION',required_all=['externally accepted V4_19 production permission receipt for at least one capability','active accepted Focus source route','accepted UI cutover authority','accepted rollback receipt schema'],receipts=[None]*4),next_stage='STOP_WAIT_R29_INDEPENDENT_EXTERNAL_AUDIT')
    descriptions=['all permissions false -> Legacy defaults','only STOCK_CORE -> stock V4 sector Legacy','only SECTOR_STAGE -> sector V4 stock Legacy','STOCK_SECTOR_DEPENDENT requires both dependencies','ROTATION false despite shared sector source','explicit Shadow never production fallback','stale permission blocks V4 default','publication capability mismatch','route head changed after page creation','old deep link reproduces old context','latest/mtime discovery forbidden','mixed page exposes module mode labels','global V4 label rejected','Shadow Focus write rejected','user pin preserved during cutover','cache invalidation on route change','single rollback affects dependents only','Sector rollback cascades to all three consumers','Stock Core survives Sector rollback','UNKNOWN permission -> Legacy/NO_PERMISSION']
    c['vectors']=[dict(id=f'U20-{i:02}',description=d,kind='CONTRACT_DESIGN_SIMULATION_NOT_UI_RUNTIME',fixture='reports/r29/design_resolver.py::vector_result',oracle='tests/test_v4_20_default_ui_contract.py',expected_actual_default_cutover=False,expected_actual_route_changes=[],future_evidence=['exact accepted permission and route heads','immutable native module/publication context manifest','independent default/cache/deep-link/write/rollback reconciliation']) for i,d in enumerate(descriptions,1)]
    write('config/v4_20_default_ui_cutover_contract_v1.json',c)
    mapping={'MODULE_CAPABILITY_MATRIX':'module_registry','SOURCE_RESOLUTION_GATE':'source_resolution','MIXED_PAGE_POLICY':'context_composition','DEEP_LINK_POLICY':'deep_links','CACHE_SESSION_INVALIDATION':'cache_session','FOCUS_WRITE_POLICY':'focus_write','UI_ROLLBACK_POLICY':'rollback','UI_CUTOVER_VECTOR_REGISTRY':'vectors','CURRENT_DEFAULT_GATE':'current_state'}
    for name,section in mapping.items(): write('reports/r29/'+name+'.json',dict(contract='config/v4_20_default_ui_cutover_contract_v1.json',contract_sha256=sha(ROOT/'config/v4_20_default_ui_cutover_contract_v1.json'),section=section,definition=c[section],scope='CONTRACT_DESIGN_ONLY'))


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT)); build()

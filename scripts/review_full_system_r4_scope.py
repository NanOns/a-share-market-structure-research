"""Evidence review without admitting/excluding modules or shrinking R3 nodes."""
import ast,csv,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_full_system_r4_scope import ROOT,OUT,sha,write

def symbols(path,names):
    if not path.exists():return []
    tree=ast.parse(path.read_text('utf-8-sig'))
    return [dict(path=path.relative_to(ROOT).as_posix(),symbol=n.name,start=n.lineno,end=n.end_lineno,sha256=sha(path)) for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]

def main():
    scope=json.loads((ROOT/'config/v4_audit_regression_scope_r3.json').read_bytes())
    graph=json.loads((OUT/'V4_RUNTIME_CALL_GRAPH_R4.json').read_bytes());reachable=set(graph['candidate_modules'])
    reviews=[]
    for category in ('included_test_modules','excluded_test_modules'):
        for item in scope[category]:
            path=ROOT/item['path'];imports=[];calls=[];contracts=[];tests=[]
            if path.exists():
                try:tree=ast.parse(path.read_text('utf-8-sig'))
                except (SyntaxError,UnicodeError):tree=None
                if tree:
                    for node in ast.walk(tree):
                        if isinstance(node,ast.Import):imports.extend(dict(module=n.name,line=node.lineno) for n in node.names)
                        elif isinstance(node,ast.ImportFrom):imports.append(dict(module=node.module or '',relative_level=node.level,line=node.lineno))
                        elif isinstance(node,ast.Call):
                            callee=ast.unparse(node.func)
                            if any(x in callee.casefold() for x in ('connect','sqlite','duckdb','postgres','popen','subprocess','execute')):calls.append(dict(callee=callee,line=node.lineno,expression=ast.unparse(node)[:350]))
                        elif isinstance(node,ast.Constant) and isinstance(node.value,str) and re.search(r'(CONTRACT|_R[123456]|_V[123456]|FEP_|PIT_|OWNER|SCOPE)',node.value):contracts.append(dict(line=node.lineno,value=node.value[:200]))
                        elif isinstance(node,ast.FunctionDef) and node.name.startswith('test_'):tests.append(dict(symbol=node.name,line=node.lineno,end=node.end_lineno))
            matches=[x for x in imports if x['module'] in reachable or any(m.startswith(x['module']+'.') for m in reachable if x['module'])]
            reviews.append(dict(path=item['path'],baseline_membership=category,baseline_sha256=item.get('sha256'),current_sha256=sha(path) if path.exists() else None,direct_imports=imports,static_entry_candidates=matches,database_or_subprocess_intents=calls,contract_mentions=contracts,test_symbols=tests,owner='Codex / root (engineering review)',current_status='SOURCE_REVIEWED_CONTRACT_AND_DYNAMIC_ADMISSION_OPEN',scope_change='NONE',limitation='Imports/contracts are evidence candidates; neither static presence nor historical baseline membership establishes legal scope'))
    write('R4_TEST_MODULE_SOURCE_REVIEW.json',dict(denominator=dict(included=len(scope['included_test_modules']),excluded=len(scope['excluded_test_modules']),reviewed=len(reviews)),reviews=reviews,current_status='BOTH_BASELINE_SETS_SOURCE_REVIEWED_ADMISSION_OPEN',next_conditions=['Per-capability contracts and dynamic supported-entry coverage; legal denominator remains null']))
    inherited=json.loads((ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5/EFFECTIVE_AUDIT_ITEMS_R3.json').read_bytes())
    locators={
        'FA-001':('src/workbench_service/core_product_bff_r1.py',['prioritize_home_changes']),
        'FA-005':('src/workbench_analysis/fep_engineering_storage.py',['engineering_directory']),
        'FA-013':('src/workbench_service/core_product_bff_r1.py',['resolve_dated_object']),
        'FA-016':('src/adjustment/tdx_adjustment_v0_3.py',['AdjustmentFactor','build_affine_factors']),
        'FA-017':('src/workbench_analysis/full_loo_v3_3.py',['recompute_full_current_loo']),
        'FA-018':('src/workbench_analysis/operational_daily_jobs_pg_r1.py',['DailyJobs','JobTransaction']),
        'FA-019':('src/workbench_service/core_product_bff_r1.py',['pack','chart']),
        'FA-020':('scripts/scan_no_symbol_specific_runtime_logic.py',['scan_file']),
    }
    issues=[]
    for original in inherited['issues']+inherited.get('additional_items',[]):
        item=dict(original);key=item.get('audit_item_id') or item.get('id');item['audit_item_id']=key
        item['inherited_status']=original.get('status');item['inherited_location']=original.get('effective_location',original.get('location'));item['engineering_owner']='Codex / root';item['external_acceptance']='PENDING_INDEPENDENT_SIGNATURE'
        if key in locators:
            path,names=locators[key];item['effective_source_locators']=symbols(ROOT/path,names)
        if key in ('FA-018','FA-019'):
            item['status']='SCOPED_NATIVE_PG_CANDIDATE_PRODUCTION_AND_FULL_INTEGRATION_OPEN'
            item['r4_evidence']=['R4_02_REAL_JOB_MIGRATION.json'] if key=='FA-018' else ['R4_03_REAL_HISTORY_ORACLE.json']
        if key=='FA-016':item['status']='EXACT_TRANSPORT_SCOPED_PASS_FULL_56_CONSUMERS_OPEN'
        if key=='FA-020':item['status']='SCOPED_RECEIPT_EQUIVALENCE_PASS_REAL_SCAN_PERFORMANCE_OPEN'
        if key in ('AR3-E02','FA-006'):item['status']='FULL_LEGAL_SCOPE_AND_REGRESSION_OPEN_BASELINE_PRESERVED'
        if key=='AR3-E03':item['status']='NONBUSINESS_GUARD_SCOPED_PASS_FULL_REPLAY_OPEN'
        if key=='FA-012':item['acceptance_independent_of_current_stage']=True;item['status']='OPEN_INDEPENDENT_AMOUNT_A_AUDIT'
        issues.append(item)
    capabilities=[
        ('DB-01','Native PG scheduler','src/workbench_analysis/operational_daily_jobs_pg_r1.py',['DailyJobs'], 'YES','Real seven-table migration and scoped runtime ledger','SCOPED_PASS_RESTART_GATE_OPEN'),
        ('DB-02','Desktop scheduler/status','src/workbench_desktop/engine.py',['EngineController'],'YES','Default class imports native PG; managed queue tests; physical package acceptance open','SCOPED_PASS_HTTP_AND_WINDOWS_OPEN'),
        ('DB-03','Dated charts','src/workbench_db/v4_history_pg_r1.py',['build','read'],'YES','5224 symbols /2162962 bars zero payload delta','SCOPED_PASS_FIVE_DATE_HTTP_BROWSER_OPEN'),
        ('DB-04','Research snapshots','src/workbench_service/production_v4.py',['build_snapshot','ProductionV4ResearchReader'],'YES','Actual staged nine-domain producer: same-source frozen oracle zero delta','SCOPED_PASS_JOINT_CAS_OPEN'),
        ('DB-05','Research BFF/continuous release','src/workbench_service/research_bff.py',['ResearchBFF'],'CONDITIONAL','Supported explicit entry imports native snapshot readers; actual route coverage pending','DYNAMIC_ROUTE_ADMISSION_OPEN'),
        ('DB-06','DuckDB bridge/research repository','src/workbench_db/api_connection.py',['PostgresDuckDBApiConnectionProvider'],'CONDITIONAL','Legacy app creates provider; V4 operational_candidate imports pure research_builder._exact_cycle_delta; capability-level proof pending','SOURCE_CONFIRMED_REACHABILITY_OPEN'),
        ('DB-07','Explicit legacy CLI branch','run_workbench_service.py',[],'NO_FOR_DEFAULT_EXPLICIT_LEGACY_FLAG_ONLY','--legacy-v3 branches after default exits; runtime negative entry proof pending','LEGACY_PRESERVED_DYNAMIC_PROOF_OPEN'),
        ('DB-08','Backup/config/old repositories','src/workbench_ops/storage.py',[],'UNKNOWN','Source inventory retained; actual DI and callable provider proof pending','SOURCE_CONFIRMED_REACHABILITY_OPEN'),
        ('DB-09','Cross-domain discovery','src/workbench_db/__init__.py',[],'UNKNOWN','Static candidates are not exhaustive runtime proof; DB-10/11/12 opened separately','DISCOVERY_OPEN'),
        ('DB-10','Stock/Focus/Forward series','src/workbench_db/v4_series_pg_r1.py',['build','range_rows'],'YES','Native immutable series, date/order and consumer tests; original source bindings fail until candidate rebinding','SCOPED_STORAGE_PASS_REAL_CONSUMER_OPEN'),
        ('DB-11','Focus append journals','src/workbench_db/v4_journal_pg_r1.py',['JournalConnection','open_read'],'YES','Shared PG registry CAS, rollback, concurrent serialization and failed export readback','SCOPED_PASS_REAL_DAILY_DRIVER_OPEN'),
        ('DB-12','Optional shadow readback','src/workbench_service/shadow_context.py',[],'CONDITIONAL','Old SQLite bindings reject without fallback; optional gate presently unbound','SOURCE_AND_MIGRATION_ADMISSION_OPEN'),
    ]
    matrix=[]
    for key,title,path,names,reach,evidence,status in capabilities:
        row=dict(audit_item_id=key,title=title,scope='V4_PG_ONLY_CAPABILITY',engineering_owner='Codex / root',owner='OWNER_UNKNOWN_UNTIL_BUSINESS_ADMISSION',status=status,V4_REACHABLE=reach,evidence=evidence,source_locators=symbols(ROOT/path,names),source_sha256=sha(ROOT/path),current_PID_loaded='NOT_VERIFIABLE_FOR_CANDIDATE_NOT_SWITCHED',acceptance_independent_of_current_stage=True)
        matrix.append(row);issues.append(row)
    write('DB_CAPABILITY_MATRIX_R4.json',dict(capabilities=matrix,denominator=12,current_status='CAPABILITY_REVIEW_DYNAMIC_AND_MIGRATION_GATES_OPEN',limitations=['DB-09 explicitly remains non-exhaustive; 12 capability rows do not imply zero hidden engines']))
    write('EFFECTIVE_AUDIT_ITEMS_R4.json',dict(contract_id='EFFECTIVE_AUDIT_ITEMS_R4_R1',issues=issues,current_status='AUDIT_INCOMPLETE',system_status='EXTERNAL_ACCEPTANCE_BLOCKED',inherited_source='full_system_repair_r3_20261011_239fb9b5/EFFECTIVE_AUDIT_ITEMS_R3.json'))
    print(json.dumps(dict(module_reviews=len(reviews),capabilities=len(matrix),issues=len(issues))))
if __name__=='__main__':main()

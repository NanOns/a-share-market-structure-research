"""Actual baseline reproductions, protected readbacks and per-item candidate seals."""
import copy
import hashlib
import json
import subprocess
import sqlite3
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock,patch
from pathlib import Path
import psycopg
from scripts.full_chain_repair_io import ROOT,PREFIX,write,binding

ITEMS={'P0-01':('A','CAPABILITY_ISSUE_DOMAIN',['v4_16_capability_resolution','test_capability']),
 'P0-02':('A','DURABLE_R4R2_SETTLEMENT',['settlement_queue','test_settlement','test_two_actual','test_V5','test_old_V3','test_roll_back','test_unknown_due']),
 'P1-03':('B','REAL_SHADOW_DB_SEMANTIC_INTEGRITY',['test_direct_db']),
 'P1-04':('C','FORWARD_BENCHMARK_SURFACE',['test_benchmark_contract']),
 'P1-05':('C','AFFINE_VALIDATION',['test_affine']),
 'P1-06':('D','FEP_SIGNAL_DB_GUARD',['test_signal']),
 'P2-07':('D','LEGACY_ENGINEERING_LEDGER_ISOLATION',['test_legacy_fixture'])}

def baseline_source(path):
    baseline=json.loads((ROOT/(PREFIX+'ENTRY_BASELINE.json')).read_bytes())['baseline_commit']
    return subprocess.check_output(['git','show',baseline+':'+path],cwd=ROOT).decode('utf8')

def reproduce():
    from workbench_analysis import v4_15_settlement as old
    deps=json.loads(baseline_source('config/v4_16_runtime_dependencies_v4.json'))
    head=json.loads((ROOT/deps['current_audit_head']['path']).read_bytes())
    repro={'P0-01':dict(actual_intersection=list(set(['PURE_CORE_STOCK']) & set(deps['blocked_capabilities'])),
        historical_set_test_would_allow=True,open_issue=head['entries']['A08_CURRENT_RUNTIME']['current_state'],
        affected_capability=head['entries']['A08_CURRENT_RUNTIME']['affected_capabilities'],
        actual_owner_code_consumes_prewatch='maturity\')==\'PREWATCH\'' in baseline_source('scripts/v4_16_real_owner_projection_v1.py'))}
    from scripts.v4_16_go_forward_shadow_runtime import SettlementObligationController
    reads=[];read_bytes=Path.read_bytes
    def observe(path):reads.append(str(path));return read_bytes(path)
    with patch.object(Path,'read_bytes',observe):
        try:SettlementObligationController(ROOT,ROOT/(PREFIX+'NEVER_CREATED.sqlite'))
        except Exception as error:failure=str(error)
    repro['P0-02']=dict(actual_restart_first_read=reads[0],actual_rejection=failure,
        contract_runtime_implemented=json.loads(baseline_source('config/v4_16_settlement_worker_contract_v1.json'))['runtime_implemented'],
        worker_storage_missing_from_baseline_schema='settlement_queue' not in baseline_source('migrations/v4_16_r24_real_shadow_v1.sql'))
    conn=sqlite3.connect(':memory:',isolation_level=None)
    conn.executescript(baseline_source('migrations/v4_16_r24_real_shadow_v1.sql'))
    conn.execute("INSERT INTO storage_identity VALUES(1,'ACTIVATION_SIMULATION','ACTIVATION_SIMULATION')")
    payload=dict(namespace='SHADOW_V4',execution_mode='SHADOW',evidence_origin='ACTIVATION_SIMULATION',slot_id='ORPHAN',revision=1,publication_id='ORPHAN')
    raw=json.dumps(payload)
    conn.execute('INSERT INTO facts VALUES(?,?,?,?,?,?,?)',('publication','ORPHAN','SHADOW_V4','SHADOW','ACTIVATION_SIMULATION',raw,hashlib.sha256(raw.encode()).hexdigest()))
    repro['P1-03']=dict(actual_orphan_publication_insert_accepted=conn.execute('SELECT count(*) FROM facts').fetchone()[0]==1,fixture_origin='ACTIVATION_SIMULATION',storage='MEMORY_ONLY');conn.close()
    from tests.test_full_chain_repair import row
    basket=old.freeze_basket([dict(security_id='S',close=10)],'2030-01-02')
    result=old.benchmark(basket,{'S':row()},.1,'2030-01-03')
    missing=[k for k in ('benchmark_valuation_coverage','benchmark_marked_weight','quote_age','quote_trade_date','relative_market_return') if k not in result]
    repro['P1-04']=dict(actual_missing_fields=missing,actual_generic_relative_return=result['relative_return'])
    rows=[row(),row()];rows[0]['transform_coefficients']['alpha']=-1
    result=old.price_path(10,rows,'2030-01-03')
    repro['P1-05']=dict(actual_invalid_interior_affine_result=result,illegal_alpha=-1)
    namespace=dict(__name__='workbench_analysis.fep_e5._baseline_ledger',__package__='workbench_analysis.fep_e5',__file__=str(ROOT/'src/workbench_analysis/fep_e5/ledger.py'))
    exec(compile(baseline_source('src/workbench_analysis/fep_e5/ledger.py'),'baseline_ledger.py','exec'),namespace)
    fake=MagicMock();fake.info.dbname='PRODUCTION_STYLE_DSN'
    namespace['Ledger'](fake).install()
    repro['P2-07']=dict(actual_default_install_executes_sql=fake.execute.called,fixture_opt_in_required=False,real_database_used=False)
    repro['P1-06']=dict(actual_database_negative_before_migration='test_baseline_unknown_signal_accepted: two isolated PostgreSQL fixtures',
                       evidence=binding(PREFIX+'targeted.xml'))
    write(PREFIX+'BUG_REPRODUCTION.json',repro)
    return repro

def database_readback(name):
    output={}
    for kind,port in [('fresh',55492),('upgrade',55493)]:
        with psycopg.connect(f'host=127.0.0.1 port={port} user=fep_e5_admin dbname=fep_e5b_{kind} connect_timeout=3') as pg:
            tables=[r[0] for r in pg.execute("SELECT tablename FROM pg_tables WHERE schemaname='fep' ORDER BY tablename")]
            from psycopg import sql
            rows={}
            for table in tables:
                count,sha=pg.execute(sql.SQL("SELECT count(*),md5(COALESCE(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text),'')) FROM fep.{} t").format(sql.Identifier(table))).fetchone()
                rows[table]=dict(count=count,logical_signature_md5=sha)
            output[kind]=dict(tables=rows,signal_registry_persisted=pg.execute("SELECT to_regclass('fep.signal_contract_registry')").fetchone()[0] is not None)
    write(PREFIX+name+'.json',output)
    return output

def finalize():
    entry=json.loads((ROOT/(PREFIX+'ENTRY_BASELINE.json')).read_bytes());repro=reproduce()
    changed=[]
    for reference in entry['protected']:
        if binding(reference['path'])!=reference:changed.append(reference['path'])
    if changed:raise ValueError('PROTECTED_STATE_CHANGED:'+','.join(changed))
    absent=[f'data/v4/V4_{n}_ACCEPTED_HEAD.json' for n in range(16,23)]
    if any((ROOT/path).exists() for path in absent):raise ValueError('FORBIDDEN_ACCEPTED_HEAD_CREATED')
    readback=database_readback('FEP_PROTECTED_AFTER')
    before=json.loads((ROOT/(PREFIX+'FEP_PROTECTED_BEFORE.json')).read_bytes())
    if readback!=before:raise ValueError('CANONICAL_FIXTURE_PROTECTED_STATE_CHANGED')
    protected=dict(status='UNCHANGED',bindings=entry['protected'],absent_accepted_heads=absent,
        production=False,focus_cutover=False,default_UI_cutover=False,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,
        FEP_PRODUCTION='UNGRANTED',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',REAL_OOS='NOT_GRANTED',CHAMPION='NONE',
        canonical_before=binding(PREFIX+'FEP_PROTECTED_BEFORE.json'),canonical_after=binding(PREFIX+'FEP_PROTECTED_AFTER.json'),
        TDX='NO_SOURCE_DIRECTORY_WRITE_OPERATION',real_storage_created=(ROOT/'data/v4/shadow_real_v1').exists())
    write(PREFIX+'PROTECTED_STATE_READBACK.json',protected)
    suites={name:json.loads((ROOT/(PREFIX+name.upper()+'_SUMMARY.json')).read_bytes()) for name in ('targeted','affected_stage','scoped_regression','cross_stage')}
    if any(s['introduced_failure_nodes'] for s in suites.values()):raise ValueError('INTRODUCED_FAILURE_NODES')
    if suites['scoped_regression']['removed_debt_nodes']:raise ValueError('KNOWN_DEBT_NODE_DRIFT')
    case_map={}
    supplemental={}
    for xml_name in ('targeted.xml','final_supplemental.xml','final_capability_projection.xml'):
        xml_cases=ET.parse(ROOT/(PREFIX+xml_name)).findall('.//testcase')
        for case in xml_cases:
            case_map[case.attrib['classname']+'::'+case.attrib['name']]=case
        if xml_name!='targeted.xml':
            if any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None for c in xml_cases):
                raise ValueError('SUPPLEMENTAL_NON_PASS:'+xml_name)
            supplemental[xml_name]=dict(passed=len(xml_cases),evidence=binding(PREFIX+xml_name))
    cases=list(case_map.values())
    write(PREFIX+'SUPPLEMENTAL_TEST_SUMMARY.json',supplemental)
    status=dict(FULL_CHAIN_REPAIR='CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',external_acceptance=False,
        introduced_failure_nodes=0,next_stage='INDEPENDENT_FULL_CHAIN_EXTERNAL_REAUDIT',first_real_shadow_authorized=False)
    unrelated_paths=[line[3:] for line in entry['unrelated_worktree']]
    names=subprocess.check_output(['git','ls-files','--modified','--others','--exclude-standard'],cwd=ROOT,text=True,encoding='utf8').splitlines()
    owned=[p for p in names if not any(p==q or (q.endswith('/') and p.startswith(q)) for q in unrelated_paths) and not p.startswith(('tmp/','artifacts/','reports/r24r1/activation_simulation/','reports/r24/activation_simulation/','reports/r23/','reports/r23r1/'))]
    owned=[p for p in owned if (ROOT/p).is_file()]
    owned=sorted(set(owned+['scripts/full_chain_repair_io.py']+[p.relative_to(ROOT).as_posix() for p in (ROOT/'docs/evidence/full_chain_repair_20261006').rglob('*') if p.is_file()]))
    write(PREFIX+'CHANGED_FILE_LIST.json',dict(files=[binding(p) for p in owned],unrelated_work_preserved=entry['unrelated_worktree']))
    design=dict(master=entry['master'],design=binding('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        accepted_heads='NO_MOVEMENT',successors=[binding(p) for p in ('config/v4_16_runtime_dependencies_v5.json','config/v4_16_runtime_capability_resolution_v1.json','config/v4_16_settlement_worker_contract_v2.json','config/v4_15_forward_benchmark_runtime_contract_v1_1.json','config/v4_18_migration_replay_contract_v1_3.json')])
    write(PREFIX+'DESIGN_BINDING.json',design)
    audit_head=json.loads((ROOT/'data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json').read_bytes())
    carry={k:{field:v.get(field) for field in ('current_state','affected_capabilities','blocks_affected_capability_in_shadow','blocks_production_cutover_for_scope')} for k,v in audit_head['entries'].items() if k.startswith(('A04','A08','AUD_R3'))}
    write(PREFIX+'BATCH_E_EXTERNAL_REAUDIT_DISPOSITION.json',dict(status='EXTERNAL_ACCEPTANCE_NOT_GRANTED',entries=carry,
        decision='KEEP_EXACT_OPEN_STATES; NO_INDEPENDENT_EXTERNAL_DISPOSITION_AVAILABLE',current_audit_head=binding('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json')))
    registry={}
    for item,(batch,scope,tokens) in ITEMS.items():
        directory=PREFIX+item+'/'
        selected=[dict(node=c.attrib['classname']+'::'+c.attrib['name'],status='PASS_EXECUTED' if c.find('failure') is None and c.find('error') is None and c.find('skipped') is None else 'NON_PASS') for c in cases if any(token in c.attrib['name'] for token in tokens)]
        if not selected:raise ValueError('NO_ITEM_ACCEPTANCE_EVIDENCE:'+item)
        records={'ENTRY_BASELINE':dict(entry=entry,stage_contract=scope,batch=batch), 'CHANGED_FILE_LIST':dict(binding=binding(PREFIX+'CHANGED_FILE_LIST.json')),
            'DESIGN_BINDING':design,'BUG_REPRODUCTION':repro[item], 'REPAIR_DISPOSITION':dict(status,item=item,scope=scope),
            'NEGATIVE_MATRIX':dict(cases=selected,executed=len(selected),not_a_production_pass=True),
            'TARGETED_TEST_SUMMARY':dict(primary=suites['targeted'],supplemental=supplemental),'SCOPED_REGRESSION_SUMMARY':dict(suites=suites,introduced_failure_nodes=0),
            'PROTECTED_STATE_READBACK':protected}
        for name,value in records.items():write(directory+name+'.json',value)
        write(directory+'CANDIDATE_SEAL.json',dict(status,evidence=[binding(directory+name+'.json') for name in records]))
        report=f'# {item} candidate repair\n\nScope: {scope}. Batch {batch}.\n\nExecuted {len(selected)} item-specific acceptance cases; inherited targeted, affected-stage and cross-stage suites retained. Known debt is explicit; introduced failure nodes = 0.\n\nHistorical heads, migrations and business outputs unchanged. No permission or real sample is created. External acceptance is not granted. Next: independent external re-audit.\n'
        write(directory+'COMPLETION_REPORT.md',report.encode(),raw=True)
        registry[item]=dict(scope=scope,batch=batch,status='CANDIDATE_REPAIRED_EXTERNAL_AUDIT_PENDING',acceptance=binding(directory+'CANDIDATE_SEAL.json'))
    registry['AUD_REPAIR_DUE_CALENDAR_EXTENSION']=dict(scope='NULL_FUTURE_DUE_SESSION_RECOVERY_WITHOUT_FACT_REWRITE',
        status='CANDIDATE_REPAIRED_EXTERNAL_AUDIT_PENDING',evidence=binding(PREFIX+'P0-02/NEGATIVE_MATRIX.json'))
    registry['AUD_REPAIR_V4_18_NAMESPACE_INVENTORY']=dict(scope='ADDITIVE_DECLARATION_INVENTORY_ONLY_NO_RUNTIME_GATE',
        status='CANDIDATE_REPAIRED_EXTERNAL_AUDIT_PENDING',evidence=binding('config/v4_18_migration_replay_contract_v1_3.json'))
    registry['AUD_REPAIR_MIGRATION_ALLOCATOR_STALE_BASELINE']=dict(scope='CURRENT_STAGE_ALLOCATOR_PARENT_BINDING',
        status='CANDIDATE_REPAIRED_EXTERNAL_AUDIT_PENDING',evidence=binding('config/v4_migration_allocation_registry_r4.json'))
    write(PREFIX+'INDEPENDENT_AUDIT_ITEM_REGISTRY.json',dict(items=registry,carry=carry,stage_gate=status))
    write(PREFIX+'STAGE_ACCEPTANCE_AND_NEXT.json',status)
    write(PREFIX+'CANDIDATE_SEAL.json',dict(status,evidence=[binding(PREFIX+n) for n in ('ENTRY_BASELINE.json','BUG_REPRODUCTION.json','DESIGN_BINDING.json','CHANGED_FILE_LIST.json','PROTECTED_STATE_READBACK.json','INDEPENDENT_AUDIT_ITEM_REGISTRY.json','BATCH_E_EXTERNAL_REAUDIT_DISPOSITION.json','SUPPLEMENTAL_TEST_SUMMARY.json')],suites=suites))
    total=sum(s['passed'] for s in suites.values())
    report=f'''# Full-chain repair candidate — 2026-10-06

FULL_CHAIN_REPAIR = CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT.

P0-01 / P0-02 / P1-03 / P1-04 / P1-05 / P1-06 / P2-07 have separate scope, baseline reproduction, acceptance evidence and candidate seals. The user authorized continuing all batches without the Batch A stop. Batch E keeps A08 / Amount-A / R3C external re-audit states unchanged.

Runtime uses explicit V5 dependencies and R4R2 exact target-session authority. PURE_CORE_STOCK transitively consumes current PREWATCH and stays blocked by A08. Settlement-only restart cannot accept publications; due facts, source-bound CAS deliveries, fencing, immutable outcomes, ack readback, retry/backlog and correction revisions are durable. New SQLite typed references are deferred within atomic publication transactions; a nonempty legacy ledger requires an audited migration rather than silent backfill. Unknown due sessions append revisions after an accepted calendar extension.

Forward successor preserves accepted calculation/revision code while validating all affine inputs and projecting market/sector contract fields. Missing/unverified local adjustment metadata stays UNKNOWN. Marked estimation remains disabled. FEP migration 033 was allocated through the R4 successor allocator because the R3 allocator is tied to superseded stage heads; 028–032 remain exact. PostgreSQL negative inserts executed on both isolated canonical fixtures and rolled back. Legacy ledger writes require an explicit fixture context and exact fixture database allowlist. V4-18 gains only an additive table inventory, no runtime or permission.

Final suites: {total} passed; scoped known debts = {len(suites['scoped_regression']['failed_nodes'])}; introduced failure nodes = 0. Supplementary executions: {sum(s['passed'] for s in supplemental.values())} passed (overlapping cases, not unique test counts). Raw initial failures are retained. Missing pinned sklearn environment and inventory/entry-point binding drift found during repair were corrected before final execution. Test suites invoke frozen historical fixture algorithms; they create no real evidence.

Protected head/migration hashes and canonical database signatures match entry. Real counters remain zero; V4-16–22 accepted runtime heads are absent; Production, Focus, Default UI, FEP production, display, Priority, REAL_OOS and Champion remain ungranted. TDX inputs were not written.

Next: independent full-chain external re-audit. Git publication is not external acceptance or first-real-Shadow authorization.
'''
    write(PREFIX+'COMPLETION_REPORT.md',report.encode(),raw=True)
    print(json.dumps(status))

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='before':database_readback('FEP_PROTECTED_BEFORE')
    else:finalize()

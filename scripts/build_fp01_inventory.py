"""Reproducible FP-01 producer inventory from explicit owner heads, never mtimes."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

from fp01_evidence import ROOT, OUT, ref, write


# Exact owner selection is deliberately reviewable; no glob chooses a latest head.
OWNERS = {
 'V4-03': ('原子因子与市场环境', ['src/v4/factors/*.py','src/v4/market_regime_ui.py'], 'data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json', '今日总览/个股研究'),
 'V4-04': ('Daily Profile Core', ['src/v4/profile*.py'], 'data/v4/V4_04_ACCEPTED_HEAD.json', '个股研究'),
 'V4-05': ('历史回放与输入门', ['src/v4/replay*.py','src/v4/r4_replay_paths.py'], 'data/v4/V4_05_ACCEPTED_HEAD_AMENDMENT_A02_R1.json', '数据与诊断/PIT Replay'),
 'V4-06': ('补充字段', ['src/workbench_analysis/v4_06_supplemental.py'], 'data/v4/V4_06_ACCEPTED_HEAD.json', '个股研究/数据与诊断'),
 'V4-07': ('Base Seed', ['src/v4/base_seed.py'], 'data/v4/V4_07_ACCEPTED_HEAD_AMENDMENT_A02_R1.json', '个股研究/今日总览'),
 'V4-08': ('板块生命周期与轮动', ['src/sector/*.py'], 'data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json', '板块研究/今日总览'),
 'V4-09': ('Stock PREWATCH', ['src/v4/stock_prewatch*.py'], 'data/v4/V4_09_ACCEPTED_HEAD_AMENDMENT_A02_R1.json', '个股研究/今日总览'),
 'V4-10': ('确认与场景', ['src/v4/confirmation.py','src/v4/confirmation_persistence.py'], 'data/v4/V4_10_ACCEPTED_HEAD.json', '个股研究'),
 'V4-11': ('D2 状态/事件', ['src/v4/confirmation*/*','src/v4/confirmation_candidate_r5.py','src/v4/confirmation_d2_candidate_r5.py','src/v4/confirmation_events_candidate_r5.py','src/v4/research_state*.py','src/v4/target_fact_producers_r4.py'], 'data/v4/V4_11_ACCEPTED_HEAD.json', '今日总览/个股研究'),
 'V4-12': ('锚点/结构/突破回调', ['src/workbench_analysis/v4_12_*.py'], 'data/v4/V4_12_ACCEPTED_HEAD.json', '个股研究/板块研究'),
 'V4-13': ('高级画像/LOO', ['src/workbench_analysis/v4_13_*.py'], 'data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json', '个股研究/板块研究'),
 'V4-14': ('完整DAG与回放', ['src/workbench_analysis/v4_14_*.py'], 'data/v4/V4_14_ACCEPTED_HEAD.json', '数据与诊断/PIT Replay'),
 'V4-15': ('Radar/Cohort/结算', ['src/workbench_analysis/v4_15_*.py'], 'data/v4/V4_15_ACCEPTED_HEAD.json', '今日总览/Forward'),
 'V4-16': ('持续运行/日更', ['src/shadow_v2/*.py','src/workbench_ops/*.py'], 'data/v4/V4_16_RUNTIME_ENGINEERING_ACCEPTED_HEAD_R1.json', '数据与诊断/Forward'),
 'V4-17': ('Shadow展示', ['src/workbench_service/shadow_context.py','src/workbench_service/shadow_server.py'], 'config/v4_17_shadow_ui_source_v1.json', '数据与诊断'),
 'V4-18': ('迁移/回滚', ['src/workbench_publish/*.py'], 'config/v4_18_migration_replay_contract_v1.json', '数据与诊断'),
 'V4-19': ('Focus路由旧合同', ['src/focus_tracker/core_activation.py','src/focus_tracker/release_gate.py'], 'config/v4_19_focus_source_cutover_contract_v1.json', '关注跟踪'),
 'V4-20': ('默认UI旧合同', ['src/workbench_service/current_v4_context.py','src/workbench_service/v4_server.py'], 'config/v4_20_default_ui_cutover_contract_v2.json', '六入口'),
 'V4-21': ('Forward累计合同', ['src/forward/*.py'], 'config/v4_21_continued_forward_observation_contract_v1.json', 'Forward'),
 'V4-22': ('独立审计合同', ['scripts/*v4_22*.py','scripts/*r31*.py'], 'config/v4_22_independent_audit_contract_v1.json', '数据与诊断'),
 'A02': ('RPS PIT历史', ['src/v4/rps*.py'], 'data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json', '个股研究/诊断'),
 'A03': ('真实PIT积累', ['src/workbench_analysis/*pit*.py','src/v4/go_forward_r3.py'], 'config/a03_forward_pit_ledger_r2.json', '数据与诊断'),
 'A04': ('Amount A', ['src/sector/*amount*.py','src/workbench_analysis/sector_amount.py'], 'data/v4/A04_AMOUNT_A_GO_FORWARD_PRODUCER_ACCEPTED_HEAD_R1.json', '板块研究'),
 'A05': ('旧成员/B2', ['src/sector/*member*.py'], 'data/v4/V4_08_B2_CURRENT_SNAPSHOT_CAPABILITY_AMENDMENT_R1.json', '板块研究'),
 'A06': ('精确输入reader', ['src/v4/accepted_input.py','src/workbench_analysis/historical_publication*.py'], 'config/historical_publication_reader_accepted_history_only_r1.json', '数据与诊断'),
 'A07': ('复权血缘', ['src/v4/adjustment_basis_r4.py','src/workbench_analysis/*adjustment*.py'], 'config/a07_adjusted_price_lineage_r2.json', '个股研究/数据与诊断'),
 'A08': ('当前运行传播/冻结', ['src/v4/scoped_promotions_r3.py','src/workbench_analysis/v4_current_stage_authority.py'], 'config/v4_cross_stage_current_audit_authority_v4.json', '数据与诊断'),
 'A09': ('未来schema约束', ['src/workbench_db/migrations/v4_postgres/*.sql'], 'config/v4_cross_stage_current_audit_authority_v4.json', '数据与诊断'),
 'A10': ('来源语义权威', ['src/workbench_analysis/source_authority*.py'], 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json', '数据与诊断'),
 'A11': ('身份/lifecycle', ['src/workbench_analysis/security_entity_identity.py','src/workbench_analysis/security_identity_event_discovery.py'], 'config/v4_security_entity_identity_v1.json', '个股研究/数据与诊断'),
 'A12': ('交易状态/ST', ['src/workbench_analysis/status_st*.py','src/workbench_analysis/source_authority_producers_r4.py'], 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json', '个股研究/市场与事件'),
 'A13': ('正式事件语义', ['src/workbench_analysis/official_event_semantics_v1.py'], 'data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json', '市场与事件/数据与诊断'),
 'Focus': ('Episode持续跟踪', ['src/focus_tracker/*.py'], 'config/focus_core_release_gate_v1.json', '关注跟踪'),
 'M14': ('公开在线增强', ['src/workbench_online/*.py'], 'config/m14_source_registry_v1.json', '市场与事件'),
 'MarketRegime': ('市场四轴', ['src/v4/factors/native.py','src/v4/market_regime_ui.py'], 'data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json', '今日总览'),
 'Rotation': ('轮动与风险', ['src/sector/*rotation*.py','src/sector/*risk*.py'], 'data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json', '今日总览/板块研究'),
 'Forward': ('到期/右删失/修订', ['src/workbench_analysis/v4_15_forward*.py','src/workbench_analysis/v4_15_settlement*.py'], 'data/v4/V4_15_ACCEPTED_HEAD.json', 'Forward'),
}
for i in range(1, 6):
    contract = {1:'fep_policy_v1.json',2:'fep_e2_historical_dataset_contract_v1.json',3:'fep_e3_experiment_protocol_v1_1.json',4:'fep_e4_challenger_protocol_v1.json',5:'fep_e5_projection_priority_protocol_v1.json'}[i]
    OWNERS[f'FEP-E{i}'] = (f'FEP E{i}', [f'src/workbench_analysis/fep_e{i}/*.py'], 'config/' + contract, 'Forward/数据与诊断')


def refs(value, location='$'):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and value.get('sha256'):
            yield location, value
        for key, child in value.items():
            yield from refs(child, location + '.' + key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from refs(child, location + f'[{i}]')


def inventory():
    audits = json.loads((ROOT / 'data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json').read_bytes())['entries']
    rows, producers = [], []
    for key, (label, patterns, owner, page) in OWNERS.items():
        modules = sorted({p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file()})
        declarations = []
        for p in modules:
            if p.suffix == '.py':
                tree = ast.parse(p.read_text('utf-8-sig'))
                for n in tree.body:
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        declarations.append(dict(name=n.name, line=n.lineno, code=p.relative_to(ROOT).as_posix()))
        owner_exists = (ROOT / owner).is_file()
        head = json.loads((ROOT / owner).read_bytes()) if owner_exists else {}
        bindings = []
        unique_refs = set()
        for location, r in refs(head):
            identity = (r['path'], r['sha256'])
            if identity in unique_refs:
                continue
            unique_refs.add(identity)
            p = ROOT / r['path']
            bindings.append(dict(location=location, declared=r, exists=p.is_file(),
                                 classification='OWNER_DECLARED_NOT_YET_FP01_QA'))
        # Thin scoped amendments frequently bind their older owner; follow exact
        # metadata edges rather than incorrectly declaring the algorithm absent.
        queue = [(r['declared'], r['location'], 0) for r in bindings]
        seen = {owner}
        while queue and len(seen) < 128:
            r, location, depth = queue.pop(0)
            name = r['path']
            p = (ROOT / name).resolve()
            if depth >= 3 or name in seen or not p.is_relative_to(ROOT) or p.suffix != '.json' or not p.is_file() or p.stat().st_size > 1_000_000:
                continue
            seen.add(name)
            try:
                nested = json.loads(p.read_bytes())
            except (ValueError, UnicodeDecodeError):
                continue
            for loc, child in refs(nested, location + '->' + name):
                identity = (child['path'], child['sha256'])
                if identity in unique_refs:
                    continue
                unique_refs.add(identity)
                item = dict(location=loc[-320:], declared=child, exists=(ROOT / child['path']).is_file(),
                            classification='TRANSITIVE_EXACT_OWNER_DECLARATION_NOT_YET_FP01_QA')
                bindings.append(item)
                queue.append((child, loc, depth + 1))
        retained_runs = []
        if key.startswith('FEP-E'):
            run = {'FEP-E1':'fep_e1_r2_final','FEP-E2':'fep_e2_r1r1','FEP-E3':'fep_e3_r1','FEP-E4':'fep_e4_r1','FEP-E5':'fep_e5_r1r1c'}[key]
            for name in ['STAGE_ACCEPTANCE_AND_NEXT.json','FINAL_ACCEPTANCE.json','COMPLETION_REPORT.md','TRAINING_TRIAL_LEDGER.json','TARGETED_SUMMARY.json','FEP_E5_R1R1C_CANDIDATE_SEAL.json','OWNER_ENGINEERING_READ_RECEIPT.json']:
                p = ROOT / 'reports' / run / name
                if p.is_file():
                    retained_runs.append(ref(p))
        audit = {k:v for k,v in audits.items() if k == key or k.startswith(key + '_')}
        row = dict(feature_id=key, module=label, code=[ref(p) for p in modules],
            owner=ref(owner) if owner_exists else dict(path=owner, status='MISSING'),
            declared_input_output_bindings=bindings,
            current_owner_state={k:head[k] for k in ['status','capabilities','scope','accepted_trade_date','accepted_input','production','focus','shadow'] if k in head},
            real_input='OWNER_BOUND_REFERENCES; output existence alone is not REAL evidence',
            current_output='OWNER_BOUND_ARTIFACTS_LOCATED' if any(r['exists'] and ('artifact' in r['location'] or 'candidate' in r['location'] or 'output' in r['location']) for r in bindings) else 'EXPLICIT_OUTPUT_QA_REQUIRED',
            operational_authorization='ELIGIBLE_FOR_SUCCESSOR_ADMISSION_AFTER_EXACT_REAL_OUTPUT_QA',
            engineering_qa='OWNER_SCOPED_HISTORY_PRESERVED; new release requires independent exact QA',
            long_term_validation_debt=audit or {'state':'VALIDATION_ONGOING','not_a_global_operational_blocker':True},
            page_entry=page, api_current='CURRENT_SEVEN_MODULE_READER_ONLY' if key in ['V4-11','V4-15','V4-20'] else 'NOT_EXPOSED_AS_FULL_PRODUCT_DOMAIN',
            api_target='FP03_DOMAIN_CONTRACT_REQUIRED', ui_current='MISSING_FULL_DOMAIN_OR_DETAIL',
            action='ADAPT_EXISTING_OUTPUT_IF_REAL_QA_PASSES_ELSE_TARGETED_PRODUCER_REPAIR',
            declaration_count=len(declarations))
        row['retained_run_evidence'] = retained_runs
        row['metadata_traversal'] = dict(max_depth=3, max_metadata_documents=128, visited=len(seen), remaining_edges=len(queue),
                                        scope='Exact declared edges, deduplicated by path/digest; full raw datasets are not loaded for inventory.')
        rows.append(row)
        producers.extend(dict(feature_id=key, **d) for d in declarations)
    # Keep every owner-registry entry including fields previously declared NOT_IMPLEMENTED.
    registry_rows = []
    for name in ['config/v4_12_producer_registry_v1.json','config/v4_13_producer_registry_v1_1.json',
                 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json','config/m14_source_registry_v1.json']:
        registry_rows.append(dict(source=ref(name), content=json.loads((ROOT / name).read_bytes()),
                                  interpretation='Historical declaration preserved; newest exact owner/runtime evidence determines actual capability, never registry wording alone.'))
    result = dict(contract_id='V4_OPERATIONAL_PRODUCER_INVENTORY_V1', baseline='a247a25d47a892042711efe2d3b2c3a0be9e52b4',
                  modules=rows, producer_declarations=producers, producer_registries=registry_rows,
                  coverage=dict(stages=list(range(3,23)), audits=list(range(2,14)), fep=list(range(1,6))),
                  inference_limit='AST declarations enumerate available code, not proof that each helper is a business producer or has run on real input.')
    write(OUT / 'producer_inventory_full.json.gz', gzip.compress(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf8'), mtime=0))
    graph = ref(OUT / 'producer_inventory_full.json.gz')
    for row in rows:
        row['full_declared_reference_count'] = len(row['declared_input_output_bindings'])
        row['full_reference_graph'] = graph
        row['declared_input_output_bindings'] = [r for r in row['declared_input_output_bindings'] if r['classification']=='OWNER_DECLARED_NOT_YET_FP01_QA']
    write(OUT / 'producer_inventory.json', result)
    return result


def policy(inv):
    verifier_raw = (ROOT / 'scripts/verify_fp01_real_admission.py').read_bytes()
    verifier_snapshot = OUT / 'source_versions' / hashlib.sha256(verifier_raw).hexdigest() / 'verify_fp01_real_admission.py'
    if verifier_snapshot.exists():
        assert verifier_snapshot.read_bytes() == verifier_raw
    else:
        write(verifier_snapshot, verifier_raw)
    value = dict(contract_id='V4_OPERATIONAL_PRODUCTION_RELEASE_POLICY_V1', version='1.0.0',
        authorization=ref(OUT / 'tasks/01_生产语义与版本化发布合同_R1_20261008.md'),
        successor_of=[ref('config/' + p) for p in ['v4_capability_cutover_policy_v1.json','v4_19_focus_source_cutover_contract_v1.json','v4_20_default_ui_cutover_contract_v1.json','v4_20_default_ui_cutover_contract_v2.json','v4_production_runtime_authority_v1.json']],
        feature_ids=[r['feature_id'] for r in inv['modules']] + ['STOCK_CORE','SECTOR_STAGE','STOCK_SECTOR_DEPENDENT','SECTOR_RISK_CHANGE','V4_13_PROFILE_ADVANCED','V4_11_STATE_EVENTS','V4_15_RADAR_PUBLICATION'],
        independent_verifier=ref(verifier_snapshot),
        dependencies={'STOCK_SECTOR_DEPENDENT':['STOCK_CORE','SECTOR_STAGE'],'Rotation':['V4-08'],
                      'V4_13_PROFILE_ADVANCED':[], 'V4_11_STATE_EVENTS':[], 'V4_15_RADAR_PUBLICATION':[]},
        required_metadata=['owner','release_id','source_snapshot','contract_version','source_as_of','trading_date','input_digest','published_at','evidence_origin','evidence_state','data_quality_state','knowledge_lineage'],
        states=dict(operational_state=['OPERATIONAL_PRODUCTION_ACTIVE','DATA_PENDING','SOURCE_INCOMPLETE','QUALITY_DEGRADED','ENGINEERING_NOT_READY'],
                    evidence_state=['VALIDATION_ONGOING','HISTORICALLY_ACCEPTED_SCOPED','STATISTICALLY_VALIDATED_SCOPED'],
                    data_quality_state=['KNOWN','QUALITY_DEGRADED','SOURCE_INCOMPLETE','PENDING','RIGHT_CENSORED']),
        migration=dict(old_production_permission='Historical shadow/forward/migration proof only; retained byte-for-byte, never set TRUE by this policy.',
            operational_admission='Exact real source/output/code/contract/context; independent schema/quality/no-future/readback QA; dependency scope and reversible release receipt.',
            shadow_20_sessions='VALIDATION_ONGOING debt; not an operational admission prerequisite',
            immature_forward='PENDING or RIGHT_CENSORED remains valid lifecycle; no maturity/profit claim',
            historical_source_integrity='Retain all input/PIT/identity/adjustment and field-consumer quality gates; no extrapolated permissions',
            focus='History preserved; V4 source routing/writes require a distinct engineering admission and transactional route CAS in FP08/FP14; historical V4-19 facts unchanged.',
            active_http_service='FP01 scopes operational release registry; FP02/03 consume it, FP14 atomically activates full-product service. No silent modification of v1 UI or data heads.'),
        field_rule='Missing/unimplemented values cannot become KNOWN; preserve original value, quality, reason, source, unit and window.',
        rollback=dict(strategy='Immutable blue/green release + serialized CAS + post-swap exact readback; restore exact retained predecessor on failure',
                      legacy_fallback='config/v4_production_runtime_authority_v1.json unchanged; Shadow and Focus history retained'),
        global_full_product_pass=False, trading_action_authorized=False, leverage_authorized=False, tdx_write_authorized=False,
        probability_claims_authorized=False, m14_hot_rank='REQUEST_TIME_ONLY_NO_RAW_ROW_BATCH_HISTORY_PERSISTENCE',
        next_stage='FP02_FP03_FP04_AFTER_FP01_LOCAL_ACCEPTANCE_AND_SEPARATE_STAGE_DISPATCH')
    write(ROOT / 'config/v4_operational_production_release_policy_v1.json', value)


if __name__ == '__main__':
    policy(inventory())

"""Additive R2 registry and A10 schema freeze; accepted records are immutable."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from workbench_analysis.source_authority_governance_r1 import SourceRole,Availability,HistoricalMode,ERROR_TAXONOMY,validate_role_contract

DOCUMENTS=('DM01_A01_R1_INDEPENDENT_REAUDIT_20261001.md','DM01_A01_R2_BAOSTOCK_CATCHUP_SUPPLEMENTAL_GATE_REPAIR_TASK_20261001.md',
    'V4_09_FULL_EXECUTION_INDEPENDENT_REAUDIT_20261001.md','V4_CROSS_STAGE_REMEDIATION_MASTER_AMENDMENT_R2_20261001.md',
    'V4_A12_V4_02_STATUS_ST_AUTHORITY_AND_CASCADE_REPAIR_TASK_R1_20261001.md',
    'V4_A11_V4_01_IDENTITY_SOURCE_AUTHORITY_RECONCILIATION_TASK_R1_20261001.md',
    'V4_A10_SOURCE_AUTHORITY_AVAILABILITY_GOVERNANCE_TASK_R1_20261001.md','V4_00_TO_V4_09_SOURCE_AUTHORITY_RETROSPECTIVE_AUDIT_R1_20261001.md')

def bind(path):
    p=ROOT/path;data=p.read_bytes();return dict(path=path,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))

def run():
    protected=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'data/v4').glob('*ACCEPTED_HEAD*.json'))]
    protected+=[bind('data/v4/V4_DEV_BASELINE_HEAD.json'),bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json')]
    stage=json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_text(encoding='utf8'))
    assert stage['phase0_status']=='FULL_PASS'
    docrefs=[]
    for name in DOCUMENTS:
        destination='docs/evidence/source_authority/'+name
        data=(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes()
        if (ROOT/destination).exists():assert (ROOT/destination).read_bytes()==data
        else:atomic_bytes(ROOT/destination,data)
        docrefs.append(bind(destination))
    previous=json.loads((ROOT/'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json').read_text(encoding='utf8'))
    registry=deepcopy(previous);registry.update(contract_id='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2',audit_count=12,
        baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        extends=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json'),
        authority=next(r for r in docrefs if 'MASTER_AMENDMENT' in r['path']),status='OPEN_IMPLEMENTATION_BATCH_0_1_AUTHORIZED',
        execution_scope=['A10','A11','A12','A01_R2'],other_work_packages_preserved_open=True,
        external_acceptance=None,accepted_head_rebinding_authorized=False)
    additions=[('A10','SOURCE_AUTHORITY_AVAILABILITY_SEMANTICS_GOVERNANCE','WP-A10-SOURCE-AUTHORITY-GOVERNANCE','V4_A10_',[],'P0'),
        ('A11','V4_01_IDENTITY_SOURCE_AUTHORITY_RECONCILIATION','WP-A11-V4-01-IDENTITY-AUTHORITY','V4_A11_',['A10_SCHEMA_FREEZE'],'P1'),
        ('A12','V4_02_STATUS_ST_SOURCE_AUTHORITY_DIVERGENCE','WP-A12-V4-02-STATUS-ST-AUTHORITY','V4_A12_',['A10_SCHEMA_FREEZE'],'P0')]
    for short,audit,wp,prefix,deps,priority in additions:
        entry=dict(audit_id=audit,work_package=wp,priority=priority,status='OPEN',external_acceptance=None,
            implementation_status='IMPLEMENTATION_ENTRY_AUTHORIZED',depends_on=deps,production_gate=True,
            does_not_block_engineering_stage=True,formal_consumer_authorization=False,
            task=next(r for r in docrefs if Path(r['path']).name.startswith(prefix)),evidence=[],
            status_path=f'reports/audits/work_packages/{wp}/STATUS_R1.json',
            next_step='Versioned candidate, independent evidence, clean regression and external reaudit; no accepted-head overwrite.')
        registry['entries'].append(entry);registry['dependency_graph'][wp]=deps
        atomic_json(ROOT/entry['status_path'],entry)
    a01=registry['entries'][0];assert a01['audit_id']=='DM01_REAL_INCREMENTAL_BUILDERS'
    a01.update(depends_on=['A10_SCHEMA_FREEZE','A12_PRODUCER_CONTRACT_FREEZE'],implementation_status='KEEP_PASS_ENGINEERING_SCOPE_REAL_SOURCE_R2_REPAIR_REQUIRED',
        latest_task=next(r for r in docrefs if 'DM01_A01_R2_' in r['path']),status_path='reports/audits/work_packages/WP-A01-DM01/STATUS_R2.json')
    registry['dependency_graph']['WP-A01-DM01']=a01['depends_on']
    atomic_json(ROOT/'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2.json',registry)
    rules=[]
    def add(field,family,role,owner,consumers,mode='TARGET_DATE_QUERYABLE_FACT',enabled=True):
        authority=role in ('CORE_AUTHORITY','FIELD_AUTHORITY')
        r=dict(field_id=field,source_family=family,role=role,owner_contract_id=owner,allowed_consumers=consumers,
            may_block_core=authority,may_change_core_value=authority,may_change_core_quality=False,
            historical_retrieval_mode=mode,pit_requirement='EXPLICIT_OBSERVATION_NO_INFERRED_FIRST_AVAILABILITY',enabled=enabled)
        validate_role_contract(r);rules.append(r)
    add('OHLC_VOLUME_AMOUNT','TDX','CORE_AUTHORITY','V4_02_FORMAL_RAW_QFQ_PERIODS_V1',['RAW_DAILY','ADJUSTED_DAILY','PERIOD_RAW','PERIOD_ADJUSTED','PRICE_LIMIT'])
    add('SECURITY_IDENTITY','LOCAL_OFFICIAL_DATED_IDENTITY','FIELD_AUTHORITY','SECURITY_ENTITY_IDENTITY_V1',['IDENTITY_UNIVERSE'])
    add('TRADING_STATUS','LOCAL_OFFICIAL_DATED_STATUS','FIELD_AUTHORITY','LOCAL_DATED_TRADING_STATUS_V2',['TRADING_STATUS','PERIOD_RAW','PERIOD_ADJUSTED'])
    add('ISST','LOCAL_OFFICIAL_DATED_ST','FIELD_AUTHORITY','LOCAL_DATED_ST_IDENTITY_V2',['ISST','PRICE_LIMIT'])
    add('QFQ','GBBQ','CORE_AUTHORITY','V4_02_FORMAL_RAW_QFQ_PERIODS_V1',['ADJUSTED_DAILY','PERIOD_ADJUSTED'])
    add('SPECIAL_PHASE','OFFICIAL_SPECIAL_PHASE','FIELD_AUTHORITY','SPECIAL_PRICE_PHASE_POLICY_V2',['SPECIAL_PHASE','PRICE_LIMIT'])
    for field in ('OHLC_FINGERPRINT','TRADING_STATUS_CROSSCHECK','ISST_CROSSCHECK','ADJUSTMENT_FACTOR_AUDIT'):
        add(field,'BAOSTOCK','SUPPLEMENTAL_CROSSCHECK','BAOSTOCK_SUPPLEMENTAL_SOURCE_V1',['SUPPLEMENTAL_DIAGNOSTICS'])
    add('TURNOVER','BAOSTOCK','FIELD_AUTHORITY','TURNOVER_CONTEXT_V1',['SUPPLEMENTAL_TURNOVER_VARIANT'],enabled=False)
    add('SECTOR_MEMBERSHIP','TDX_CURRENT_MEMBERSHIP','FIELD_AUTHORITY','V4_08_SECTOR_MEMBERSHIP_SOURCE_V1',['SECTOR_CURRENT_PIT'],'MUTABLE_CURRENT_SNAPSHOT')
    add('AS_RECORDED_PRICE','FROZEN_FIRST_AVAILABILITY','FIELD_AUTHORITY','HISTORICAL_AS_RECORDED_PRICE',['HISTORICAL_AS_RECORDED_VARIANT'],'AS_RECORDED_PIT_FACT',enabled=False)
    contract=dict(contract_id='V4_SOURCE_AUTHORITY_GOVERNANCE_R1',version='1.0.0',status='CANDIDATE_PENDING_EXTERNAL_REAUDIT',
        task=next(r for r in docrefs if Path(r['path']).name.startswith('V4_A10_')),
        master_contract=bind('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        source_roles=[v.value for v in SourceRole],availability_states=[v.value for v in Availability],
        historical_retrieval_modes=[v.value for v in HistoricalMode],failure_taxonomy=list(ERROR_TAXONOMY),field_rules=rules,
        runtime=bind('src/workbench_analysis/source_authority_governance_r1.py'),
        supplemental_promotion_requires=['Explicit new field-level owner contract','Independent external source-semantics acceptance','Explicit declared consumer requirement'],
        runtime_acceptance_is_distinct_from_target_capture=True,protected_bindings=protected,
        external_acceptance=None,production_permission=False,data_head_promotion_permitted=False)
    atomic_json(ROOT/'config/source_authority_governance_r1.json',contract)
    atomic_json(ROOT/'reports/audits/A10_STAGE_ENTRY_R1.json',dict(stage_contract=contract['task'],
        phase0_status=stage['phase0_status'],phase0=stage['bindings']['phase0'],governance_contract=bind('config/source_authority_governance_r1.json'),
        evidence=docrefs,acceptance_result='ENGINEERING_ENTRY_AUTHORIZED_EXTERNAL_PENDING',next_stage='A10_GUARDS_SCAN_REGRESSION_THEN_A11_A12',protected_bindings=protected))
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in protected)
    print(json.dumps(dict(status='A10_SCHEMA_FROZEN_MASTER_R2_ADDED',audits=12,heads_changed=False)))

if __name__=='__main__':run()

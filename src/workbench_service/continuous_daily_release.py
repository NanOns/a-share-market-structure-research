"""Admitted local daily release: immutable candidates, bounded QA, joint CAS."""
import copy,json,urllib.request
from pathlib import Path
from .current_v4_context import SourceInvalid,canonical,digest
from .joint_release import AUTHORITY,activate,checked_path,load,validate
from .production_v4 import ProductionV4ResearchReader
from .pit_observation import freeze
from .v4_daily_refresh import atomic_bytes

ADMISSION='config/v4_continuous_daily_admission_v10.json'

def _admitted_bytes(root,binding):
    """Resolve an exact daily-release binding from PG, admitting it once if needed."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import admit_source_binding_bytes
    return admit_source_binding_bytes(root,binding,
        source_origin='V4_CONTINUOUS_DAILY_RELEASE_HEAD_BOUND_SOURCE_R1')

def promote(root,staged,health=None):
    root=Path(root).resolve();before=(root/AUTHORITY).read_bytes();previous=json.loads(before)
    admission_binding=previous.get('daily_pipeline_admission')
    if not isinstance(admission_binding,dict) or admission_binding.get('path')!=ADMISSION:
        raise SourceInvalid('DAILY_ADMISSION_HEAD_BINDING_REQUIRED')
    admission=json.loads(_admitted_bytes(root,admission_binding))
    if admission.get('contract_id')!='R2_CONTINUOUS_DAILY_ADMISSION_V10' or admission.get('result')!='DEGRADED_PASS':
        raise SourceInvalid('DAILY_ADMISSION_REQUIRED')
    for binding in admission['evidence']+list(admission['implementations'].values()):
        _admitted_bytes(root,binding)
    if previous['ui_build_id']!=admission['ui_build_id']:raise SourceInvalid('DAILY_UI_ADMISSION_VERSION_CONFLICT')
    if previous.get('full_product_release') or previous.get('trading') is not False:raise SourceInvalid('DAILY_SCOPE_NOT_ADMITTED')
    candidate=copy.deepcopy(previous);candidate.update(contract_id='V4_JOINT_RELEASE_V2_PG_CONTENT',snapshot=staged['snapshot']['pointer'],trade_date=staged['trade_date'],
        daily_owner_authorities=staged['owner_authorities'],daily_pipeline_admission=admission_binding,
        continuous_daily_candidate_write=True,full_product_release=False,focus_automatic_write=False)
    manifest=validate(root,candidate);reader=ProductionV4ResearchReader(root,snapshot_authority=candidate['snapshot'])
    day=reader.context['trade_date']
    if day<previous['trade_date']:raise SourceInvalid('DAILY_BACKWARD_RELEASE_FORBIDDEN')
    if manifest['sources']['focus_journal']!=staged['focus']['journal']:raise SourceInvalid('DAILY_JOURNAL_BINDING_CONFLICT')
    for key in ('market','sector','stocks','market_center','forward'):
        owner=staged['owner_authorities'][key]
        if owner['trade_date']!=day or owner['input_data_head']['sha256']!=manifest['context']['data_head_digest']:
            raise SourceInvalid('DAILY_OWNER_CONTEXT_MISMATCH_'+key)
    raw=json.loads(checked_path(root,manifest['sources']['RAW_DAILY']).read_bytes())['rows']
    if any(row['trade_date']!=day for row in raw):raise SourceInvalid('DAILY_RAW_DATE_CONFLICT')
    expected={r['security_id']:r for r in raw};comparisons=0
    with reader.connect() as db:
        for domain,payload in db.execute('SELECT domain,payload FROM objects'):
            row=json.loads(payload)
            for cell in row.get('fields',{}).values():
                if cell.get('quality')=='KNOWN' and cell.get('value')=='UNKNOWN':raise SourceInvalid('DAILY_LITERAL_UNKNOWN_QUALITY_CONFLICT')
                asof=cell.get('source_as_of') or ''
                if len(asof)==10 and asof>day:raise SourceInvalid('DAILY_FUTURE_VALUE_DATE')
            if domain=='stocks':
                for field in ('open','high','low','close'):
                    if row['fields'][field]['value']!=expected[row['entity_id']][field]:raise SourceInvalid('DAILY_RAW_ORACLE_MISMATCH')
                    comparisons+=1
    focus=manifest['domain_features']['focus']
    for episode in focus['episodes']:
        if episode['T0']>day or any(o['trade_date']>day for o in episode['observations']):raise SourceInvalid('DAILY_FUTURE_FOCUS')
        if any(o['outcome_status']=='OBSERVED' and o['target_trade_date']>day for o in episode['outcomes']):raise SourceInvalid('DAILY_PREMATURE_OUTCOME')
    from .forward_daily import verify_due_settlement
    publication=manifest['domain_features']['forward']
    due_count=verify_due_settlement(publication,day)
    if publication.get('adapter_contract_id'):
        def check_bindings(value):
            if isinstance(value,dict):
                if {'path','sha256'}<=value.keys():checked_path(root,value)
                else:
                    for item in value.values():check_bindings(item)
            elif isinstance(value,list):
                for item in value:check_bindings(item)
        check_bindings(publication['sources'])
        if publication['sources']['accepted_data_head']['sha256']!=manifest['context']['data_head_digest']:
            raise SourceInvalid('DAILY_FORWARD_EVALUATION_HEAD_MISMATCH')
        calendar=json.loads(checked_path(root,publication['sources']['evaluation_inputs']['calendar']).read_bytes())['session_dates']
        for outcome in publication['outcomes']:
            if outcome.get('adapter_contract_id')!=publication['adapter_contract_id']:raise SourceInvalid('DAILY_FORWARD_ADAPTER_MISMATCH')
            if outcome['report_cutoff']!=day:raise SourceInvalid('DAILY_FORWARD_EVALUATION_CUTOFF_MISMATCH')
            source=outcome['evaluation_source'];frozen=json.loads(checked_path(root,outcome['frozen_t0']).read_bytes())
            expected=digest(canonical(dict(inputs=publication['sources']['evaluation_inputs'],t0=frozen['T0'],cutoff=day,
                calendar=calendar,kernel=publication['sources']['kernel'])))
            if source['sha256']!=expected:raise SourceInvalid('DAILY_FORWARD_EVALUATION_SOURCE_IDENTITY_MISMATCH')
    freeze_receipt=freeze(reader)
    if health is None:
        from scripts.activate_v4_full_product import health
    result=activate(root,candidate,digest(before),health)
    result.update(raw_oracle_comparisons=comparisons,first_observed_freeze=freeze_receipt,
        forward_due='DUE_PROCESSED' if due_count else 'NO_DUE',forward_due_count=due_count,strict_pit=False,full_product_release=False)
    atomic_bytes(root/'runtime/research_daily/JOINT_DAILY_LATEST.json',canonical(result))
    return result

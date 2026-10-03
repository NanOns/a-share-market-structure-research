"""Independent exact-authority feasibility oracle; no runtime or writer imports."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HORIZONS=(1,3,5,10,20)
def require(condition,message):
    if not condition:raise ValueError(message)
def descriptor(path,root=ROOT):
    raw=(Path(root)/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def exact(binding,root=ROOT):
    p=(Path(root)/binding['path']).resolve();require(p.is_relative_to(Path(root).resolve()),'PATH_ESCAPE')
    require(descriptor(binding['path'],root)['sha256']==binding['sha256'],'BOUND_DIGEST_MISMATCH')
    require(p.stat().st_size==binding.get('bytes',binding.get('byte_count')),'BOUND_SIZE_MISMATCH')
    return json.loads(p.read_bytes()) if p.suffix=='.json' else p.read_bytes()
def inspect(root=ROOT):
    root=Path(root);bindings={n:descriptor(p,root) for n,p in {'stage':'data/v4/V4_STAGE_ACCEPTED_HEAD.json','data':'data/v4/V4_DATA_ACCEPTED_HEAD.json','head':'data/v4/V4_14_ACCEPTED_HEAD.json','r20_seal':'reports/r20e/V4_15_RUNTIME_CANDIDATE_R20_SEAL.json','producer':'reports/r20e/PRODUCER_RECEIPT.json','settlement':'reports/r20e/SETTLEMENT_RECEIPT.json','r20d':'reports/r20d/SETTLEMENT_GATE.json','package':'config/v4_15_contract_package_v1.json'}.items()}
    stage=exact(bindings['stage'],root);data=exact(bindings['data'],root);head=exact(bindings['head'],root)
    require(stage['accepted_stage_range']=='V4_00_TO_V4_14_ACCEPTED' and stage['v4_14_binding']==bindings['head'],'CURRENT_EXACT_V4_14')
    require(head['bindings']['data_head']==bindings['data'],'EXACT_DATA_HEAD')
    require(head['accepted_trade_date']==data['accepted_trade_date']=='2026-09-30','FROZEN_ACCEPTED_CUTOFF')
    require(head['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','NO_PIT_UPGRADE')
    require(not (root/'data/v4/V4_15_ACCEPTED_HEAD.json').exists(),'NO_V4_15_HEAD')
    require(all(stage[k] is False for k in ['production_permission','shadow_production_permission','focus_cutover_permission']),'NO_OPERATIONAL_PERMISSION')
    seal=exact(head['bindings']['runtime_seal'],root);calendar=exact(head['bindings']['calendar'],root)
    sessions=[x['trade_date'] if isinstance(x,dict) else x for x in calendar['session_dates']]
    inventory=[];earlier=[]
    for b in seal['replay_publications']:
        p=exact(b,root);date=p.get('trade_date',p.get('target_trade_date'));kind=p.get('evidence_class')
        matured=[n for n in HORIZONS if date in sessions and sessions.index(date)+n<len(sessions) and sessions[sessions.index(date)+n]<=data['accepted_trade_date']]
        real=kind=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED'
        inventory.append(dict(binding=b,T0=date,evidence_class=kind,accepted_source_publication=real,due_horizons_within_data_head=matured,admissible_for_real_maturity=real and bool(matured),exclusion='ENGINEERING_NOT_REAL' if not real else 'NO_ACCEPTED_FUTURE_SESSION' if not matured else 'REQUIRES_EXACT_REAL_ENROLLMENT_AND_ENDPOINT_PROOF'))
        if real and date<head['accepted_trade_date'] and matured:earlier.append(b)
    producer=exact(bindings['producer'],root);settlement=exact(bindings['settlement'],root);d=exact(bindings['r20d'],root)
    publication=exact(producer['real_publication'],root);enrollment=exact(producer['real_enrollment'],root)
    require(publication['source_publication'] in seal['replay_publications'],'SEALED_PUBLICATION_LINEAGE')
    owner=exact(publication['source_publication'],root)
    require(owner['evidence_class']==publication['evidence_class']==enrollment['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','REAL_T0_PROVENANCE')
    require(enrollment['source_publication']==publication['source_publication'] and enrollment['T0']==publication['trade_date']==head['accepted_trade_date'],'NO_FABRICATED_EARLIER_T0')
    require(enrollment['cohort_namespace']=='RECONSTRUCTED_ASOF' and enrollment['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','T0_RECONSTRUCTED_SCOPE_DISCLOSED')
    require(enrollment['enrollment_id'] in [exact(x,root)['enrollment_id'] for x in publication['enrollments']],'PERSISTED_ENROLLMENT_LINEAGE')
    outcomes=[exact(b,root) for b in settlement['real_outcomes']];dout=[exact(b,root) for b in d['outcomes']]
    require(sorted(x['horizon'] for x in outcomes)==list(HORIZONS) and all(x['outcome_status']=='PENDING' and not x['price_path'] for x in outcomes+dout),'CURRENT_REAL_PENDING_ONLY')
    require(all(x[k] is None for x in outcomes+dout for k in ['R_N','MFE_N','MAE_N','PATH_MDD_CLOSE_N']),'NO_REAL_NUMERICAL_CLAIM')
    require(not producer['future_source_reads'] and d['future_read_count']==0,'NO_REAL_ACCEPTED_FUTURE_ENDPOINT')
    require(not settlement['raw_provider_fallback'],'NO_RAW_PROVIDER')
    require(not earlier,'UNEXPECTED_REAL_EARLIER_LINEAGE_REQUIRES_SEPARATE_SETTLEMENT_PROOF')
    # Repository discovery is disclosure, not admission: the sealed allowlist above is authority.
    heads=subprocess.check_output(['git','ls-files','data/v4/*V4_14*ACCEPTED_HEAD*'],cwd=root,text=True,encoding='utf8').splitlines()
    require(heads==['data/v4/V4_14_ACCEPTED_HEAD.json'],'UNEXPECTED_ADDITIONAL_V4_14_ACCEPTED_HEAD')
    return dict(contract_id='R20R1_REAL_MATURITY_FEASIBILITY_V1',decision='NO_ACCEPTED_MATURED_LINEAGE_AVAILABLE',bindings=bindings,runtime_seal=head['bindings']['runtime_seal'],calendar=head['bindings']['calendar'],accepted_head_inventory=heads,publication_inventory=inventory,earlier_real_accepted_matured_lineage_count=0,current_real_T0=enrollment['T0'],data_cutoff=data['accepted_trade_date'],current_cohort_namespace=enrollment['cohort_namespace'],future_read_count=0,real_outcomes=[dict(binding=b,horizon=x['horizon'],status=x['outcome_status']) for b,x in zip(settlement['real_outcomes'],outcomes)],real_lineage=dict(publication=producer['real_publication'],enrollment=producer['real_enrollment'],freezes=producer['real_freezes']),historical_prices_alone_are_not_lineage=True,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED')
if __name__=='__main__':print(json.dumps(inspect(),indent=2))

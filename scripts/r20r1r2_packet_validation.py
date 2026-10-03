"""Active production-shaped maturity admission with separately bound projection."""
import json,math
from datetime import datetime
from pathlib import Path
from scripts.r20r1r2_io import ROOT,ref,exact,require
from scripts.r20r1r2_dm01_resolver import accepted_heads
from scripts.r20r1r2_forward_projection import project
HORIZONS=(1,3,5,10,20)

def data_chain(root,registry):return list(reversed(accepted_heads(root)))

def validate_packet(packet,root=ROOT):
    root=Path(root);registry=json.loads((root/'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json').read_bytes())
    require(packet['accepted_head']==registry['accepted_head']==ref('data/v4/V4_14_ACCEPTED_HEAD.json',root),'EXACT_FROZEN_HEAD')
    head=exact(packet['accepted_head'],root);seal=exact(head['bindings']['runtime_seal'],root)
    require(all(head['bindings']['data_head'][k]==registry['T0_data_archive'][k] for k in ['sha256','bytes']),'EXACT_FROZEN_T0_DATA_ARCHIVE')
    require(packet['owner_publication']==registry['owner_publication'] and packet['owner_publication'] in seal['replay_publications'],'EXACT_SEALED_REAL_OWNER')
    require(exact(packet['owner_publication'],root)['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','SYNTHETIC_OWNER_REJECTED')
    require(packet['enrollment']==registry['enrollment'] and packet['freeze']==registry['freeze'],'EXACT_T0_ANCHORS')
    en=exact(packet['enrollment'],root);freeze=exact(packet['freeze'],root);producer=exact(registry['producer_receipt'],root)
    require(en['source_publication']==packet['owner_publication'] and freeze['enrollment']==packet['enrollment'] and freeze['T0']==en['T0']==registry['T0'] and en['cohort_namespace']=='RECONSTRUCTED_ASOF','EXACT_RECONSTRUCTED_T0_LINEAGE')
    require(packet['freeze_completed_at']==producer['end'] and packet['freeze'] in producer['real_freezes'] and producer['real_enrollment']==packet['enrollment'],'PERSISTED_FREEZE_TIME')
    log=exact(packet['endpoint_read_receipt'],root)
    require(log['freeze']==packet['freeze'] and log['accepted_endpoints']==packet['accepted_endpoints'] and log['projection']==packet.get('projection') and log['first_future_endpoint_open_at']==packet['first_future_endpoint_open_at'],'EXACT_ENDPOINT_PROJECTION_READ_RECEIPT')
    before=datetime.fromisoformat(producer['end']);after=datetime.fromisoformat(packet['first_future_endpoint_open_at'])
    require(before.tzinfo is not None and after.tzinfo is not None and before<after,'T0_BEFORE_FUTURE_READ')
    require(log['raw_provider_fallback'] is False and packet['raw_provider_fallback'] is False and packet['historical_prices_only'] is False,'NO_PRICE_ONLY_OR_PROVIDER_FALLBACK')
    require(packet['HISTORICAL_PIT_EFFECTIVENESS']==packet['REALTIME_ACCEPTED_COHORT_MATURITY']=='NOT_GRANTED','NO_PIT_REALTIME_UPGRADE')
    n=packet['horizon'];require(type(n) is int and n in HORIZONS,'FROZEN_HORIZON')
    require('projection' in packet,'SEPARATE_PROJECTION_RECEIPT_REQUIRED');projection=exact(packet['projection'],root);rows=projection['rows']
    require(len(rows)==n and projection==project(packet['freeze'],projection['evaluation_basis_date'],root,packet['data_head']),'EXACT_DETERMINISTIC_FORWARD_PROJECTION')
    chain=accepted_heads(root,packet['data_head'])
    require(any((b['sha256'],b['bytes'])==(packet['data_head']['sha256'],packet['data_head']['bytes']) for b,_ in chain),'ACCEPTED_DATA_SNAPSHOT_ANCESTRY')
    require(projection['resolution']['source_data_head']['sha256']==packet['data_head']['sha256'],'PROJECTION_SELECTED_DATA_HEAD')
    require(packet['accepted_endpoints']==[x['source_adjusted_daily_artifact'] for x in rows],'EXACT_RESOLVED_ENDPOINTS')
    outcome=exact(packet['outcome'],root)
    require(outcome['frozen_t0']==packet['freeze'] and outcome['enrollment_id']==en['enrollment_id'] and outcome['horizon']==n and outcome['due_date']==projection['evaluation_basis_date'] and outcome['outcome_status']=='OBSERVED' and outcome['projection']==packet['projection'] and outcome['price_path']==rows,'BOUND_OBSERVED_PROJECTED_OUTCOME')
    require(outcome['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' and all(x['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' for x in [projection,outcome,en,freeze]),'NO_OUTCOME_PIT_UPGRADE')
    t=projection['T0_transform_coefficients'];p0=t['alpha']*float(freeze['comparison_reference'])+t['beta'];require(math.isfinite(p0) and p0>0,'PROVEN_POSITIVE_T0_BASIS')
    val=lambda r,k:r['transform_coefficients']['alpha']*float(r[k])+r['transform_coefficients']['beta']
    peak=p0;mdd=0
    for r in rows:c=val(r,'close');require(math.isfinite(c) and c>0,'POSITIVE_EVALUATED_PRICE');peak=max(peak,c);mdd=min(mdd,c/peak-1)
    expected={'R_N':val(rows[-1],'close')/p0-1,'MFE_N':max([p0]+[val(r,'high') for r in rows])/p0-1,'MAE_N':min([p0]+[val(r,'low') for r in rows])/p0-1,'PATH_MDD_CLOSE_N':mdd}
    require(all(not isinstance(outcome[k],bool) and math.isfinite(outcome[k]) and abs(outcome[k]-v)<1e-10 for k,v in expected.items()),'SOURCE_BACKED_NUMERICAL_RECOMPUTATION')
    return dict(enrollment_id=en['enrollment_id'],horizon=n,due_date=outcome['due_date'],accepted_future_endpoint_read_count=n,T0_OBSERVATION_SCOPE='RECONSTRUCTED_ASOF',REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',packet=packet,validation_environment='CURRENT_ACCEPTED_AUTHORITY' if root.resolve()==ROOT.resolve() else 'ISOLATED_ENGINEERING_REACHABILITY_ONLY')

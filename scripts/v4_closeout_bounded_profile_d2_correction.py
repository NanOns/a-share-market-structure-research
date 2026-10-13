"""Replay only thirteen affected entities from sealed D0 facts, never full producers."""
import copy,gzip,json,os
from pathlib import Path
from datetime import datetime,timezone
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_operational_owner_authority_v2 import load as load_owner,read as read_owner
from workbench_db.v4_profile_semantic_corrections_pg_v1 import apply
from v4.state_identity import digest
from v4 import confirmation_d2_candidate_r5 as d2
from v4.stock_prewatch import evaluate,load_package

def main():
    report=OUT/'BOUNDED_PROFILE_D2_CORRECTION_R6_R2.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_BOUNDED_D2_CORRECTION')
    preparation=json.loads((OUT/'NATIVE_PROFILE_SEMANTIC_PREPARATION_R6_R1.json').read_bytes());scope=json.loads((OUT/'EXTENSION_CHANGED_SCOPE_SIX_DATES_R6_R1.json').read_bytes())
    candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());ids={c['security_id'] for date in scope['dates'] for c in date['corrections']}
    folder=checked(ROOT,candidate['owners'][candidate['accepted_trade_date']]['focus']).parents[2]
    replay=json.loads((folder/'PROFILE_STRUCTURE_REPLAY.json').read_bytes());sectors=json.loads((folder.parent/'sector_v3/SECTOR_REPLAY.json').read_bytes());receipt=json.loads((folder/'FOCUS_FORWARD_REPLAY.json').read_bytes());calendar=json.loads((folder/'FOCUS_CALENDAR.json').read_bytes())
    saved={r['trade_date']:r for r in receipt['owners']};owners={r['owner']['trade_date']:r['owner'] for r in replay['owners']};sector_by={r['trade_date']:r for r in sectors['owners']}
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]];authority=load_owner(ROOT,candidate)
    package=load_package(ROOT);reducer=d2.extracted_runtime()[0];prior=None;prior_pid=None;dated=[];now=datetime.now(timezone.utc).isoformat()
    target_folder=ROOT/'data/v4/profile_semantic_d2_corrections_v1'/digest([preparation['candidate'],now])
    from workbench_analysis.tdx_official_daily_source import _atomic_write
    producer_source=target_folder/'producer.py';_atomic_write(producer_source,Path(__file__).read_bytes(),tdx_root=Path('D:/new_tdx'))
    for day in candidate['dates']:
        original=json.load(gzip.open(checked(ROOT,saved[day]['D2']),'rt',encoding='utf8'));old_rows={r['entity_id']:r for r in original['rows']};fact_rows=rows(ROOT,saved[day]['facts'])
        minimal=[{k:r[k] for k in ('entity_id','entity_type','fields')} for r in fact_rows];owner=owners[day];sector=sector_by[day]
        manifest=d2.seal_fact_manifest(dict(contract_id='V4_R4_CORRECTED_STATE_INPUT_FACT_PUBLICATION_V1',trade_date=day,calendar_publication_id=calendar['publication_id'],rows=minimal,source_bindings=[owner['core'],owner['profiles'],owner['history'],sector['seed']],accepted=False,AS_RECORDED=False))
        original_ids={f['publication_id'] for r in original['rows'] for f in r['input_provenance'].values() if f.get('publication_id')}
        if original_ids!={manifest['publication_id']}:raise ValueError('ORIGINAL_FACT_MANIFEST_RECONSTRUCTION_MISMATCH:'+day)
        core={r['security_id']:r for r in read_owner(ROOT,authority,day,'core',candidate['owners'][day]['core']) if r['security_id'] in ids}
        raw_profiles=read_owner(ROOT,authority,day,'profile',candidate['owners'][day]['profile']);profiles={r['security_id']:r for r in apply(ROOT,candidate,day,raw_profiles) if r['security_id'] in ids}
        seeds={r['security_id']:r for r in read_owner(ROOT,authority,day,'seed',candidate['owners'][day]['seed']) if r['security_id'] in ids}
        facts=[];calculations=[];changed_fields={}
        for r in minimal:
            sid=r['entity_id']
            if sid not in ids:continue
            fact=copy.deepcopy(r);f=core[sid]['fields'];p=profiles[sid];damage=f['core_price_damage']['value'];seed=seeds[sid]['base_seed_state']
            inputs=dict(base_seed_state=seed,mandatory_core_quality_ready='TRUE' if seed!='UNKNOWN' and isinstance(damage,bool) else 'UNKNOWN',delta3=f['rps5_delta3']['value'],priority_lineage_failures=[],**{k:p['states'][k]['value'] for k in ('compression_state','ma_structure_state','core_extension_risk')})
            prewatch=evaluate(inputs,package);calculations.append(dict(security_id=sid,inputs=inputs,prewatch=prewatch));changed_fields[sid]=set()
            for name,value in (('risk',p['states']['core_extension_risk']['value']),('PREWATCH',prewatch['raw_qualification'])):
                cell=fact['fields'][name]
                if cell['value']==value:continue
                changed_fields[sid].add(name)
                cell.update(value=value,quality='UNKNOWN' if value=='UNKNOWN' else 'KNOWN',system_available_at=now)
                cell['source_field_payload']['value']=value;cell['source_output_digest']=digest(cell['source_field_payload'])
            facts.append(fact)
        correction=d2.seal_fact_manifest(dict(contract_id='V4_PROFILE_THIN_CORRECTED_D2_FACTS_R1',trade_date=day,calendar_publication_id=calendar['publication_id'],rows=facts,source_bindings=[preparation['candidate'],candidate['native_profile_semantic_corrections'],saved[day]['facts']],accepted=False,AS_RECORDED=False))
        pid=correction['publication_id'];entities={(r['entity_id'],r['entity_type']):r for r in facts}
        original_entities={(r['entity_id'],r['entity_type']):r for r in minimal}
        context=dict(calendar=calendar,manifests={pid:(correction,entities),manifest['publication_id']:(manifest,original_entities)},prior_publication=None if prior is None else dict(publication_id=prior_pid),prior_rows=prior or {})
        corrected=[]
        for fact in facts:
            sid=fact['entity_id'];fields={k:dict(v,publication_id=(pid if k in changed_fields[sid] else manifest['publication_id']) if v['status']=='IMPLEMENTED' else None) for k,v in fact['fields'].items()}
            x=d2.input_skeleton(entity_id=sid,trade_date=day,session_index=calendar['session_dates'].index(day),cutoff=now,calendar_manifest=calendar,fields=fields,prior_state=(prior or {}).get(sid),prior_publication_id=prior_pid)
            row=reducer(x,ledger=context);d2.validate_candidate_output(row);corrected.append(row)
        publication=dict(contract_id='V4_BOUNDED_PROFILE_D2_CORRECTION_R1',T0=day,rows=corrected,fact_manifest=correction,original=saved[day]['D2'],prewatch_calculations=calculations,AS_RECORDED=False,PIT_ELIGIBLE=False,publication_ready=False)
        prior_pid='V4_PROFILE_CORRECTED_D2:'+digest(publication);publication['publication_id']=prior_pid;prior={r['entity_id']:r for r in corrected}
        path=target_folder/(day+'.json');atomic_json(ROOT,path,publication);dated.append(dict(T0=day,source=ref(ROOT,path),rows=len(corrected),business_axis_changes=[dict(entity_id=r['entity_id'],changed_axes=[k for k in ('maturity','validity','health','tracking','scenario','final_eligibility','expiry_count','downgrade_count') if r.get(k)!=old_rows[r['entity_id']].get(k)]) for r in corrected if any(r.get(k)!=old_rows[r['entity_id']].get(k) for k in ('maturity','validity','health','tracking','scenario','final_eligibility','expiry_count','downgrade_count'))]))
    result=dict(contract_id='V4_BOUNDED_PROFILE_D2_CORRECTION_R2',acceptance='PASS_MATERIALIZATION_PENDING_INDEPENDENT_D2_ORACLE',candidate=preparation['candidate'],producer_source=ref(ROOT,producer_source),entities=len(ids),reducer_calls=sum(r['rows'] for r in dated),dates=dated,unchanged_core_profile_sector_period_producers_reexecuted=False,full_focus_reexecuted=False,native_pg_changed=False,publication=False,forward_acceptance='PENDING_BOUNDED_NATIVE_CORE_PATH_UPDATE',previous_preparation='R1 preserved, replaced only because unchanged field source IDs were unnecessarily rebound; no independent R1 numerical PASS existed')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],entities=len(ids),calls=result['reducer_calls'])))

if __name__=='__main__':main()

"""Update only changed native predicates; reuse all sealed price/settlement math."""
import copy,gzip,json,os
from decimal import Decimal
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_operational_owner_authority_v2 import load as load_owner,read as read_owner
from workbench_db.v4_profile_semantic_corrections_pg_v1 import load as load_patch
from focus_tracker.path_state_v2 import classify_stock_v2,STOCK_PRIORITY
from focus_tracker.predicates import Tri

def main():
    report=OUT/'BOUNDED_FORWARD_SEMANTIC_CORRECTION_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_BOUNDED_FORWARD_CORRECTION')
    material=json.loads((OUT/'BOUNDED_PROFILE_D2_CORRECTION_R6_R2.json').read_bytes());preparation=json.loads((OUT/'NATIVE_PROFILE_SEMANTIC_PREPARATION_R6_R1.json').read_bytes());scope=json.loads((OUT/'EXTENSION_CHANGED_SCOPE_SIX_DATES_R6_R1.json').read_bytes())
    candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());day=candidate['accepted_trade_date'];source=candidate['owners'][day]['forward'];projection=json.load(gzip.open(checked(ROOT,source),'rt',encoding='utf8'))
    d2_rows={d['T0']:{r['entity_id']:r for r in json.loads(checked(ROOT,d['source']).read_bytes())['rows']} for d in material['dates']}
    correction_values={(d['T0'],c['security_id']):c for d in scope['dates'] for c in d['corrections']}
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]];authority=load_owner(ROOT,candidate);patch_authority=load_patch(ROOT,candidate);cores={};patches=[];unavailable=[]
    for episode in projection['episodes']:
        sid=episode['entity_id']
        for observation in episode['observations']:
            t=observation['trade_date'];expected=correction_values.get((t,sid))
            if expected is None:continue
            native=observation['native_core_evidence'];path=observation['price_path'];row=d2_rows[t][sid]
            if native['status']=='UNAVAILABLE' and path['quality']=='DATA_UNAVAILABLE':
                if native['reason']!='ACTUAL_PRICE_PATH_NOT_READY' or native['facts']!={} or observation['path_resolution']!='UNAVAILABLE' or observation['path_state'] is not None:raise ValueError('UNAVAILABLE_BRANCH_CONSERVATION_REQUIRED')
                unavailable.append(dict(entity_id=sid,T0=t,episode_id=episode['episode_id'],reason=native['reason'],original_price_path=path,native_classification_not_executed=True,dependent_business_output_changed=False));continue
            if native['status']!='BOUND' or path['quality']!='READY':raise ValueError('CHANGED_NATIVE_FACT_UNAVAILABLE_REQUIRES_SEPARATE_SCOPE')
            if t not in cores:cores[t]={r['security_id']:r for r in read_owner(ROOT,authority,t,'core',candidate['owners'][t]['core'])}
            core=cores[t][sid]['fields'];facts=copy.deepcopy(native['facts'])
            if facts['ma20']!=core['ma20']['value'] or facts['r5']!=core['ret5']['value'] or facts['source_extended']!=expected['old_severe']:raise ValueError('FORWARD_NATIVE_UNCHANGED_INPUT_CONSERVATION')
            facts['source_extended']=expected['new_severe']
            inputs=dict(has_actual_bar=True,close=path['close'],drawdown_current=path['metrics']['drawdown_current'],mfe=path['metrics']['mfe'],launch_confirm={'TRUE':True,'FALSE':False}.get(row['raw_qualification'].get('CONFIRMED')),exited=episode['end_date'] is not None and t>=episode['end_date'],early_or_setup=observation['membership']=='EARLY',waiting_evaluable=True,**facts)
            invalidation={'INVALID':Tri.TRUE,'VALID':Tri.FALSE}.get(row['validity'],Tri.UNKNOWN)
            decision=classify_stock_v2(inputs,invalidation=invalidation,applicable=frozenset(STOCK_PRIORITY))
            evidence=dict(observation['predicate_evidence']);evidence['TOO_EXTENDED']='FALSE'
            if decision.predicate_evidence!=evidence:raise ValueError('FORWARD_UNCHANGED_PREDICATE_CONSERVATION')
            # Independent ordered priority scan, using previously verified
            # untouched predicates and exactly one changed false predicate.
            unresolved=[];best=None
            for name in STOCK_PRIORITY:
                if evidence[name]=='TRUE':best=name;break
                if evidence[name]=='UNKNOWN':unresolved.append(name)
            resolution=('PARTIAL' if unresolved else 'READY') if best else ('UNAVAILABLE' if unresolved else 'READY')
            if (decision.path_resolution,decision.best_confirmed_state,decision.resolved_primary_state,list(decision.higher_priority_unresolved))!=(resolution,best,best if resolution=='READY' else None,unresolved):raise ValueError('INDEPENDENT_CHANGED_PRIORITY_SCAN_FAILED')
            replacement=copy.deepcopy(observation);replacement['native_core_evidence']['facts']=facts;replacement['native_core_evidence']['source']=dict(native['source'],profile_semantic_correction=patch_authority['dates'][t]['source'])
            replacement.update(path_state=decision.resolved_primary_state,best_confirmed_state=decision.best_confirmed_state,path_resolution=decision.path_resolution,path_reason='HIGHER_PRIORITY_UNRESOLVED' if decision.higher_priority_unresolved else None,higher_priority_unresolved=list(decision.higher_priority_unresolved),predicate_evidence=decision.predicate_evidence)
            if replacement['price_path']!=observation['price_path']:raise ValueError('SEALED_PRICE_PATH_CHANGED')
            patches.append(dict(episode_id=episode['episode_id'],entity_id=sid,T0=t,original_observation=observation,replacement=replacement))
    if len(patches)+len(unavailable)!=2:raise ValueError('EXPECTED_TWO_AFFECTED_FORWARD_OBSERVATIONS')
    target=ROOT/'data/v4/profile_semantic_forward_corrections_v1'/preparation['candidate']['sha256']/'PATCH_R1.json'
    document=dict(contract_id='V4_BOUNDED_FORWARD_NATIVE_SEMANTIC_CORRECTION_R1',original_forward=source,original_candidate=preparation['candidate'],d2_sources=material['dates'],profile_correction_authority=candidate['native_profile_semantic_corrections'],rows=patches,unavailable_branches_preserved=unavailable,AS_RECORDED=False,PIT_ELIGIBLE=False,publication_ready=False)
    atomic_json(ROOT,target,document)
    result=dict(contract_id=document['contract_id'],acceptance='PASS_AFFECTED_BRANCH_CONSERVATION_ONLY',candidate=preparation['candidate'],patch=ref(ROOT,target),affected_observations=len(patches)+len(unavailable),changed_observations=len(patches),unavailable_observations_preserved=len(unavailable),changed_predicate_checks=len(patches),independent_priority_checks=4*len(patches),unchanged_price_paths_and_settlement_recomputed=False,unchanged_predicates_retested=False,unavailable_paths_preserved=True,native_pg_changed=False,publication=False,next='Native D0/D2 dependent patch authority and consumer readback. Original Forward business payload retained when both branches unavailable; do not fill facts or manufacture path PASS.')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],changed=len(patches))))

if __name__=='__main__':main()

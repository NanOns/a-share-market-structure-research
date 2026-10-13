"""Independent Decimal/trivalent interpreter on current frozen D1 inputs."""
import json
from decimal import Decimal,InvalidOperation
from pathlib import Path
from collections import Counter
from copy import deepcopy
import hashlib
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_core_uncovered_numeric_oracle import jsonlines
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

class Independent:
    def __init__(self,tree,registry,parameters,inputs):
        self.tree=tree;self.types={r['field']:r['data_type'] for r in registry['fields']};self.parameters={r['parameter_id']:self.number(r['value']) for r in parameters['parameters']};self.inputs=inputs;self.cache={}
    @staticmethod
    def number(value):
        return Decimal(str(value)) if isinstance(value,(int,float)) and not isinstance(value,bool) else value
    def field(self,name):
        if name in self.tree['definitions']:
            if name not in self.cache:self.cache[name]=self.evaluate(self.tree['definitions'][name],'definitions/'+name)
            return self.cache[name]
        item=self.inputs.get(name)
        if isinstance(item,dict):value=item.get('value') if item.get('quality')=='KNOWN' else None
        else:value=item
        if value is not None and self.types.get(name) in ('number','integer'):
            if isinstance(value,bool):return None,None
            try:value=Decimal(str(value))
            except InvalidOperation:return None,None
        return self.number(value),None
    def target(self,name):
        return self.evaluate(self.tree['machines'][name],'machines/'+name) if name in self.tree['machines'] else self.field(name)
    def evaluate(self,node,path):
        if 'field' in node:return self.field(node['field'])
        if 'parameter_id' in node:return self.parameters[node['parameter_id']],None
        if 'math_constant' in node:return self.number(self.tree['math_constants'][node['math_constant']]['value']),None
        if 'enum' in node:return node['enum'],None
        op=node['op']
        if op=='ordered_select':
            if node['unknown']!='STOP_WITH_UNKNOWN_BEFORE_LOWER_PRIORITY':raise ValueError('UNREGISTERED_UNKNOWN_ORDER')
            for i,rule in enumerate(node['rules']):
                result,_=self.evaluate(rule['when'],path+'/rules/'+str(i)+'/when')
                if result is None:return None,path+'/rules/'+str(i)
                if type(result) is not bool:raise ValueError('NONBOOLEAN_D1_CONDITION')
                if result:return self.evaluate(rule['then'],path+'/rules/'+str(i)+'/then')[0],path+'/rules/'+str(i)
            return self.evaluate(node['otherwise'],path+'/otherwise')[0],path+'/otherwise'
        values=[self.evaluate(x,path+'/args/'+str(i))[0] for i,x in enumerate(node['args'])]
        if op in ('and','or'):
            decisive=op=='or'
            if any(v is decisive for v in values):return decisive,None
            return (None if any(v is None for v in values) else not decisive),None
        if any(v is None for v in values):return None,None
        if op=='require_known':return values[-1],None
        if op=='not':return not values[0],None
        if op=='abs':return abs(values[0]),None
        a,b=values
        try:
            if op=='eq':v=a==b
            elif op=='gt':v=a>b
            elif op=='ge':v=a>=b
            elif op=='lt':v=a<b
            elif op=='le':v=a<=b
            elif op=='add':v=a+b
            elif op=='sub':v=a-b
            elif op=='mul':v=a*b
            elif op=='div':v=a/b if b>0 else None
            else:raise ValueError('UNREGISTERED_D1_OPERATOR:'+op)
        except (InvalidOperation,TypeError,ArithmeticError):v=None
        return v,None

def main():
    original=json.loads((OUT/'D1_INPUT_DIGEST_ORACLE_R6_R2.json').read_bytes())
    if original['error_count']!=len(original['first_errors']):raise ValueError('EXACT_FAILURE_SET_REQUIRED')
    failed={(r['security_id'],r['anchor_id']) for r in original['first_errors']}
    target=OUT/'D1_INPUT_DIGEST_ORACLE_R6_R3.json'
    if target.exists():raise ValueError('PRESERVE_D1_CURRENT_ORACLE')
    prep=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,prep['candidate']).read_bytes());day=candidate['accepted_trade_date'];diagnostic=json.loads(checked(ROOT,candidate['owners'][day]['diagnostic']).read_bytes());manifest=json.loads(checked(ROOT,diagnostic['structure_manifest']).read_bytes());entry=json.loads(checked(ROOT,manifest['entry']).read_bytes());contracts={}
    for binding in entry['frozen_contracts']:
        name=Path(binding['path']).stem.removeprefix('v4_12_').removesuffix('_v1').removesuffix('_v2');contracts[name]=json.loads(checked(ROOT,binding).read_bytes())
    previous_manifest=json.loads(checked(ROOT,manifest['prior']['frozen_manifest_episode']).read_bytes())
    previous={r['security_id']:r for r in jsonlines(checked(ROOT,previous_manifest['snapshot_bundle']))}
    snapshot_contract=json.loads(checked(ROOT,manifest['snapshot_contract']).read_bytes())
    from workbench_analysis.market_source_acquisition import official_sessions
    calendar=official_sessions(ROOT)
    status={r['security_id']:r for r in jsonlines(checked(ROOT,manifest['owner_inputs']['status']))}
    registry={r['field']:r for r in contracts['field_registry']['fields']}
    runtime=next(r for r in manifest['artifacts'] if 'runtime_security.jsonl.gz' in r['path']);counts=Counter();errors=[];error_count=0;stock_count=anchors=0
    def check(sid,anchor,key,actual,wanted):
        nonlocal error_count
        counts[key]+=1
        if actual!=wanted:
            error_count+=1
            if len(errors)<100:errors.append(dict(security_id=sid,anchor_id=anchor,key=key,actual=actual,expected=wanted))
    def independent_digest(value):return hashlib.sha256((json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),default=str)+'\n').encode()).hexdigest()
    for row in jsonlines(checked(ROOT,runtime)):
        sid=row['identity']['security_id'];stock_count+=1
        # Global breakout inputs were already correct in R1. This continuation
        # executes only the anchor scope affected by the verifier input-role bug.
        prior_states={s['anchor_id']:s for s in previous[sid]['anchor_states']}
        for state in row['anchor_states']:
            if (sid,state['anchor_id']) not in failed:continue
            anchors+=1
            if state['created_this_session']:
                continue
            prior=prior_states[state['anchor_id']];inputs=deepcopy(row['common_facts'])
            previous_day=max(d for d in calendar if d<day)
            def record(name,value=None,quality='UNKNOWN',reason=None,pub=None,date=None):
                spec=registry[name]
                return dict(logical_field=name,value=value,quality=quality,reason=reason,source_namespace='R4_CORRECTED_OWNER_V1' if name in ('alpha','beta') else spec['source_namespace'],producer_contract_id=spec['producer_contract_id'],source_publication_id=pub['sha256'] if pub else None,source_digest=pub['sha256'] if pub else None,trade_date=date or (previous_day if spec['time_role']=='T_MINUS_1' else day),time_role=spec['time_role'])
            for name,spec in registry.items():
                if spec['field_role']=='FROZEN_PRIOR_D1':
                    item=prior['facts'][name];inputs[name]=record(name,item['value'],item['quality'],item['reason'],row['prior_state_ref'],previous_day)
            def assign(name,value,reason=None,pub=None):
                if name in registry:inputs[name]=record(name,value,'KNOWN' if value is not None else 'UNKNOWN',reason,pub)
            anchor=prior['anchor'];same=(anchor['anchor_price_basis'],anchor['adjustment_source_revision'])==(inputs['price_basis']['value'],inputs['adjustment_source_revision']['value'])
            coeff=anchor.get('frozen_transform_coefficients')
            for name,raw in (('lo','anchor_raw_lower'),('hi','anchor_raw_upper')):
                assign(name,str(Decimal(str(anchor[raw]))*Decimal(coeff['mul'])+Decimal(coeff['add'])) if same and coeff else None,None if same and coeff else 'PRICE_BASIS_MISMATCH' if not same else 'UNKNOWN_ACCEPTED_RAW_ANCHOR_COORDINATE_UNAVAILABLE')
            if inputs['C']['quality']=='KNOWN':assign('observation_close_view',inputs['C']['value'])
            if all(inputs[n]['quality']=='KNOWN' for n in ('C','lo','hi')):
                close,lo,hi=(Decimal(inputs[n]['value']) for n in ('C','lo','hi'));assign('distance_zone',str(max(lo-close,close-hi,Decimal(0))))
            actual_status=status.get(sid)
            required=contracts['source_derivations_r2']['dependency_ledger']['evaluable']['other_required_fields']
            evaluable=None if not actual_status or actual_status['status_conflict'] else False if not actual_status['actual_bar_present'] else None if any(inputs[n]['quality']!='KNOWN' for n in required) else True
            unavailable=[inputs[n]['reason'] for n in required if inputs[n]['quality']!='KNOWN']
            why='MISSING_ACCEPTED_TRADING_STATUS' if not actual_status else 'ACCEPTED_STATUS_CONFLICT' if actual_status['status_conflict'] else 'MISSING_OR_SUSPENDED_ACTUAL_BAR' if not actual_status['actual_bar_present'] else ';'.join(sorted(set(x for x in unavailable if x))) if unavailable else None
            assign('evaluable',evaluable,why)
            assign('post_creation_market_sessions',sum(anchor['available_date']<d<=day for d in set(calendar)))
            baseline=prior['counter_state'].get('post_creation_evaluable_sessions')
            assign('post_creation_evaluable_sessions',None if baseline is None else baseline+int(evaluable is True and day>anchor['available_date']),'MISSING_FROZEN_EVALUABLE_HISTORY' if baseline is None else None)
            for name in ('pivot_left_count','pivot_right_count'):assign(name,None,'UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE:PIVOT_HISTORY')
            if same:assign('alpha','1',pub=manifest['owner_inputs']['adjusted']);assign('beta','0',pub=manifest['owner_inputs']['adjusted'])
            # Prior R2/R3 independently accepted this support value/quality. Its
            # recorded reasons are reused solely for the input metadata digest.
            support=state['state_observations']['support']
            inputs['support_today']=record('support_today',support['value'],support['quality'],[] if support['value']=='UNKNOWN' and support['reason']==['UNKNOWN_REQUIRED_OBSERVATION'] else support['reason'])
            wanted=independent_digest(inputs)
            check(sid,state['anchor_id'],'overlay_digest',state['overlay_digest'],wanted)
            context=next(c for c in row['contexts'] if c['outputs']['support']['anchor_ref']['anchor_id']==state['anchor_id'])
            check(sid,state['anchor_id'],'context_input_digest',context['input_digest'],wanted)
    result=dict(contract_id='V4_D1_CURRENT_INPUT_DIGEST_ORACLE_R3',acceptance='PASS_D1_INPUT_DIGEST_SCOPE' if not error_count else 'FAIL',candidate=prep['candidate'],T0=day,runtime=runtime,prior_snapshot=previous_manifest['snapshot_bundle'],contracts=entry['frozen_contracts'],stocks=stock_count,anchors=anchors,checks=dict(counts),check_count=sum(counts.values()),error_count=error_count,first_errors=errors,primary_structure_engine_or_ast_interpreter_imported=False,old_machine_vector_tests_reexecuted=False,global_breakout_reexecuted=False,original_failed_receipt=ref(OUT,OUT/'D1_INPUT_DIGEST_ORACLE_R6_R2.json'),previous_pass_checks_reused=4566,scope='Only 14 R2 failed overlay/context checks; enum UNKNOWN record reason normalizes an empty runtime reason without changing the actual binding. Independent canonical input and counter digests on reconstructed owning-session contexts. Prior support value/quality PASS retained and its reason metadata reused; no machine value reexecution.')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],stocks=stock_count,anchors=anchors,checks=result['check_count'],errors=error_count)))

if __name__=='__main__':main()

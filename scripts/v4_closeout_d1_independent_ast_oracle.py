"""Independent Decimal/trivalent interpreter on current frozen D1 inputs."""
import json
from decimal import Decimal,InvalidOperation
from pathlib import Path
from collections import Counter
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
            return self.evaluate(node['otherwise'],path+'/otherwise')
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
    target=OUT/'D1_CURRENT_INDEPENDENT_AST_ORACLE_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_D1_CURRENT_ORACLE')
    prep=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,prep['candidate']).read_bytes());day=candidate['accepted_trade_date'];diagnostic=json.loads(checked(ROOT,candidate['owners'][day]['diagnostic']).read_bytes());manifest=json.loads(checked(ROOT,diagnostic['structure_manifest']).read_bytes());entry=json.loads(checked(ROOT,manifest['entry']).read_bytes());contracts={}
    for binding in entry['frozen_contracts']:
        name=Path(binding['path']).stem.removeprefix('v4_12_').removesuffix('_v1').removesuffix('_v2');contracts[name]=json.loads(checked(ROOT,binding).read_bytes())
    runtime=next(r for r in manifest['artifacts'] if 'runtime_security.jsonl.gz' in r['path']);counts=Counter();errors=[];error_count=0;stock_count=anchors=0
    def compare(sid,anchor,machine,actual,expected,rule):
        nonlocal error_count
        value=str(expected) if isinstance(expected,Decimal) else expected;quality='UNKNOWN' if value is None or value=='UNKNOWN' else 'KNOWN'
        if machine=='retention' and value=='NOT_APPLICABLE':value=None;quality='NOT_APPLICABLE'
        for key,wanted in (('value',value),('quality',quality),('matched_rule_id',rule)):
            counts[key]+=1
            if actual.get(key)!=wanted:
                error_count+=1
                if len(errors)<100:errors.append(dict(security_id=sid,anchor_id=anchor,machine=machine,key=key,actual=actual.get(key),expected=wanted))
    for row in jsonlines(checked(ROOT,runtime)):
        sid=row['identity']['security_id'];stock_count+=1
        global_engine=Independent(contracts['machine_ast'],contracts['field_registry'],contracts['parameter_set'],row['breakout_input_bindings'])
        value,rule=global_engine.target('breakout');compare(sid,None,'breakout',row['global_state_observations']['breakout'],value,rule)
        for state in row['anchor_states']:
            anchors+=1;engine=Independent(contracts['machine_ast'],contracts['field_registry'],contracts['parameter_set'],state['facts'])
            for machine,actual in state['state_observations'].items():
                value,rule=engine.target('retention_value' if machine=='retention' else machine);compare(sid,state['anchor_id'],machine,actual,value,rule)
    result=dict(contract_id='V4_CURRENT_D1_INDEPENDENT_DECIMAL_AST_ORACLE_R1',acceptance='PASS_CURRENT_D1_AST_SCOPE' if not error_count else 'FAIL',candidate=prep['candidate'],T0=day,runtime=runtime,contracts=entry['frozen_contracts'],stocks=stock_count,anchors=anchors,checks=dict(counts),check_count=sum(counts.values()),error_count=error_count,first_errors=errors,primary_structure_engine_or_ast_interpreter_imported=False,old_machine_vector_tests_reexecuted=False,scope='All current global breakout and per-anchor state machines, exact values/quality/matched-rule identities on saved bound facts; coordinate/binder/counter/active-selector conservation remains separate')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],stocks=stock_count,anchors=anchors,checks=result['check_count'],errors=error_count)))

if __name__=='__main__':main()

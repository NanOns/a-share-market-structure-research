"""Pure frozen-expression runtime. No readers, detector thresholds or audit imports."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal,InvalidOperation
from typing import Any

@dataclass(frozen=True)
class Result:
    value: Any=None
    reasons: tuple[str,...]=()
    matched_rule_id: str|None=None
    @property
    def unknown(self):return self.value is None
    @property
    def quality(self):return 'UNKNOWN' if self.unknown or self.value=='UNKNOWN' else 'KNOWN'
    def record(self):
        value=str(self.value) if isinstance(self.value,Decimal) else self.value
        return dict(value=value,quality=self.quality,reason=list(self.reasons) or (['UNKNOWN_REQUIRED_OBSERVATION'] if self.value=='UNKNOWN' else []),matched_rule_id=self.matched_rule_id)

def missing(*reasons):return Result(None,tuple(sorted(set(reasons or ('MISSING_REQUIRED_FACT',)))))
def known(value):
    if value is None:return missing('MISSING_REQUIRED_FACT')
    if isinstance(value,(int,float,Decimal)) and not isinstance(value,bool):
        try:
            value=Decimal(str(value))
            if not value.is_finite():return missing('NONFINITE_INPUT')
        except InvalidOperation:return missing('INVALID_NUMERIC_INPUT')
    return Result(value)

class ASTEngine:
    def __init__(self,contracts,inputs):
        self.tree=contracts['machine_ast'];self.inputs=inputs;self.cache={};self.visiting=set()
        self.types={r['field']:r['data_type'] for r in contracts['field_registry']['fields']}
        self.parameters={r['parameter_id']:known(r['value']) for r in contracts['parameter_set']['parameters']}
    def field(self,name):
        if name in self.tree['definitions']:
            if name in self.visiting:raise ValueError('STOP_WITH_CONTRACT_GAP:AST_CYCLE')
            if name not in self.cache:
                self.visiting.add(name)
                try:self.cache[name]=self.evaluate(self.tree['definitions'][name],'definitions/'+name)
                finally:self.visiting.remove(name)
            return self.cache[name]
        value=self.inputs.get(name)
        if isinstance(value,Result):return value
        if isinstance(value,dict) and 'quality' in value:
            if value['quality']!='KNOWN':
                reasons=value.get('reason') or 'MISSING_REQUIRED_FACT:'+name
                return missing(*(reasons if isinstance(reasons,list) else [reasons]))
            value=value.get('value')
        if value is not None and self.types.get(name) in ['number','integer']:
            try:return known(Decimal(str(value))) if not isinstance(value,bool) else missing('INVALID_NUMERIC_INPUT:'+name)
            except InvalidOperation:return missing('INVALID_NUMERIC_INPUT:'+name)
        return known(value) if value is not None else missing('MISSING_REQUIRED_FACT:'+name)
    def target(self,name):
        if name in self.tree['machines']:return self.evaluate(self.tree['machines'][name],'machines/'+name)
        return self.field(name)
    def evaluate(self,node,path):
        if 'field' in node:return self.field(node['field'])
        if 'parameter_id' in node:return self.parameters[node['parameter_id']]
        if 'math_constant' in node:return known(self.tree['math_constants'][node['math_constant']]['value'])
        if 'enum' in node:return known(node['enum'])
        op=node['op']
        if op=='ordered_select':
            if node['unknown']!='STOP_WITH_UNKNOWN_BEFORE_LOWER_PRIORITY':raise ValueError('STOP_WITH_CONTRACT_GAP:UNKNOWN_POLICY')
            for index,rule in enumerate(node['rules']):
                condition=self.evaluate(rule['when'],path+'/rules/'+str(index)+'/when')
                if condition.unknown:return Result(None,condition.reasons,path+'/rules/'+str(index))
                if not isinstance(condition.value,bool):return missing('INVALID_PREDICATE:'+path)
                if condition.value:
                    result=self.evaluate(rule['then'],path+'/rules/'+str(index)+'/then')
                    return Result(result.value,result.reasons,path+'/rules/'+str(index))
            result=self.evaluate(node['otherwise'],path+'/otherwise')
            return Result(result.value,result.reasons,path+'/otherwise')
        args=[self.evaluate(n,path+'/args/'+str(i)) for i,n in enumerate(node['args'])]
        reasons=tuple(sorted({r for a in args for r in a.reasons}))
        if op in ['and','or']:
            if any(not a.unknown and not isinstance(a.value,bool) for a in args):return missing('INVALID_BOOLEAN_OPERAND:'+path)
            decisive=False if op=='and' else True
            if any(not a.unknown and a.value is decisive for a in args):return known(decisive)
            return missing(*reasons) if any(a.unknown for a in args) else known(not decisive)
        if any(a.unknown for a in args):return missing(*reasons)
        values=[a.value for a in args]
        if op=='require_known':return args[-1]
        if op=='not':return known(not values[0]) if isinstance(values[0],bool) else missing('INVALID_BOOLEAN_OPERAND:'+path)
        try:
            if op=='abs':return known(abs(values[0]))
            a,b=values
            if op=='eq':return known(a==b)
            if op in ['gt','ge','lt','le']:return known({'gt':lambda:a>b,'ge':lambda:a>=b,'lt':lambda:a<b,'le':lambda:a<=b}[op]())
            if op=='add':return known(a+b)
            if op=='sub':return known(a-b)
            if op=='mul':return known(a*b)
            if op=='div':return missing('NONPOSITIVE_DENOMINATOR') if b<=0 else known(a/b)
        except (TypeError,InvalidOperation,ArithmeticError):return missing('INVALID_OPERAND:'+path)
        raise ValueError('STOP_WITH_CONTRACT_GAP:UNSUPPORTED_OP:'+op)

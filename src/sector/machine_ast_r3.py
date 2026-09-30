"""Serializable four-state rule AST interpreter; no production authorization."""
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

NOT_APPLICABLE = 'NOT_APPLICABLE'

@dataclass(frozen=True)
class Evaluation:
    state: bool | None | str
    reason_code: str | None = None

def ast_digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate_ast(rules, fields, parameters):
    seen=set()
    def walk(node, stack):
        if not isinstance(node,dict):raise ValueError('canonical AST node must be an object')
        op=node.get('operator')
        if op in ('AND','OR'):
            if not node.get('children'):raise ValueError('empty logical node')
            for child in node['children']:walk(child,stack)
        elif op=='REF':
            ref=node['rule_id']
            if ref not in rules or ref in stack:raise ValueError('missing or cyclic rule reference')
            walk(rules[ref],stack|{ref})
        elif op=='NOT_APPLICABLE_IF':
            if node.get('then_state') != NOT_APPLICABLE or 'else' not in node or 'condition' not in node:
                raise ValueError('invalid NOT_APPLICABLE_IF node')
            walk(node['condition'],stack)
            walk(node['else'],stack)
        else:
            if op not in ('EQ','GT','GTE','LT','LTE','IN'):raise ValueError('unsupported AST comparison')
            required={'field_id','producer','time_role','quality_requirement','unknown_behavior'}
            if not required<=node.keys() or node['unknown_behavior']!='UNKNOWN':raise ValueError('unbound AST leaf')
            field=fields.get(node['field_id'])
            if not field or field['producer']!=node['producer'] or field['time_role']!=node['time_role']:raise ValueError('field producer/time role mismatch')
            if ('parameter_id' in node)==('constant' in node):raise ValueError('exactly one parameter or constant required')
            if 'parameter_id' in node and node['parameter_id'] not in parameters:raise ValueError('unregistered parameter')
    for key in rules:walk(rules[key],{key});seen.add(key)
    return {'status':'PASS','rule_count':len(seen)}

def evaluate_ast_explain(rule_id: str, rules: Mapping, facts: Mapping, parameters: Mapping) -> Evaluation:
    def ev(node):
        op=node['operator']
        if op=='REF':return ev(rules[node['rule_id']])
        if op=='NOT_APPLICABLE_IF':
            condition=ev(node['condition'])
            if condition.state is None:return Evaluation(None,'NOT_APPLICABLE_GUARD_UNKNOWN')
            if condition.state is NOT_APPLICABLE:return Evaluation(None,'NOT_APPLICABLE_GUARD_UNAVAILABLE')
            return Evaluation(NOT_APPLICABLE,'STRONG_PREV_EMPTY') if condition.state is True else ev(node['else'])
        if op in ('AND','OR'):
            values=[ev(x) for x in node['children']]
            states=[x.state for x in values]
            if op=='AND':
                if False in states:return Evaluation(False,'REQUIRED_BRANCH_FALSE')
                if None in states:return Evaluation(None,next(x.reason_code for x in values if x.state is None))
                if states and all(x is NOT_APPLICABLE for x in states):return Evaluation(NOT_APPLICABLE,'ALL_REQUIRED_BRANCHES_NOT_APPLICABLE')
                return Evaluation(True,'NOT_APPLICABLE_BRANCH_SKIPPED' if NOT_APPLICABLE in states else None)
            if True in states:return Evaluation(True)
            if None in states:return Evaluation(None,next(x.reason_code for x in values if x.state is None))
            if states and all(x is NOT_APPLICABLE for x in states):return Evaluation(None,'NO_USABLE_RETENTION_BRANCH')
            return Evaluation(False,'NOT_APPLICABLE_BRANCH_SKIPPED' if NOT_APPLICABLE in states else None)
        entry=facts.get(node['field_id'])
        if not entry:return Evaluation(None,'MISSING_REQUIRED_INPUT')
        if entry.get('producer')!=node['producer'] or entry.get('time_role')!=node['time_role']:return Evaluation(None,'PRODUCER_OR_TIME_ROLE_MISMATCH')
        if entry.get('quality')==NOT_APPLICABLE or entry.get('value')==NOT_APPLICABLE:
            return Evaluation(NOT_APPLICABLE,entry.get('reason_code') or 'INPUT_NOT_APPLICABLE')
        if entry.get('quality') not in node['quality_requirement']:return Evaluation(None,'REQUIRED_QUALITY_UNAVAILABLE')
        value=entry.get('value');rhs=parameters.get(node['parameter_id']) if 'parameter_id' in node else node['constant']
        if value is None or rhs is None:return Evaluation(None,'REQUIRED_VALUE_UNKNOWN')
        try:
            if op=='EQ':result=value==rhs
            elif op=='IN':result=value in rhs
            elif op=='GT':result=value>rhs
            elif op=='GTE':result=value>=rhs
            elif op=='LT':result=value<rhs
            elif op=='LTE':result=value<=rhs
            else:return Evaluation(None,'UNSUPPORTED_OPERATOR')
            return Evaluation(result)
        except (TypeError,ValueError):return Evaluation(None,'INCOMPARABLE_VALUE_UNKNOWN')
    return ev(rules[rule_id])

def evaluate_ast(rule_id: str, rules: Mapping, facts: Mapping, parameters: Mapping):
    """Evaluate to True, False, None (UNKNOWN), or the explicit N/A value."""
    return evaluate_ast_explain(rule_id,rules,facts,parameters).state

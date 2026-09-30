"""Serializable three-valued rule AST interpreter; no production authorization."""
import hashlib
import json
from typing import Any, Mapping

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

def evaluate_ast(rule_id: str, rules: Mapping, facts: Mapping, parameters: Mapping):
    def ev(node):
        op=node['operator']
        if op=='REF':return ev(rules[node['rule_id']])
        if op in ('AND','OR'):
            values=[ev(x) for x in node['children']]
            if op=='AND':return False if False in values else None if None in values else True
            return True if True in values else None if None in values else False
        entry=facts.get(node['field_id'])
        if not entry or entry.get('quality') not in node['quality_requirement'] or entry.get('producer')!=node['producer'] or entry.get('time_role')!=node['time_role']:return None
        value=entry.get('value');rhs=parameters.get(node['parameter_id']) if 'parameter_id' in node else node['constant']
        if value is None or value=='NOT_APPLICABLE' or rhs is None:return None
        try:
            if op=='EQ':return value==rhs
            if op=='IN':return value in rhs
            if op=='GT':return value>rhs
            if op=='GTE':return value>=rhs
            if op=='LT':return value<rhs
            if op=='LTE':return value<=rhs
        except (TypeError,ValueError):return None
    return ev(rules[rule_id])

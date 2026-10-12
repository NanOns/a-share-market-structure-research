"""Separate historical accepted sources from versioned closeout runtime sources.

No accepted Head or original algorithm file is replaced. Candidate packaging
requires exact bytes for both the upstream version and the bounded repair.
"""
import hashlib,json
from pathlib import Path
CONTRACT='V4_CLOSEOUT_RUNTIME_SOURCE_BINDINGS_R1'
AUTHORITY='config/v4_closeout_runtime_source_authority_r1.json'
REPAIRS={'src/workbench_analysis/r43_focus_replay.py','src/workbench_analysis/r43_owner_replay.py','src/workbench_analysis/operational_owner_adapter_v1.py'}
def checked(root,binding):
    root=Path(root).resolve();path=(root/binding['path']).resolve()
    if not path.is_relative_to(root):raise ValueError('CLOSEOUT_RUNTIME_SOURCE_PATH_ESCAPE')
    raw=path.read_bytes()
    if len(raw)!=binding['bytes'] or hashlib.sha256(raw).hexdigest()!=binding['sha256']:raise ValueError('CLOSEOUT_RUNTIME_SOURCE_EXACT_BYTES_REQUIRED')
    return path
def admitted(root):
    root=Path(root).resolve();path=root/AUTHORITY
    if not path.exists():return {}
    document=json.loads(path.read_bytes())
    if document.get('contract_id')!=CONTRACT or document.get('scope')!='BOUNDED_NATIVE_PG_ADAPTER_AND_CORRECTED_FOCUS_ONLY':raise ValueError('CLOSEOUT_RUNTIME_SOURCE_CONTRACT_REQUIRED')
    if document.get('production_acceptance') is not False or document.get('general_algorithm_upgrade_permission') is not False or document.get('historical_PIT_permission') is not False or document.get('automated_trading_permission') is not False:raise ValueError('CLOSEOUT_RUNTIME_SOURCE_SCOPE_ESCALATION')
    checked(root,document['task_card']);checked(root,document['user_scope_amendment'])
    policy=json.loads((root/'config/read_only_operational_daily_release_policy_v1_1.json').read_bytes())
    accepted={b['path']:b for b in policy['accepted_algorithm_bindings']}
    rows=document['repairs']
    if {r['module_path'] for r in rows}!=REPAIRS or len(rows)!=len(REPAIRS):raise ValueError('CLOSEOUT_RUNTIME_SOURCE_REPAIR_SET_REQUIRED')
    result={}
    for row in rows:
        original=accepted[row['module_path']]
        if row['upstream']['sha256']!=original['sha256'] or row['upstream']['bytes']!=original['bytes']:raise ValueError('CLOSEOUT_UPSTREAM_ACCEPTED_IDENTITY_REQUIRED')
        checked(root,row['upstream']);checked(root,row['runtime'])
        if row['runtime']['sha256']==row['upstream']['sha256']:raise ValueError('CLOSEOUT_DISTINCT_RUNTIME_VERSION_REQUIRED')
        result[row['module_path']]=row
    return result

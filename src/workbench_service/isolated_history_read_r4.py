"""Explicit isolated native history authority; never publishes accepted heads."""
from pathlib import Path
import hashlib,json
from workbench_analysis.r43_owner_replay import checked
from workbench_db.v4_native import workspace_schema
from workbench_db.v4_history_pg_r1 import CONTRACT

CONTEXT='R4_ISOLATED_DATED_HISTORY_READ_R1'

def load(api,path):
    path=Path(path).resolve();path.relative_to(Path('G:/codex_tmp/full_system_r4_fbd23a6b').resolve())
    value=json.loads(path.read_bytes())
    if value.get('contract_id')!=CONTEXT or value.get('production_accepted') is not False:raise ValueError('ISOLATED_HISTORY_CONTRACT_REQUIRED')
    if value.get('source_root')!=str(api.root.resolve()) or value.get('head_token')!=api.token:raise ValueError('ISOLATED_HISTORY_HEAD_MISMATCH')
    index_root=Path(value['index_root']).resolve();index_root.relative_to(Path('G:/codex_tmp/full_system_r4_fbd23a6b').resolve())
    for day,entry in value['dates'].items():
        if day not in api.candidate['published_sessions']:raise ValueError('ISOLATED_HISTORY_DATE_NOT_ADMITTED')
        binding=entry['history_index'];source=entry['source_binding']
        checked(api.root,source)
        if binding.get('contract_id')!=CONTRACT or binding.get('engine')!='postgresql' or binding.get('schema')!=workspace_schema(index_root,'history') or binding.get('T0')!=day or binding.get('head_token')!=api.token or binding.get('source_digest')!=source['sha256']:raise ValueError('ISOLATED_HISTORY_BINDING_MISMATCH')
    return value,index_root,hashlib.sha256(path.read_bytes()).hexdigest()

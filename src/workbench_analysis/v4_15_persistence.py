"""Dedicated append-only V4-15 engineering artifact namespace."""
import json,re
from pathlib import Path
from .v4_14_replay_io import digest

class Store:
    def __init__(self,root,namespace='reports/v4_15_runtime_r20'):
        self.root=Path(root).resolve(); self.namespace=Path(namespace).as_posix()
        p=self.root/self.namespace
        if Path(namespace).is_absolute() or '..' in Path(namespace).parts or not (self.namespace=='reports/v4_15_runtime_r20' or self.namespace.startswith('reports/v4_15_runtime_r20/')):
            raise ValueError('V4_15_ENGINEERING_NAMESPACE_REQUIRED')
        if not p.resolve().is_relative_to(self.root):raise ValueError('NAMESPACE_ESCAPE')
        from workbench_db.v4_forward_pg_r1 import ForwardFactStore
        self.pg=ForwardFactStore(self.root,self.root/'data/v4/v4_15_runtime_pg_r1')
    def append(self,kind,identity,payload):
        if not re.fullmatch('[a-z][a-z0-9_]*',kind):raise ValueError('INVALID_ARTIFACT_KIND')
        key=identity if re.fullmatch('[0-9a-f]{64}',str(identity)) else digest(identity)
        value=dict(contract_id='V4_15_APPEND_ONLY_RUNTIME_FACT_V1',namespace=self.namespace,
                   artifact_kind=kind,artifact_key=key,payload=payload)
        return self.pg.append('v4_15_'+kind,key,value,migration_timeout_seconds=120)
    def read(self,binding):
        value=self.pg.read(binding)
        if value.get('contract_id')!='V4_15_APPEND_ONLY_RUNTIME_FACT_V1' or value.get('namespace')!=self.namespace:
            raise ValueError('V4_15_PG_RUNTIME_FACT_AUTHORITY_MISMATCH')
        return value['payload']
    def refs(self,kind):
        if not re.fullmatch('[a-z][a-z0-9_]*',kind):raise ValueError('INVALID_ARTIFACT_KIND')
        return self.pg.refs('v4_15_'+kind)

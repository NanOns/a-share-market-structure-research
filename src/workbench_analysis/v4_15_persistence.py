"""Dedicated append-only V4-15 engineering artifact namespace."""
import json,re
from pathlib import Path
from .v4_14_replay_io import publish,exact,ref,digest

class Store:
    def __init__(self,root,namespace='reports/v4_15_runtime_r20'):
        self.root=Path(root).resolve(); self.namespace=Path(namespace).as_posix()
        p=self.root/self.namespace
        if Path(namespace).is_absolute() or '..' in Path(namespace).parts or not (self.namespace=='reports/v4_15_runtime_r20' or self.namespace.startswith('reports/v4_15_runtime_r20/')):
            raise ValueError('V4_15_ENGINEERING_NAMESPACE_REQUIRED')
        if not p.resolve().is_relative_to(self.root):raise ValueError('NAMESPACE_ESCAPE')
    def append(self,kind,identity,payload):
        if not re.fullmatch('[a-z][a-z0-9_]*',kind):raise ValueError('INVALID_ARTIFACT_KIND')
        key=identity if re.fullmatch('[0-9a-f]{64}',str(identity)) else digest(identity)
        return publish(self.root,f'{self.namespace}/{kind}/{key}.json',payload)
    def read(self,binding):return json.loads(exact(self.root,binding))
    def refs(self,kind):
        if not re.fullmatch('[a-z][a-z0-9_]*',kind):raise ValueError('INVALID_ARTIFACT_KIND')
        return [ref(self.root,p.relative_to(self.root).as_posix()) for p in sorted((self.root/self.namespace/kind).glob('*.json'))]

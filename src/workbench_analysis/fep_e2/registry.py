"""Append-only atomic local registry, deliberately independent of Core/E1 writes."""
import json
import os
import tempfile
from pathlib import Path
from workbench_analysis.fep_e1.contracts import digest


def register(directory, artifact):
    directory = Path(directory).resolve()
    if not str(directory).lower().startswith(('e:\\', 'f:\\')):
        raise ValueError('E2_ENGINEERING_STORAGE_REQUIRED')
    payload = {k:v for k,v in artifact.items() if k not in ('logical_digest','artifact_id','created_at')}
    if digest(payload) != artifact['logical_digest'] or artifact['artifact_id'] != 'FEP_E2:'+digest(payload):
        raise ValueError('E2_ARTIFACT_DIGEST')
    directory.mkdir(parents=True,exist_ok=True)
    path = directory/(artifact['logical_digest']+'.json')
    raw = (json.dumps(artifact,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    descriptor,temporary = tempfile.mkstemp(dir=directory,suffix='.tmp')
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(temporary,path)  # Atomic exclusive publication; never overwrite.
        except FileExistsError:
            old=json.loads(path.read_bytes())
            if {k:v for k,v in old.items() if k != 'created_at'} != {k:v for k,v in artifact.items() if k != 'created_at'}:
                raise ValueError('E2_REGISTRY_COLLISION')
    finally:
        os.unlink(temporary)
    return path

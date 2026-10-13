"""Exact archived bytes prepared from Git; no runtime Git or new authority."""
import json,hashlib
from pathlib import Path
from .v4_13_io import exact

CONTRACT='V4_PORTABLE_EXACT_HISTORICAL_ARCHIVE_WITNESS_R1'
PATH='config/v4_portable_historical_archive_witness_r1.json'
BOOK='config/v4_corrected_historical_archives_v1.json'

def resolve(root,binding):
    root=Path(root).resolve();manifest=json.loads((root/PATH).read_bytes())
    if manifest.get('contract_id')!=CONTRACT or manifest.get('authority_granted') is not False:
        raise ValueError('PORTABLE_ARCHIVE_WITNESS_CONTRACT_REQUIRED')
    if manifest['registry_binding']['path']!=BOOK:raise ValueError('PORTABLE_ARCHIVE_EXACT_REGISTRY_REQUIRED')
    registry=json.loads(exact(root,manifest['registry_binding']))
    row=next((r for r in registry['entries'] if r['original']==binding),None)
    witness=next((r for r in manifest['entries'] if r['original']==binding),None)
    if row is None or witness is None:raise ValueError('UNREGISTERED_PORTABLE_ARCHIVE_IDENTITY')
    if any(witness[k]!=row[k] for k in ('original','archive','source_commit')):
        raise ValueError('PORTABLE_ARCHIVE_ORIGINAL_IDENTITY_CHANGED')
    raw=exact(root,row['archive'])
    digest=hashlib.sha256(raw).hexdigest()
    sizes=[binding[k] for k in ('bytes','byte_count') if k in binding]
    if not sizes or any(len(raw)!=n for n in sizes) or digest!=binding['sha256'] or witness['verified_git_blob_sha256']!=digest:
        raise ValueError('PORTABLE_ARCHIVE_NOT_EXACT_ORIGINAL_BYTES')
    return root/row['archive']['path']

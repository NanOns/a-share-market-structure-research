"""Append-only scoped engineering publication with exact fresh-process readback."""
from pathlib import Path
import gzip
import json
import re
from .v4_13_io import canonical,digest,atomic,exact,rows
from datetime import date


def publication_prefix(root,namespace,trade_date,revision):
    if not all(isinstance(v,str) for v in [namespace,trade_date,revision]) or not re.fullmatch(r'[A-Za-z0-9_-]+',namespace) or not re.fullmatch(r'r[1-9][0-9]*',revision) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',trade_date):raise ValueError('INVALID_PUBLICATION_IDENTITY')
    try:date.fromisoformat(trade_date)
    except ValueError:raise ValueError('INVALID_PUBLICATION_IDENTITY') from None
    prefix=f'reports/v4_13_runtime_r16/{namespace}/{trade_date}/{revision}/'
    if not (Path(root)/prefix).resolve().is_relative_to(Path(root).resolve()):raise ValueError('WRITE_PATH_OUTSIDE_REPOSITORY')
    return prefix


def publish(root, namespace, trade_date, revision, profiles, contexts, metadata):
    prefix=publication_prefix(root,namespace,trade_date,revision)
    profiles=sorted(profiles,key=lambda r:r['security_id']);contexts=sorted(contexts,key=lambda r:(r['security_id'],r['sector_id']))
    if len({r['security_id'] for r in profiles})!=len(profiles):raise ValueError('DUPLICATE_PROFILE_IDENTITY')
    if any(r['trade_date']!=trade_date or r['revision']!=revision for r in profiles+contexts):raise ValueError('PUBLICATION_ROW_IDENTITY_MISMATCH')
    artifacts=[]
    for name,items in [('profile_advanced',profiles),('loo_context',contexts)]:
        payload=b''.join(canonical(r)+b'\n' for r in items)
        binding=atomic(root,prefix+name+'.jsonl.gz',gzip.compress(payload,mtime=0),append_only=True)
        artifacts.append(binding)
    for name,obj in [('source_refs',metadata['source_refs']),('diagnostics',metadata['diagnostics'])]:artifacts.append(atomic(root,prefix+name+'.json',canonical(obj),append_only=True))
    manifest=dict(contract_id='V4_13_R16_SCOPED_PUBLICATION_V1',trade_date=trade_date,revision=revision,profile_count=len(profiles),context_count=len(contexts),artifacts=artifacts,**{k:v for k,v in metadata.items() if k not in ['source_refs','diagnostics']},knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False)
    # Immutable per-revision index; no mutable "latest" directory or pointer.
    index=dict(trade_date=trade_date,revision=revision,input_identity=digest(metadata),artifact_refs=artifacts)
    manifest['publication_index']=atomic(root,prefix+'publication_index.json',canonical(index),append_only=True)
    return atomic(root,prefix+'manifest.json',canonical(manifest),append_only=True)


def readback(root, manifest_ref, collect=True):
    manifest=json.loads(exact(root,manifest_ref));exact(root,manifest['publication_index'])
    result={}
    for binding in manifest['artifacts']:
        name=Path(binding['path']).name.split('.')[0]
        if binding['path'].endswith('.jsonl.gz'):
            values=[];count=0
            for row in rows(root,binding):
                if row['trade_date']!=manifest['trade_date'] or row['revision']!=manifest['revision']:raise ValueError('READBACK_REVISION_MISMATCH')
                count+=1
                if collect:values.append(row)
            result[name]=values if collect else count
        else:result[name]=json.loads(exact(root,binding))
    for name,key in [('profile_advanced','profile_count'),('loo_context','context_count')]:
        count=len(result[name]) if collect else result[name]
        if count!=manifest[key]:raise ValueError('PUBLICATION_COUNT_MISMATCH')
    result['manifest']=manifest;return result


def publish_stream(root,namespace,trade_date,revision,records,metadata):
    """Bounded memory, deterministic gzip; immutable manifest is the completion seal."""
    import tempfile,os
    prefix=publication_prefix(root,namespace,trade_date,revision)
    target=Path(root)/prefix;target.mkdir(parents=True,exist_ok=True)
    counts={'profile_advanced':0,'loo_context':0};artifacts=[];last=None
    with tempfile.TemporaryDirectory(prefix='.stream-',dir=target) as tmp:
        paths={n:Path(tmp)/(n+'.gz') for n in counts}
        streams={n:gzip.GzipFile(filename='',fileobj=open(p,'wb'),mode='wb',mtime=0) for n,p in paths.items()}
        try:
            for profile,contexts in records:
                sid=profile['security_id']
                if last is not None and sid<=last:raise ValueError('NON_DETERMINISTIC_OR_DUPLICATE_SECURITY_ORDER')
                last=sid
                for name,items in [('profile_advanced',[profile]),('loo_context',sorted(contexts,key=lambda r:r['sector_id']))]:
                    for row in items:
                        if row['trade_date']!=trade_date or row['revision']!=revision:raise ValueError('PUBLICATION_ROW_IDENTITY_MISMATCH')
                        streams[name].write(canonical(row)+b'\n');counts[name]+=1
        finally:
            for stream in streams.values():
                raw=stream.fileobj;stream.close();raw.close()
        for name,p in paths.items():artifacts.append(atomic(root,prefix+name+'.jsonl.gz',p.read_bytes(),append_only=True))
    for name,obj in [('source_refs',metadata['source_refs']),('diagnostics',metadata['diagnostics'])]:artifacts.append(atomic(root,prefix+name+'.json',canonical(obj),append_only=True))
    index=atomic(root,prefix+'publication_index.json',canonical(dict(trade_date=trade_date,revision=revision,input_identity=digest(metadata),artifact_refs=artifacts)),append_only=True)
    manifest=dict(contract_id='V4_13_R16_SCOPED_PUBLICATION_V1',trade_date=trade_date,revision=revision,profile_count=counts['profile_advanced'],context_count=counts['loo_context'],artifacts=artifacts,publication_index=index,**{k:v for k,v in metadata.items() if k not in ['source_refs','diagnostics']},knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False)
    return atomic(root,prefix+'manifest.json',canonical(manifest),append_only=True)

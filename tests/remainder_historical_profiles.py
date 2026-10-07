"""Pinned Git historical fixtures and named accepted byte compatibility; no head fallback."""
import json,subprocess,os,threading,hashlib
from tests.final_disposable_paths import resolve_destination_inside_root
from functools import lru_cache
from pathlib import Path,PureWindowsPath
from scripts.full_chain_repair_io import ROOT as REPOSITORY
BASE=Path('G:/codex_tmp/test_temp')
_LOCK=threading.RLock()
_REPRESENTATIONS={}
@lru_cache(maxsize=None)
def profile(commit):
    out=resolve_destination_inside_root(BASE,'remainder_frozen_v5_'+commit[:12])
    if not (out/'.git').exists():
        out.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','init',str(out)],check=True,stdout=subprocess.DEVNULL)
        (out/'.git/objects/info/alternates').write_bytes(((REPOSITORY/'.git/objects').as_posix()+'\n').encode())
        subprocess.run(['git','-C',str(out),'config','core.longpaths','true'],check=True)
        subprocess.run(['git','-C',str(out),'read-tree',commit],check=True)
        names=subprocess.check_output(['git','-C',str(out),'ls-files','-z'])
        subprocess.run(['git','-C',str(out),'update-index','--skip-worktree','-z','--stdin'],input=names,check=True)
        subprocess.run(['git','-C',str(out),'update-ref','--no-deref','HEAD',commit],check=True)
    subprocess.run(['git','-C',str(out),'config','core.autocrlf','true'],check=True)
    refs=subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/remotes/','refs/tags/'],cwd=REPOSITORY,text=True)
    for line in refs.splitlines():
        name,oid=line.split();subprocess.run(['git','update-ref',name,oid],cwd=out,check=True)
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=out,text=True).strip()==commit
    raw=subprocess.check_output(['git','ls-tree','-r','-z',commit],cwd=out)
    entries={}
    for record in raw.split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1);mode,kind,oid=metadata.split()
        if kind==b'blob':
            path=name.decode('utf8');win=PureWindowsPath(path)
            if win.drive or win.root or '..' in win.parts:raise ValueError('HISTORICAL_GIT_PATH_ESCAPE')
            entries[path]=oid.decode()
    representations={}
    manifest='reports/r19a/PROTECTED_WORKTREE_BYTES.json'
    if manifest in entries and commit=='2020234020e09020aca13fd84cdabde6fbb81f50':
        values=json.loads(subprocess.check_output(['git','cat-file','blob',entries[manifest]],cwd=out))
        representations={path:ref for path,ref in values.items() if path in entries}
        package='config/v4_15_contract_package_v1.json'
        if package in entries:
            def declared(value):
                if isinstance(value,dict):
                    if value.get('path') in entries and 'sha256' in value and 'bytes' in value:representations[value['path']]=value
                    for child in value.values():declared(child)
                elif isinstance(value,list):
                    for child in value:declared(child)
            declared(json.loads(subprocess.check_output(['git','cat-file','blob',entries[package]],cwd=out)))
    protected='reports/pre16_governance_r1_1/PROTECTED_BYTES.json'
    if protected in entries:
        catalog=json.loads(subprocess.check_output(['git','cat-file','blob',entries[protected]],cwd=out))
        for ref in catalog['bindings']:
            if ref['path'] in entries:representations[ref['path']]=ref
    if commit=='f8614fa0614820a7edd5f58ad4a7feed23c11d64':
        manifest='reports/v4_12_runtime_r11/a_persisted_chain_synthetic/2026-09-29/r1/frozen_d1_manifest.json'
        value=json.loads(subprocess.check_output(['git','cat-file','blob',entries[manifest]],cwd=out))
        ref=value['snapshot_contract']
        if ref['path'] not in entries:raise ValueError('R11_DECLARED_SNAPSHOT_CONTRACT_MISSING')
        representations[ref['path']]=ref
    _REPRESENTATIONS[out]=representations
    registry='data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json'
    if registry not in entries:
        # The already accepted path-specific portability contract is an explicit
        # compatibility fixture, not a stage/head replacement or permission grant.
        raw=subprocess.check_output(['git','show','433c3378d4bc4db572f95de20cadbf899c2a04ce:'+registry],cwd=REPOSITORY)
        target=resolve_destination_inside_root(out,registry);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
    selected=[name for name in entries if name.startswith(('config/','src/','scripts/','migrations/')) or (name.startswith('data/v4/') and name.count('/')==2 and name.endswith('.json'))]
    batch=subprocess.check_output(['git','cat-file','--batch'],cwd=out,input=('\n'.join(entries[name] for name in selected)+'\n').encode())
    offset=0
    for name in selected:
        end=batch.index(b'\n',offset);header=batch[offset:end].split();size=int(header[2]);raw=batch[end+1:end+1+size];offset=end+size+2
        if header[:2]!=[entries[name].encode(),b'blob']:raise ValueError('HISTORICAL_BATCH_IDENTITY')
        ref=representations.get(name)
        if ref:
            options=[raw,raw.replace(b'\r\n',b'\n'),raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
            raw=next((x for x in options if len(x)==ref['bytes'] and hashlib.sha256(x).hexdigest()==ref['sha256']),None)
            if raw is None:raise ValueError('PINNED_DECLARED_REPRESENTATION_UNRECOVERABLE')
        target=resolve_destination_inside_root(out,name)
        if target.is_file():
            if target.read_bytes()!=raw:raise ValueError('HISTORICAL_PROFILE_EXISTING_BYTES_CHANGED')
        else:
            target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.batch.tmp');temp.write_bytes(raw);os.replace(temp,target)
    present=[name for name in entries if (out/name).is_file()]
    if present:subprocess.run(['git','-C',str(out),'update-index','--no-skip-worktree','-z','--stdin'],input=('\0'.join(present)+'\0').encode(),check=True)
    return out,entries

def install(monkeypatch,out,entries):
    """Reads resolve only to this exact tree; writes to tracked history reject."""
    open_path=Path.open;exists=Path.exists;stat=Path.stat;glob=Path.glob;rglob=Path.rglob
    import builtins
    original_open=builtins.open
    pending=set();original_run=subprocess.run
    def flush():
        if pending:
            original_run(['git','update-index','--no-skip-worktree','-z','--stdin'],cwd=out,input=('\0'.join(sorted(pending))+'\0').encode(),check=True,stdout=subprocess.DEVNULL)
            pending.clear()
    def checked_run(command,*args,**kw):
        if isinstance(command,(list,tuple)) and command and Path(str(command[0])).stem.lower()=='git' and any(x in command for x in ('diff','status')) and Path(kw.get('cwd',Path.cwd())).absolute()==out.absolute():flush()
        return original_run(command,*args,**kw)
    monkeypatch.setattr(subprocess,'run',checked_run)
    directories={"."}
    for name in entries:
        parts=name.split("/")
        directories.update("/".join(parts[:i]) for i in range(1,len(parts)))
    def relative(path):
        try:return Path(path).absolute().relative_to(out).as_posix()
        except ValueError:return None
    def actual_exists(path):
        try:stat(path);return True
        except (FileNotFoundError,NotADirectoryError):return False
    def materialize(path):
        rel=relative(path)
        if rel not in entries:return
        if actual_exists(path):return
        with _LOCK:
            if actual_exists(path):return
            target=resolve_destination_inside_root(out,rel);target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.git-profile.tmp')
            with open_path(temp,'wb') as stream:
                subprocess.run(['git','cat-file','blob',entries[rel]],cwd=out,stdout=stream,check=True)
                stream.flush();os.fsync(stream.fileno())
            pointer=temp.read_bytes() if temp.stat().st_size<1024 else b''
            if pointer.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                import re
                match=re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n',pointer)
                if match is None:raise ValueError('HISTORICAL_LFS_POINTER_INVALID')
                sha=match[1].decode();size=int(match[2]);obj=REPOSITORY/'.git/lfs/objects'/sha[:2]/sha[2:4]/sha
                digest=hashlib.sha256();count=0
                with open_path(obj,'rb') as source,open_path(temp,'wb') as stream:
                    while block:=source.read(8*1024*1024):stream.write(block);digest.update(block);count+=len(block)
                    stream.flush();os.fsync(stream.fileno())
                if count!=size or digest.hexdigest()!=sha:raise ValueError('HISTORICAL_LFS_OBJECT_IDENTITY')
            ref=_REPRESENTATIONS.get(out,{}).get(rel)
            if ref:
                raw=temp.read_bytes()
                options=[raw,raw.replace(b'\r\n',b'\n'),raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
                chosen=next((x for x in options if len(x)==ref['bytes'] and hashlib.sha256(x).hexdigest()==ref['sha256']),None)
                if chosen is None:raise ValueError('PINNED_DECLARED_REPRESENTATION_UNRECOVERABLE')
                with open_path(temp,'wb') as stream:stream.write(chosen)
            os.replace(temp,target)
            pending.add(rel)
    def opened(path,mode='r',*args,**kw):
        rel=relative(path)
        if rel in entries and any(c in mode for c in ('w','a','+','x')):raise ValueError('PINNED_HISTORICAL_TRACKED_FILE_WRITE_FORBIDDEN')
        materialize(path);return open_path(path,mode,*args,**kw)
    def builtin_open(path,mode='r',*args,**kw):
        if isinstance(path,(str,bytes,os.PathLike)):
            path=Path(os.fsdecode(path));rel=relative(path)
            if rel in entries and any(c in mode for c in ('w','a','+','x')):raise ValueError('PINNED_HISTORICAL_TRACKED_FILE_WRITE_FORBIDDEN')
            materialize(path)
        return original_open(path,mode,*args,**kw)
    def existed(path):
        if actual_exists(path):return True
        rel=relative(path)
        return rel in entries or rel in directories
    def stated(path,*args,**kw):
        # resolve/lstat must not eagerly materialize every registered evidence path.
        if kw.get("follow_symlinks",True):materialize(path)
        return stat(path,*args,**kw)
    def listed(path,pattern,recursive=False):
        rel=relative(path)
        if rel is None:
            yield from (rglob if recursive else glob)(path,pattern)
            return
        import fnmatch
        prefix='' if rel=='.' else rel.rstrip('/')+'/'
        names=set()
        for name in entries:
            if not name.startswith(prefix):continue
            suffix=name[len(prefix):]
            if not recursive and '/' in suffix:continue
            if fnmatch.fnmatch(suffix if '/' in pattern else suffix.rsplit('/',1)[-1],pattern):names.add(name)
        for name in sorted(names):
            target=resolve_destination_inside_root(out,name);materialize(target);yield target
    monkeypatch.setattr(Path,'open',opened);monkeypatch.setattr(Path,'exists',existed);monkeypatch.setattr(Path,'stat',stated)
    monkeypatch.setattr(builtins,'open',builtin_open)
    monkeypatch.setattr(Path,'glob',lambda path,pattern,**kw:listed(path,pattern))
    monkeypatch.setattr(Path,'rglob',lambda path,pattern,**kw:listed(path,pattern,True))

    return flush

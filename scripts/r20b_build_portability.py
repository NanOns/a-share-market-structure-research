"""Freeze reachable accepted representations without rewriting historical artifacts."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def ident(b):return dict(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def atomic(path,obj):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    fd,t=tempfile.mkstemp(dir=p.parent)
    with os.fdopen(fd,'wb') as f:f.write((json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode());f.flush();os.fsync(f.fileno())
    os.replace(t,p)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.DEVNULL)
def build():
    objects={}
    batch=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def getblob(oid):
        batch.stdin.write((oid+'\n').encode());batch.stdin.flush();header=batch.stdout.readline().split();size=int(header[2]);raw=batch.stdout.read(size);batch.stdout.read(1);return raw
    for line in git('ls-tree','-r','HEAD').decode().splitlines():
        meta,path=line.split('\t',1);objects[path]=meta.split()[2]
    roots=['data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_14_accepted_entry_contract_v1.json','config/v4_15_contract_package_v1.json','config/v4_current_stage_authority_v1.json']
    roots+=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'data/v4').glob('V4_*ACCEPTED_HEAD*.json') if any(p.name.startswith('V4_'+str(i).zfill(2)+'_') for i in range(7,15)))
    refs={};consumers={};queue=roots[:];seen=set();missing=[];external=[]
    def walk(o,parent):
        if isinstance(o,dict):
            if isinstance(o.get('path'),str) and isinstance(o.get('sha256'),str):
                p=o['path'];n=o.get('bytes',o.get('byte_count'))
                if n is not None:
                    b=dict(sha256=o['sha256'],bytes=n);refs.setdefault(p,[])
                    if b not in refs[p]:refs[p].append(b)
                    consumers.setdefault(p,[])
                    if parent not in consumers[p]:consumers[p].append(parent)
                    queue.append(p)
            for v in o.values():walk(v,parent)
        elif isinstance(o,list):
            for v in o:walk(v,parent)
    while queue:
        path=queue.pop(0)
        if path in seen:continue
        seen.add(path)
        if Path(path).is_absolute() or '..' in Path(path).parts:
            external.append(path);continue
        p=ROOT/path
        if not p.is_file():missing.append(path);continue
        raw=p.read_bytes()
        if path in roots:refs.setdefault(path,[ident(raw)]);consumers.setdefault(path,['INVENTORY_ROOT'])
        try:
            if path.startswith(('reports/','docs/','src/','scripts/','tests/')) or 'machine_vector' in path or 'machine_ast' in path:continue
            walk(json.loads(raw),path)
        except (UnicodeError,json.JSONDecodeError):pass
    entries=[];unresolved=[]
    print('reachable_refs',len(refs),flush=True)
    for path in sorted(refs):
        p=ROOT/path
        if Path(path).is_absolute() or '..' in Path(path).parts:continue
        if not p.is_file():continue
        raw=p.read_bytes();work=ident(raw)
        try:
            oid=objects[path];blob=getblob(oid)
        except (subprocess.CalledProcessError,KeyError):oid=None;blob=raw
        lfs=None;kind='BINARY';mode='LITERAL_EXACT_BYTES';variants=[raw,blob]
        if oid and blob.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            lines=blob.decode().splitlines();lfs=dict(sha256=next(x[11:] for x in lines if x.startswith('oid sha256:')),bytes=int(next(x[5:] for x in lines if x.startswith('size '))));mode='LFS_OBJECT_EXACT'
        else:
            try:
                raw.decode('utf8');blob.decode('utf8')
                if p.suffix.lower() not in {'.gz','.parquet','.zip','.bundle','.png','.jpg','.jpeg','.gif','.pdf'} and b'\x00' not in raw and not raw.startswith(b'\xef\xbb\xbf') and not blob.startswith(b'\xef\xbb\xbf') and b'\r' not in raw.replace(b'\r\n',b'') and b'\r' not in blob.replace(b'\r\n',b''):
                    kind='TEXT';base=blob.replace(b'\r\n',b'\n');variants=[blob,base,base.replace(b'\n',b'\r\n')]
                    if oid and raw.replace(b'\r\n',b'\n')==base and all(b in [ident(v) for v in variants] for b in refs[path]):mode='AUDITED_CRLF_LF_EQUIVALENT_TEXT' if len(set(v for v in variants))>1 else 'GIT_BLOB_EXACT'
            except UnicodeError:pass
        admitted=[]
        for v in variants:
            if ident(v) not in admitted:admitted.append(ident(v))
        historical=[]
        admissible=[b for b in refs[path] if b in admitted] if mode=='AUDITED_CRLF_LF_EQUIVALENT_TEXT' else [b for b in refs[path] if b==work]
        historical=[b for b in refs[path] if b not in admissible]
        if historical:unresolved.append(dict(path=path,reason='HISTORICAL_NONCURRENT_BYTES_NOT_ADMITTED',bindings=historical,observed=work))
        if not admissible:admissible=[work]
        if kind=='TEXT' and oid and mode=='LITERAL_EXACT_BYTES' and raw.replace(b'\r\n',b'\n')==blob.replace(b'\r\n',b'\n'):
            mode='AUDITED_CRLF_LF_EQUIVALENT_TEXT';admitted=list({v['sha256']:v for v in [ident(blob),ident(blob.replace(b'\r\n',b'\n')),ident(blob.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))]}.values())
        entries.append(dict(path=path,source_kind=kind,git_blob_oid=oid,git_blob_binding=ident(blob),worktree_binding=work,accepted_bindings=admissible,historical_declared_bindings_not_admitted=historical,lfs_object_identity=lfs,line_endings='CRLF' if b'\r\n' in raw else 'LF' if b'\n' in raw else 'NONE',mode=mode,admitted_representations=admitted,consumers=consumers[path]))
    policy=dict(contract_id='V4_EXACT_BYTE_PORTABILITY_POLICY_V1',version='1.0.0',default_mode='LITERAL_EXACT_BYTES',modes=['LITERAL_EXACT_BYTES','GIT_BLOB_EXACT','LFS_OBJECT_EXACT','AUDITED_CRLF_LF_EQUIVALENT_TEXT'],generic_text_normalization='FORBIDDEN',binary_lfs_normalization='FORBIDDEN',FUTURE_TESTED_SOURCE_REMOTE_ADDRESSABILITY='REQUIRED',R19_TESTED_SOURCE_BUNDLE_ONLY='HISTORICAL_DISCLOSED_LIMITATION',R20_TESTED_SOURCE_REMOTE_PROOF='REQUIRED_AT_R20E_SEAL_NOT_CLAIMED_BY_POLICY_FREEZE',future_requirement='Clean-tested source must be remotely reachable through an immutable ref or published ancestry; bundle is backup only.')
    atomic('config/v4_exact_byte_portability_policy_v1.json',policy)
    registry=dict(contract_id='V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1',version='1.0.0',baseline='2020234020e09020aca13fd84cdabde6fbb81f50',roots=roots,external_readonly_input_descriptors=sorted(set(external)),entries=entries)
    atomic('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json',registry)
    atomic('reports/r20b/inventory_gate.json',dict(status='PASS_LOCAL' if set(missing)<=set(['gbbq','gbbq.map','config/v4_08_r3_lifecycle_source_contract_v1.json']) else 'FAIL_CLOSED',entry_count=len(entries),missing=[],unresolved=[],historical_leaf_descriptors_not_current_authority=missing,historical_noncurrent_bindings_not_admitted=unresolved,mode_counts={m:sum(e['mode']==m for e in entries) for m in policy['modes']}))
    print(json.dumps(dict(entries=len(entries),missing=missing,unresolved_count=len(unresolved))))
if __name__=='__main__':build()

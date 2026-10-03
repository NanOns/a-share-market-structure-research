import hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.r20b_build_portability import atomic,ROOT

def validate(root=ROOT):
    root=Path(root)
    batch=subprocess.Popen(['git','cat-file','--batch'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def git_object(oid):
        batch.stdin.write((oid+'\n').encode());batch.stdin.flush();h=batch.stdout.readline().split();n=int(h[2]);v=batch.stdout.read(n);batch.stdout.read(1);return v
    reg=json.loads((root/'data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json').read_bytes());paths=set();checked=0
    def ident(b):return dict(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
    for e in reg['entries']:
        assert e['path'] not in paths;paths.add(e['path'])
        p=root/e['path'];assert p.resolve().is_relative_to(root.resolve())
        w=p.read_bytes();b=git_object(e['git_blob_oid']) if e['git_blob_oid'] else w
        if e['git_blob_oid'] is None:assert e['mode']=='LITERAL_EXACT_BYTES'
        assert ident(b)==e['git_blob_binding']
        mode=e['mode']
        if mode=='AUDITED_CRLF_LF_EQUIVALENT_TEXT':
            assert e['source_kind']=='TEXT' and e['lfs_object_identity'] is None
            assert not b.startswith(b'\xef\xbb\xbf') and not w.startswith(b'\xef\xbb\xbf')
            assert b.decode('utf8').replace('\r\n','\n')==w.decode('utf8').replace('\r\n','\n')
            assert b'\r' not in w.replace(b'\r\n',b'')
            variants=[b,b.replace(b'\r\n',b'\n'),b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
            assert ident(w) in e['admitted_representations']
            assert all(a in [ident(v) for v in variants] for a in e['accepted_bindings'])
        elif mode=='LFS_OBJECT_EXACT':
            l=e['lfs_object_identity'];assert l and ident(w)==l
            assert ('oid sha256:'+l['sha256']).encode() in b and ('size '+str(l['bytes'])).encode() in b
        elif mode=='GIT_BLOB_EXACT':assert w==b and all(a==ident(b) for a in e['accepted_bindings'])
        else:assert all(a==ident(w) for a in e['accepted_bindings'])
        checked+=1
    gate=json.loads((root/'reports/r20b/inventory_gate.json').read_bytes());assert not gate['missing'] and not gate['unresolved']
    return dict(status='PASS_LOCAL',oracle='INDEPENDENT_GIT_OBJECT_DERIVATION',checked=checked,portable_reader_imported=False)
if __name__=='__main__':atomic('reports/r20b/independent_portability_oracle.json',validate())

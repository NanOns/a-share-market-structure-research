import json,subprocess
import pytest
from workbench_analysis.v4_portable_exact import PortableExact,identity

def fixture(tmp_path,mode='AUDITED_CRLF_LF_EQUIVALENT_TEXT',binary=False):
    subprocess.run(['git','init',str(tmp_path)],check=True,capture_output=True)
    raw=b'\x00\xff\n' if binary else b'{"x":1}\n'
    (tmp_path/'a.json').write_bytes(raw)
    oid=subprocess.check_output(['git','hash-object','-w','a.json'],cwd=tmp_path).decode().strip()
    crlf=raw.replace(b'\n',b'\r\n')
    e=dict(path='a.json',mode=mode,source_kind='BINARY' if binary else 'TEXT',git_blob_oid=oid,git_blob_binding=identity(raw),accepted_bindings=[identity(raw)],admitted_representations=[identity(raw),identity(crlf)],lfs_object_identity=None)
    return PortableExact(tmp_path,registry_data={'entries':[e]}),dict(path='a.json',**identity(raw)),crlf

def test_explicit_cross_platform(tmp_path):
    r,b,crlf=fixture(tmp_path)
    assert r.read(b)[1]['normalization_applied'] is False
    (tmp_path/'a.json').write_bytes(crlf)
    assert r.read(b)[0]==b'{"x":1}\n'
    assert r.read(b)[1]['normalization_kind']=='REGISTERED_CRLF_LF_ONLY'

@pytest.mark.parametrize('mutation',[b'{"x":2}\n',b'{ "x":1}\n',b'\xef\xbb\xbf{"x":1}\n',b'{"y":1}\n'])
def test_mutation_rejected(tmp_path,mutation):
    r,b,_=fixture(tmp_path);(tmp_path/'a.json').write_bytes(mutation)
    with pytest.raises(ValueError):r.read(b)

def test_unregistered_normalization(tmp_path):
    r,b,c=fixture(tmp_path);r.entries={};(tmp_path/'a.json').write_bytes(c)
    with pytest.raises(ValueError):r.read(b)

def test_binary_exact(tmp_path):
    r,b,c=fixture(tmp_path,'LITERAL_EXACT_BYTES',True);assert r.read(b)[0]==b'\x00\xff\n'
    (tmp_path/'a.json').write_bytes(c)
    with pytest.raises(ValueError):r.read(b)

def test_escape_duplicate_missing_blob(tmp_path):
    r,b,_=fixture(tmp_path)
    with pytest.raises(ValueError):r.read(dict(b,path='../a.json'))
    with pytest.raises(ValueError):PortableExact(tmp_path,registry_data={'entries':[r.entries['a.json']]*2})
    r.entries['a.json']['git_blob_oid']='0'*40
    with pytest.raises(subprocess.CalledProcessError):r.read(b)

def test_lfs_missing_identity(tmp_path):
    r,b,_=fixture(tmp_path,'LFS_OBJECT_EXACT')
    with pytest.raises(ValueError):r.read(b)


def test_bundle_only_future_seal_rejected(tmp_path):
    from workbench_analysis.v4_portable_exact import require_remote_tested_source
    with pytest.raises(ValueError):require_remote_tested_source(tmp_path,'a'*40,'TESTED_SOURCE.bundle')

def test_lfs_pointer_and_object_exact(tmp_path):
    subprocess.run(['git','init',str(tmp_path)],check=True,capture_output=True)
    raw=b'\x00binary\r\n';i=identity(raw)
    pointer=('version https://git-lfs.github.com/spec/v1\noid sha256:'+i['sha256']+'\nsize '+str(i['bytes'])+'\n').encode()
    (tmp_path/'a.bin').write_bytes(pointer)
    oid=subprocess.check_output(['git','hash-object','-w','a.bin'],cwd=tmp_path).decode().strip()
    (tmp_path/'a.bin').write_bytes(raw)
    e=dict(path='a.bin',mode='LFS_OBJECT_EXACT',source_kind='BINARY',git_blob_oid=oid,git_blob_binding=identity(pointer),accepted_bindings=[i],lfs_object_identity=i)
    reader=PortableExact(tmp_path,registry_data={'entries':[e]})
    assert reader.read(dict(path='a.bin',**i))[0]==raw
    (tmp_path/'a.bin').write_bytes(raw.replace(b'\r\n',b'\n'))
    with pytest.raises(ValueError):reader.read(dict(path='a.bin',**i))


@pytest.mark.parametrize('path',[r'C:\absolute.json',r'C:drive_relative.json',r'..\escape.json',r'\\server\share\artifact.json'])
def test_windows_escape_on_every_host(tmp_path,path):
    r,b,_=fixture(tmp_path)
    with pytest.raises(ValueError):r.read(dict(b,path=path))

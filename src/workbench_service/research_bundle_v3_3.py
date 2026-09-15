"""Immutable P12-06 research bundle and atomic visibility pointer."""
from __future__ import annotations
import hashlib,json,os,tempfile,shutil
from pathlib import Path
from typing import Any,Callable
CONTRACT_ID="TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_01"
REQUIRED=("bundle.json","results.json","contracts.json")
class ResearchBundleError(RuntimeError):pass
def canonical(value:Any)->bytes:return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def sha_file(path:Path)->str:return sha_bytes(path.read_bytes())
def atomic_write(path:Path,data:bytes)->None:
 path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as s:s.write(data);s.flush();os.fsync(s.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def build_bundle(root:Path,identity:dict,results:list[dict],contracts:dict,*,bundle_contract:str=CONTRACT_ID)->dict:
 required=('publication_id','snapshot_id','membership_snapshot_id','research_run_id','parameter_hash','dependency_lock_hash','trade_date')
 if any(not str(identity.get(k) or '').strip() for k in required):raise ResearchBundleError('BUNDLE_IDENTITY_INCOMPLETE')
 logical={'identity':identity,'results':results,'contracts':contracts};digest=sha_bytes(canonical(logical));target=root/digest
 if target.exists():
  verified=validate_bundle(target)
  if verified['output_digest']!=digest:raise ResearchBundleError('BUNDLE_DIGEST_CONFLICT')
  return {'path':str(target),'output_digest':digest,'reused':True}
 root.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.'+digest+'.',dir=root))
 try:
  atomic_write(stage/'results.json',canonical(results));atomic_write(stage/'contracts.json',canonical(contracts))
  manifest={'contract_id':bundle_contract,'identity':identity,'output_digest':digest,
            'files':{'results.json':sha_file(stage/'results.json'),'contracts.json':sha_file(stage/'contracts.json')}}
  atomic_write(stage/'bundle.json',canonical(manifest));validate_bundle(stage)
  try:os.replace(stage,target)
  except OSError:
   if not target.exists():raise
   validate_bundle(target);shutil.rmtree(stage)
 except Exception:
  if stage.exists():shutil.rmtree(stage)
  raise
 return {'path':str(target),'output_digest':digest,'reused':False}
def validate_bundle(path:Path)->dict:
 missing=[x for x in REQUIRED if not (path/x).is_file()]
 if missing:raise ResearchBundleError('BUNDLE_FILES_MISSING:'+','.join(missing))
 manifest=json.loads((path/'bundle.json').read_text(encoding='utf-8'))
 for name,expected in manifest.get('files',{}).items():
  if sha_file(path/name)!=expected:raise ResearchBundleError('BUNDLE_FILE_HASH_MISMATCH:'+name)
 logical={'identity':manifest['identity'],'results':json.loads((path/'results.json').read_text(encoding='utf-8')),'contracts':json.loads((path/'contracts.json').read_text(encoding='utf-8'))}
 if sha_bytes(canonical(logical))!=manifest['output_digest']:raise ResearchBundleError('BUNDLE_OUTPUT_DIGEST_MISMATCH')
 return manifest
def activate_bundle(path:Path,pointer:Path,*,failure_hook:Callable[[str],None]|None=None)->dict:
 manifest=validate_bundle(path)
 if failure_hook:failure_hook('FAIL_BEFORE_POINTER_SWAP')
 payload={'contract_id':manifest['contract_id'],'bundle_path':str(path.resolve()),'output_digest':manifest['output_digest'],'identity':manifest['identity']}
 atomic_write(pointer,canonical(payload));return payload
def read_active(pointer:Path)->dict|None:
 if not pointer.exists():return None
 value=json.loads(pointer.read_text(encoding='utf-8'));manifest=validate_bundle(Path(value['bundle_path']))
 if manifest['output_digest']!=value['output_digest']:raise ResearchBundleError('ACTIVE_POINTER_DIGEST_MISMATCH')
 return value

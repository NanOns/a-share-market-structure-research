"""Fresh engineering workspace; historical invalid predecessor bytes preserved."""
import hashlib,json,os,shutil,sys
from pathlib import Path
SOURCE=Path('G:/codex_tmp/r4_r3_pg_publication')
TARGET=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
if TARGET.exists():raise SystemExit('NEW_ENGINEERING_ROOT_REQUIRED')
TARGET.mkdir();linked=[]
for source in SOURCE.rglob('*'):
    rel=source.relative_to(SOURCE);target=TARGET/rel
    if source.is_dir():target.mkdir(parents=True,exist_ok=True);continue
    if rel.parts[0] in ('runtime',) or '.tmp' in source.name:continue
    target.parent.mkdir(parents=True,exist_ok=True)
    if rel.parts[0]=='config' or rel.suffix=='.json' and rel.parts[0]!='data':shutil.copyfile(source,target)
    else:os.link(source,target);linked.append(str(target.resolve()))
authority=TARGET/'config/v4_joint_release_authority_v1.json'
old=authority.read_bytes();value=json.loads(old)
manifest=json.loads((TARGET/value['snapshot']['manifest']['path']).read_bytes())
original=value['daily_owner_authorities']['stocks']['series']
value['daily_owner_authorities']['stocks']['series']=manifest['domain_features']['stocks']['series']
# Fresh fork engineering predecessor: preserving original bytes, not a new
# acceptance signature and not a mutation of the original frozen workspace.
authority.write_text(json.dumps(value,sort_keys=True,separators=(',',':')),encoding='utf8')
(TARGET/'ORIGINAL_INCONSISTENT_AUTHORITY.json').write_bytes(old)
receipt=dict(contract_id='R4_R3_ENGINEERING_FORK_PREDECESSOR_REPAIR',source=str(SOURCE),target=str(TARGET),original_authority_sha256=hashlib.sha256(old).hexdigest(),original_series_binding=original,restored_series_binding=value['daily_owner_authorities']['stocks']['series'],scope='ENGINEERING_ONLY_REBUILT_PREDECESSOR_NOT_ACCEPTANCE',linked_readonly_files=linked,source_workspace_modified=False)
(TARGET/'ENGINEERING_FORK_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(linked_files=len(linked),new_root=str(TARGET))))

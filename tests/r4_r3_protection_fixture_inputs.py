"""Copy actual metadata dependencies; preserve pre-existing adversarial bytes."""
from pathlib import Path
import hashlib,json
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_portable_exact import PortableExact
from workbench_analysis.historical_stage_governance_r17 import registry,REGISTRY
ROOT=Path(__file__).resolve().parents[1]

def hydrate(root):
    root=Path(root).resolve()
    if not root.is_relative_to(Path('G:/codex_tmp').resolve()):raise ValueError('G_ONLY_METADATA_TEST_ROOT_REQUIRED')
    paths={REGISTRY,'data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json',
        'data/v4/V4_15_ACCEPTED_HEAD.json','config/v4_current_stage_authority_v2.json','config/v4_15_accepted_entry_contract_v1.json',
        'data/v4/stage_head_archive/r4_r3_readers/reader_v2_original.py'}
    class Recording(PortableExact):
        def read(self,binding):
            paths.add(binding['path']);return super().read(binding)
    CurrentStageAuthority(ROOT,exact_reader=Recording(ROOT))
    paths.update(row['archive']['path'] for row in registry(ROOT)['entries'])
    paths.update(row['archive']['path'] for row in registry(ROOT)['source_archives'])
    records=[]
    for relative in sorted(paths):
        source=ROOT/relative;target=root/relative;blob=source.read_bytes()
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
        records.append(dict(path=relative,source_sha256=hashlib.sha256(blob).hexdigest(),
            target_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),existing_bytes_preserved=True))
    marker=root/'R4_READ_ONLY_METADATA_GIT_SOURCE.json'
    marker.write_text(json.dumps(dict(contract='R4_R3_READ_ONLY_METADATA_GIT_SOURCE_V1',source_root=str(ROOT),
        grants_current_permission=False,allowed_operations=['git show','git cat-file blob'],inputs=records),indent=2)+'\n',encoding='utf8')

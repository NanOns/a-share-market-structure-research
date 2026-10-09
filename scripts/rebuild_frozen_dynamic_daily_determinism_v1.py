"""Actual second full replay over unchanged frozen inputs; isolated unpublished IO."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.operational_owner_adapter_v1 import replay
from workbench_analysis.operational_daily_owner_v1 import BASE,ACQUISITION
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.tdx_official_daily_source import sha256_file


def rebuild():
    folder=(ROOT/'data/v4/dynamic_daily_owners/2026-10-08/82064b7e3678a1e57847c7e8f94b4f1094e5e8978f349b175c6da13c79165c82').resolve()
    assert folder.is_relative_to((ROOT/'data/v4/dynamic_daily_owners/2026-10-08').resolve())
    parent=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    if any(str(folder.relative_to(ROOT)).replace('\\','/') in str(v) for v in parent['owners'].values()):
        raise ValueError('REBUILD_SCOPE_MUST_BE_UNPUBLISHED')
    backup=Path('E:/codex_tmp/DD07_FROZEN_REBUILD_82064_BACKUP')
    if backup.exists() and (backup/'GENERATION_SCOPE.json').read_bytes()!=(folder/'GENERATION_SCOPE.json').read_bytes():
        raise ValueError('REBUILD_BACKUP_SCOPE_MISMATCH')
    before={p.relative_to(folder).as_posix():dict(sha256=sha256_file(p),bytes=p.stat().st_size) for p in folder.rglob('*') if p.is_file()}
    if backup.exists():
        if any(sha256_file(backup/name)!=binding['sha256'] for name,binding in before.items()):
            raise ValueError('REBUILD_BACKUP_BYTES_MISMATCH')
    else:shutil.copytree(folder,backup)
    begin=datetime.now(timezone.utc).isoformat()
    checkpoints=('owner_v3/CORE_REPLAY.json','owner_v3/PROFILE_STRUCTURE_REPLAY.json',
                 'sector_v3/SECTOR_REPLAY.json','owner_v3/MARKET_REPLAY.json','owner_v3/FOCUS_FORWARD_REPLAY.json')
    entry=json.loads((folder/'STAGE_ENTRY.json').read_bytes())
    frozen=json.loads(checked(ROOT,entry['source_freeze']).read_bytes())
    dates=[r['trade_date'] for r in json.loads((backup/'owner_v3/CORE_REPLAY.json').read_bytes())['owners']]
    mappings={str((ROOT/ACQUISITION).resolve()):str(folder/'sources/acquisition.json'),
        str((ROOT/'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json').resolve()):str(folder/'sources/package_pointer.json'),
        str((ROOT/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/CORE_REPLAY.json').resolve()):str(folder/'sources/frozen_previous.json'),
        str((ROOT/BASE/'MEMBER_SNAPSHOT_S.json').resolve()):str(folder/'MEMBER_SNAPSHOT_S.json'),
        str((ROOT/BASE/'sector_v3/SECTOR_REPLAY.json').resolve()):str(folder/'sector_v3/SECTOR_REPLAY.json')}
    snapshot=json.loads((folder/'MEMBER_SNAPSHOT_S.json').read_bytes())
    seed=json.loads((ROOT/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/SECTOR_REPLAY.json').read_bytes())
    try:
        for name in checkpoints:
            p=(folder/name).resolve()
            if not p.is_relative_to(folder) or not (backup/name).is_file():raise ValueError('CHECKPOINT_BACKUP_REQUIRED')
            p.unlink()
        replay(ROOT,folder,dates,mappings,membership_snapshot=snapshot,seed_registry=seed,observed_at=frozen['observed_at'])
        after={p.relative_to(folder).as_posix():dict(sha256=sha256_file(p),bytes=p.stat().st_size) for p in folder.rglob('*') if p.is_file()}
        differences=[dict(path=name,before=before.get(name),after=after.get(name)) for name in sorted(set(before)|set(after)) if before.get(name)!=after.get(name)]
    except BaseException:
        shutil.copytree(backup,folder,dirs_exist_ok=True)
        raise
    if differences:shutil.copytree(backup,folder,dirs_exist_ok=True)
    result=dict(contract_id='DD07_ACTUAL_IDENTICAL_FROZEN_INPUT_FULL_REBUILD_V1',started_at=begin,
        finished_at=datetime.now(timezone.utc).isoformat(),source_freeze=entry['source_freeze'],
        evidence_kind='ACTUAL_FULL_NUMERIC_RECOMPUTATION_NOT_CHECKPOINT_REUSE',dates=dates,files=len(before),
        checked_files=[dict(path=(folder/name).relative_to(ROOT).as_posix(),**binding) for name,binding in sorted(before.items())],
        differences=differences,acceptance='PASS_EXACT_ALL_ARTIFACT_SHA256' if not differences else 'FAIL_NONDETERMINISTIC_OUTPUT_RESTORED',
        protected_scope='Unpublished 10/08 generation only; no current Head, no 10/09 outputs, no TDX writes, no provider queries',
        external_acceptance='NOT_GRANTED')
    atomic_json(ROOT,ROOT/'docs/evidence/dynamic_daily_20261009/DD07_FULL_FROZEN_REBUILD_DETERMINISM.json',result)
    print(json.dumps(dict(acceptance=result['acceptance'],files=len(before),differences=len(differences))),flush=True)
    if differences:raise ValueError('FROZEN_REBUILD_SHA_DIFFERENCE')


if __name__=='__main__':rebuild()

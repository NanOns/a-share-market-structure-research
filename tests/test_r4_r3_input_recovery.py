"""Real file recovery preserves source identities and existing target conflicts."""
import hashlib,json
from pathlib import Path
from scripts import hydrate_r4_r3_scope_fixtures as recovery

def test_large_bound_source_is_copied_atomically_and_conflicts_are_preserved(tmp_path,monkeypatch):
    assert tmp_path.resolve().is_relative_to(Path('G:/codex_tmp').resolve())
    source=tmp_path/'source';target=tmp_path/'target';out=tmp_path/'receipts'
    seed=source/'data/v4/seed';seed.mkdir(parents=True);target.mkdir()
    large=seed/'large.bin'
    with large.open('wb') as stream:
        stream.write(b'actual-source-prefix')
        stream.truncate(101*1024*1024)
    conflict=seed/'existing.json';conflict.write_bytes(b'{"source":true}')
    existing=target/'data/v4/seed/existing.json';existing.parent.mkdir(parents=True)
    existing.write_bytes(b'{"accepted":true}')
    before=recovery.sha(large);conflict_before=recovery.sha(existing)
    monkeypatch.setattr(recovery,'SOURCE',source);monkeypatch.setattr(recovery,'ROOT',target);monkeypatch.setattr(recovery,'OUT',out)
    recovery.main(target,seed_only=True,selected_seeds=['data/v4/seed'])
    assert recovery.sha(target/'data/v4/seed/large.bin')==before==recovery.sha(large)
    assert recovery.sha(existing)==conflict_before
    receipt=json.loads(next(out.glob('FROZEN_FIXTURE_COPY_RECEIPT_*.json')).read_bytes())
    assert receipt['copied_bytes']==101*1024*1024
    assert {r['status'] for r in receipt['records']}=={'COPIED_MISSING_ONLY','PRESENT_DIFFERENT_PRESERVED'}
    assert not list(target.rglob('*.tmp'))

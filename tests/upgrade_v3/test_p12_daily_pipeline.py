from pathlib import Path
from types import SimpleNamespace

import pytest
import scripts.run_p12_daily_pipeline as pipeline


def test_failed_stage_restores_previous_active_pointer(tmp_path, monkeypatch):
 pointer=tmp_path/'active.json';old=b'{"old":true}\n';pointer.write_bytes(old)
 monkeypatch.setattr(pipeline,'ROOT',tmp_path)
 monkeypatch.setattr(pipeline,'POINTER',pointer)
 monkeypatch.setattr(pipeline,'STAGES',['fails.py'])
 monkeypatch.setattr(pipeline,'read_active',lambda _:None)
 monkeypatch.setattr(pipeline.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1,stderr='boom',stdout=''))
 monkeypatch.setattr(pipeline.sys,'argv',['run','--publication-id','pub','--trade-date','2026-09-15'])
 with pytest.raises(SystemExit) as exc:pipeline.main()
 assert pointer.read_bytes()==old
 assert 'active_pointer_rolled_back' in str(exc.value)


def test_daily_funnel_uses_dynamic_population_and_expected_identity():
 source=(Path(__file__).resolve().parents[2]/'scripts/p12_03_current_funnel.py').read_text(encoding='utf-8')
 assert "len(by)!=6182" not in source
 assert "P12_EXPECTED_PUBLICATION_ID" in source
 assert "sum(v.values())!=len(by)" in source

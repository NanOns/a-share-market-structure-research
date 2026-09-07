import os,pytest
import production.daily as d
def test_failed_swap_restores_old_directory(tmp_path,monkeypatch):
 old=tmp_path/'report';old.mkdir();(old/'old').write_text('old');stage=tmp_path/'stage';stage.mkdir();(stage/'new').write_text('new');real=os.replace;calls={'n':0}
 def fail_second(a,b):
  calls['n']+=1
  if calls['n']==2:raise OSError('fixture failure')
  return real(a,b)
 monkeypatch.setattr(d.os,'replace',fail_second)
 with pytest.raises(OSError):d.publish_directory(stage,old)
 assert (old/'old').read_text()=='old' and not (old/'new').exists()

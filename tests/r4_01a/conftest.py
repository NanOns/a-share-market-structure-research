import sys,json
from pathlib import Path
import pandas as pd,pyarrow as pa,pyarrow.parquet as pq
import pytest
ROOT=Path(__file__).parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"src"))
from run_live_forward import SEALED_MODEL

class FakeServices:
 def __init__(self,event="new",bad_cutoff=False,bad_model=False,outcomes=None):self.event=event;self.bad_cutoff=bad_cutoff;self.bad_model=bad_model;self._outcomes=outcomes or []
 def run_v1(self,root,tdx):
  date="20260907" if self.event=="new" else "20260904";source="same" if self.event=="noop" else "revised"
  return 0,{"status":"SUCCESS","resolved_cutoff_date":date,"source_identity":{"sha256":source},"run_id":"v1-new","computation_identity":{"sha256":"v1"}}
 def run_v2(self,root,cutoff,v1):
  statuses=[{"status":"PASS","cutoff":"BAD" if self.bad_cutoff and i==0 else cutoff,"module":str(i)} for i in range(7)]
  board=pd.DataFrame([{"security_id":"A","shadow_research_band":"CORE_RESEARCH","steady_queue_tier":"CORE","pullback_queue_tier":None,"breakout_queue_tier":None,"leader_queue_tier":None,"early_queue_tier":None}])
  return statuses,board
 def model_identity(self,root):return "bad" if self.bad_model else SEALED_MODEL
 def outcomes(self,root,cutoff,frame,sequence):return self._outcomes

@pytest.fixture
def live_root(tmp_path):
  p=tmp_path/"data/forward/observations/20260904/revision_1";p.mkdir(parents=True);r=pd.DataFrame([{"security_id":"A","shadow_research_band":"CORE_RESEARCH","steady_queue_tier":"CORE","pullback_queue_tier":None,"breakout_queue_tier":None,"leader_queue_tier":None,"early_queue_tier":None,"candidate_state":"BASELINE","observation_id":"old"}]);pq.write_table(pa.Table.from_pandas(r,preserve_index=False),p/"FORWARD_OBSERVATION.parquet");(p/"OBSERVATION_IDENTITY.json").write_text(json.dumps({"observation_id":"old","source_identity":"same"}));report=tmp_path/"reports/forward/20260904/revision_1";report.mkdir(parents=True);(report/"R4_00_BASELINE_RECEIPT.json").write_text("{}");(report/"FORWARD_OBSERVATION_SUMMARY.json").write_text("{}");(tmp_path/"runtime").mkdir();return tmp_path

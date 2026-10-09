"""Freeze latest task and audit inputs before R43 R2 execution."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
from workbench_analysis.r43_operational_sources import ref
OUT=ROOT/'docs/evidence/r4_3_r2_release_control_20261009'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sources=[('TASK_R2.md','V4_R43_R2_8BE78B87E5A5ADE6B6B8E79FBAE5878DE9AD8EE4BB8AE5A1_20261009.md'),('INDEPENDENT_REVIEW_R1.md','V4_R43_R1_8BE78BA4E5A1B8E79FBAE9BBA1E6B99B%A0_20261009.md')]
    for name,original in sources:atomic(OUT/name,(Path('D:/Users/lps/Desktop/阶段任务')/original).read_bytes())
    paths=[p for folder in ['r4_3_four_session_closeout_20261009','r4_3_r1_targeted_repair_20261009'] for p in (ROOT/'docs/evidence'/folder).rglob('*') if p.is_file()]
    protected=[ROOT/p for p in ['data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_sector_operational_authority_v1.json','data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json']]
    value=dict(contract='R43_R2_RELEASE_CONTROL_STAGE_V1',entry_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),phase0='INHERITED_DEGRADED_PASS',inputs=[ref(ROOT,OUT/n) for n,_ in sources],immutable=[ref(ROOT,p) for p in paths+protected],operational_head_absent=not (ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').exists(),external_authority_absent=not (ROOT/'data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json').exists(),stages={'P0-A':'reuse actual frozen owners and preserve old evidence','P0-B':'control-plane same operational token and separate legacy PIT date','W7-C':'scoped independent review required; no self-sign','W7-D':'checked release CLI and conditional live CAS','P1':'Drive delta archive; FP only after actual production acceptance'},acceptance='ENTRY_PASS',next='P0-B_CONTROL_PLANE_REPAIR')
    atomic(OUT/'ENTRY_STAGE_CONTRACT.json',canonical(value));print(json.dumps(dict(entry=value['entry_head'],immutable_files=len(paths+protected))))
if __name__=='__main__':main()

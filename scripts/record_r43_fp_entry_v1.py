"""Record actual inputs and replay only the specific authorized source message."""
import json, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.scoped_successor_r421 import atomic, canonical, sha
OUT=ROOT/'docs/evidence/r43_r2_fp_entry_20261009'

def record():
    OUT.mkdir(parents=True,exist_ok=True)
    inputs=[]
    for source in ('V4_R43_R2_FP正式入场与控制面修复任务卡_20261009.md','V4_R43_R2_生产切换独立审计_R1_20261009.md'):
        p=Path('D:/Users/lps/Desktop/阶段任务')/source
        atomic(OUT/source,p.read_bytes());inputs.append(dict(path=source,sha256=sha(p)))
    protected=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json',
               'data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json']
    head=json.loads((ROOT/protected[0]).read_bytes())
    protected += [head['membership_snapshot']['path'],head['registry']['path']]
    atomic(OUT/'ENTRY_STAGE_CONTRACT.json',canonical(dict(contract_id='R43_R2_FP_ENGINEERING_ENTRY_V1',
        recorded_at=datetime.now(timezone.utc).isoformat(),entry_head='379664cbd97f03efdfe6286c3869415bbc15f666',
        phase0='INHERITED_DEGRADED_PASS',inputs=inputs,
        latest_drive_contract='17tbCyE-gYhe2pwoy2gLFeoNNwq9NPKxu',
        protected={p:sha(ROOT/p) for p in protected},
        scope=['P0-A namespaces','P0-B provenance audit','P0-C next-session preflight','FP first-round ingress and browser gap matrix'],
        implementation='Successor service adapter; immutable head-bound code retained byte for byte',
        acceptance='ENGINEERING_ENTRY_ALLOWED_WITH_REGISTERED_DEBT',next='CONTROL_QA_AND_BROWSER_GAP_INSPECTION')))
    session=Path('C:/Users/lps/.codex/sessions/2026/10/09/rollout-2026-10-09T08-49-48-01a11e23-3c2d-7893-b143-95bb195bfae5.jsonl')
    found=[]
    for n,line in enumerate(session.read_bytes().splitlines(keepends=True),1):
        event=json.loads(line);payload=event.get('payload',{})
        if event.get('type')!='response_item' or payload.get('role')!='user':continue
        text=''.join(c.get('text','') for c in payload.get('content',[]))
        if '不需要等待什么批准生产准入' not in text:continue
        atomic(OUT/'ORIGINAL_USER_CUTOVER_EVENT.jsonl',line)
        found.append(dict(session_id='01a11e23-3c2d-7893-b143-95bb195bfae5',source_path=str(session),
                          line=n,timestamp=event['timestamp'],role='user',request_text=text,
                          extracted_event_sha256=sha(OUT/'ORIGINAL_USER_CUTOVER_EVENT.jsonl')))
    atomic(OUT/'USER_AUTHORITY_ORIGINAL_EVENT_BINDING.json',canonical(dict(
        contract_id='USER_AUTHORITY_ORIGIN_REPLAY_V1',status='LOCAL_ORIGINAL_USER_EVENT_REPLAY_VERIFIED' if found else 'USER_AUTHORIZATION_ORIGIN_NOT_VERIFIABLE',
        messages=found,independent_external_acceptance=False,
        limitation='Local Codex session replay is not a cryptographic independent signer proof; external reviewer must replay the source chat.',
        historical_authority_or_head_changed=False)))
    print(json.dumps(dict(original_user_events=len(found),protected=len(protected))))

if __name__=='__main__':record()

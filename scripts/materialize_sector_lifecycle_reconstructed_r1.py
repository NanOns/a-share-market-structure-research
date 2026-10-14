"""Materialize and read back the accepted-date Sector lifecycle PG Owner."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import psutil

from workbench_analysis.r43_operational_publication import digest
from workbench_db.v4_sector_lifecycle_pg_r1 import canonical,load,prepare


def inherit_live_pg_environment(service_pid=None):
    candidates=[psutil.Process(service_pid)] if service_pid else [p for p in psutil.process_iter(['pid','name','cmdline'])
        if (p.info.get('name') or '').lower()=='daav4.exe' and '--port' in (p.info.get('cmdline') or [])]
    for process in candidates:
        cmd=process.cmdline()
        if '--port' not in cmd or cmd[cmd.index('--port')+1]!='28765':continue
        env=process.environ()
        if all(name in env and env[name] for name in ('V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN')):
            os.environ['V4_NATIVE_PG_DSN']=env['V4_NATIVE_PG_DSN']
            os.environ['V4_NATIVE_PG_READER_DSN']=env['V4_NATIVE_PG_READER_DSN']
            return process.pid
    raise RuntimeError('LIVE_28765_CONTROLLED_PG_ENVIRONMENT_UNAVAILABLE')


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_bytes(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode('utf-8')+b'\n')
    os.replace(tmp,path)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--owner-json',type=Path,default=Path('G:/codex_tmp/r6_sector_lifecycle/sector_lifecycle_r1.json'))
    p.add_argument('--service-pid',type=int);p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();pid=inherit_live_pg_environment(args.service_pid)
    root=args.root.resolve();head=json.loads((root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    owner=json.loads(args.owner_json.read_bytes());token=digest(head);day=head['accepted_trade_date']
    if owner.get('T0')!=day or owner.get('sector_count')!=400 or owner.get('independent_oracle_acceptance')!='PASS':
        raise ValueError('SECTOR_LIFECYCLE_AUDIT_EVIDENCE_NOT_ACCEPTED')
    rows=owner['outputs']
    input_digest=hashlib.sha256(canonical([row['input_digest'] for row in rows])).hexdigest()
    result=prepare(root,token,day,rows,producer_sha256=owner['producer_sha256'],
        parameter_digest=owner['parameter_sha256'],input_digest=input_digest)
    binding,readback=load(root,token,day)
    if len(readback)!=400 or set(readback)!={row['sector_id'] for row in rows}:
        raise ValueError('SECTOR_LIFECYCLE_PG_READBACK_DENOMINATOR_MISMATCH')
    proof=dict(contract_id='SECTOR_LIFECYCLE_PG_OWNER_READBACK_R1',T0=day,
        head_token_sha256=hashlib.sha256(token.encode()).hexdigest(),head_digest=hashlib.sha256(canonical(head)).hexdigest(),
        owner_digest=binding['digest'],pg_schema=binding['schema'],pg_database=binding['database_identity'].get('database'),
        pg_database_oid=binding['database_identity'].get('database_oid'),pg_system_identifier=binding['database_identity'].get('system_identifier'),
        readback_rows=len(readback),independent_real_sample_count=owner['independent_real_sample_count'],
        independent_oracle_acceptance=owner['independent_oracle_acceptance'],readback_match=True,
        head_changed=False,auto_daily_changed=False,service_pid_used_for_environment=pid,authority_sha256=result['authority_sha256'])
    atomic_json(args.evidence,proof)
    print(json.dumps(proof,ensure_ascii=False,sort_keys=True))


if __name__=='__main__':main()

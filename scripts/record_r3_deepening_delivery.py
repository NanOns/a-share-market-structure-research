"""Actual downloaded cloud bytes, exact Git report blob and protected-head readback."""
from immediate_r3_common import *
from datetime import datetime,timezone
def main():
    D=OUT/'11_DEEPENING';offline=load(D/'OFFLINE_RECEIPT.json');stage=load(D/'STAGE_CONTRACT.json')
    for ref in stage['protected_heads']:checked(ref)
    records=[]
    for i,local,file_id,size,url in [(0,D/'DEEPENING_RESULT.md','1RDc0CDk7dBHZjN1M0_4A8GlB4hV0y8hE',3095,'https://drive.google.com/file/d/1RDc0CDk7dBHZjN1M0_4A8GlB4hV0y8hE/view?usp=drivesdk'),(1,path(offline['archive']),'1Ged3ZLZBRdxYx5uJl-qQadbs1h0KmKBT',1110409,'https://drive.google.com/file/d/1Ged3ZLZBRdxYx5uJl-qQadbs1h0KmKBT/view?usp=drivesdk')]:
        cloud=Path('G:/codex_tmp/r3_deepening_cloud_readback_'+str(i)+('.zip' if i else '.md'))
        assert sha(cloud)==sha(local) and cloud.stat().st_size==local.stat().st_size==size
        records.append(dict(file_id=file_id,url=url,folder_id='1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD',local=binding(local),cloud_readback=binding(cloud),cloud_metadata_bytes=size,verification='ACTUAL_FETCH_STREAM_DOWNLOAD_BYTES_AND_SHA256_MATCH',status='PASS'))
    result=git('rev-parse','HEAD');rel=(D/'DEEPENING_RESULT.md').relative_to(ROOT).as_posix();blob=subprocess.check_output(['git','show',result+':'+rel],cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest()==sha(D/'DEEPENING_RESULT.md')
    remote=git('ls-remote','origin','refs/heads/codex/v4-fp14-r2-repair').split()[0];assert remote==result
    write(OUT/'10_DRIVE_READBACK_RECEIPT.json',dict(contract='R3_DEEPENING_ACTUAL_CLOUD_DELIVERY_V1',observed_at=datetime.now(timezone.utc).isoformat(),BASE_SHA=stage['BASE_SHA'],RESULT_SHA=result,RESULT_CODE_SHA=offline['RESULT_SHA'],branch='codex/v4-fp14-r2-repair',remote_result_sha=remote,report_matches_result_git_blob=True,files=records,
      protected_heads=stage['protected_heads'],independent_offline_runs=offline['runs'],acceptance='ENGINEERING_PASS_SCOPED_EXACT_FORMAL_GAPS_OPEN',EXTERNAL_RECHECK_REQUESTED=True,EXTERNAL_ACCEPTANCE_PASS=False,
      user_exclusions=['BSE26','SZ.001235 user-reported delisted excluded this round'],production_loading='PROD_RESTART_PENDING',receipt_commit_follows_result=True))
    print(json.dumps(dict(RESULT_SHA=result,files=[dict(file_id=r['file_id'],bytes=r['local']['bytes'],sha256=r['local']['sha256'],status=r['status']) for r in records]),ensure_ascii=False))
if __name__=='__main__':main()

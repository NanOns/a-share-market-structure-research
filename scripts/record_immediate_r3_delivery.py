"""Receipt-only verification after real Drive download; no external sign-off."""
from immediate_r3_common import *
from datetime import datetime, timezone

def main():
    pairs=[('report','1XcXgBVSzjS1oqxVKX9jSEYC9lMbGT3Aa',OUT/'00_EXECUTION_RESULT_R3.md',Path('G:/codex_tmp/r3_drive_readback_0.md')),('review','1spjg_nV3jVSyOkDD6ItYFSkZe0kRN701',Path('G:/codex_tmp/V4_IMMEDIATE_R3_REVIEW_20261010.zip'),Path('G:/codex_tmp/r3_drive_readback_1.zip'))]
    items=[]
    for kind,id,local,download in pairs:
        assert local.read_bytes()==download.read_bytes(),kind
        items.append(dict(kind=kind,drive_id=id,url=f'https://drive.google.com/file/d/{id}/view',local=binding(local),actual_download=binding(download),readback='BYTE_AND_SHA256_MATCH'))
    stage=load(OUT/'STAGE_LEDGER.json')
    for ref in stage['protected']:checked(ref)
    write(OUT/'DRIVE_DELIVERY_RECEIPT.json',dict(RESULT_SHA=git('rev-parse','HEAD'),BASE_SHA=stage['BASE_SHA'],report_sha256=sha(pairs[0][2]),parent_folder_id='1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD',verified_at=datetime.now(timezone.utc).isoformat(),items=items,protected_heads='UNCHANGED',external_acceptance='NOT_GRANTED',remaining_engineering='See 08_REMAINING_LEDGER.json; not a full completion claim'))
    print(json.dumps(dict(RESULT_SHA=git('rev-parse','HEAD'),readback='BOTH_BYTE_AND_SHA256_MATCH')))

if __name__=='__main__':main()

"""Verify downloaded master and independent ZIP volumes against all payloads."""
from pathlib import Path
import argparse,hashlib,json,zipfile


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def verify(master,expected_master_sha256):
    master=Path(master)
    if digest(master)!=expected_master_sha256:raise ValueError('MASTER_SHA256_MISMATCH')
    with zipfile.ZipFile(master) as z:
        if z.testzip():raise ValueError('MASTER_CRC_FAILED')
        manifest=json.loads(z.read('DELIVERY_MANIFEST.json'))
    expected={r['path']:r for r in manifest['payload']};seen=set()
    for volume in manifest['volumes']:
        p=master.parent/volume['name']
        if p.stat().st_size!=volume['bytes'] or digest(p)!=volume['sha256']:
            raise ValueError('VOLUME_SHA256_MISMATCH:'+volume['name'])
        with zipfile.ZipFile(p) as z:
            if z.testzip():raise ValueError('VOLUME_CRC_FAILED')
            part=json.loads(z.read('VOLUME_MANIFEST.json'))
            if part['git_sha']!=manifest['git_sha']:raise ValueError('VOLUME_GIT_MISMATCH')
            if len(part['payload'])!=volume['payload_count']:raise ValueError('VOLUME_COUNT_MISMATCH')
            for row in part['payload']:
                if row!=expected.get(row['path']) or row['path'] in seen:raise ValueError('PAYLOAD_MANIFEST_MISMATCH')
                data=z.read(row['path'])
                if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
                    raise ValueError('PAYLOAD_SHA256_MISMATCH:'+row['path'])
                seen.add(row['path'])
    if seen!=set(expected):raise ValueError('INCOMPLETE_VOLUME_SET')
    return dict(contract_id='DD07_INDEPENDENT_ARCHIVE_READBACK_V1',acceptance='PASS_ALL_BYTES_CRC_SHA256',
        payload_count=len(seen),volume_count=len(manifest['volumes']),git_sha=manifest['git_sha'],
        operational_head_sha256=manifest['operational_head_sha256'],accepted_trade_date=manifest['accepted_trade_date'],
        external_acceptance='NOT_GRANTED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--master',required=True);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();print(json.dumps(verify(args.master,args.sha256)))

import struct
from production.daily import day_source_fingerprint
def test_tail_revision_changes_fingerprint(tmp_path):
 p=tmp_path/'vipdoc/sh/lday';p.mkdir(parents=True);f=p/'sh600000.day';f.write_bytes(struct.pack('<I',20260904)+b'a'*28);a=day_source_fingerprint(tmp_path)[0];f.write_bytes(struct.pack('<I',20260904)+b'b'*28);b=day_source_fingerprint(tmp_path)[0];assert a!=b

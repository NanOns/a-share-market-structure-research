import gzip
import pytest
from workbench_service.product_http_transport_r2 import accepts_gzip,encode

@pytest.mark.parametrize('header,expected',[('gzip',True),('br, gzip;q=0.5',True),('gzip;q=0, *;q=1',False),('*;q=1',True),('gzip;q=bad',False),('gzip;q=2',False),('',False)])
def test_negotiation(header,expected):assert accepts_gzip(header)==expected

def test_complete_payload_and_error_fields_unchanged():
    body={'context_token':'x'*64,'quality':'UNKNOWN','values':[{'amount':123.456,'missing':None,'source':'中文'*100}]*100}
    identity,plain=encode(body,'application/json; charset=utf-8','identity')
    compressed,codec=encode(body,'application/json; charset=utf-8','gzip')
    assert plain is None and codec=='gzip'
    assert gzip.decompress(compressed)==identity
    assert len(compressed)<len(identity)

def test_small_or_binary_not_transformed():
    for raw,kind in [(b'error','application/json'),(b'x'*9000,'application/octet-stream')]:
        assert encode(raw,kind,'gzip')==(raw,None)

def test_nonfinite_payload_still_rejected():
    with pytest.raises(ValueError):encode({'bad':float('nan')},'application/json','gzip')

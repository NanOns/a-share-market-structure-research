"""V4_HTTP_GZIP_TRANSPORT_R2: lossless negotiated payload compression."""
import gzip
import json

CONTRACT='V4_HTTP_GZIP_TRANSPORT_R2'

def accepts_gzip(header):
    values={}
    for item in header.lower().split(','):
        parts=[p.strip() for p in item.split(';')]
        if not parts[0]:continue
        quality=1.0
        for option in parts[1:]:
            if option.startswith('q='):
                try:quality=float(option[2:])
                except ValueError:quality=0.0
        if not 0<=quality<=1:quality=0.0
        values[parts[0]]=quality
    return values.get('gzip',values.get('*',0))>0

def encode(body,content_type,accept_encoding):
    raw=body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf8')
    if len(raw)>=4096 and content_type.startswith(('application/json','text/','application/javascript')) and accepts_gzip(accept_encoding):
        compressed=gzip.compress(raw,compresslevel=1,mtime=0)
        if len(compressed)<len(raw):return compressed,'gzip'
    return raw,None

from io import BytesIO
from pathlib import Path
import zipfile
import pytest

from workbench_input.pipeline import (
    DownloadPolicy, ExtractionPolicy, analyze_dynamic_metadata,
    capture_stable_metadata, download_official_package, replace_with_retry, safe_extract_zip,
    seal_source_bundle,
)

class Response:
    def __init__(self,data,declared=None,fail=False):
        self.data=BytesIO(data); self.headers={"Content-Length":str(declared if declared is not None else len(data)),"ETag":"test"}; self.fail=fail
    def read(self,n):
        value=self.data.read(n)
        if self.fail and not value: raise OSError("connection lost")
        return value
    def geturl(self): return "https://data.tdx.com.cn/vipdoc/hsjday.zip"
    def __enter__(self): return self
    def __exit__(self,*_): pass

def zip_bytes(entries):
    out=BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in entries: z.writestr(name,data)
    return out.getvalue()

def test_half_package_never_becomes_final(tmp_path):
    target=tmp_path/"hsjday.zip"
    with pytest.raises(Exception):
        download_official_package("https://data.tdx.com.cn/vipdoc/hsjday.zip",target,opener=lambda *_args,**_kw:Response(b"PKbroken",999))
    assert not target.exists() and not target.with_name(target.name+".part").exists()

def test_html_challenge_is_rejected(tmp_path):
    class Html(Response):
        def __init__(self): super().__init__(b"<script>challenge</script>") ; self.headers["Content-Type"]="text/html"
    with pytest.raises(ValueError,match="PACKAGE_HTML_CHALLENGE"):
        download_official_package("https://data.tdx.com.cn/vipdoc/hsjday.zip",tmp_path/"bad.zip",opener=lambda *_args,**_kw:Html())

@pytest.mark.parametrize("name",["../escape.day","/absolute.day","C:/escape.day"])
def test_unsafe_zip_paths_are_rejected(tmp_path,name):
    package=tmp_path/"bad.zip"; package.write_bytes(zip_bytes([(name,b"x")]))
    with pytest.raises(ValueError,match="ZIP_PATH_ESCAPE"): safe_extract_zip(package,tmp_path/"out")

def test_case_collision_and_expansion_limits(tmp_path):
    package=tmp_path/"bad.zip"; package.write_bytes(zip_bytes([("SH/A.day",b"x"),("sh/a.day",b"y")]))
    with pytest.raises(ValueError,match="ZIP_CASE_COLLISION"): safe_extract_zip(package,tmp_path/"out")
    bomb=tmp_path/"bomb.zip"; bomb.write_bytes(zip_bytes([("a.day",b"0"*1000)]))
    with pytest.raises(ValueError): safe_extract_zip(bomb,tmp_path/"bomb",ExtractionPolicy(max_expanded_bytes=100))

def test_extraction_replace_retries_transient_windows_lock(tmp_path, monkeypatch):
    package=tmp_path/"input.zip"; package.write_bytes(zip_bytes([("sh/lday/sh600001.day",b"x")]))
    destination=tmp_path/"out"; calls={"count":0}
    real_replace=__import__("workbench_input.pipeline",fromlist=["os"]).os.replace

    def flaky_replace(source,dest):
        calls["count"]+=1
        if calls["count"]<3: raise PermissionError(13,"access denied")
        return real_replace(source,dest)

    monkeypatch.setattr("workbench_input.pipeline.os.replace",flaky_replace)
    result=safe_extract_zip(package,destination)
    assert result["entry_count"]==1
    assert destination.joinpath("sh/lday/sh600001.day").read_bytes()==b"x"
    assert calls["count"]==3

def metadata_files(root):
    cache=root/"T0002/hq_cache"; cache.mkdir(parents=True)
    (cache/"tdxhy.cfg").write_text("1|600001|I1\n",encoding="gb18030")
    (cache/"tdxzs.cfg").write_text("行业|||||I1\n",encoding="gb18030")
    (cache/"infoharbor_block.dat").write_text("#GN_概念,x,G1\n1#600001\n",encoding="gb18030")
    for market in ("shs","szs","bjs"): (cache/f"{market}.tnf").write_bytes(b"0"*50+tnf_record("600001","测试"))
    (cache/"gbbq").write_bytes(b"x"); (cache/"gbbq.map").write_bytes(b"x")
    return cache

def test_metadata_change_during_stability_is_blocked(tmp_path):
    source=tmp_path/"tdx"; cache=metadata_files(source)
    def mutate(_): (cache/"tdxhy.cfg").write_text("changed",encoding="utf-8")
    with pytest.raises(ValueError,match="METADATA_SOURCE_CHANGING"):
        capture_stable_metadata(source,tmp_path/"snapshot",stable_seconds=0,sleeper=mutate)
    assert not (tmp_path/"snapshot").exists()

def test_missing_required_metadata_is_blocked(tmp_path):
    source=tmp_path/"tdx"; cache=source/"T0002/hq_cache"; cache.mkdir(parents=True)
    (cache/"tdxhy.cfg").write_text("x")
    with pytest.raises(ValueError,match="METADATA_REQUIRED_FILES_MISSING"):
        capture_stable_metadata(source,tmp_path/"snapshot",stable_seconds=0,sleeper=lambda _:None)

def tnf_record(code,name):
    record=bytearray(360); record[:6]=code.encode(); raw=name.encode("gb18030"); record[31:31+len(raw)]=raw; return bytes(record)

def dynamic_root(tmp_path,include_ref=True):
    root=tmp_path/"snapshot"; cache=root/"T0002/hq_cache"; cache.mkdir(parents=True)
    (cache/"shs.tnf").write_bytes(b"0"*50+tnf_record("600001","新股"))
    (cache/"tdxhy.cfg").write_text("1|600001|I1\n",encoding="gb18030")
    (cache/"tdxzs.cfg").write_text("行业|||||I1\n",encoding="gb18030")
    member="1#600001" if include_ref else "1#600999"
    (cache/"infoharbor_block.dat").write_text(f"#GN_新概念,x,G001\n{member}\n",encoding="gb18030")
    return root

def test_new_security_new_concept_and_member_are_discovered(tmp_path):
    result=analyze_dynamic_metadata(dynamic_root(tmp_path))
    assert result["changes"]["new_securities"]==["SH.600001"]
    assert "concept:G001" in result["changes"]["new_sectors"]
    assert ["concept","G001","SH.600001"] in result["changes"]["member_joins"]

def test_missing_membership_reference_blocks(tmp_path):
    with pytest.raises(ValueError,match="MEMBERSHIP_SECURITY_REFERENCE_MISSING"):
        analyze_dynamic_metadata(dynamic_root(tmp_path,False))

def test_valid_package_extract_metadata_and_seal_read_only_bundle(tmp_path):
    raw=zip_bytes([("vipdoc/sh/lday/sh600001.day",b"x"*32)])
    package=tmp_path/"hsjday.zip"
    meta=download_official_package("https://data.tdx.com.cn/vipdoc/hsjday.zip",package,opener=lambda *_args,**_kw:Response(raw))
    extraction=safe_extract_zip(package,tmp_path/"daily",ExtractionPolicy(max_compression_ratio=1000))
    source=tmp_path/"tdx"; metadata_files(source)
    snapshot=capture_stable_metadata(source,tmp_path/"metadata",stable_seconds=0,sleeper=lambda _:None)
    bundle=seal_source_bundle(tmp_path/"bundles",target_trade_date="2026-09-07",package=meta,extraction=extraction,metadata=snapshot,calendar_sha256="calendar")
    assert bundle["read_only"] and (tmp_path/"bundles"/bundle["source_bundle_id"]/"source_bundle.json").is_file()
    assert seal_source_bundle(tmp_path/"bundles",target_trade_date="2026-09-07",package=meta,extraction=extraction,metadata=snapshot,calendar_sha256="calendar")==bundle

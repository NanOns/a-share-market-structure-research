def test_bom(tmp_path):
 p=tmp_path/'x.csv';p.write_text('a',encoding='utf-8-sig');assert p.read_bytes().startswith(b'\xef\xbb\xbf')

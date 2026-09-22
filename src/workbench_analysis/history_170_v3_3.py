"""Verified consumer for the immutable P12-13 170-session dataset."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import duckdb
CONTRACT_ID="TODAY_RESEARCH_HISTORY_170_CONSUMER_V1"
def _sha(path):
 h=hashlib.sha256();
 with Path(path).open("rb") as f:
  for block in iter(lambda:f.read(8*1024*1024),b""):h.update(block)
 return h.hexdigest()
def resolve_dataset(root:Path)->tuple[Path,dict]:
 receipt=json.loads((root/"reports/p12_13/p12_13_170_stage_gate.json").read_text(encoding="utf-8"));path=Path(receipt["dataset_path"]);manifest=json.loads((path/"manifest.json").read_text(encoding="utf-8"))
 if receipt.get("acceptance")!="FULL_PASS" or manifest.get("output_digest")!=receipt.get("output_digest"):raise RuntimeError("HISTORY_170_IDENTITY_INVALID")
 for name,expected in manifest["files"].items():
  if _sha(path/name)!=expected:raise RuntimeError("HISTORY_170_HASH_MISMATCH:"+name)
 return path,manifest
def load_stock_facts(root:Path,trade_date:str)->tuple[dict[str,dict],dict]:
 path,manifest=resolve_dataset(root)
 with duckdb.connect(database=":memory:") as con:frame=con.execute("select * from read_parquet(?) where cast(trade_date as varchar)=?",[str(path/"stock_facts.parquet"),trade_date]).fetchdf()
 return ({str(row["security_id"]):row for row in frame.to_dict("records")},{"consumer_contract":CONTRACT_ID,"dataset_contract":manifest["contract_id"],"dataset_digest":manifest["output_digest"],"trade_date":trade_date,"rows":len(frame)})
__all__=["CONTRACT_ID","load_stock_facts","resolve_dataset"]

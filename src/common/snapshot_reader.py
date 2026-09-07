"""Safe readers for append-only, multi-date canonical snapshots.

The production contract permits historical rows to remain in a canonical
dataset.  Consumers must first reject future rows and only then select the
requested cutoff snapshot.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


def _cutoff_value(cutoff: Any) -> int:
    if isinstance(cutoff, datetime):
        return int(cutoff.strftime("%Y%m%d"))
    if isinstance(cutoff, date):
        return int(cutoff.strftime("%Y%m%d"))
    return int(str(cutoff).replace("-", ""))


def _date_values(frame: pd.DataFrame) -> pd.Series:
    if "date" not in frame.columns:
        raise ValueError("SNAPSHOT_DATE_COLUMN_MISSING")
    values = frame["date"]
    if pd.api.types.is_datetime64_any_dtype(values):
        return values.dt.strftime("%Y%m%d").astype(int)
    return values.map(lambda value: _cutoff_value(value) if pd.notna(value) else None)


def validate_dataset_dates(path: str | Path, cutoff: Any) -> dict[str, Any]:
    """Validate that *path* has no rows after cutoff.

    Returns a small audit object.  It intentionally does not require every
    row to equal cutoff, which is the core R0 multi-date behavior.
    """
    path = Path(path)
    limit = _cutoff_value(cutoff)
    if path.suffix.lower() in {".parquet", ".pq"}:
        column=pq.read_table(path,columns=["date"])["date"]
        kind=column.type
        if pa.types.is_date(kind): boundary=date(limit//10000,(limit//100)%100,limit%100)
        elif pa.types.is_timestamp(kind): boundary=datetime(limit//10000,(limit//100)%100,limit%100)
        else: boundary=limit
        distinct=pc.unique(column).to_pylist()
        normalized=sorted(_cutoff_value(x) for x in distinct if x is not None)
        future_count=int(pc.sum(pc.cast(pc.greater(column,pa.scalar(boundary,type=kind)),pa.int64())).as_py() or 0)
        return {"path":str(path),"cutoff_date":str(limit),"row_count":pq.ParquetFile(path).metadata.num_rows,
                "distinct_dates":normalized,"future_row_count":future_count,"valid":future_count==0}
    frame = _read(path)
    values = _date_values(frame)
    future = values[values > limit]
    return {
        "path": str(path),
        "cutoff_date": str(limit),
        "row_count": int(len(frame)),
        "distinct_dates": sorted({int(x) for x in values.dropna().tolist()}),
        "future_row_count": int(len(future)),
        "valid": len(future) == 0,
    }


def assert_no_future_rows(path: str | Path, cutoff: Any) -> bool:
    audit = validate_dataset_dates(path, cutoff)
    if not audit["valid"]:
        raise ValueError(f"FUTURE_SNAPSHOT:{audit['path']}:{audit['cutoff_date']}")
    return True


def read_snapshot(path: str | Path, cutoff: Any, *, columns: list[str] | None = None) -> pd.DataFrame:
    """Read only the cutoff rows after validating the whole dataset."""
    path = Path(path)
    assert_no_future_rows(path, cutoff)
    frame = _read(path, columns=columns)
    limit = _cutoff_value(cutoff)
    values = _date_values(frame)
    return frame.loc[values == limit].reset_index(drop=True)


def _read(path: Path, *, columns: list[str] | None = None) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pq.read_table(path, columns=columns).to_pandas()
    return pd.read_csv(path, usecols=columns)

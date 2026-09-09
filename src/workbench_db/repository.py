"""Repository boundary and idempotent historical import."""
from __future__ import annotations

import csv
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .digest import VERSION as DIGEST_VERSION, logical_digest, normalize_csv_row
from .owner import DatabaseOwner


SCHEMA_VERSION = "workbench-schema-v1.0"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = [normalize_csv_row(row) for row in reader]
    return columns, rows


def _parquet_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    table = pq.read_table(path)
    return list(table.column_names), table.to_pylist()


def _bulk_insert(con: duckdb.DuckDBPyConnection, table: str, rows: list[dict[str, Any]], columns: list[str]) -> None:
    if not rows:
        return
    batch = pa.Table.from_pylist(rows)
    con.register("_m1_bulk_batch", batch)
    try:
        select = ", ".join(f"{column}::JSON" if column == "payload_json" else column for column in columns)
        names = ", ".join(columns)
        con.execute(f"INSERT INTO {table} ({names}) SELECT {select} FROM _m1_bulk_batch")
    finally:
        con.unregister("_m1_bulk_batch")


class WorkbenchRepository:
    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else self.root / "data/database/market_research.duckdb"
        self.owner = DatabaseOwner(self.database_path)
        self.connection: duckdb.DuckDBPyConnection | None = None

    def open(self) -> "WorkbenchRepository":
        self.owner.acquire()
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = duckdb.connect(str(self.database_path))
            self.connection.execute((Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8"))
            self.connection.execute("INSERT INTO schema_migrations VALUES (?, ?) ON CONFLICT DO NOTHING", [SCHEMA_VERSION, datetime.now(timezone.utc)])
        except Exception:
            self.owner.release()
            raise
        return self

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.owner.release()

    def __enter__(self) -> "WorkbenchRepository":
        return self.open()

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        assert self.connection is not None
        self.connection.execute("BEGIN TRANSACTION")
        try:
            yield self.connection
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def _artifact(self, con: duckdb.DuckDBPyConnection, publication_id: str, name: str, path: Path, rows: list[dict[str, Any]], columns: list[str], primary_key: list[str]) -> dict[str, Any]:
        digest = logical_digest(rows, columns, primary_key)
        con.execute("INSERT INTO publication_artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING", [publication_id, name, str(path), _sha(path), DIGEST_VERSION, digest["sha256"], digest["row_count"], _json(columns), _json(primary_key)])
        return digest

    def import_publication(self, release_path: str | Path, *, revision: int, make_head: bool = True) -> dict[str, Any]:
        path = Path(release_path).resolve()
        receipt = json.loads((path / "PRODUCTION_RECEIPT.json").read_text(encoding="utf-8"))
        if receipt.get("status") != "SUCCESS":
            raise ValueError("RELEASE_NOT_SUCCESS")
        publication_id = str(receipt["run_id"])
        trade_date = datetime.strptime(str(receipt["cutoff_date"]), "%Y%m%d").date()
        assert self.connection is not None
        existing = self.connection.execute("SELECT status FROM publications WHERE publication_id=?", [publication_id]).fetchone()
        if existing and existing[0] == "SUCCESS":
            stored = self.connection.execute(
                "SELECT trade_date, revision, source_manifest_sha256, source_identity_sha256, computation_identity_sha256, render_identity_sha256 "
                "FROM publications WHERE publication_id=?",
                [publication_id],
            ).fetchone()
            expected = (
                trade_date,
                revision,
                receipt.get("manifest_sha256"),
                receipt.get("source_identity", {}).get("sha256"),
                receipt.get("computation_identity", {}).get("sha256"),
                receipt.get("render_identity", {}).get("sha256"),
            )
            if stored != expected:
                raise ValueError("EXISTING_PUBLICATION_IDENTITY_MISMATCH")
            artifacts = self.connection.execute(
                "SELECT source_path, file_sha256 FROM publication_artifacts WHERE publication_id=?",
                [publication_id],
            ).fetchall()
            if not artifacts or any(not Path(source).is_file() or _sha(Path(source)) != digest for source, digest in artifacts):
                raise ValueError("EXISTING_PUBLICATION_ARTIFACT_MISMATCH")
            return {"publication_id": publication_id, "trade_date": trade_date.isoformat(), "reused": True, "artifacts": {}}
        if existing:
            raise ValueError("INCOMPLETE_PUBLICATION_EXISTS")
        artifacts: dict[str, Any] = {}
        with self.transaction() as con:
            con.execute("INSERT INTO publications VALUES (?, ?, ?, 'IMPORTING', ?, ?, ?, ?, ?, ?, ?, ?)", [publication_id, trade_date, revision, receipt.get("source_revision_id"), receipt.get("production_version"), receipt.get("manifest_sha256"), receipt.get("source_identity", {}).get("sha256"), receipt.get("computation_identity", {}).get("sha256"), receipt.get("render_identity", {}).get("sha256"), str(path), datetime.now(timezone.utc)])
            specs = {
                "stocks.csv": ("stock_daily", ["security_id"], "security_id"),
                "sectors.csv": ("sector_daily", ["sector_id"], "sector_id"),
                "candidates.csv": ("candidate_daily", ["security_id"], "security_id"),
            }
            for filename, (table, primary_key, id_column) in specs.items():
                columns, rows = _csv_rows(path / filename)
                artifacts[filename] = self._artifact(con, publication_id, filename, path / filename, rows, columns, primary_key)
                if table == "stock_daily":
                    values = [{"publication_id": publication_id, "security_id": row[id_column], "trade_date": trade_date, "security_name": row.get("security_name"), "primary_pattern": row.get("primary_pattern"), "payload_json": _json(row)} for row in rows]
                    _bulk_insert(con, "stock_daily", values, ["publication_id", "security_id", "trade_date", "security_name", "primary_pattern", "payload_json"])
                elif table == "sector_daily":
                    values = [{"publication_id": publication_id, "sector_id": row[id_column], "trade_date": trade_date, "sector_name": row.get("sector_name"), "sector_type": row.get("sector_type"), "primary_pattern": row.get("primary_pattern"), "display_rank": float(row["display_rank"]) if row.get("display_rank") else None, "payload_json": _json(row)} for row in rows]
                    _bulk_insert(con, "sector_daily", values, ["publication_id", "sector_id", "trade_date", "sector_name", "sector_type", "primary_pattern", "display_rank", "payload_json"])
                else:
                    values = [{"publication_id": publication_id, "security_id": row[id_column], "trade_date": trade_date, "security_name": row.get("security_name"), "primary_pattern": row.get("primary_pattern"), "research_priority": row.get("research_priority"), "payload_json": _json(row)} for row in rows]
                    _bulk_insert(con, "candidate_daily", values, ["publication_id", "security_id", "trade_date", "security_name", "primary_pattern", "research_priority", "payload_json"])
            self._import_v2(con, publication_id, trade_date, artifacts)
            self._import_workbench_ranking(con, publication_id, trade_date, artifacts)
            self._import_market_and_membership(con, publication_id, trade_date, artifacts)
            con.execute("UPDATE publications SET status='SUCCESS' WHERE publication_id=?", [publication_id])
            if make_head:
                con.execute("INSERT INTO publication_heads VALUES (?, ?) ON CONFLICT (trade_date) DO UPDATE SET publication_id=excluded.publication_id", [trade_date, publication_id])
        return {"publication_id": publication_id, "trade_date": trade_date.isoformat(), "artifacts": artifacts}

    def _import_workbench_ranking(self, con, publication_id, trade_date, artifacts):
        base = self.root / "reports/workbench" / trade_date.strftime("%Y%m%d") / publication_id
        matches = sorted(base.glob("*/V2_QUEUE_RANKING.parquet"), key=lambda p: p.stat().st_mtime_ns, reverse=True)
        if not matches:
            raise FileNotFoundError(f"QUEUE_RANKING_MISSING:{base}")
        path = matches[0]
        columns, rows = _parquet_rows(path)
        artifacts["queue_rankings"] = self._artifact(con, publication_id, "queue_rankings", path, rows, columns, ["security_id"])
        values = [{"publication_id": publication_id, "security_id": row["security_id"], "payload_json": _json(row)} for row in rows]
        _bulk_insert(con, "queue_rankings", values, ["publication_id", "security_id", "payload_json"])

    def _import_v2(self, con: duckdb.DuckDBPyConnection, publication_id: str, trade_date: Any, artifacts: dict[str, Any]) -> None:
        base = self.root / "reports/shadow/v2" / trade_date.strftime("%Y%m%d")
        queue_files = {
            "STEADY": base / "steady_trend/STEADY_TREND_V2_SHADOW.parquet",
            "PULLBACK": base / "strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet",
            "BREAKOUT": base / "breakout_prep/BREAKOUT_PREP_V2_SHADOW.parquet",
            "LEADER": base / "sector_leader/SECTOR_LEADER_V2_SHADOW.parquet",
            "EARLY": base / "early_mover/EARLY_MOVER_V2_SHADOW.parquet",
        }
        for queue, path in queue_files.items():
            if not path.is_file():
                raise FileNotFoundError(f"V2_QUEUE_MISSING:{queue}:{path}")
            columns, rows = _parquet_rows(path)
            name = f"structure_details/{queue}"
            artifacts[name] = self._artifact(con, publication_id, name, path, rows, columns, ["security_id"])
            values = [{"publication_id": publication_id, "queue_name": queue, "security_id": row["security_id"], "trade_date": trade_date, "payload_json": _json(row)} for row in rows]
            _bulk_insert(con, "structure_details", values, ["publication_id", "queue_name", "security_id", "trade_date", "payload_json"])
        memberships = base / "priority/V2_QUEUE_MEMBERSHIP.parquet"
        if not memberships.is_file():
            raise FileNotFoundError(f"V2_MEMBERSHIPS_MISSING:{memberships}")
        columns, rows = _parquet_rows(memberships)
        artifacts["queue_memberships"] = self._artifact(con, publication_id, "queue_memberships", memberships, rows, columns, ["security_id", "queue_name"])
        values = [{"publication_id": publication_id, "queue_name": row["queue_name"], "security_id": row["security_id"], "queue_tier": row["queue_tier"], "source_v2_class": row.get("source_v2_class"), "payload_json": _json(row)} for row in rows]
        _bulk_insert(con, "queue_memberships", values, ["publication_id", "queue_name", "security_id", "queue_tier", "source_v2_class", "payload_json"])
        board = base / "priority/V2_UNIFIED_RESEARCH_BOARD.parquet"
        if not board.is_file():
            raise FileNotFoundError(f"V2_BOARD_MISSING:{board}")
        columns, rows = _parquet_rows(board)
        artifacts["unified_board"] = self._artifact(con, publication_id, "unified_board", board, rows, columns, ["security_id"])
        values = [{"publication_id": publication_id, "security_id": row["security_id"], "trade_date": trade_date, "payload_json": _json(row)} for row in rows]
        _bulk_insert(con, "unified_board", values, ["publication_id", "security_id", "trade_date", "payload_json"])

    def _import_market_and_membership(self, con: duckdb.DuckDBPyConnection, publication_id: str, trade_date: Any, artifacts: dict[str, Any]) -> None:
        market_path = self.root / "data/market/market_regime_daily.parquet"
        if not market_path.is_file(): raise FileNotFoundError(f"MARKET_REGIME_MISSING:{market_path}")
        columns, all_rows = _parquet_rows(market_path)
        rows = [row for row in all_rows if str(row.get("date")) == trade_date.isoformat()]
        if not rows: raise ValueError(f"MARKET_REGIME_DATE_MISSING:{trade_date}")
        artifacts["market_daily"] = self._artifact(con, publication_id, "market_daily", market_path, rows, columns, ["date"])
        con.execute("INSERT INTO market_daily VALUES (?, ?, ?)", [publication_id, trade_date, _json(rows[0])])
        membership_path = self.root / "data/sectors/sector_membership_daily.parquet"
        if not membership_path.is_file(): raise FileNotFoundError(f"MEMBERSHIP_MISSING:{membership_path}")
        columns, all_rows = _parquet_rows(membership_path)
        rows = [row for row in all_rows if str(row.get("date")) == trade_date.isoformat()]
        if not rows: raise ValueError(f"MEMBERSHIP_DATE_MISSING:{trade_date}")
        digest = logical_digest(rows, columns, ["sector_id", "security_id"])
        snapshot_id = digest["sha256"]
        artifacts["membership_entries"] = self._artifact(con, publication_id, "membership_entries", membership_path, rows, columns, ["sector_id", "security_id"])
        con.execute("INSERT INTO membership_snapshots VALUES (?, ?, ?, ?, ?)", [snapshot_id, trade_date, rows[0].get("snapshot_version", "UNKNOWN"), digest["sha256"], digest["row_count"]])
        batch = [{"membership_snapshot_id": snapshot_id, "sector_id": row["sector_id"], "security_id": row["security_id"], "payload_json": _json(row)} for row in rows]
        _bulk_insert(con, "membership_entries", batch, ["membership_snapshot_id", "sector_id", "security_id", "payload_json"])
        con.execute("INSERT INTO publication_memberships VALUES (?, ?)", [publication_id, snapshot_id])

    def table_count(self, table: str, publication_id: str | None = None) -> int:
        assert self.connection is not None
        allowed = {"publications", "publication_heads", "stock_daily", "sector_daily", "candidate_daily", "market_daily", "structure_details", "queue_memberships", "unified_board", "queue_rankings", "membership_entries", "publication_artifacts"}
        if table not in allowed:
            raise ValueError("TABLE_NOT_ALLOWED")
        if publication_id:
            return int(self.connection.execute(f"SELECT count(*) FROM {table} WHERE publication_id=?", [publication_id]).fetchone()[0])
        return int(self.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])

    def payload_rows(self, table: str, publication_id: str) -> list[dict[str, Any]]:
        assert self.connection is not None
        if table not in {"stock_daily", "sector_daily", "candidate_daily", "market_daily", "structure_details", "queue_memberships", "unified_board", "queue_rankings"}:
            raise ValueError("TABLE_NOT_ALLOWED")
        return [json.loads(value) for (value,) in self.connection.execute(f"SELECT payload_json FROM {table} WHERE publication_id=?", [publication_id]).fetchall()]

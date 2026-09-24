"""Read and hash-check the accepted M13 technical result for Focus factors."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from psycopg import sql

from workbench_analysis.technical import (TECHNICAL_RESULT_COLUMNS,
                                          _technical_hash)

from .contracts import digest


CONTRACT_ID = "FOCUS_ACCEPTED_TECHNICAL_FACTS_V1"


@dataclass(frozen=True)
class TechnicalFact:
    security_id: str
    trade_date: date
    contract_id: str
    price_basis: str
    adjusted_close: float | None
    ma5: float | None
    ma20: float | None
    ret5: float | None
    quality: str
    result_object_id: str
    value_hash: str
    fact_digest: str


@dataclass(frozen=True)
class AcceptedTechnical:
    snapshot_id: str
    slice_id: str
    result_object_id: str
    value_hash: str
    row_count: int
    facts: dict[str, TechnicalFact]
    fact_digest: str


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str)


def read_accepted_technical(repository, *, publication_id: str,
                            trade_date: date,
                            expected_normalized_sha256: str) -> AcceptedTechnical:
    """Select one accepted technical snapshot and verify its full object hash."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select h.snapshot_id,s.status,s.cutoff_date,e.slice_id,"
            "b.result_object_id,b.identity_evidence,o.domain,o.schema_version,"
            "o.semantic_contract,o.value_hash,o.row_count,o.storage_kind "
            "from {}.analysis_snapshot_heads h "
            "join {}.analysis_snapshots s using(snapshot_id) "
            "join {}.analysis_snapshot_entries e on e.snapshot_id=h.snapshot_id "
            "and e.domain='technical' and e.trade_date=h.trade_date "
            "join {}.analysis_slice_result_bindings b using(slice_id) "
            "join {}.analysis_result_objects o using(result_object_id) "
            "where h.trade_date=%s and h.publication_id=%s "
            "and h.domain in ('LOCAL_OBSERVED','LOCAL_RECONSTRUCTED')"
        ).format(schema, schema, schema, schema, schema),
            (trade_date, publication_id))
        bindings = cur.fetchall()
        if len(bindings) != 1:
            raise ValueError("accepted technical snapshot unavailable or ambiguous")
        (snapshot_id, status, cutoff, slice_id, object_id, identity_evidence,
         domain, schema_version, semantic, value_hash, expected_count,
         storage_kind) = bindings[0]
        if (status != "SUCCESS" or cutoff != trade_date or domain != "technical" or
                schema_version != "technical-result-rows-v1" or
                semantic != "TECHNICAL_RESULT_V3" or storage_kind not in {"DUCKDB", "PARQUET"}):
            raise ValueError("accepted technical identity mismatch")
        if isinstance(identity_evidence, str):
            identity_evidence = json.loads(identity_evidence)
        source_basis = identity_evidence.get("source_basis", {}) if isinstance(identity_evidence, dict) else {}
        input_artifacts = source_basis.get("input_artifacts", {}) if isinstance(source_basis, dict) else {}
        if input_artifacts.get("normalized") != expected_normalized_sha256:
            raise ValueError("technical/normalized artifact identity mismatch")
        columns = sql.SQL(",").join(map(sql.Identifier, TECHNICAL_RESULT_COLUMNS))
        cur.execute(sql.SQL("select {} from {}.technical_result_rows "
                            "where result_object_id=%s order by security_id,trade_date")
                    .format(columns, schema), (object_id,))
        records = [dict(zip(TECHNICAL_RESULT_COLUMNS, row)) for row in cur.fetchall()]
    if len(records) != int(expected_count):
        raise ValueError("accepted technical row count mismatch")
    if len({(row["security_id"], row["trade_date"]) for row in records}) != len(records):
        raise ValueError("duplicate accepted technical key")
    for row in records:
        row["quality_codes"] = _json_text(row["quality_codes"])
        row["basis_json"] = _json_text(row["basis_json"])
    actual_hash, actual_count, _ = _technical_hash(records)
    if actual_count != int(expected_count) or actual_hash != str(value_hash):
        raise ValueError("accepted technical value hash mismatch")
    current_rows = [row for row in records if row["trade_date"] == trade_date]
    facts: dict[str, TechnicalFact] = {}
    for row in current_rows:
        try:
            quality_codes = json.loads(row["quality_codes"])
        except (TypeError, json.JSONDecodeError):
            quality_codes = ["INVALID_QUALITY_EVIDENCE"]
        quality = "READY" if row["validity"] == "VALID" and not quality_codes else "PARTIAL"
        evidence = {"contract_id": CONTRACT_ID, "snapshot_id": str(snapshot_id),
                    "slice_id": str(slice_id), "result_object_id": str(object_id),
                    "value_hash": str(value_hash), "trade_date": trade_date,
                    "security_id": str(row["security_id"]),
                    "technical_contract_id": str(row["contract_id"]),
                    "price_basis": str(row["price_basis"]),
                    "adjusted_close": row["adj_close"], "ma5": row["ma5"],
                    "ma20": row["ma20"], "ret5": row["ret5"],
                    "validity": row["validity"], "quality_codes": quality_codes}
        fact = TechnicalFact(str(row["security_id"]), trade_date,
                             str(row["contract_id"]), str(row["price_basis"]),
                             row["adj_close"], row["ma5"], row["ma20"], row["ret5"],
                             quality, str(object_id), str(value_hash), digest(evidence))
        if fact.security_id in facts:
            raise ValueError("duplicate accepted technical daily fact")
        facts[fact.security_id] = fact
    return AcceptedTechnical(str(snapshot_id), str(slice_id), str(object_id),
                             str(value_hash), int(expected_count), facts,
                             digest({"contract_id": CONTRACT_ID,
                                     "snapshot_id": str(snapshot_id),
                                     "result_object_id": str(object_id),
                                     "value_hash": str(value_hash),
                                     "trade_date": trade_date,
                                     "facts": [(sid, fact.fact_digest)
                                               for sid, fact in sorted(facts.items())]}))

from datetime import date
from hashlib import sha256
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.focus_tracker.materialize import (PathRequest, materialize_stock_facts,
                                           materialize_stock_paths, write_observation_input)
from src.focus_tracker.sector_basket import (SectorBasket, baskets_from_accepted_publication,
                                             one_day_sector_return)
from src.focus_tracker.sector_path import frozen_sector_path


def _source(tmp_path, *, missing=False):
    days = [date(2026, 9, 21), date(2026, 9, 22)]
    rows = []
    for day, price in zip(days, [10.0, 11.0]):
        rows.append({"security_id": "000001.SZ", "date": day,
                     "raw_open": price, "raw_high": price + 1,
                     "raw_low": price - 1, "raw_close": price,
                     "raw_volume": 100, "raw_amount": 1000,
                     "qfq_mul": 1.0, "qfq_add": 0.0,
                     "adjustment_status": "VERIFIED", "adjustment_version": "local-v1",
                     "has_actual_bar": not (missing and day == days[0]),
                     "is_master_session": True,
                     "missing_state": "BAR" if not (missing and day == days[0]) else "FILE_MISSING"})
    path = tmp_path / "normalized.parquet"
    pq.write_table(pa.Table.from_pylist(rows), path)
    return path, sha256(path.read_bytes()).hexdigest(), days


def test_materialize_real_bar_path_and_immutable_artifact(tmp_path):
    path, source_hash, days = _source(tmp_path)
    facts = materialize_stock_facts(normalized_path=path, expected_sha256=source_hash,
                                    trade_date=days[1], starts={"000001.SZ": days[0]})
    assert len(facts) == 1
    assert facts[0].quality_status == "READY"
    assert facts[0].return_since_start == "0.1"
    output = tmp_path / "focus-input.json"
    first_hash = write_observation_input(output_path=output, trade_date=days[1],
                                         source_identity_digest="source-a",
                                         normalized_sha256=source_hash, facts=facts)
    assert write_observation_input(output_path=output, trade_date=days[1],
                                   source_identity_digest="source-a",
                                   normalized_sha256=source_hash, facts=facts) == first_hash
    with pytest.raises(ValueError, match="immutable observation artifact conflict"):
        write_observation_input(output_path=output, trade_date=days[1],
                                source_identity_digest="source-b",
                                normalized_sha256=source_hash, facts=facts)


def test_materialize_missing_bar_fails_closed(tmp_path):
    path, source_hash, days = _source(tmp_path, missing=True)
    facts = materialize_stock_facts(normalized_path=path, expected_sha256=source_hash,
                                    trade_date=days[1], starts={"000001.SZ": days[0]})
    assert facts[0].quality_status == "DATA_UNAVAILABLE"
    assert facts[0].return_since_start is None


def test_shared_scan_projects_two_anchors_without_merging_source_semantics(tmp_path):
    path, source_hash, days = _source(tmp_path)
    facts = materialize_stock_paths(
        normalized_path=path, expected_sha256=source_hash, trade_date=days[1],
        requests=[PathRequest("000001.SZ", days[0]), PathRequest("000001.SZ", days[1])])
    assert {(fact.start_trade_date, fact.return_since_start) for fact in facts} == {
        (days[0], "0.1"), (days[1], "0")}
    with pytest.raises(ValueError, match="duplicate path request"):
        materialize_stock_paths(normalized_path=path, expected_sha256=source_hash,
                                trade_date=days[1], requests=[PathRequest("000001.SZ", days[0])] * 2)


def test_materialize_rejects_artifact_identity_mismatch(tmp_path):
    path, _, days = _source(tmp_path)
    with pytest.raises(ValueError, match="digest mismatch"):
        materialize_stock_facts(normalized_path=path, expected_sha256="0" * 64,
                                trade_date=days[1], starts={"000001.SZ": days[0]})


def test_sector_basket_uses_bound_revision_and_deduplicates_members():
    class Repository:
        connection = object()

        def relation_edges_for_publication(self, publication_id):
            assert publication_id == "pub-1"
            return [("pub-1", "scope-1", 4, "sector-1", "stock-1", "x", 1, None),
                    ("pub-1", "scope-1", 4, "sector-1", "stock-1", "y", 2, None),
                    ("pub-1", "scope-1", 4, "sector-1", "stock-2", "x", 1, None)]

    basket = baskets_from_accepted_publication(Repository(), "pub-1", {"sector-1"})[0]
    assert basket.security_ids == ("stock-1", "stock-2")
    assert basket.source_identity == "scope-1:4"


def test_sector_median_and_coverage_gate():
    basket = SectorBasket("sector-1", ("a", "b", "c", "d", "e"),
                          "BOUND_RELATION_REVISION", "scope:1", "digest")
    ready = one_day_sector_return(basket, {"a": Decimal("0.01"),
                                           "b": Decimal("0.03"),
                                           "c": Decimal("0.05"),
                                           "d": Decimal("0.07")})
    assert ready.quality_status == "READY"
    assert ready.median_return == Decimal("0.04")
    assert ready.coverage == Decimal("0.8")
    gap = one_day_sector_return(basket, {"a": Decimal("0.01"),
                                         "b": Decimal("0.03"),
                                         "c": Decimal("0.05")})
    assert gap.quality_status == "DATA_UNAVAILABLE"
    assert gap.median_return is None


def test_frozen_sector_nav_breaks_at_gap_and_does_not_bridge():
    days = [date(2026, 9, 18), date(2026, 9, 21), date(2026, 9, 22)]
    basket = SectorBasket("s", ("a", "b", "c", "d", "e"),
                          "BOUND_RELATION_REVISION", "scope:1", "digest")
    rows = {}
    for sid in basket.security_ids:
        rows[sid] = {}
        for day, price in zip(days, [10, 11, 12]):
            rows[sid][day] = {"has_actual_bar": not (day == days[1] and sid in {"c", "d", "e"}),
                              "qfq_mul": 1, "qfq_add": 0,
                              "adjustment_status": "VERIFIED",
                              "adjustment_version": "local-v1",
                              "raw_open": price, "raw_high": price,
                              "raw_low": price, "raw_close": price}
    result = frozen_sector_path(basket=basket, sessions=days, member_rows=rows)
    assert result[0].nav == Decimal(1)
    assert result[1].one_day.coverage == Decimal("0.4")
    assert result[1].nav is None
    assert result[2].nav is None


def test_frozen_sector_anchor_requires_actual_covered_members():
    first, second = date(2026, 9, 21), date(2026, 9, 22)
    basket = SectorBasket("s", ("a", "b", "c", "d", "e"),
                          "BOUND_RELATION_REVISION", "scope:1", "digest")
    rows = {}
    for sid in basket.security_ids:
        rows[sid] = {day: {"has_actual_bar": day == second or sid in {"a", "b", "c"},
                           "qfq_mul": 1, "qfq_add": 0,
                           "adjustment_status": "VERIFIED",
                           "adjustment_version": "local-v1",
                           "raw_open": 10, "raw_high": 10,
                           "raw_low": 10, "raw_close": 10}
                     for day in (first, second)}
    result = frozen_sector_path(basket=basket, sessions=[first, second], member_rows=rows)
    assert result[0].nav is None
    assert result[1].nav is None

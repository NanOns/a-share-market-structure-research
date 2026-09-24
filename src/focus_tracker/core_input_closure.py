"""FOCUS-03 full-day immutable input closure before a core transaction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .contracts import FocusKey, digest, source_item_digest
from .daily_plan import PlannedDay, require_tracking_coverage
from .input_manifest import CONTRACT_ID as MANIFEST_CONTRACT, DailyInputManifest
from .materialize import StockFact
from .observation import Observation
from .source_reader import AcceptedSources
from .states import CONTRACT_ID as PATH_CONTRACT


CONTRACT_ID = "FOCUS_CORE_INPUT_CLOSURE_V2"


@dataclass(frozen=True)
class ObservationItem:
    key: FocusKey
    observation: Observation


@dataclass(frozen=True)
class CoreInputClosure:
    trade_date: str
    source_count: int
    observation_count: int
    stock_fact_count: int
    input_digest: str


def validate_core_input_closure(*, manifest: DailyInputManifest,
                                sources: AcceptedSources, plan: PlannedDay,
                                stock_facts: Sequence[StockFact],
                                observations: Sequence[ObservationItem]) -> CoreInputClosure:
    """Require exact source/tracking/observation sets and frozen digests.

    The caller still has to enforce the manifest release gate and current PG
    authority inside the eventual writer transaction. This check rejects
    incomplete or internally inconsistent computed batches before any write.
    """
    payload = manifest.payload
    if (manifest.trade_date != sources.trade_date or plan.trade_date != sources.trade_date
            or payload.get("trade_date") != sources.trade_date
            or payload.get("source_identity_digest") != sources.source_identity_digest
            or payload.get("tracking_plan_digest") != plan.plan_digest
            or digest(payload) != manifest.sha256):
        raise ValueError("core manifest authority/digest mismatch")
    if payload.get("contract_id") != MANIFEST_CONTRACT:
        raise ValueError("unknown core manifest contract")
    source_keys = [row.key for row in sources.rows]
    if len(set(source_keys)) != len(source_keys):
        raise ValueError("duplicate core source key")
    if any(row.trade_date != sources.trade_date or
           source_item_digest(row.source_item_key, row.source_contract_id,
                              row.source_facts) != row.source_item_digest
           for row in sources.rows):
        raise ValueError("core source row identity mismatch")
    family_rows = {family: [] for family in sources.capabilities}
    for row in sources.rows:
        if row.key.source_family not in family_rows:
            raise ValueError("unregistered core source family")
        family_rows[row.key.source_family].append(row.source_item_digest)
    expected_families = {
        family: {"capability": sources.capabilities[family],
                 "count": len(items), "digest": digest(items)}
        for family, items in sorted(family_rows.items())}
    if payload.get("source_family_rows") != expected_families:
        raise ValueError("core source family count/digest mismatch")
    require_tracking_coverage(
        tracking_keys=plan.tracking_keys, source_keys=set(source_keys),
        pending_followup=set(plan.pending_followup_keys),
        due_outcomes=set(plan.due_outcome_keys))
    decisions = plan.episode_tracking or plan.decisions
    decision_by_episode = {(item.key, item.episode_id): item for item in decisions}
    expected_episodes = set(decision_by_episode)
    if len(expected_episodes) != len(decisions):
        raise ValueError("duplicate core episode tracking identity")
    by_episode: dict[tuple[FocusKey, str], Observation] = {}
    for item in observations:
        identity = (item.key, item.observation.episode_id)
        if identity in by_episode:
            raise ValueError("duplicate core observation episode identity")
        by_episode[identity] = item.observation
    if set(by_episode) != expected_episodes:
        raise ValueError("core observation set differs from episode tracking union")
    require_tracking_coverage(
        tracking_keys=tuple({key for key, _ in by_episode}), source_keys=set(source_keys),
        pending_followup=set(plan.pending_followup_keys),
        due_outcomes=set(plan.due_outcome_keys))
    expected_paths = {(request.security_id, request.start_trade_date)
                      for request in plan.stock_path_requests}
    facts_by_path = {(fact.security_id, fact.start_trade_date): fact
                     for fact in stock_facts}
    if (len(facts_by_path) != len(stock_facts) or
            set(facts_by_path) != expected_paths or
            any(fact.trade_date != sources.trade_date for fact in stock_facts)):
        raise ValueError("core stock fact set differs from tracking plan")
    manifest_facts = [(fact.security_id, fact.start_trade_date,
                       fact.quality_status, fact.input_digest)
                      for fact in sorted(stock_facts,
                                         key=lambda item: (item.security_id,
                                                           item.start_trade_date))]
    if payload.get("stock_facts") != manifest_facts:
        raise ValueError("core stock fact digest differs from manifest")
    stock_digests: dict[str, set[str]] = {}
    for fact in stock_facts:
        stock_digests.setdefault(fact.security_id, set()).add(fact.input_digest)
    basket_digests = dict(payload.get("entry_baskets", []))
    strength_digests = dict(payload.get("member_strength", []))
    sector_episode_ids = {item.episode_id for item in decisions
                          if item.key.entity_type == "SECTOR" and item.episode_id}
    if (set(basket_digests) != sector_episode_ids or
            set(strength_digests) != sector_episode_ids):
        raise ValueError("core sector fact set differs from tracking plan")
    for (key, episode), observation in by_episode.items():
        decision = decision_by_episode[(key, episode)]
        evidence_key = observation.evidence.get("key")
        if (decision.episode_id is None or
                observation.episode_id != decision.episode_id or
                observation.source_membership_state != decision.membership or
                observation.membership_phase != decision.phase or
                observation.evidence.get("path_contract_id") != PATH_CONTRACT or
                observation.evidence.get("contract_id") != "FOCUS_OBSERVATION_ASSEMBLY_V2" or
                observation.evidence.get("path_state_v2", {}).get("contract_id") !=
                "FOCUS_PATH_STATE_V2" or
                evidence_key != {"family": key.source_family,
                                 "entity_type": key.entity_type,
                                 "entity_id": key.entity_id} or
                digest(observation.evidence) != observation.fact_digest):
            raise ValueError("core observation identity/digest mismatch")
        path_v2 = observation.evidence["path_state_v2"]
        if (path_v2.get("predicate_evidence") != observation.evidence.get("path_predicates") or
                path_v2.get("path_resolution") not in
                {"READY", "PARTIAL", "AMBIGUOUS", "UNAVAILABLE"} or
                (path_v2.get("path_resolution") != "READY" and
                 path_v2.get("resolved_primary_state") is not None)):
            raise ValueError("core path-state-v2 evidence mismatch")
        price_digest = observation.evidence.get("price_input_digest")
        if key.entity_type == "STOCK":
            if price_digest not in stock_digests.get(key.entity_id, set()):
                raise ValueError("core observation stock fact mismatch")
        else:
            predicate_facts = observation.evidence.get("predicate_facts")
            if (price_digest is not None or
                    not isinstance(predicate_facts, dict) or
                    predicate_facts.get("basket_digest") != basket_digests.get(episode) or
                    predicate_facts.get("strength_fact_digest") != strength_digests.get(episode)):
                raise ValueError("core sector observation fact identity mismatch")
    closure_payload = {"contract_id": CONTRACT_ID,
                       "manifest_sha256": manifest.sha256,
                       "source_identity_digest": sources.source_identity_digest,
                       "plan_digest": plan.plan_digest,
                       "observations": [(key.source_family, key.entity_type,
                                         key.entity_id, episode,
                                         by_episode[(key, episode)].fact_digest)
                                        for key, episode in sorted(by_episode)]}
    return CoreInputClosure(sources.trade_date.isoformat(), len(sources.rows),
                            len(observations), len(stock_facts),
                            digest(closure_payload))

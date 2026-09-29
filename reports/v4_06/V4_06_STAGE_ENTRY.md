# V4-06 Stage Entry

```json
{
  "acceptance_result_at_entry": "IN_PROGRESS; required implementation and runtime evidence not yet produced.",
  "accepted_core": {
    "core_profile_logical_digest": "d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74",
    "core_profile_sha256": "9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0",
    "external_acceptance": "EXTERNALLY_ACCEPTED",
    "identity_count": 5222,
    "publication_id": "PUB-3c03e227-c60a-4d8c-86ae-2861507c257b",
    "stage_range": "V4_00_TO_V4_05_ACCEPTED",
    "trade_date": "2026-09-28",
    "v4_05_status": "DATA_FACTOR_REPLAY_DEGRADED_PASS"
  },
  "branch": "codex/v4-system-reform",
  "contract": {
    "core_dependency_on_baostock": "NONE",
    "dataset_enabled_at_entry": false,
    "raw_hot_rank_persistence": "FORBIDDEN",
    "source_contract_id": "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1",
    "source_contract_version": "1.1.0",
    "strict_tolerance_status_at_entry": "UNFROZEN",
    "target_trade_date": "2026-09-28",
    "tdx_authority": "unchanged",
    "turnover_factor_contract_id": "TURNOVER_CONTEXT_V1"
  },
  "evidence_at_entry": {
    "accepted_head": {
      "byte_count": 8456,
      "path": "data/v4/V4_05_ACCEPTED_HEAD.json",
      "sha256": "fc929d85553a900a6479ac9f50291d50cf750ad0e6c21fc58e4e05e92189f5cb"
    },
    "b6_receipt": {
      "byte_count": 2469,
      "path": "reports/v4_baostock/public_b6_fingerprint_sample_receipt.json",
      "sha256": "fd4afc7f6ce91c62d7d4d1cb297b533f1ca7aec60a480e6f41ca93db710baffc"
    },
    "baostock_contract": {
      "byte_count": 12177,
      "path": "config/baostock_supplemental_contract_v1.json",
      "sha256": "b90979d0e0c96c18c42e11de46d1940d84f3121c765870ce6997b8ce2b0c5799"
    },
    "baostock_request_ledger": {
      "byte_count": 2947,
      "path": "reports/v4_baostock/request_ledger.json",
      "sha256": "16f2f3a9610be91222d2f69246991d35fcdbffc6b5c3e39d0a636cabb279e54b"
    },
    "core_profile": {
      "byte_count": 48848465,
      "path": "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz",
      "sha256": "9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0"
    },
    "entry_authorization": {
      "byte_count": 4349,
      "path": "docs/evidence/V4_05_ACCEPTED_HEAD_PROMOTION_V4_06_ENTRY_TASK_20260929.md",
      "sha256": "ddb1526ca4c1eee78c4c9579db7f1760ac41cff71f0f60c553ae7c27e048b206"
    },
    "full_scope_factors": {
      "byte_count": 32316843,
      "path": "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz",
      "sha256": "17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48"
    },
    "global_head": {
      "byte_count": 3990,
      "path": "data/v4/V4_STAGE_ACCEPTED_HEAD.json",
      "sha256": "6fd6e16b3769726f14e44b1d2062d087fd40ec1ede51956a5353631896547043"
    },
    "postgres_ledger": {
      "byte_count": 63674,
      "path": "reports/v4_05/V4_05_R4_2_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json",
      "sha256": "75f601ea61c00f4a8d240f151d2117e2aaefa6d73139bfd1d1eae3c1934f460d"
    },
    "project_guardrails": {
      "byte_count": 1379,
      "path": "AGENTS.md",
      "sha256": "b72647b6275f6ae3489a24ccc8a9e1e29d0e440739c3e2f360c7f05bf44e403d"
    },
    "promotion_external_acceptance": {
      "byte_count": 5015,
      "path": "D:/Users/lps/Desktop/V4_05_PROMOTION_EXTERNAL_ACCEPTANCE_20260929.md",
      "sha256": "ff64b0f50d6fcb49ebee172cf208ebbee24dea264d7cf528b7bcf8b45511d197"
    },
    "task_card": {
      "byte_count": 9697,
      "path": "D:/Users/lps/Desktop/V4_06_SUPPLEMENTAL_ENRICHMENT_STAGE_TASK_20260929.md",
      "sha256": "d46fe4f35d6bba04b75ba34f2924690c73d4063874438b4ca82bbb2fddc939e8"
    },
    "upgrade_plan_v2": {
      "byte_count": 20691,
      "path": "docs/UNIFIED_WORKBENCH_SERVICE_UPGRADE_PLAN_V2.md",
      "sha256": "3b3de5f4e41252a0ce8fd4704c461a590900629cb24c0ddbc5165d85df3bfcd2"
    },
    "v4_00f_audit": {
      "byte_count": 6426,
      "path": "docs/audits/V4_00F_BAOSTOCK_GATE_AUDIT_20260925.md",
      "sha256": "c2b0502c241a36128da9b597e5f5c0b28c987d69f2a3196dd720bcf7594e0af3"
    }
  },
  "external_acceptance": "PENDING",
  "initial_observations": [
    "V4-05 accepted head and V4-06 authorization match the supplied promotion review; current HEAD equals the authorized starting commit; git worktree was clean at entry.",
    "V4-05 target is 2026-09-28 with 5,222 identities; accepted Core profile logical digest is bound to the V4-05 head.",
    "V4-00F source contract currently has UNFROZEN strict tolerance and disabled BaoStock turnover capability.",
    "Existing B6 receipt reports 0 representative date pairs and no independently accepted tolerance; no BaoStock strict binding may be claimed.",
    "No reports/v4_06 artifacts existed at stage entry."
  ],
  "next_stage": "Implement V4-06 candidate; retain external acceptance as PENDING and submit the completed candidate for independent review.",
  "stage": "V4-06 Supplemental Enrichment",
  "stage_acceptance_result": "PENDING",
  "stage_contract": "V4_06_SUPPLEMENTAL_ENRICHMENT_STAGE_TASK_20260929",
  "stage_contract_scope": [
    "Implement versioned TURNOVER_CONTEXT_V1 engine and append-only supplemental enrichment revisions without changing accepted Core identity or semantics.",
    "Use the existing V4-00F BaoStock source contract and bounded serial request worker; capability failures remain supplemental-only.",
    "Run required history, binding, append-only, and Core isolation checks; preserve actual provider failure receipts.",
    "Do not create V4-06 Accepted Head and do not start V4-07 or V4-08."
  ],
  "stage_status": "IN_PROGRESS",
  "started_at_local": "2026-09-29 Asia/Shanghai",
  "starting_head": "e0fbcc665b0926322b5098c0c99465fa2b427cb8"
}
```

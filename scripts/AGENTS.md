# Script execution storage policy

Inherited project guardrails in the root AGENTS.md remain applicable.

Use G: only for project temporary checkouts, regression workspaces, test temporary directories and large caches. Do not allocate project temporary space on C:.

The current explicit roots are G:/codex_tmp for clean regression checkouts and G:/codex_tmp/test_temp for test temporary directories. Consult config/project_workspace_storage_policy_v1.json. Do not invoke a legacy helper that hardcodes a C: checkout; use the G-only checkout helper or implement a successor without modifying frozen historical source.

The user plans a dedicated 3 TB mechanical disk for Codex projects, the PGS database and stock/TDX data. Its drive and paths are not configured yet. Existing TDX source roots remain read-only.

User instruction dated 2026-10-09 supersedes the previous E/F rule: all newly created Codex temporary files and workspaces use G:. Set child-process TMP/TEMP/TMPDIR to G:/codex_tmp.

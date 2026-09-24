"""Resolve accepted publication source identities without rewriting legacy rows."""
from __future__ import annotations

import re


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def accepted_source_identity(native_sha, migrated_sha=None) -> tuple[str | None, str]:
    native = str(native_sha).strip() if native_sha else None
    migrated = str(migrated_sha).strip() if migrated_sha else None
    if native and not SHA256.fullmatch(native):
        raise ValueError("PUBLICATION_NATIVE_SOURCE_SHA_INVALID")
    if migrated and not SHA256.fullmatch(migrated):
        raise ValueError("PUBLICATION_MIGRATED_SOURCE_SHA_INVALID")
    if native and migrated and native != migrated:
        raise ValueError("PUBLICATION_SOURCE_IDENTITY_MIGRATION_CONFLICT")
    if native:
        return native, "SOURCE_SHA256"
    if migrated:
        return migrated, "SOURCE_SHA256_MIGRATED"
    return None, "PUBLICATION_ID_ONLY"

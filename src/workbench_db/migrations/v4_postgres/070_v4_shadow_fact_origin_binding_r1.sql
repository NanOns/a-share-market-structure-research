-- Bind every Shadow fact to the exact evidence origin of its export identity.
SET search_path TO v4, pg_catalog;

ALTER TABLE v4.shadow_readback_identity_r1
    ADD CONSTRAINT shadow_readback_identity_r1_digest_origin_uq
    UNIQUE (logical_digest, evidence_origin);

ALTER TABLE v4.shadow_readback_facts_r1
    ADD CONSTRAINT shadow_readback_facts_r1_identity_origin_fk
    FOREIGN KEY (logical_digest, evidence_origin)
    REFERENCES v4.shadow_readback_identity_r1 (logical_digest, evidence_origin);

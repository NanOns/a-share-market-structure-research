-- Ordinal order is local to each source namespace; R7 and R8 preserve the
-- original append order without colliding in the single fixed relation.
ALTER TABLE v4.forward_r7_facts_r1
    DROP CONSTRAINT IF EXISTS forward_r7_facts_r1_ordinal_key;

CREATE UNIQUE INDEX IF NOT EXISTS forward_r7_facts_namespace_ordinal_r1
    ON v4.forward_r7_facts_r1(origin_namespace,ordinal);

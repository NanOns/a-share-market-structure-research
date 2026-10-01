-- A09 additive hardening. Historical 021 and accepted payloads remain byte-identical.
ALTER TABLE v4.stock_prewatch_publications
    ADD COLUMN consumer_contract_id text NOT NULL DEFAULT 'V4_09_PRIORITY_PROVENANCE_AND_IMMUTABILITY_R1_1',
    ADD CONSTRAINT ck_stock_prewatch_consumer_id CHECK (length(btrim(consumer_contract_id)) BETWEEN 1 AND 256),
    ADD CONSTRAINT uq_stock_prewatch_publication_consumer UNIQUE (publication_id,consumer_contract_id);
ALTER TABLE v4.stock_prewatch_results
    ADD COLUMN consumer_contract_id text NOT NULL DEFAULT 'V4_09_PRIORITY_PROVENANCE_AND_IMMUTABILITY_R1_1',
    ADD CONSTRAINT fk_stock_prewatch_result_consumer FOREIGN KEY (publication_id,consumer_contract_id)
        REFERENCES v4.stock_prewatch_publications(publication_id,consumer_contract_id);
CREATE FUNCTION v4.guard_stock_prewatch_consumer_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.payload ? 'consumer_contract_id' AND
       NEW.payload->>'consumer_contract_id' IS DISTINCT FROM NEW.consumer_contract_id THEN
        RAISE EXCEPTION 'STOCK_PREWATCH_PAYLOAD_CONSUMER_MISMATCH';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER v4_stock_prewatch_consumer_identity BEFORE INSERT ON v4.stock_prewatch_results
FOR EACH ROW EXECUTE FUNCTION v4.guard_stock_prewatch_consumer_identity();

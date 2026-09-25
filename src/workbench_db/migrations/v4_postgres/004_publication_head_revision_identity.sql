-- publication_id is the immutable revision identity; heads do not carry a second revision number.
CREATE OR REPLACE FUNCTION v4.validate_publication_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.publications%ROWTYPE;
BEGIN
    SELECT * INTO p FROM v4.publications WHERE publication_id = NEW.publication_id;
    IF NOT FOUND OR p.status <> 'ACCEPTED' OR p.trade_date <> NEW.trade_date
       OR p.model_namespace_id <> NEW.model_namespace_id THEN
        RAISE EXCEPTION 'V4_PUBLICATION_HEAD_TARGET_INVALID';
    END IF;
    RETURN NEW;
END $$;

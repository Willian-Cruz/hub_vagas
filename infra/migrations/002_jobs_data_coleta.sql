-- Adds the timestamp column expected by app/database/job_model.py.
-- Existing rows receive the migration time because the old schema did not
-- retain an individual collection timestamp.
ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS data_coleta TIMESTAMP WITHOUT TIME ZONE
    NOT NULL DEFAULT CURRENT_TIMESTAMP;

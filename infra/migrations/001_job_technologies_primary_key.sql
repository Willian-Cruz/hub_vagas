-- Adds the composite key to existing PostgreSQL installations.
-- Run once against the Hub Vagas database after reviewing any duplicates.
DO $$
BEGIN
    IF to_regclass('job_technologies') IS NULL THEN
        RAISE EXCEPTION 'job_technologies table does not exist';
    ELSIF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = to_regclass('job_technologies')
          AND contype = 'p'
    ) THEN
        IF EXISTS (
            SELECT 1
            FROM job_technologies
            GROUP BY job_id, technology_id
            HAVING COUNT(*) > 1
        ) THEN
            RAISE EXCEPTION
                'job_technologies has duplicate pairs; remove duplicates before applying this migration';
        END IF;

        ALTER TABLE job_technologies
            ADD CONSTRAINT pk_job_technologies
            PRIMARY KEY (job_id, technology_id);
    END IF;
END
$$;

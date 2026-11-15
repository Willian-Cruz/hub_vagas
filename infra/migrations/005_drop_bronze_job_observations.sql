-- 005: remove tabela obsoleta bronze.job_observations
--
-- Esta tabela era gravada por BronzeRepository.persistir_resultados() mas não
-- era lida por nenhum consumidor (dbt staging usa select_raw_jobs, não
-- select_bronze_jobs). Foi removida na refatoração de desacoplamento
-- ingestão vs transformação.
--
-- A tabela bronze.scrape_runs é mantida (monitoramento de execução).
--
-- Este script é idempotente: rodar de novo não causa erro.

DROP TABLE IF EXISTS bronze.job_observations CASCADE;

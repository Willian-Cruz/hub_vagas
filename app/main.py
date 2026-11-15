"""Ponto de entrada para executar a INGESTÃO de dados: scrape → Bronze (landing zone).

Responsabilidade única: coletar dados dos portais e gravá-los na camada Bronze.
A transformação (Bronze → Silver → Gold) é executada separadamente via dbt:
    python app/transform.py

Uso:
    python app/main.py
"""
import os
import sys

# Permite executar `python app/main.py` a partir da raiz do repositório.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from database.connection import (
    engine,
    ensure_bronze_schema,
    ensure_local_database_exists,
)
from database.models import base
from database.job_model import Job  # registra o modelo no metadata
from database.tech_model import Technology  # registra o modelo no metadata
from database.job_tech_model import job_technologies  # registra a associação
from database.bronze_model import JobObservation, ScrapeRun  # registra Bronze
from services.pipeline_service import PipelineService


def main() -> int:
    """Executa a ingestão: scrape → Bronze.

    Não executa dbt nem mantém a tabela legacy `jobs`.
    Para transformação, use `python app/transform.py`.
    """
    if ensure_local_database_exists():
        print("Banco local criado com sucesso!")

    ensure_bronze_schema()
    base.metadata.create_all(bind=engine)
    print("Banco verificado/criado com sucesso!")

    metricas = PipelineService.executar()
    return 0 if metricas["sucesso"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
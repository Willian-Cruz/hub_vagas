"""Ponto de entrada para executar uma coleta e persistência do pipeline."""
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


def main(executar_dbt: bool = False) -> int:
    if ensure_local_database_exists():
        print("Banco local criado com sucesso!")

    ensure_bronze_schema()
    base.metadata.create_all(bind=engine)
    print("Banco verificado/criado com sucesso!")

    metricas = PipelineService.executar()
    if executar_dbt and metricas.get("bronze_ok"):
        from run_dbt import main as executar_transformacoes

        print("Executando modelos e testes dbt...")
        codigo_dbt = executar_transformacoes(["build"])
        return 0 if codigo_dbt == 0 and metricas["sucesso"] else 1
    return 0 if metricas["sucesso"] else 1


if __name__ == "__main__":
    raise SystemExit(main(executar_dbt=True))

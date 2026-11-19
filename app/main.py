"""Ponto de entrada para executar a INGESTÃO de dados: scrape → raw layer `jobs`.

Responsabilidade única: coletar dados dos portais e gravá-los na tabela raw `jobs`.
A transformação (raw → Bronze → Silver → Gold) é executada separadamente via dbt:
    python app/transform.py

Uso:
    python app/main.py
"""
from app.database.connection import (
    engine,
    ensure_bronze_schema,
    ensure_local_database_exists,
)
from app.database.models import base
from app.services.pipeline_service import PipelineService


def main() -> int:
    """Executa a ingestão: scrape → raw layer `jobs`.

    Não executa dbt.
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
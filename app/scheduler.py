"""
Ponto de entrada para execução automática agendada da INGESTÃO de dados.

Uso padrão (todo dia às 06:00, horário de São Paulo):
    python app/scheduler.py

Horário customizado (ex: 08:30):
    python app/scheduler.py --hora 8 --minuto 30

Modo intervalo — útil para testes (ex: a cada 2 horas):
    python app/scheduler.py --intervalo 2

O processo ficará ativo aguardando o próximo ciclo.
Pressione Ctrl+C para encerrar.

Para executar a transformação (dbt) separadamente:
    python app/transform.py
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import (
    engine,
    ensure_bronze_schema,
    ensure_local_database_exists,
)
from database.models import base
from database.job_model import Job
from database.tech_model import Technology
from database.job_tech_model import job_technologies
from database.bronze_model import ScrapeRun
from services.scheduler_service import SchedulerService
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Hub Vagas — agendador de ingestão de dados"
    )
    parser.add_argument(
        "--hora",
        type    = int,
        default = None,
        help    = "Hora de execução diária (0-23). Padrão: 6",
    )
    parser.add_argument(
        "--minuto",
        type    = int,
        default = None,
        help    = "Minuto de execução diária (0-59). Padrão: 0",
    )
    parser.add_argument(
        "--intervalo",
        type    = int,
        default = None,
        help    = "Executa a cada N horas (modo debug). Ignora --hora e --minuto",
    )
    parser.add_argument(
        "--com-transformacao",
        action="store_true",
        help="Após cada coleta bem-sucedida na Bronze, executa dbt build (transform.py)",
    )
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()

    # Cria tabelas no banco se ainda não existirem
    if ensure_local_database_exists():
        logger.info("Banco local criado com sucesso")

    ensure_bronze_schema()
    base.metadata.create_all(bind=engine)
    logger.info("Banco verificado/criado com sucesso")

    if args.intervalo:
        logger.info(f"Modo intervalo: a cada {args.intervalo}h")
        SchedulerService.iniciar_por_intervalo(
            horas=args.intervalo,
            executar_transformacao=args.com_transformacao,
        )
    else:
        SchedulerService.iniciar_diario(
            hora=args.hora,
            minuto=args.minuto,
            executar_transformacao=args.com_transformacao,
        )
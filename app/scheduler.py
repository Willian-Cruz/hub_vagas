"""
Ponto de entrada para execução automática agendada do pipeline.

Uso padrão (todo dia às 06:00, horário de São Paulo):
    python app/scheduler.py

Horário customizado (ex: 08:30):
    python app/scheduler.py --hora 8 --minuto 30

Modo intervalo — útil para testes (ex: a cada 2 horas):
    python app/scheduler.py --intervalo 2

O processo ficará ativo aguardando o próximo ciclo.
Pressione Ctrl+C para encerrar.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from database.connection import engine
from database.models import base
from database.job_model import Job
from database.tech_model import Technology
from database.job_tech_model import job_technologies
from services.scheduler_service import SchedulerService
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Hub Vagas — agendador de pipeline"
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
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()

    # Cria tabelas no banco se ainda não existirem
    base.metadata.create_all(bind=engine)
    logger.info("Banco verificado/criado com sucesso")

    if args.intervalo:
        logger.info(f"Modo intervalo: a cada {args.intervalo}h")
        SchedulerService.iniciar_por_intervalo(horas=args.intervalo)
    else:
        SchedulerService.iniciar_diario(hora=args.hora, minuto=args.minuto)
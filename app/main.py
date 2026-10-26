"""
Ponto de entrada de uma execução única do pipeline (coleta + persistência).

Uso:
    python app/main.py

Código de saída:
    0 — pipeline concluído com sucesso
    1 — pipeline falhou, inclusive quando nenhuma vaga foi coletada
        (agendadores e CI usam esse código para marcar a execução como falha)
"""
import sys

from database.connection import engine
from database.models import base
from database.job_model import Job
from database.tech_model import Technology
from database.job_tech_model import job_technologies
from services.pipeline_service import PipelineService
from utils.logger import get_logger

logger = get_logger(__name__)


def main() -> int:
    base.metadata.create_all(bind=engine)
    logger.info("Banco verificado/criado com sucesso")

    metricas = PipelineService.executar()

    return 0 if metricas["sucesso"] else 1


if __name__ == "__main__":
    sys.exit(main())

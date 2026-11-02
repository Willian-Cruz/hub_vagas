import os
import sys


def main() -> int:
    # Mantém `python app/main.py` compatível com os imports internos do projeto.
    sys.path.insert(0, os.path.dirname(__file__))

    from database.connection import engine, ensure_local_database_exists
    from database.models import base
    from database.job_model import Job  # registra o modelo no metadata
    from database.tech_model import Technology  # registra o modelo no metadata
    from database.job_tech_model import job_technologies  # registra a associação
    from services.pipeline_service import PipelineService

    if ensure_local_database_exists():
        print("Banco local criado com sucesso!")

    base.metadata.create_all(bind=engine)
    print("Banco verificado/criado com sucesso!")

    metricas = PipelineService.executar()
    return 0 if metricas["sucesso"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

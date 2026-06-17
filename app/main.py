from database.connection import engine
from database.models import base
from database.job_model import Job
from database.tech_model import Technology
from database.job_tech_model import job_technologies
from services.collector_service import CollectorService
from repositories.job_repository import JobRepository

base.metadata.create_all(bind=engine)

print("Banco criado com sucesso!")

vagas = CollectorService.coletar_todas_vagas()

print(f"\nTotal coletado: " f"{len(vagas)} vagas\n")

for vaga in vagas:

    JobRepository.salvar(vaga)

print("\nProcessamento finalizado.")

from config.settings import DATABASE_URL

print("=" * 80)
print("DATABASE_URL:", DATABASE_URL)
print("=" * 80)
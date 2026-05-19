from database.connection import engine
from database.models import base
from config.settings import *
from scrapers.vagas_scraper import VagasScraper
from services.job_service import JobService

base.metadata.create_all(engine)
print("Banco criado com sucesso!")

vagas = VagasScraper.coletar()

for vaga in vagas:
    JobService.salvar(vaga)

print(f"{len(vagas)} vagas salvas!")
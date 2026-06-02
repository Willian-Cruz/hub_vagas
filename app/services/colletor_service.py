from scrapers.vagas_scraper import VagasScraper
from scrapers.infojobs_scraper import InfoJobsScraper


class CollectorService:

    @staticmethod
    def coletar_todas_vagas():

        vagas = []

        try:

            vagas.extend(VagasScraper.coletar())

        except Exception as e:

            print(f"Erro Vagas.com: {e}")

        try:

            vagas.extend(InfoJobsScraper.coletar())

        except Exception as e:

            print(f"Erro InfoJobs: {e}")

        return vagas
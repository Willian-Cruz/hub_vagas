from scrapers.vagas_scraper import VagasScraper
from scrapers.infojobs_scraper import InfoJobsScraper


class CollectorService:

    @staticmethod
    def coletar_todas_vagas():

        vagas = []

        scrapers = [VagasScraper, InfoJobsScraper]

        for scraper in scrapers:

            try:

                resultado = scraper.coletar()

                print(f"{scraper.__name__}: " f"{len(resultado)} vagas")

                vagas.extend(resultado)

            except Exception as erro:

                print(f"Erro em " f"{scraper.__name__}: " f"{erro}")

        return vagas

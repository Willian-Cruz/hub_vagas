from time import perf_counter

from scrapers.base_scraper import ScrapeResult, ScrapeStatus
from scrapers.infojobs_scraper import InfoJobsScraper
from scrapers.gupy_scraper import GupyScraper
from utils.logger import get_logger

logger = get_logger(__name__)


class CollectorService:
    """Executa os scrapers e preserva um resultado por fonte."""

    SCRAPERS = [VagasScraper, InfoJobsScraper, GupyScraper]

    @classmethod
    def coletar_resultados(cls) -> list[ScrapeResult]:
        resultados: list[ScrapeResult] = []

        for scraper in cls.SCRAPERS:

            logger.info(f"Iniciando: {scraper.__name__}")

            inicio = time.time()

            try:
                resultado = scraper.coletar()
                duracao   = time.time() - inicio

                logger.info(
                    f"{scraper.__name__}: "
                    f"{len(resultado)} vagas coletadas "
                    f"em {duracao:.1f}s"
                )

                todas_vagas.extend(resultado)

            except Exception as erro:
                duracao = time.time() - inicio
                logger.error(
                    f"{scraper.__name__} falhou "
                    f"após {duracao:.1f}s: {erro}"
                )

        logger.info(f"Total geral: {len(todas_vagas)} vagas coletadas")

        return todas_vagas

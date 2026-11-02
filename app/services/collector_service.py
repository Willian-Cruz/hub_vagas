from time import perf_counter

from scrapers.base_scraper import ScrapeResult, ScrapeStatus
from scrapers.gupy_scraper import GupyScraper
from scrapers.infojobs_scraper import InfoJobsScraper
from scrapers.vagas_scraper import VagasScraper
from utils.logger import get_logger

logger = get_logger(__name__)


class CollectorService:
    """Executa os scrapers e preserva um resultado por fonte."""

    SCRAPERS = [VagasScraper, InfoJobsScraper, GupyScraper]

    @classmethod
    def coletar_resultados(cls) -> list[ScrapeResult]:
        resultados: list[ScrapeResult] = []

        for scraper in cls.SCRAPERS:
            fonte = getattr(scraper, "SOURCE", scraper.__name__)
            inicio = perf_counter()
            logger.info("Iniciando scraper: %s", fonte)

            try:
                resultado = scraper.coletar()
                if not isinstance(resultado, ScrapeResult):
                    raise TypeError(
                        f"{scraper.__name__}.coletar() deve retornar ScrapeResult, "
                        f"recebido: {type(resultado).__name__}"
                    )

                resultados.append(resultado)
                logger.info(
                    "%s: status=%s, vagas=%d, páginas=%d, duração=%.1fs",
                    resultado.source,
                    resultado.status.value,
                    len(resultado.jobs),
                    resultado.pages_processed,
                    perf_counter() - inicio,
                )
                if resultado.error:
                    logger.warning("%s: %s", resultado.source, resultado.error)

            except Exception as erro:
                logger.exception(
                    "Scraper %s falhou após %.1fs",
                    fonte,
                    perf_counter() - inicio,
                )
                resultados.append(
                    ScrapeResult(
                        source=fonte,
                        status=ScrapeStatus.FAILED,
                        error=str(erro),
                    )
                )

        total_vagas = sum(len(resultado.jobs) for resultado in resultados)
        logger.info("Total coletado: %d vagas em %d fontes", total_vagas, len(resultados))
        return resultados

    @classmethod
    def coletar_todas_vagas(cls):
        """Compatibilidade para consumidores antigos que esperam somente vagas."""
        return [
            vaga
            for resultado in cls.coletar_resultados()
            for vaga in resultado.jobs
        ]

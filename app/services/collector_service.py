from time import perf_counter
import os

from scrapers.base_scraper import ScrapeResult, ScrapeStatus
from scrapers.catho_scraper import CathoScraper
from scrapers.gupy_scraper import GupyScraper
from scrapers.infojobs_scraper import InfoJobsScraper
from scrapers.vagas_scraper import VagasScraper
from services.relevance_service import RelevanceService
from utils.logger import get_logger

logger = get_logger(__name__)

# Feature flag: Gupy desligado por padrão até ser calibrado (item #12/P3).
# Defina GUPY_ENABLED=true para reativar.
GUPY_ENABLED = os.getenv("GUPY_ENABLED", "false").lower() == "true"


class CollectorService:
    """Executa os scrapers e preserva um resultado por fonte."""

    _SCRAPERS_BASE = [VagasScraper, InfoJobsScraper, CathoScraper]

    @classmethod
    def _scrapers(cls) -> list:
        scrapers = list(cls._SCRAPERS_BASE)
        if GUPY_ENABLED:
            scrapers.append(GupyScraper)
        return scrapers

    @classmethod
    def coletar_resultados(cls) -> list[ScrapeResult]:
        resultados: list[ScrapeResult] = []

        for scraper in cls._scrapers():
            fonte = getattr(scraper, "SOURCE", scraper.__name__)
            inicio = perf_counter()
            logger.info("Iniciando scraper: %s", fonte)

            try:
                # Retry com backoff exponencial + jitter para erros de rede
                resultado = scraper.coletar_com_retry()
                if not isinstance(resultado, ScrapeResult):
                    raise TypeError(
                        f"{scraper.__name__}.coletar_com_retry() deve retornar ScrapeResult, "
                        f"recebido: {type(resultado).__name__}"
                    )

                # Aplicar filtro de relevância centralizado: marca is_relevant
                # em cada vaga sem descartar (a Silver filtra nos marts).
                vagas_marcadas = RelevanceService.separar(resultado.jobs)
                n_relevantes = sum(1 for v in vagas_marcadas if v.is_relevant)
                n_descartadas = len(vagas_marcadas) - n_relevantes
                resultado = ScrapeResult(
                    source=resultado.source,
                    status=resultado.status,
                    jobs=vagas_marcadas,
                    pages_processed=resultado.pages_processed,
                    error=resultado.error,
                    discarded=(resultado.discarded or 0) + n_descartadas,
                )

                resultados.append(resultado)
                logger.info(
                    "%s: status=%s, vagas=%d, descartadas=%d, páginas=%d, duração=%.1fs",
                    resultado.source,
                    resultado.status.value,
                    len(resultado.jobs),
                    resultado.discarded,
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

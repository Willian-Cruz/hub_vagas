from time import perf_counter

from scrapers.base_scraper import ScrapeResult, ScrapeStatus
from scrapers.infojobs_scraper import InfoJobsScraper
from scrapers.vagas_scraper import VagasScraper


class CollectorService:
    """Executa os scrapers e preserva um resultado por fonte."""

    SCRAPERS = [VagasScraper, InfoJobsScraper]

    @classmethod
    def coletar_resultados(cls) -> list[ScrapeResult]:
        resultados: list[ScrapeResult] = []

        for scraper in cls.SCRAPERS:
            inicio = perf_counter()
            try:
                resultado = scraper.coletar()
                if not isinstance(resultado, ScrapeResult):
                    raise TypeError(
                        f"{scraper.__name__}.coletar() deve retornar ScrapeResult"
                    )
            except Exception as erro:
                resultado = ScrapeResult(
                    source=getattr(scraper, "SOURCE", scraper.__name__),
                    status=ScrapeStatus.FAILED,
                    error=f"{type(erro).__name__}: {erro}",
                )

            duracao = perf_counter() - inicio
            resultados.append(resultado)
            print(
                f"[{resultado.source}] {resultado.status.value}: "
                f"{len(resultado.jobs)} vaga(s), "
                f"{resultado.pages_processed} página(s), {duracao:.1f}s"
            )
            if resultado.error:
                print(f"[{resultado.source}] Detalhe: {resultado.error}")

        return resultados

    @classmethod
    def coletar_todas_vagas(cls) -> list:
        """Compatibilidade para chamadores que precisam somente das vagas."""
        return [
            vaga
            for resultado in cls.coletar_resultados()
            for vaga in resultado.jobs
        ]

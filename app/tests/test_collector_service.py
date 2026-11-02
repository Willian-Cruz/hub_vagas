from services.collector_service import CollectorService
from scrapers.base_scraper import ScrapeResult, ScrapeStatus


class FakeScraper:
    SOURCE = "FonteTeste"

    @classmethod
    def coletar(cls):
        return ScrapeResult(
            source=cls.SOURCE,
            status=ScrapeStatus.SUCCESS,
            pages_processed=2,
        )


class BrokenScraper:
    SOURCE = "FonteQuebrada"

    @classmethod
    def coletar(cls):
        raise RuntimeError("falha simulada")


class LegacyScraper:
    SOURCE = "FonteLegada"

    @classmethod
    def coletar(cls):
        return []


def test_coletor_preserva_status_de_cada_fonte(monkeypatch):
    monkeypatch.setattr(CollectorService, "SCRAPERS", [FakeScraper])

    resultados = CollectorService.coletar_resultados()

    assert len(resultados) == 1
    assert resultados[0].source == "FonteTeste"
    assert resultados[0].status is ScrapeStatus.SUCCESS
    assert resultados[0].pages_processed == 2


def test_coletor_converte_excecao_em_resultado_failed(monkeypatch):
    monkeypatch.setattr(CollectorService, "SCRAPERS", [BrokenScraper])

    resultados = CollectorService.coletar_resultados()

    assert len(resultados) == 1
    assert resultados[0].source == "FonteQuebrada"
    assert resultados[0].status is ScrapeStatus.FAILED
    assert "falha simulada" in resultados[0].error


def test_coletor_sinaliza_scraper_fora_do_contrato(monkeypatch):
    monkeypatch.setattr(CollectorService, "SCRAPERS", [LegacyScraper])

    resultados = CollectorService.coletar_resultados()

    assert resultados[0].status is ScrapeStatus.FAILED
    assert "deve retornar ScrapeResult" in resultados[0].error

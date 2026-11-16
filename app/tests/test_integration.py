"""
Testes de integracao do pipeline completo.

Estes testes validam o fluxo: scrape -> raw -> bronze -> silver -> gold.
Como dbt requer PostgreSQL real, os testes de transformacao (silver/gold)
sao marcados como `integration` e requerem a variavel de ambiente
`DBT_TEST_DATABASE_URL` configurada.

Execucao:
    pytest tests/test_integration.py -v
    # Para rodar com banco real:
    DBT_TEST_DATABASE_URL=postgresql://user:pass@localhost/test pytest tests/test_integration.py -v -m integration
"""
import os
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from scrapers.base_scraper import ScrapeResult, ScrapeStatus
from schemas.job_schema import JobSchema
from services.collector_service import CollectorService
from services.pipeline_service import PipelineService
from repositories.bronze_repository import BronzeRepository
from repositories.job_repository import JobRepository


# Marca testes que requerem banco PostgreSQL real
requires_db = pytest.mark.skipif(
    not os.getenv("DBT_TEST_DATABASE_URL"),
    reason="DBT_TEST_DATABASE_URL nao configurado; pulando teste de integracao com banco real"
)


def _scrape_result(source: str, jobs: list, status: ScrapeStatus = ScrapeStatus.SUCCESS, error: str | None = None, pages: int = 1) -> ScrapeResult:
    """Helper para criar ScrapeResult mock."""
    return ScrapeResult(
        source=source,
        status=status,
        jobs=jobs,
        pages_processed=pages,
        error=error,
        discarded=0,
    )


class TestCollectorIntegracao:
    """Testes de integracao do CollectorService (scrape -> collector)."""

    @pytest.fixture
    def vaga_exemplo(self):
        return JobSchema(
            titulo="Engenheiro de Dados Senior",
            empresa="Empresa Teste",
            link="https://example.com/vaga/1",
            origem="Vagas.com",
            id_externo="12345",
            localizacao="Sao Paulo - SP",
            descricao="Experiencia com Python, SQL e AWS.",
            salario="R$ 10.000,00",
            modalidade="Hibrido",
            senioridade="Senior",
            data_publicacao=datetime(2026, 1, 15),
        )

    def test_coletor_retorna_vagas_de_todas_fontes(self, monkeypatch, vaga_exemplo):
        """Verifica que o CollectorService executa todos os scrapers registrados."""
        from scrapers.vagas_scraper import VagasScraper
        from scrapers.infojobs_scraper import InfoJobsScraper
        from scrapers.gupy_scraper import GupyScraper
        from scrapers.catho_scraper import CathoScraper

        def mock_coletar():
            return _scrape_result("Vagas.com", [vaga_exemplo])

        monkeypatch.setattr(VagasScraper, "coletar", staticmethod(mock_coletar))
        monkeypatch.setattr(InfoJobsScraper, "coletar", staticmethod(lambda: _scrape_result("InfoJobs", [vaga_exemplo])))
        monkeypatch.setattr(GupyScraper, "coletar", staticmethod(lambda: _scrape_result("Gupy", [vaga_exemplo])))
        monkeypatch.setattr(CathoScraper, "coletar", staticmethod(lambda: _scrape_result("Catho", [vaga_exemplo])))

        resultados = CollectorService.coletar_resultados()

        assert len(resultados) == 4  # 4 fontes registradas
        fontes = {r.source for r in resultados}
        assert fontes == {"Vagas.com", "InfoJobs", "Gupy", "Catho"}

    def test_coletor_aplica_filtro_relevancia_centralizado(self, monkeypatch, vaga_exemplo):
        """Verifica que o filtro de relevancia e aplicado centralmente no CollectorService."""
        from scrapers.vagas_scraper import VagasScraper

        vaga_fora_tema = JobSchema(
            titulo="Engenheiro Civil",
            empresa="Empresa",
            link="https://example.com/2",
            origem="Vagas.com",
        )

        # Scraper retorna 2 vagas (1 relevante, 1 fora do tema)
        monkeypatch.setattr(VagasScraper, "coletar", staticmethod(lambda: _scrape_result("Vagas.com", [vaga_exemplo, vaga_fora_tema])))
        monkeypatch.setattr(
            "services.collector_service.CollectorService.SCRAPERS", [VagasScraper]
        )

        resultados = CollectorService.coletar_resultados()

        # Collector deve filtrar: apenas 1 vaga relevante
        assert len(resultados) == 1
        assert resultados[0].source == "Vagas.com"
        assert len(resultados[0].jobs) == 1
        assert resultados[0].jobs[0].titulo == "Engenheiro de Dados Senior"
        assert resultados[0].discarded == 1

    def test_coletor_lida_com_falha_parcial(self, monkeypatch, vaga_exemplo):
        """Verifica que o CollectorService lida com falha parcial de um scraper."""
        from scrapers.vagas_scraper import VagasScraper
        from scrapers.infojobs_scraper import InfoJobsScraper

        # Vagas.com retorna sucesso, InfoJobs falha
        monkeypatch.setattr(VagasScraper, "coletar", staticmethod(lambda: _scrape_result("Vagas.com", [vaga_exemplo])))
        monkeypatch.setattr(InfoJobsScraper, "coletar", staticmethod(lambda: _scrape_result("InfoJobs", [], ScrapeStatus.FAILED, error="Timeout")))
        monkeypatch.setattr(
            "services.collector_service.CollectorService.SCRAPERS", [VagasScraper, InfoJobsScraper]
        )

        resultados = CollectorService.coletar_resultados()

        assert len(resultados) == 2
        assert resultados[0].status == ScrapeStatus.SUCCESS
        assert resultados[1].status == ScrapeStatus.FAILED
        assert "Timeout" in resultados[1].error


@requires_db
class TestPipelineComBanco:
    """Testes de integracao do pipeline completo com banco de dados real."""

    @pytest.fixture
    def vaga_exemplo(self):
        return JobSchema(
            titulo="Engenheiro de Dados Senior",
            empresa="Empresa Teste",
            link="https://example.com/vaga/1",
            origem="Vagas.com",
            id_externo="12345",
            localizacao="Sao Paulo - SP",
            descricao="Experiencia com Python, SQL e AWS.",
            salario="R$ 10.000,00",
            modalidade="Hibrido",
            senioridade="Senior",
            data_publicacao=datetime(2026, 1, 15),
        )

    def test_pipeline_persiste_vagas_e_registra_bronze(self, monkeypatch, vaga_exemplo):
        """Verifica que o PipelineService persiste na raw layer e registra no bronze."""
        from scrapers.vagas_scraper import VagasScraper
        from scrapers.infojobs_scraper import InfoJobsScraper
        from scrapers.gupy_scraper import GupyScraper
        from scrapers.catho_scraper import CathoScraper

        monkeypatch.setattr(VagasScraper, "coletar", staticmethod(lambda: _scrape_result("Vagas.com", [vaga_exemplo])))
        monkeypatch.setattr(InfoJobsScraper, "coletar", staticmethod(lambda: _scrape_result("InfoJobs", [vaga_exemplo])))
        monkeypatch.setattr(GupyScraper, "coletar", staticmethod(lambda: _scrape_result("Gupy", [vaga_exemplo])))
        monkeypatch.setattr(CathoScraper, "coletar", staticmethod(lambda: _scrape_result("Catho", [vaga_exemplo])))

        metricas = PipelineService.executar()

        assert metricas["sucesso"] is True
        assert metricas["coletadas"] == 4
        assert metricas["raw_salvas"] == 4
        assert metricas["bronze_ok"] is True
        assert len(metricas["fontes"]) == 4

    def test_pipeline_deduplica_vagas_por_link(self, monkeypatch, vaga_exemplo):
        """Verifica que vagas com mesmo link sao deduplicadas na raw layer."""
        from scrapers.vagas_scraper import VagasScraper

        monkeypatch.setattr(VagasScraper, "coletar", staticmethod(lambda: _scrape_result("Vagas.com", [vaga_exemplo, vaga_exemplo])))
        monkeypatch.setattr(
            "services.collector_service.CollectorService.SCRAPERS", [VagasScraper]
        )

        metricas = PipelineService.executar()

        assert metricas["raw_salvas"] == 1
        assert metricas["raw_duplicadas"] == 1

    def test_pipeline_filtro_relevancia_centralizado(self, monkeypatch, vaga_exemplo):
        """Verifica que o filtro de relevancia e aplicado no CollectorService."""
        from scrapers.vagas_scraper import VagasScraper

        vaga_fora_tema = JobSchema(
            titulo="Engenheiro Civil",
            empresa="Empresa",
            link="https://example.com/2",
            origem="Vagas.com",
        )

        monkeypatch.setattr(VagasScraper, "coletar", staticmethod(lambda: _scrape_result("Vagas.com", [vaga_exemplo, vaga_fora_tema])))
        monkeypatch.setattr(
            "services.collector_service.CollectorService.SCRAPERS", [VagasScraper]
        )

        metricas = PipelineService.executar()

        assert metricas["coletadas"] == 1
        assert metricas["descartadas"] == 1


@requires_db
class TestDbtTransformacaoIntegracao:
    """Testes de integracao com dbt (requerem PostgreSQL real)."""

    def test_dbt_build_e_test(self):
        """Executa dbt build e dbt test contra banco de teste."""
        import subprocess
        import sys

        os.environ["DBT_HOST"] = "localhost"
        os.environ["DBT_USER"] = "postgres"
        os.environ["DBT_PASSWORD"] = "postgres"
        os.environ["DBT_PORT"] = "5432"
        os.environ["DBT_DATABASE"] = "hub_vagas_test"
        os.environ["DBT_SCHEMA"] = "public"
        os.environ["DBT_SSLMODE"] = "disable"
        os.environ["DBT_THREADS"] = "2"

        dbt_dir = "dbt"

        result = subprocess.run(
            [sys.executable, "-m", "dbt", "debug", "--profiles-dir", dbt_dir, "--project-dir", dbt_dir],
            capture_output=True, text=True, cwd="."
        )
        assert result.returncode == 0, f"dbt debug falhou: {result.stderr}"

        result = subprocess.run(
            [sys.executable, "-m", "dbt", "deps", "--profiles-dir", dbt_dir, "--project-dir", dbt_dir],
            capture_output=True, text=True, cwd="."
        )
        assert result.returncode == 0, f"dbt deps falhou: {result.stderr}"

        result = subprocess.run(
            [sys.executable, "-m", "dbt", "build", "--profiles-dir", dbt_dir, "--project-dir", dbt_dir],
            capture_output=True, text=True, cwd="."
        )
        assert result.returncode == 0, f"dbt build falhou: {result.stderr}"

        result = subprocess.run(
            [sys.executable, "-m", "dbt", "test", "--profiles-dir", dbt_dir, "--project-dir", dbt_dir],
            capture_output=True, text=True, cwd="."
        )
        assert result.returncode == 0, f"dbt test falhou: {result.stderr}"


@requires_db
class TestExportacaoExcel:
    """Testes de exportacao para Excel (Gold -> Excel)."""

    def test_exportacao_gera_arquivo_valido(self, tmp_path):
        """Verifica que a exportacao gera arquivo Excel valido."""
        from services.export_service import ExportService
        import pandas as pd

        arquivo = tmp_path / "vagas.xlsx"
        caminho = ExportService.exportar(nome_arquivo=str(arquivo))

        assert os.path.exists(caminho)
        df_lido = pd.read_excel(caminho)
        assert len(df_lido) >= 0  # Pode ser 0 se banco vazio
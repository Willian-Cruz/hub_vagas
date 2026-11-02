from services.collector_service import CollectorService
from services.dashboard_service import DashboardService
from services.pipeline_service import PipelineService
from repositories.job_repository import JobRepository
from schemas.job_schema import JobSchema
from scrapers.base_scraper import ScrapeResult, ScrapeStatus


def test_pipeline_registra_falha_da_fonte(monkeypatch):
    resultado_fonte = ScrapeResult(
        source="InfoJobs",
        status=ScrapeStatus.FAILED,
        error="certificado TLS inválido",
    )
    monkeypatch.setattr(
        CollectorService, "coletar_resultados", lambda: [resultado_fonte]
    )
    monkeypatch.setattr(DashboardService, "gerar", lambda: None)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False
    assert metricas["fontes"] == [
        {
            "origem": "InfoJobs",
            "status": "failed",
            "vagas": 0,
            "paginas": 0,
            "erro": "certificado TLS inválido",
        }
    ]


def test_pipeline_persiste_vagas_parciais_e_marca_execucao_com_falha(monkeypatch):
    vaga = JobSchema(
        titulo="Analista de Dados",
        empresa="Empresa Exemplo",
        link="https://example.com/vaga/1",
        origem="InfoJobs",
    )
    resultado_fonte = ScrapeResult(
        source="InfoJobs",
        status=ScrapeStatus.PARTIAL,
        jobs=[vaga],
        pages_processed=1,
        error="falha ao buscar a página seguinte",
    )
    monkeypatch.setattr(
        CollectorService, "coletar_resultados", lambda: [resultado_fonte]
    )
    monkeypatch.setattr(JobRepository, "salvar", lambda _vaga: "salva")
    monkeypatch.setattr(DashboardService, "gerar", lambda: None)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False
    assert metricas["coletadas"] == 1
    assert metricas["salvas"] == 1


def test_pipeline_considera_fonte_vazia_execucao_bem_sucedida(monkeypatch):
    resultado_fonte = ScrapeResult(
        source="Vagas.com",
        status=ScrapeStatus.EMPTY,
        pages_processed=1,
    )
    monkeypatch.setattr(
        CollectorService, "coletar_resultados", lambda: [resultado_fonte]
    )
    monkeypatch.setattr(DashboardService, "gerar", lambda: None)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is True
    assert metricas["coletadas"] == 0

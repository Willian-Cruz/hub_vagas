import main
from repositories.job_repository import JobRepository
from schemas.job_schema import JobSchema
from scrapers.base_scraper import ScrapeResult, ScrapeStatus
from services.collector_service import CollectorService
from services.pipeline_service import PipelineService


def _vaga():
    return JobSchema(
        titulo="Analista de Dados",
        empresa="Empresa Exemplo",
        link="https://example.com/vaga/1",
        origem="InfoJobs",
    )


def test_pipeline_registra_falha_da_fonte(monkeypatch):
    resultado = ScrapeResult(
        source="InfoJobs",
        status=ScrapeStatus.FAILED,
        error="certificado TLS inválido",
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])

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


def test_pipeline_persiste_vagas_parciais_e_marca_falha(monkeypatch):
    resultado = ScrapeResult(
        source="InfoJobs",
        status=ScrapeStatus.PARTIAL,
        jobs=[_vaga()],
        pages_processed=1,
        error="falha ao buscar a página seguinte",
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])
    monkeypatch.setattr(JobRepository, "salvar", lambda _vaga: "salva")

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False
    assert metricas["coletadas"] == 1
    assert metricas["salvas"] == 1


def test_pipeline_considera_coleta_vazia_valida_como_sucesso(monkeypatch):
    resultado = ScrapeResult(
        source="Vagas.com",
        status=ScrapeStatus.EMPTY,
        pages_processed=1,
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is True
    assert metricas["coletadas"] == 0


def test_pipeline_sem_fontes_marca_execucao_como_falha(monkeypatch):
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [])

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False


def test_pipeline_considera_erro_de_persistencia_como_falha(monkeypatch):
    resultado = ScrapeResult(
        source="InfoJobs",
        status=ScrapeStatus.SUCCESS,
        jobs=[_vaga()],
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])
    monkeypatch.setattr(JobRepository, "salvar", lambda _vaga: "erro")

    metricas = PipelineService.executar()

    assert metricas["erros"] == 1
    assert metricas["sucesso"] is False


def test_pipeline_converte_excecao_geral_em_falha(monkeypatch):
    def falhar():
        raise RuntimeError("falha inesperada")

    monkeypatch.setattr(CollectorService, "coletar_resultados", falhar)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False
    assert metricas["duracao_seg"] >= 0


def test_main_retorna_zero_quando_pipeline_tem_sucesso(monkeypatch):
    monkeypatch.setattr(main, "ensure_local_database_exists", lambda: False)
    monkeypatch.setattr(main.base.metadata, "create_all", lambda **_kwargs: None)
    monkeypatch.setattr(
        main.PipelineService, "executar", staticmethod(lambda: {"sucesso": True})
    )

    assert main.main() == 0


def test_main_retorna_um_quando_pipeline_falha(monkeypatch):
    monkeypatch.setattr(main, "ensure_local_database_exists", lambda: False)
    monkeypatch.setattr(main.base.metadata, "create_all", lambda **_kwargs: None)
    monkeypatch.setattr(
        main.PipelineService, "executar", staticmethod(lambda: {"sucesso": False})
    )

    assert main.main() == 1

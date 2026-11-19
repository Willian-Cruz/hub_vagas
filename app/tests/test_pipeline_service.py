import main
from repositories.bronze_repository import BronzeRepository
from repositories.job_repository import DUPLICADA, ERRO, JobRepository, REVISADA, SALVA
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


def _mock_persistence(monkeypatch):
    """Mocka JobRepository.salvar e BronzeRepository.persistir_resultados."""
    monkeypatch.setattr(JobRepository, "salvar", lambda vaga, run_id=None: SALVA)
    monkeypatch.setattr(
        BronzeRepository, "persistir_resultados",
        lambda resultados, run_id, started_at, finished_at=None: len(
            [v for r in resultados for v in r.jobs]
        ),
    )


def test_pipeline_registra_falha_da_fonte(monkeypatch):
    resultado = ScrapeResult(
        source="InfoJobs",
        status=ScrapeStatus.FAILED,
        error="certificado TLS inválido",
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])
    _mock_persistence(monkeypatch)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False
    assert metricas["fontes"] == [
        {
            "origem": "InfoJobs",
            "status": "failed",
            "vagas": 0,
            "paginas": 0,
            "erro": "certificado TLS inválido",
            "descartadas": 0,
        }
    ]


def test_pipeline_persiste_vagas_parciais_como_sucesso(monkeypatch):
    resultado = ScrapeResult(
        source="InfoJobs",
        status=ScrapeStatus.PARTIAL,
        jobs=[_vaga()],
        pages_processed=1,
        error="falha ao buscar a página seguinte",
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])
    _mock_persistence(monkeypatch)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is True  # PARTIAL com vagas = sucesso
    assert metricas["status"] == "PARTIAL"  # mas não é SUCESSO total
    assert metricas["coletadas"] == 1
    assert metricas["raw_novas"] == 1
    assert metricas["bronze_ok"] is True
    assert metricas["fontes_parcial"] == 1
    assert metricas["fontes_falha"] == 0


def test_pipeline_todas_fontes_sucesso_marca_execucao_como_sucesso(monkeypatch):
    """Quando todas as fontes têm SUCCESS, o status é SUCESSO."""
    resultado = ScrapeResult(
        source="Vagas.com",
        status=ScrapeStatus.SUCCESS,
        jobs=[_vaga()],
        pages_processed=1,
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])
    _mock_persistence(monkeypatch)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is True
    assert metricas["status"] == "SUCESSO"
    assert metricas["coletadas"] == 1
    assert metricas["raw_novas"] == 1
    assert metricas["fontes_sucesso"] == 1
    assert metricas["fontes_falha"] == 0


def test_pipeline_considera_coleta_vazia_como_falha(monkeypatch):
    resultado = ScrapeResult(
        source="Vagas.com",
        status=ScrapeStatus.EMPTY,
        pages_processed=1,
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])
    _mock_persistence(monkeypatch)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False  # EMPTY sem vagas = falha
    assert metricas["coletadas"] == 0
    assert metricas["fontes_vazio"] == 1


def test_pipeline_sem_fontes_marca_execucao_como_falha(monkeypatch):
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [])
    _mock_persistence(monkeypatch)

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False


def test_pipeline_considera_erro_de_persistencia_como_falha(monkeypatch):
    resultado = ScrapeResult(
        source="InfoJobs",
        status=ScrapeStatus.SUCCESS,
        jobs=[_vaga()],
    )
    monkeypatch.setattr(CollectorService, "coletar_resultados", lambda: [resultado])
    # Simula erro de persistência: salvar retorna ERRO
    monkeypatch.setattr(JobRepository, "salvar", lambda vaga, run_id=None: ERRO)
    monkeypatch.setattr(
        BronzeRepository, "persistir_resultados",
        lambda resultados, run_id, started_at, finished_at=None: len(
            [v for r in resultados for v in r.jobs]
        ),
    )

    metricas = PipelineService.executar()

    assert metricas["sucesso"] is False
    assert metricas["status"] == "FALHADO"
    assert metricas["raw_erros"] == 1
    assert metricas["raw_novas"] == 0


def test_pipeline_converte_excecao_geral_em_falha(monkeypatch):
    def falhar():
        raise RuntimeError("falha inesperada")

    monkeypatch.setattr(CollectorService, "coletar_resultados", falhar)
    _mock_persistence(monkeypatch)

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

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
"""
Testes do PipelineService e do ponto de entrada main.py.

Cobrem o que as métricas da execução prometem: contagem de salvas,
duplicadas e erros, e a regra de que uma coleta vazia ou uma falha em
qualquer etapa nunca termina como sucesso.

Execução: pytest tests/test_pipeline_service.py -v
"""
from unittest.mock import patch

import main
from repositories.job_repository import SALVA, DUPLICADA, ERRO
from services import pipeline_service
from services.pipeline_service import PipelineService


def _executar(vagas, resultados=None, coletor_erro=None):
    """Roda o pipeline com coletor e repositório substituídos por mocks."""
    with patch.object(pipeline_service, "CollectorService") as coletor, \
         patch.object(pipeline_service, "JobRepository") as repo:

        if coletor_erro:
            coletor.coletar_todas_vagas.side_effect = coletor_erro
        else:
            coletor.coletar_todas_vagas.return_value = vagas

        repo.salvar.side_effect = resultados or []

        metricas = PipelineService.executar()

        return metricas, repo


def test_conta_salvas_duplicadas_e_erros():
    metricas, _ = _executar(
        vagas=["v1", "v2", "v3"],
        resultados=[SALVA, DUPLICADA, ERRO],
    )

    assert metricas["coletadas"] == 3
    assert metricas["salvas"] == 1
    assert metricas["duplicadas"] == 1
    assert metricas["erros"] == 1
    assert metricas["sucesso"] is True


def test_todas_salvas_nao_gera_erros():
    metricas, _ = _executar(vagas=["v1", "v2"], resultados=[SALVA, SALVA])

    assert metricas["salvas"] == 2
    assert metricas["erros"] == 0


def test_coleta_vazia_falha_e_nao_tenta_salvar():
    metricas, repo = _executar(vagas=[])

    assert metricas["sucesso"] is False
    assert metricas["coletadas"] == 0
    repo.salvar.assert_not_called()


def test_falha_no_coletor_marca_execucao_como_falha():
    metricas, _ = _executar(vagas=[], coletor_erro=RuntimeError("portal fora do ar"))

    assert metricas["sucesso"] is False


def test_duracao_e_sempre_registrada():
    metricas, _ = _executar(vagas=[])

    assert metricas["duracao_seg"] >= 0


def test_main_retorna_zero_quando_pipeline_tem_sucesso():
    with patch.object(main, "base"), \
         patch.object(main.PipelineService, "executar", return_value={"sucesso": True}):
        assert main.main() == 0


def test_main_retorna_um_quando_pipeline_falha():
    with patch.object(main, "base"), \
         patch.object(main.PipelineService, "executar", return_value={"sucesso": False}):
        assert main.main() == 1

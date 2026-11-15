"""
Testes do BronzeRepository: gravação de scrape_runs na camada Bronze.

Execução: pytest tests/test_bronze_repository.py -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from repositories.bronze_repository import BronzeRepository
from schemas.job_schema import JobSchema
from scrapers.base_scraper import ScrapeResult, ScrapeStatus


def _resultado(vagas=None, source="Vagas.com"):
    return ScrapeResult(
        source=source,
        status=ScrapeStatus.SUCCESS,
        jobs=vagas or [],
        pages_processed=1,
    )


def _vaga(**campos):
    base = dict(
        titulo="Analista de Dados",
        link="https://www.vagas.com.br/vagas/v1/analista-de-dados",
        origem="Vagas.com",
        raw_payload={"html_fragment": "<li>card</li>"},
    )
    base.update(campos)
    return JobSchema(**base)


def _persistir(resultados):
    sessao = MagicMock()
    with patch("repositories.bronze_repository.SessionLocal", MagicMock(return_value=sessao)):
        total = BronzeRepository.persistir_resultados(
            resultados, uuid4(), datetime.now(timezone.utc)
        )
    return total, sessao


class TestGravacaoScrapeRun:

    def test_execucao_eh_gravada_antes_do_commit(self):
        _, sessao = _persistir([_resultado([_vaga()])])

        chamadas = [c[0] for c in sessao.method_calls]
        assert chamadas.index("add") < chamadas.index("commit")
        assert sessao.add.call_count == 1  # apenas um ScrapeRun

    def test_erro_na_gravacao_faz_rollback_e_propaga(self):
        sessao = MagicMock()
        sessao.commit.side_effect = RuntimeError("falhou")

        with patch("repositories.bronze_repository.SessionLocal", MagicMock(return_value=sessao)):
            try:
                BronzeRepository.persistir_resultados(
                    [_resultado([_vaga()])], uuid4(), datetime.now(timezone.utc)
                )
                assert False, "deveria propagar o erro"
            except RuntimeError:
                pass

        sessao.rollback.assert_called_once()
        sessao.close.assert_called_once()


class TestPayload:

    def test_guarda_campos_do_scrape_run(self):
        vaga = _vaga(
            id_externo="1",
            data_publicacao=datetime(2026, 10, 30),
            qtd_posicoes=2,
            empresa=None,
        )

        total, sessao = _persistir([_resultado([vaga])])

        assert total == 1
        scrape_run = sessao.add.call_args[0][0]
        assert scrape_run.source == "Vagas.com"
        assert scrape_run.status == "success"
        assert scrape_run.pages_processed == 1
        assert scrape_run.jobs_found == 1
        assert scrape_run.error is None

    def test_fonte_sem_vagas_ainda_registra_a_execucao(self):
        total, sessao = _persistir([_resultado([])])

        assert total == 1  # ScrapeRun sempre é gravado, mesmo sem vagas
        assert sessao.add.call_count == 1  # só o ScrapeRun

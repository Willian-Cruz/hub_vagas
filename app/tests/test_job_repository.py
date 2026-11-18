"""
Testes unitários para JobRepository (nova responsabilidade: gravar o payload
bruto em `raw.job_observations`, sem normalização de negócio).

Estratégia:
    - SessionLocal mockado via patch — sem banco real.
    - Verifica que: raw_payload + payload_hash são gravados, a dedup é feita
      por (origem, id_externo) + payload_hash, a sessão é sempre fechada.

Execução: pytest tests/test_job_repository.py -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from repositories.job_repository import (
    JobRepository,
    DUPLICADA,
    ERRO,
    REVISADA,
    SALVA,
    _payload_hash,
    _raw_payload_de_vaga,
)
from schemas.job_schema import JobSchema


def _vaga(
    titulo="Engenheiro de Dados Jr",
    empresa="Empresa Teste",
    senioridade="Jr.",
    localizacao="sao paulo/sp",
    descricao="Experiência em Python e SQL.",
    link="https://www.vagas.com.br/vaga-1",
    origem="Vagas.com",
    id_externo=None,
):
    return JobSchema(
        titulo=titulo,
        empresa=empresa,
        senioridade=senioridade,
        localizacao=localizacao,
        descricao=descricao,
        link=link,
        origem=origem,
        id_externo=id_externo,
    )


def _hash_da(vaga):
    return _payload_hash(_raw_payload_de_vaga(vaga))


def _mock_session(fetchone_return=None):
    """
    Retorna (session_class, session).

    session.execute devolve um resultado cujo .fetchone() retorna
    `fetchone_return` (None = nenhuma observação anterior; tupla (hash,) =
    observação anterior com aquele hash).
    """
    session = MagicMock()
    resultado = MagicMock()
    resultado.fetchone.return_value = fetchone_return
    session.execute.return_value = resultado
    session_class = MagicMock(return_value=session)
    return session_class, session


def _params_da_ultima_execucao(session):
    """Params (dict) da última chamada a session.execute (o INSERT)."""
    return session.execute.call_args_list[-1].args[1]


class TestSalvaEDedup:

    def test_vaga_nova_retorna_salva_e_commita(self):
        session_class, session = _mock_session(fetchone_return=None)

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga()) == SALVA

        # SELECT de dedup + INSERT da nova observação
        assert session.execute.call_count == 2
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

    def test_payload_idêntico_retorna_duplicada_sem_commit(self):
        vaga = _vaga()
        session_class, session = _mock_session(fetchone_return=(_hash_da(vaga),))

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(vaga) == DUPLICADA

        # Apenas o SELECT de dedup; nenhum INSERT nem commit
        assert session.execute.call_count == 1
        session.commit.assert_not_called()
        session.rollback.assert_not_called()

    def test_payload_diferente_retorna_revisada(self):
        vaga = _vaga()
        outro_hash = "0" * 64
        session_class, session = _mock_session(fetchone_return=(outro_hash,))

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(vaga) == REVISADA

        session.commit.assert_called_once()

    def test_primeira_coleta_retorna_salva(self):
        session_class, session = _mock_session(fetchone_return=None)

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga()) == SALVA

        session.commit.assert_called_once()

    def test_id_externo_none_nao_impede_a_gravacao(self):
        session_class, session = _mock_session(fetchone_return=None)

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga(id_externo=None)) == SALVA

        session.commit.assert_called_once()

    def test_commit_falha_retorna_erro_e_faz_rollback(self):
        session_class, session = _mock_session(fetchone_return=None)
        session.commit.side_effect = Exception("conexão perdida")

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga()) == ERRO

        session.rollback.assert_called_once()


class TestSessao:

    def test_sessao_fechada_apos_sucesso(self):
        session_class, session = _mock_session(fetchone_return=None)

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        session.close.assert_called_once()

    def test_sessao_fechada_apos_erro(self):
        session_class, session = _mock_session(fetchone_return=None)
        session.commit.side_effect = Exception("falha")

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        session.close.assert_called_once()


class TestSemNormalizacao:

    def test_campos_brutos_sao_gravados_sem_normalizar(self):
        """senioridade/local/empresa ficam exatamente como vieram do scraper."""
        session_class, session = _mock_session(fetchone_return=None)

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(
                _vaga(
                    senioridade="Jr.",
                    localizacao="sao paulo/sp",
                    empresa="  Empresa Teste  ",
                )
            )

        params = _params_da_ultima_execucao(session)
        import json as _json

        payload = _json.loads(params["raw_payload"])
        assert payload["senioridade"] == "Jr."
        assert payload["localizacao"] == "sao paulo/sp"
        assert payload["empresa"] == "  Empresa Teste  "
        assert payload["titulo"] == "Engenheiro de Dados Jr"
        assert payload["link"] == "https://www.vagas.com.br/vaga-1"

    def test_raw_payload_inclui_fragmento_do_scraper_quando_houver(self):
        session_class, session = _mock_session(fetchone_return=None)
        vaga = _vaga()
        vaga.raw_payload = {"html_fragment": "<li>...</li>"}

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(vaga)

        import json as _json

        payload = _json.loads(_params_da_ultima_execucao(session)["raw_payload"])
        assert payload["_raw_payload_scraper"] == {"html_fragment": "<li>...</li>"}

    def test_collected_at_usa_datetime_now(self):
        momento_fixo = datetime(2026, 11, 17, 2, 0, 0, tzinfo=timezone.utc)
        session_class, session = _mock_session(fetchone_return=None)

        with patch("repositories.job_repository.SessionLocal", session_class):
            with patch("repositories.job_repository.datetime") as mock_dt:
                mock_dt.now.return_value = momento_fixo
                JobRepository.salvar(_vaga())

        params = _params_da_ultima_execucao(session)
        assert params["collected_at"] == momento_fixo


class TestPayloadHash:

    def test_hash_é_estável_para_o_mesmo_payload(self):
        p = {"titulo": "X", "link": "http://a"}
        assert _payload_hash(p) == _payload_hash(p)

    def test_hash_muda_quando_o_payload_muda(self):
        assert _payload_hash({"a": 1}) != _payload_hash({"a": 2})

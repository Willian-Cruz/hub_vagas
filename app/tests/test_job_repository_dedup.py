"""
Testes de deduplicação do JobRepository em `raw.job_observations`.

A dedup agora é feita por (origem, id_externo) + payload_hash: apenas
reinsere quando o payload bruto mudou.

Estratégia: SessionLocal mockado, sem banco real.

Execução: pytest tests/test_job_repository_dedup.py -v
"""
from unittest.mock import MagicMock, patch

from app.repositories.job_repository import (
    DUPLICADA,
    REVISADA,
    SALVA,
    JobRepository,
    _payload_hash,
    _raw_payload_de_vaga,
)
from app.schemas.job_schema import JobSchema


def _vaga(**campos):
    base = dict(
        titulo="Engenheiro de Dados Jr",
        empresa="Empresa Teste",
        senioridade="Jr.",
        localizacao="sao paulo/sp",
        descricao="Experiência em Python e SQL.",
        link="https://www.vagas.com.br/vagas/v1/engenheiro-de-dados",
        origem="Vagas.com",
        id_externo="1",
    )
    base.update(campos)
    return JobSchema(**base)


def _hash_da(vaga):
    return _payload_hash(_raw_payload_de_vaga(vaga))


def _mock_session(fetchone_return=None):
    session = MagicMock()
    resultado = MagicMock()
    resultado.fetchone.return_value = fetchone_return
    session.execute.return_value = resultado
    session_class = MagicMock(return_value=session)
    return session_class, session


class TestDedupPorHash:

    def test_mesmo_hash_para_mesma_vaga_e_duplicada(self):
        vaga = _vaga()
        session_class, session = _mock_session(fetchone_return=(_hash_da(vaga),))

        with patch("app.repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(vaga) == DUPLICADA

        assert session.execute.call_count == 1  # apenas o SELECT de dedup
        session.commit.assert_not_called()

    def test_hash_diferente_para_mesma_vaga_e_revisada(self):
        vaga = _vaga()
        session_class, session = _mock_session(fetchone_return=("hash-antigo",))

        with patch("app.repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(vaga) == REVISADA

        session.commit.assert_called_once()

    def test_sem_observacao_anterior_e_salva(self):
        session_class, session = _mock_session(fetchone_return=None)

        with patch("app.repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga()) == SALVA

        session.commit.assert_called_once()


class TestExecucao:

    def test_chama_insert_e_commit_ao_salvar(self):
        session_class, session = _mock_session(fetchone_return=None)

        with patch("app.repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        assert session.execute.call_count == 2  # SELECT + INSERT
        session.commit.assert_called_once()

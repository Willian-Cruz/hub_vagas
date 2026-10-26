"""
Testes unitários para JobRepository.

Estratégia:
    - SessionLocal mockado via patch — sem banco real.
    - Verifica que: normalização ocorre antes de salvar, data_coleta
      é sempre preenchida, duplicatas são ignoradas, a sessão é
      sempre fechada mesmo em caso de erro.

Execução: pytest tests/test_job_repository.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy.exc import IntegrityError

from repositories.job_repository import JobRepository, SALVA, DUPLICADA, ERRO
from database.job_model import Job
from schemas.job_schema import JobSchema


# ── Vaga padrão usada na maioria dos testes ──────────────────────────────────

def _vaga(
    titulo="Engenheiro de Dados Jr",
    empresa="Empresa Teste",
    senioridade="Jr.",
    localizacao="sao paulo/sp",
    descricao="Experiência em Python e SQL.",
    link="https://www.vagas.com.br/vaga-1",
    origem="Vagas.com",
):
    return JobSchema(
        titulo=titulo,
        empresa=empresa,
        senioridade=senioridade,
        localizacao=localizacao,
        descricao=descricao,
        link=link,
        origem=origem,
    )


# ── Helper: monta sessão mockada com comportamento configurável ──────────────

def _mock_session(duplicata=None):
    """
    Retorna (mock_session_class, mock_session).

    duplicata: objeto Job a retornar na busca de duplicata.
               None = nenhuma duplicata encontrada.
    """
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = duplicata
    session_class = MagicMock(return_value=session)
    return session_class, session


# ═══════════════════════════════════════════════════════════════
# TESTES — data_coleta
# ═══════════════════════════════════════════════════════════════

class TestDataColeta:

    def test_data_coleta_e_definida_ao_salvar(self):
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        job_salvo = session.add.call_args_list[0][0][0]
        assert job_salvo.data_coleta is not None

    def test_data_coleta_e_um_datetime(self):
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        job_salvo = session.add.call_args_list[0][0][0]
        assert isinstance(job_salvo.data_coleta, datetime)

    def test_data_coleta_usa_datetime_now(self):
        """Verifica que data_coleta vem de datetime.now()."""
        session_class, session = _mock_session()
        momento_fixo = datetime(2026, 6, 29, 12, 0, 0)

        with patch("repositories.job_repository.SessionLocal", session_class):
            with patch("repositories.job_repository.datetime") as mock_dt:
                mock_dt.now.return_value = momento_fixo
                JobRepository.salvar(_vaga())

        job_salvo = session.add.call_args_list[0][0][0]
        assert job_salvo.data_coleta == momento_fixo


# ═══════════════════════════════════════════════════════════════
# TESTES — normalização antes de salvar
# ═══════════════════════════════════════════════════════════════

class TestNormalizacao:

    def test_senioridade_normalizada(self):
        """'Jr.' deve virar 'Júnior' antes de persistir."""
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga(senioridade="Jr."))

        job_salvo = session.add.call_args_list[0][0][0]
        assert job_salvo.senioridade == "Júnior"

    def test_localizacao_normalizada(self):
        """'sao paulo/sp' deve ter o separador normalizado para ' - '."""
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga(localizacao="sao paulo/sp"))

        job_salvo = session.add.call_args_list[0][0][0]
        # O NormalizeService converte a barra para ' - ' e aplica title case,
        # mas não adiciona acentos ("sao" → "Sao", não "São")
        assert " - " in job_salvo.localizacao
        assert "SP" in job_salvo.localizacao

    def test_empresa_normalizada(self):
        """Espaços extras na empresa devem ser removidos."""
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga(empresa="  Empresa Teste  "))

        job_salvo = session.add.call_args_list[0][0][0]
        assert job_salvo.empresa == "Empresa Teste"

    def test_titulo_preservado_sem_alteracao(self):
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga(titulo="Engenheiro de Dados Jr"))

        job_salvo = session.add.call_args_list[0][0][0]
        assert job_salvo.titulo == "Engenheiro de Dados Jr"

    def test_origem_preservada_sem_alteracao(self):
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga(origem="Vagas.com"))

        job_salvo = session.add.call_args_list[0][0][0]
        assert job_salvo.origem == "Vagas.com"

    def test_link_preservado_sem_alteracao(self):
        session_class, session = _mock_session()
        link = "https://www.vagas.com.br/vaga-123"

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga(link=link))

        job_salvo = session.add.call_args_list[0][0][0]
        assert job_salvo.link == link


# ═══════════════════════════════════════════════════════════════
# TESTES — deduplicação por link
# ═══════════════════════════════════════════════════════════════

class TestDeduplicacao:

    def test_vaga_duplicada_nao_e_salva(self):
        """Se o link já existe no banco, a vaga deve ser ignorada."""
        job_existente = MagicMock(spec=Job)
        session_class, session = _mock_session(duplicata=job_existente)

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        session.add.assert_not_called()
        session.commit.assert_not_called()

    def test_vaga_nova_e_salva(self):
        """Se o link não existe, add e commit devem ser chamados."""
        session_class, session = _mock_session(duplicata=None)

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        session.commit.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# TESTES — gerenciamento da sessão
# ═══════════════════════════════════════════════════════════════

class TestGerenciamentoDeSessao:

    def test_sessao_e_fechada_apos_sucesso(self):
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        session.close.assert_called_once()

    def test_sessao_e_fechada_apos_erro(self):
        """Mesmo quando o commit lança exceção, a sessão deve ser fechada."""
        session_class, session = _mock_session()
        session.commit.side_effect = Exception("falha no banco")

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        session.close.assert_called_once()

    def test_rollback_e_chamado_apos_erro(self):
        session_class, session = _mock_session()
        session.commit.side_effect = Exception("falha no banco")

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        session.rollback.assert_called_once()

    def test_erro_nao_propaga_excecao(self):
        """Falha interna não deve subir como exceção não tratada."""
        session_class, session = _mock_session()
        session.commit.side_effect = Exception("falha no banco")

        with patch("repositories.job_repository.SessionLocal", session_class):
            try:
                JobRepository.salvar(_vaga())
            except Exception:
                pytest.fail("JobRepository.salvar() não deveria propagar exceção")


# ═══════════════════════════════════════════════════════════════
# TESTES — objeto Job criado com campos corretos
# ═══════════════════════════════════════════════════════════════

class TestJobCriado:

    def test_objeto_salvo_e_instancia_de_job(self):
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        job_salvo = session.add.call_args_list[0][0][0]
        assert isinstance(job_salvo, Job)

    def test_job_tem_todos_os_campos_preenchidos(self):
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            JobRepository.salvar(_vaga())

        job = session.add.call_args_list[0][0][0]
        assert job.titulo is not None
        assert job.empresa is not None
        assert job.senioridade is not None
        assert job.localizacao is not None
        assert job.link is not None
        assert job.origem is not None
        assert job.data_coleta is not None


# ═══════════════════════════════════════════════════════════════
# TESTES — valor de retorno (contrato com o PipelineService)
# ═══════════════════════════════════════════════════════════════

class TestRetorno:
    """
    O PipelineService conta salvas, duplicadas e erros a partir do valor
    devolvido por salvar(). Se salvar() devolver None, toda vaga vira "erro".
    """

    def test_vaga_nova_retorna_salva(self):
        session_class, session = _mock_session()

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga()) == SALVA

    def test_vaga_existente_retorna_duplicada(self):
        job_existente = MagicMock(spec=Job)
        session_class, session = _mock_session(duplicata=job_existente)

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga()) == DUPLICADA

    def test_violacao_de_unicidade_no_commit_retorna_duplicada(self):
        """Corrida entre dois processos: a restrição UNIQUE do link decide."""
        session_class, session = _mock_session()
        session.commit.side_effect = IntegrityError("INSERT", {}, Exception("link duplicado"))

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga()) == DUPLICADA

        session.rollback.assert_called_once()

    def test_erro_inesperado_retorna_erro(self):
        session_class, session = _mock_session()
        session.commit.side_effect = Exception("conexão perdida")

        with patch("repositories.job_repository.SessionLocal", session_class):
            assert JobRepository.salvar(_vaga()) == ERRO

        session.rollback.assert_called_once()

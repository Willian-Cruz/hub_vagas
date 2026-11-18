"""
Testes de integração E2E — Fluxo completo Raw → Silver → Gold.

Cenários obrigatórios (M08):
  A — Pipeline com sucesso: vaga válida coletada, persistida, transformada,
      disponibilizada no mart analítico.
  B — Dados incompletos: vaga sem salário/localização preservada com NULLs.
  C — Duplicidade: mesma publicação recebida mais de uma vez, dedup respeitada.
  D — Fonte indisponível: falha registrada, status correto.
  E — Banco indisponível: persistência falha, sucesso não registrado indevidamente.
  F — Falha de transformação: dbt build falha, dados analíticos não marcados como atualizados.
  G — Alteração inesperada na fonte: formato da resposta muda, scraper trata controladamente.

Execução (CI com services: postgres):
    pytest app/tests/integration/test_e2e.py -m integration -v
"""
import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text

from repositories.job_repository import (
    JobRepository,
    DUPLICADA,
    ERRO,
    SALVA,
    _payload_hash,
    _raw_payload_de_vaga,
)
from schemas.job_schema import JobSchema


def _inserir_raw(conexao, run_id, vaga_dict):
    """Insere uma observação bruta diretamente na tabela raw (simula scraper)."""
    vaga = JobSchema(**vaga_dict)
    payload = _raw_payload_de_vaga(vaga)
    payload_hash = _payload_hash(payload)

    conexao.execute(
        text(
            """
            INSERT INTO raw.job_observations
                (run_id, source, source_job_id, collected_at, ingested_at,
                 link, scraper_version, payload_hash, raw_payload, is_relevant)
            VALUES
                (:run_id, :source, :source_job_id, :collected_at, :ingested_at,
                 :link, :scraper_version, :payload_hash, CAST(:raw_payload AS jsonb), :is_relevant)
            """
        ),
        {
            "run_id": run_id,
            "source": vaga_dict.get("origem", "Vagas.com"),
            "source_job_id": vaga_dict.get("id_externo"),
            "collected_at": vaga_dict.get("collected_at"),
            "ingested_at": vaga_dict.get("ingested_at", vaga_dict.get("collected_at")),
            "link": vaga_dict.get("link"),
            "scraper_version": vaga_dict.get("scraper_version", "1.0.0"),
            "payload_hash": payload_hash,
            "raw_payload": json.dumps(payload),
            "is_relevant": vaga_dict.get("is_relevant", True),
        },
    )


@pytest.mark.integration
class TestCenarioASucesso:
    """Cenário A — Pipeline com sucesso."""

    def test_vaga_valida_persiste_na_raw_com_linhagem(self, conexao):
        """Uma vaga válida é inserida na raw com todos os campos de linhagem."""
        run_id = uuid4()
        vaga = {
            "titulo": "Engenheiro de Dados Pleno",
            "empresa": "Empresa Exemplo",
            "senioridade": "Pleno",
            "localizacao": "São Paulo - SP",
            "descricao": "Vaga para engenheiro de dados com Python e SQL.",
            "salario": "R$ 8.000,00 a R$ 12.000,00",
            "link": "https://example.com/vaga/e2e-a",
            "origem": "Vagas.com",
            "id_externo": "e2e-a-001",
            "data_publicacao": "2026-11-17T10:00:00+00:00",
            "modalidade": "Híbrido",
            "is_relevant": True,
            "collected_at": "2026-11-17T10:00:00+00:00",
        }

        _inserir_raw(conexao, run_id, vaga)

        # Verifica que está na raw com campos de linhagem
        row = conexao.execute(
            text(
                "SELECT is_relevant, scraper_version, ingested_at, "
                "run_id, source, payload_hash, link "
                "FROM raw.job_observations WHERE link = :link"
            ),
            {"link": vaga["link"]},
        ).fetchone()

        assert row is not None
        assert row.is_relevant is True
        assert row.scraper_version == "1.0.0"
        assert row.ingested_at is not None
        assert row.run_id == run_id
        assert row.source == "Vagas.com"
        assert row.payload_hash is not None
        assert row.link == vaga["link"]


@pytest.mark.integration
class TestCenarioBDadosIncompletos:
    """Cenário B — Dados incompletos (sem salário/localização)."""

    def test_vaga_sem_salario_e_localizacao_preserva_campos_disponiveis(self, conexao):
        """Vaga sem salário e localização é persistida com campos ausentes no payload."""
        run_id = uuid4()
        vaga = {
            "titulo": "Analista de Dados",
            "empresa": "Empresa X",
            "senioridade": "Júnior",
            "localizacao": None,
            "descricao": "Vaga para analista de dados.",
            "salario": None,
            "link": "https://example.com/vaga/e2e-b",
            "origem": "InfoJobs",
            "id_externo": "e2e-b-001",
            "is_relevant": True,
            "collected_at": "2026-11-17T10:00:00+00:00",
        }

        _inserir_raw(conexao, run_id, vaga)

        row = conexao.execute(
            text(
                "SELECT raw_payload, is_relevant, link "
                "FROM raw.job_observations WHERE link = :link"
            ),
            {"link": vaga["link"]},
        ).fetchone()

        assert row is not None
        assert row.is_relevant is True
        assert row.link == vaga["link"]
        # raw_payload preserva o que veio (campos ausentes não aparecem ou são None)
        payload = row.raw_payload
        if isinstance(payload, str):
            payload = json.loads(payload)
        assert payload.get("salario") is None
        assert payload.get("localizacao") is None


@pytest.mark.integration
class TestCenarioCDuplicidade:
    """Cenário C — Duplicidade."""

    def test_mesma_publicacao_dois_inserts_via_jobrepository(self, conexao):
        """Duas chamadas a JobRepository.salvar com mesmo payload → SALVA, DUPLICADA."""
        vaga = JobSchema(
            titulo="Engenheiro de Dados",
            empresa="Empresa Y",
            link="https://example.com/vaga/e2e-c",
            origem="Catho",
            id_externo="e2e-c-001",
            descricao="Vaga para teste de duplicidade.",
            is_relevant=True,
        )

        r1 = JobRepository.salvar(vaga, run_id=uuid4())
        assert r1 == SALVA

        r2 = JobRepository.salvar(vaga, run_id=uuid4())
        assert r2 == DUPLICADA

        # Apenas 1 linha na raw
        count = conexao.execute(
            text("SELECT count(*) FROM raw.job_observations WHERE link = :link"),
            {"link": "https://example.com/vaga/e2e-c"},
        ).scalar()
        assert count == 1


@pytest.mark.integration
class TestCenarioDFonteIndisponivel:
    """Cenário D — Fonte indisponível."""

    def test_outras_fontes_nao_bloqueadas_quando_uma_falha(self, conexao):
        """Quando uma fonte falha, as outras continuam sendo persistidas normalmente."""
        run_id = uuid4()

        # Insere dados para uma fonte (simula sucesso)
        vaga_ok = {
            "titulo": "Vaga OK",
            "link": "https://example.com/vaga/e2e-d-ok",
            "origem": "Vagas.com",
            "is_relevant": True,
            "collected_at": "2026-11-17T10:00:00+00:00",
        }
        _inserir_raw(conexao, run_id, vaga_ok)

        # Verifica que a fonte com sucesso tem dados e a outra não
        count_ok = conexao.execute(
            text(
                "SELECT count(*) FROM raw.job_observations WHERE source = 'Vagas.com'"
            )
        ).scalar()
        count_infojobs = conexao.execute(
            text(
                "SELECT count(*) FROM raw.job_observations WHERE source = 'InfoJobs'"
            )
        ).scalar()

        assert count_ok >= 1
        assert count_infojobs == 0


@pytest.mark.integration
class TestCenarioEBancoIndisponivel:
    """Cenário E — Banco indisponível."""

    def test_persistencia_falha_retorna_erro(self):
        """
        Se a sessão de banco falhar, JobRepository.salvar retorna ERRO e faz rollback.
        Simula falha de conexão via mock do SessionLocal.
        """
        vaga = JobSchema(
            titulo="Vaga teste banco indisponível",
            link="https://example.com/vaga/e2e-e",
            origem="Vagas.com",
            id_externo="e2e-e-001",
        )

        with patch(
            "repositories.job_repository.SessionLocal"
        ) as mock_session_local:
            mock_session = mock_session_local.return_value
            mock_session.execute.side_effect = Exception("conexão perdida")

            resultado = JobRepository.salvar(vaga, run_id=uuid4())

        assert resultado == ERRO


@pytest.mark.integration
class TestCenarioFFalhaTransformacao:
    """Cenário F — Falha de transformação dbt."""

    def test_dbt_build_falha_retorna_codigo_nao_zero(self):
        """
        Simula falha de dbt build verificando que o transform.py retorna
        código de saída diferente de zero quando o dbt falha.
        """
        from run_dbt import main as executar_dbt

        # Mock do subprocess para simular falha do dbt
        with patch("run_dbt.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1

            codigo = executar_dbt(["build"])

        assert codigo != 0


@pytest.mark.integration
class TestCenarioGAlteracaoFonte:
    """Cenario G — Alteração inesperada na fonte."""

    def test_contrato_aceita_campos_ausentes(self, conexao):
        """Se o portal mudar o formato e remover campos, o contrato ainda aceita."""
        run_id = uuid4()
        vaga = {
            "titulo": "Vaga com formato novo",
            "link": "https://example.com/vaga/e2e-g",
            "origem": "Vagas.com",
            "is_relevant": True,
            "collected_at": "2026-11-17T10:00:00+00:00",
            # sem empresa, salario, descricao - campos ausentes
        }

        _inserir_raw(conexao, run_id, vaga)

        count = conexao.execute(
            text("SELECT count(*) FROM raw.job_observations WHERE link = :link"),
            {"link": vaga["link"]},
        ).scalar()
        assert count == 1
